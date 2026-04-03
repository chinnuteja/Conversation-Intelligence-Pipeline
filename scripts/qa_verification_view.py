"""
Standalone QA: verify worst-conversation view matches report + all_evaluations + messages.

Run from repo root: python scripts/qa_verification_view.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "output"
DATA = ROOT / "data"

_FLAG_SCORE_MAX = 3.99
_MIN_EVIDENCE_LEN = 10


def _norm_text(s: str) -> str:
    return " ".join((s or "").lower().split())


def _strip_user_prefix(quote: str) -> str:
    q = quote.strip()
    m = re.match(r"^user\s+(asked|said|wrote)\s*:\s*", q, re.I)
    if m:
        return q[m.end() :].strip()
    return q


def collect_dimension_flags(ev: dict | None) -> list[dict]:
    if not ev:
        return []
    out: list[dict] = []
    for key, d in (ev.get("dimensions") or {}).items():
        if not isinstance(d, dict):
            continue
        score = float(d.get("score", 5))
        issues = [x for x in (d.get("issues") or []) if isinstance(x, str) and x.strip()]
        evidence = [x for x in (d.get("evidence") or []) if isinstance(x, str) and x.strip()]
        weak = score <= _FLAG_SCORE_MAX
        if not weak and not issues and not evidence:
            continue
        out.append(
            {
                "key": key,
                "label": key.replace("_", " ").title(),
                "score": score,
                "issues": issues,
                "evidence": evidence,
            }
        )
    return out


def match_flags_to_message(msg_text: str, flags: list[dict]) -> list[str]:
    nmsg = _norm_text(msg_text)
    if len(nmsg) < 5:
        return []
    matched: list[str] = []
    seen: set[str] = set()
    for row in flags:
        key = row["key"]
        for quote in row["evidence"]:
            variants = {_norm_text(quote), _norm_text(_strip_user_prefix(quote))}
            variants.discard("")
            for v in variants:
                if len(v) < _MIN_EVIDENCE_LEN:
                    continue
                if v in nmsg or (len(nmsg) >= _MIN_EVIDENCE_LEN and nmsg in v):
                    if key not in seen:
                        seen.add(key)
                        matched.append(f"{row['label']} (score {row['score']:.1f})")
                    break
    return matched


def load_messages_index() -> dict[str, list[dict]]:
    path = DATA / "messages.json"
    if not path.is_file():
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    idx: dict[str, list[dict]] = {}
    for m in raw:
        cid = str(m.get("conversationId", ""))
        idx.setdefault(cid, []).append(
            {
                "sender": m.get("sender"),
                "text": (m.get("text") or "")[:8000],
                "messageType": m.get("messageType", "text"),
                "timestamp": str(m.get("timestamp", "")),
            }
        )
    for cid in idx:
        idx[cid].sort(key=lambda x: x["timestamp"])
    return idx


def main() -> int:
    report_path = OUTPUT / "report.json"
    eval_path = OUTPUT / "all_evaluations.json"
    if not report_path.is_file():
        print("FAIL: missing", report_path)
        return 1
    report = json.loads(report_path.read_text(encoding="utf-8"))
    worst = report.get("worst_conversations") or []
    if not worst:
        print("FAIL: report has no worst_conversations")
        return 1

    all_evals = []
    if eval_path.is_file():
        all_evals = json.loads(eval_path.read_text(encoding="utf-8"))
    eval_by_id = {str(e.get("conversation_id", "")): e for e in all_evals if e.get("conversation_id")}

    msg_index = load_messages_index()
    if not msg_index:
        print("WARN: no data/messages.json — transcript column will be empty in dashboard")

    print("=== QA: verification view (dashboard logic) ===\n")

    if not all_evals:
        print("WARN: missing all_evaluations.json — dashboard will not merge full dimensions for some rows.\n")

    sample = worst[:8]
    problems: list[str] = []
    ok_transcripts = 0
    ok_text_transcripts = 0
    orphan_evidence_total = 0
    matched_evidence_total = 0
    highlight_checks_ok = 0
    highlight_checks_run = 0

    for ev in sample:
        cid = str(ev.get("conversation_id", ""))
        merged = eval_by_id.get(cid) if eval_by_id.get(cid, {}).get("dimensions") else ev
        flags = collect_dimension_flags(merged)
        transcript = msg_index.get(cid, [])
        text_msgs = [m for m in transcript if m.get("messageType") == "text"]

        print(f"Conversation {cid[:12]}…  score={ev.get('overall_score')}  flags={len(flags)}  text_msgs={len(text_msgs)}")

        if transcript:
            ok_transcripts += 1
        else:
            problems.append(f"{cid[:12]}…: no transcript in messages.json")
        if text_msgs:
            ok_text_transcripts += 1
        elif transcript:
            problems.append(
                f"{cid[:12]}…: messages exist but no text-type rows — dashboard transcript column may look empty"
            )

        if eval_by_id.get(cid) is None and all_evals:
            problems.append(f"{cid[:12]}…: not found in all_evaluations.json (merge falls back to report row)")

        # Evidence that should appear in chat: check substring match in any text message
        for row in flags:
            for quote in row["evidence"]:
                v = _norm_text(quote)
                v2 = _norm_text(_strip_user_prefix(quote))
                if len(v) < _MIN_EVIDENCE_LEN and len(v2) < _MIN_EVIDENCE_LEN:
                    continue
                found = False
                for m in text_msgs:
                    t = _norm_text(m.get("text") or "")
                    for cand in (x for x in (v, v2) if len(x) >= _MIN_EVIDENCE_LEN):
                        if cand in t or (len(t) >= _MIN_EVIDENCE_LEN and t in cand):
                            found = True
                            break
                    if found:
                        break
                if found:
                    matched_evidence_total += 1
                else:
                    orphan_evidence_total += 1
                    print(f"  · Orphan evidence ({row['key']}): {quote[:80]}…" if len(quote) > 80 else f"  · Orphan evidence ({row['key']}): {quote}")

        # Highlight consistency: if match_flags_to_message says hit, substring must hold
        for m in text_msgs:
            text = m.get("text") or ""
            hits = match_flags_to_message(text, flags)
            if not hits:
                continue
            highlight_checks_run += 1
            nmsg = _norm_text(text)
            ok = False
            for row in flags:
                for quote in row["evidence"]:
                    for cand in {_norm_text(quote), _norm_text(_strip_user_prefix(quote))}:
                        if len(cand) >= _MIN_EVIDENCE_LEN and (
                            cand in nmsg or (len(nmsg) >= _MIN_EVIDENCE_LEN and nmsg in cand)
                        ):
                            ok = True
                            break
            if ok:
                highlight_checks_ok += 1
            else:
                problems.append(f"{cid[:12]}…: matcher returned hits but substring check failed (bug)")

        print()

    print("--- Summary ---")
    print(f"Sample size: {len(sample)} worst conversations")
    print(f"Rows in messages.json: {ok_transcripts}/{len(sample)}")
    print(f"With at least one text message: {ok_text_transcripts}/{len(sample)}")
    print(f"Evidence quotes (long enough) matched to some message: {matched_evidence_total}")
    print(f"Evidence quotes with no verbatim match in transcript: {orphan_evidence_total}")
    print(
        f"Highlight logic self-check: {highlight_checks_ok}/{highlight_checks_run} messages with highlights passed substring audit"
    )

    if problems:
        print("\nIssues:")
        for p in problems:
            print(" -", p)
    else:
        print("\nNo structural issues in sample.")

    # Verdict
    print("\n--- Verdict ---")
    if ok_transcripts < len(sample) * 0.5:
        print("DATA: Many conversations lack transcripts — fix data path or IDs before demo.")
        return 2
    if not all_evals:
        print("OK for transcript layout, but add all_evaluations.json for full dimension flags.")
        return 0
    if orphan_evidence_total > matched_evidence_total and matched_evidence_total > 0:
        print(
            "OK: Pipeline is consistent; many LLM evidence strings are paraphrases — "
            "highlights will be sparse; left panel still shows quotes for manual check."
        )
    elif orphan_evidence_total == 0 and matched_evidence_total > 0:
        print("GOOD: Evidence quotes in sample usually appear verbatim in messages — highlights should work well.")
    else:
        print("OK: Review orphan lines above — expected when model paraphrases.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
