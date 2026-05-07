"""
Minimal Streamlit Dashboard — Conversation Review Feed
Focuses entirely on reviewing bad interactions per brand.
"""

from __future__ import annotations

import html
import re
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dashboard.cached_loaders import (
    _output_cache_signature,
    load_all_evaluations,
    load_messages_index,
    load_report,
)
from src.stage1_ingest import parse_agent_message

OUTPUT_DIR = ROOT / "output"
DATA_DIR = ROOT / "data"

# Human-readable labels for backend dimension keys (snake_case → executive UI)
DIMENSION_LABELS: dict[str, str] = {
    "factual_accuracy": "Factual Accuracy",
    "hallucination_check": "Hallucination Check",
    "policy_compliance": "Policy Compliance",
    "tone_and_helpfulness": "Tone & Helpfulness",
    "user_satisfaction_signals": "User Satisfaction",
    "cross_brand_check": "Cross-Brand Check",
}


def humanize_dimension(key: str) -> str:
    return DIMENSION_LABELS.get(key, key.replace("_", " ").title())


BADGE_LABEL: dict[str, str] = {
    "user_satisfaction_signals": "FRUSTRATION",
    "tone_and_helpfulness": "UNHELPFUL",
    "hallucination_check": "HALLUCINATION",
    "factual_accuracy": "WRONG INFO",
    "cross_brand_check": "WRONG BRAND",
    "policy_compliance": "POLICY ISSUE",
}

ASSISTANT_DIMS: set[str] = {
    "tone_and_helpfulness",
    "policy_compliance",
    "hallucination_check",
    "cross_brand_check",
    "factual_accuracy",
}
USER_DIMS: set[str] = {"user_satisfaction_signals"}


st.set_page_config(
    page_title="Conversation Review",
    layout="wide",
    page_icon="🔍",
    initial_sidebar_state="expanded",
)

# ── World-class CSS ──
CUSTOM_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    .block-container { padding-top: 1rem; padding-bottom: 2rem; max-width: 900px; }

    /* ── Compact Executive Verdict ── */
    .eval-summary {
        border: 1px solid rgba(255, 255, 255, 0.12);
        border-radius: 6px;
        padding: 5px 7px;
        margin: 3px 0 7px 0;
        max-width: min(100%, 620px);
        box-sizing: border-box;
        background: rgba(255, 255, 255, 0.025);
        font-family: 'Inter', sans-serif;
    }
    .eval-meta {
        display: flex;
        flex-wrap: wrap;
        gap: 4px;
        margin-bottom: 4px;
    }
    .eval-chip {
        font-size: 0.56rem;
        font-weight: 800;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        padding: 1px 6px;
        border-radius: 999px;
        color: #bbb;
        border: 1px solid rgba(255, 255, 255, 0.12);
        background: rgba(255, 255, 255, 0.04);
    }
    .eval-chip.score-bad {
        color: #ffb3b3;
        border-color: rgba(255, 107, 107, 0.35);
        background: rgba(255, 107, 107, 0.08);
    }
    .eval-chip.score-ok {
        color: #b7f7c2;
        border-color: rgba(0, 184, 148, 0.35);
        background: rgba(0, 184, 148, 0.08);
    }
    .eval-alert {
        font-size: 0.68rem;
        line-height: 1.45;
        padding: 1px 0;
        margin: 1px 0;
        color: rgba(255, 255, 255, 0.55);
    }
    .eval-alert::before { content: "· "; }
    .eval-alert.success { color: rgba(180, 240, 195, 0.7); }
    /* Native <details> — works inside Streamlit expanders (no nested st.expander). */
    .eval-scratch-details {
        margin-top: 8px;
        max-width: min(100%, 620px);
        box-sizing: border-box;
        font-family: 'Inter', sans-serif;
        font-size: 0.69rem;
        line-height: 1.34;
        color: rgba(255, 255, 255, 0.86);
    }
    .eval-scratch-details summary {
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 10px;
        padding: 7px 11px;
        border-radius: 8px;
        border: 1px solid rgba(255, 255, 255, 0.22);
        background: rgba(255, 255, 255, 0.07);
        font-weight: 700;
        font-size: 0.72rem;
        letter-spacing: 0.02em;
        color: rgba(255, 255, 255, 0.95);
        user-select: none;
        list-style: none;
        transition: background 0.15s ease, border-color 0.15s ease;
    }
    .eval-scratch-details summary:hover {
        background: rgba(255, 255, 255, 0.11);
        border-color: rgba(255, 255, 255, 0.32);
    }
    .eval-scratch-details summary::-webkit-details-marker { display: none; }
    /* Chevron: reads as a dropdown control */
    .eval-scratch-details summary::after {
        content: "";
        flex-shrink: 0;
        width: 0;
        height: 0;
        border-left: 5px solid transparent;
        border-right: 5px solid transparent;
        border-top: 6px solid rgba(255, 255, 255, 0.65);
        margin-left: 4px;
        transition: transform 0.18s ease;
    }
    .eval-scratch-details[open] summary::after {
        transform: rotate(180deg);
    }
    .eval-scratch-details[open] summary {
        border-radius: 8px 8px 0 0;
        border-bottom-color: transparent;
    }
    .eval-scratch-body {
        margin-top: 0;
        padding: 8px 11px 10px 11px;
        border-radius: 0 0 8px 8px;
        border: 1px solid rgba(255, 255, 255, 0.22);
        border-top: 1px dashed rgba(255, 255, 255, 0.12);
        background: rgba(0, 0, 0, 0.18);
    }
    /* ── Chat Thread ── */
    .chat-thread {
        display: flex;
        flex-direction: column;
        gap: 6px;
        padding: 8px 0;
    }

    /* ── Single Message Row ── */
    .msg-row {
        display: flex;
        flex-direction: column;
        padding: 0 4px;
    }
    .msg-row.left  { align-items: flex-start; }
    .msg-row.right { align-items: flex-end; }

    /* ── Role Tag ── */
    .role-tag {
        font-family: 'Inter', sans-serif;
        font-size: 0.6rem;
        font-weight: 700;
        letter-spacing: 0.08em;
        color: #999;
        margin-bottom: 3px;
        padding-left: 6px;
        padding-right: 6px;
    }

    /* ── Message Card (bubble + its badges grouped together) ── */
    .msg-card {
        max-width: 75%;
        display: flex;
        flex-direction: column;
        gap: 4px;
    }

    /* ── Chat Bubble ── */
    .bubble {
        padding: 10px 14px;
        border-radius: 16px;
        font-family: 'Inter', sans-serif;
        font-size: 0.88rem;
        line-height: 1.55;
        color: #1a1a2e;
        word-wrap: break-word;
        background: #f8f9fa;
        border: 1px solid #e0e0e0;
    }

    /* ── Turn Verdict Bar (represents the whole user+agent exchange) ── */
    .turn-verdict {
        display: flex;
        align-items: center;
        gap: 6px;
        flex-wrap: wrap;
        padding: 5px 14px;
        margin: 2px 0 10px 0;
        border-radius: 6px;
        background: rgba(214, 48, 49, 0.06);
        border: 1px dashed rgba(214, 48, 49, 0.22);
    }
    .turn-verdict.amber {
        background: rgba(240, 165, 0, 0.06);
        border-color: rgba(240, 165, 0, 0.22);
    }
    .verdict-badge {
        font-family: 'Inter', sans-serif;
        font-size: 0.60rem;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        padding: 2px 7px;
        border-radius: 4px;
        white-space: nowrap;
    }
    .verdict-badge.red {
        color: #d63031;
        background: rgba(214, 48, 49, 0.10);
        border: 1px solid rgba(214, 48, 49, 0.30);
    }
    .verdict-badge.amber {
        color: #e17055;
        background: rgba(225, 112, 85, 0.10);
        border: 1px solid rgba(225, 112, 85, 0.30);
    }
    .verdict-reason {
        font-family: 'Inter', sans-serif;
        font-size: 0.73rem;
        color: #888;
        line-height: 1.4;
    }

    /* ── Group Divider ── */
    .pattern-header {
        font-family: 'Inter', sans-serif;
        font-size: 0.85rem;
        font-weight: 800;
        color: #d63031;
        letter-spacing: 0.03em;
        padding: 16px 0 6px 0;
        border-bottom: 2px solid #f0f0f0;
        margin-bottom: 8px;
    }

    .pattern-count {
        font-weight: 500;
        color: #999;
        font-size: 0.78rem;
    }

    /* Links inside bubbles */
    .bubble a { color: #0984e3; text-decoration: underline; }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# ── Text Processing ──

_FLAG_SCORE_MAX = 3.99
_MIN_EVIDENCE_LEN = 10
_ELLIPSIS_RE = re.compile(r"(?:\.{3,}|…)")


def _norm_text(s: str) -> str:
    return " ".join((s or "").lower().split())


def _strip_user_prefix(quote: str) -> str:
    q = quote.strip()
    m = re.match(r"^user\s+(asked|said|wrote)\s*:\s*", q, re.I)
    if m:
        return q[m.end() :].strip()
    return q


def _is_reference_evidence(quote: str) -> bool:
    """Skip non-transcript references so catalog facts do not get pinned to chat turns."""
    q = (quote or "").strip().lower()
    reference_markers = (
        "product catalog",
        "catalog faq",
        "behavioral signal",
        "event count",
        "add_to_cart",
    )
    return any(marker in q for marker in reference_markers)


def _quoted_phrases(text: str) -> list[str]:
    phrases: list[str] = []
    for single_quoted, double_quoted in re.findall(r"'([^']{4,})'|\"([^\"]{4,})\"", text or ""):
        phrase = single_quoted or double_quoted
        if phrase and phrase.strip():
            phrases.append(phrase.strip())
    return phrases


def _clean_evidence_segment(segment: str) -> str:
    s = (segment or "").strip()
    s = re.sub(r"^\s*(?:quoted\s+)?(?:message|reply|response|text)\s*:\s*", "", s, flags=re.I)
    s = s.strip(" \t\r\n\"'")
    return s


def _evidence_segments_for_role(quote: str, role: str) -> list[str]:
    """Extract exact evidence snippets that belong to one chat bubble role."""
    if _is_reference_evidence(quote):
        return []

    current_role: str | None = None
    buckets: list[tuple[str, list[str]]] = []

    for line in (quote or "").splitlines():
        m = re.match(r"^\s*\[?\s*(CUSTOMER|USER|ASSISTANT|BOT)\s*\]?\s*:\s*(.*)$", line, re.I)
        if m:
            current_role = "User" if m.group(1).upper() in {"CUSTOMER", "USER"} else "Assistant"
            buckets.append((current_role, [m.group(2).strip()]))
        elif current_role and buckets:
            buckets[-1][1].append(line.strip())

    role_labeled_segments = [
        _clean_evidence_segment(" ".join(part for part in parts if part))
        for segment_role, parts in buckets
        if segment_role == role
    ]
    if role_labeled_segments:
        return [s for s in role_labeled_segments if s]

    q = (quote or "").strip()
    q_lower = q.lower()

    if role == "Assistant" and re.search(r"\b(assistant|bot)\b", q_lower):
        phrases = _quoted_phrases(q)
        if phrases:
            return [_clean_evidence_segment(p) for p in phrases]
        cleaned = re.sub(r"^\s*(the\s+)?(assistant|bot)\s+(listed|sent|said|responded|replied)\s*:?\s*", "", q, flags=re.I)
        cleaned = _clean_evidence_segment(cleaned)
        return [cleaned] if cleaned and cleaned != q else []

    if role == "User" and re.search(r"\b(user|customer)\b", q_lower):
        phrases = _quoted_phrases(q)
        if phrases:
            return [_clean_evidence_segment(p) for p in phrases]
        cleaned = re.sub(r"^\s*(the\s+)?(user|customer)\s+(asked|said|wrote|sent)\s*:?\s*", "", q, flags=re.I)
        cleaned = _clean_evidence_segment(cleaned)
        return [cleaned] if cleaned and cleaned != q else []

    # If the evaluator did not role-label the evidence, only use it as-is.
    if not re.search(r"\[?\s*(CUSTOMER|USER|ASSISTANT|BOT)\s*\]?\s*:", quote, re.I):
        stripped = _strip_user_prefix(quote) if role == "User" else quote.strip()
        stripped = _clean_evidence_segment(stripped)
        return [stripped] if stripped else []

    return []


def _evidence_matches_message(evidence_norm: str, message_norm: str) -> bool:
    """True only when evidence text is present in this bubble, including safe truncation."""
    if len(evidence_norm) < _MIN_EVIDENCE_LEN:
        return False
    if evidence_norm in message_norm:
        return True

    # LLM evidence often uses "..." to abbreviate the exact bubble. Require every
    # meaningful chunk to appear in the same message; never match across turns.
    chunks = [
        chunk.strip()
        for chunk in _ELLIPSIS_RE.split(evidence_norm)
        if len(chunk.strip()) >= _MIN_EVIDENCE_LEN
    ]
    if not chunks:
        return False
    return all(chunk in message_norm for chunk in chunks)


def _md_to_html(text: str) -> str:
    """Convert basic markdown links [text](url) to HTML <a> tags and **bold** to <strong>."""
    # Bold
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    # Links
    text = re.sub(r'\[(.+?)\]\((.+?)\)', r'<a href="\2" target="_blank">\1</a>', text)
    return text


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
                "label": humanize_dimension(key),
                "score": score,
                "issues": issues,
                "evidence": evidence,
            }
        )
    return out


def match_flags_to_message(msg_text: str, role: str, flags: list[dict]) -> list[dict]:
    """Return flags whose role-specific evidence quote is found in this exact message."""
    nmsg = _norm_text(msg_text)
    if len(nmsg) < 5:
        return []
    matched: list[dict] = []
    seen: set[str] = set()
    for row in flags:
        key = row["key"]
        for quote in row["evidence"]:
            variants = {_norm_text(s) for s in _evidence_segments_for_role(quote, role)}
            variants.discard("")
            for v in variants:
                # Only place inline badges when the evaluator's quote is directly
                # present in this bubble. Do not reverse-match broad/multi-turn quotes.
                if _evidence_matches_message(v, nmsg):
                    match_key = f"{key}:{v}"
                    if match_key not in seen:
                        seen.add(match_key)
                        issues_list = row.get("issues")
                        reason = issues_list[0] if issues_list else "Flagged by AI"
                        matched.append({
                            "key": row["key"],
                            "label": row["label"],
                            "reason": reason,
                            "score": row.get("score", 0.0),
                            "quote_norm": v,
                        })
                    break
    return matched


def merge_eval_from_store(cid: str, report_ev: dict, eval_by_id: dict) -> dict:
    full = eval_by_id.get(cid)
    if full and isinstance(full, dict) and full.get("dimensions"):
        return full
    return report_ev


def prepare_transcript_turn(role: str, raw: str) -> tuple[str, str, list, str]:
    raw_stored = raw or ""
    if role != "Assistant":
        t = raw_stored[:8000]
        return t, t, [], raw_stored
    clean, products = parse_agent_message(raw_stored)
    vis = (clean or "").strip()
    if not vis and "End of stream" in raw_stored:
        vis = "No visible reply text before the product payload."
    elif not vis:
        vis = "Empty assistant text."
    match_text = (clean or "")[:12000]
    return vis[:8000], match_text, products, raw_stored


def is_failed_evaluation(ev: dict) -> bool:
    failure_descriptions = ev.get("failure_descriptions") or []
    open_observations = (ev.get("open_observations") or "").lower()
    return any(
        isinstance(fd, str) and fd.startswith("EVALUATION_ERROR")
        for fd in failure_descriptions
    ) or "content management policy" in open_observations


def _repetition_info(transcript: list[dict]) -> tuple[str, str]:
    """Return (note_string, repeated_normalized_text). note is '' if no repetition."""
    agent_texts = []
    for m in transcript:
        if m.get("sender") != "user":
            _, clean, _, _ = prepare_transcript_turn("Assistant", m.get("text") or "")
            t = " ".join(clean.lower().split())[:120]
            if t:
                agent_texts.append(t)
    if not agent_texts:
        return "", ""
    most_common, count = max(
        ((t, agent_texts.count(t)) for t in set(agent_texts)),
        key=lambda x: x[1],
    )
    if count >= 2:
        return f" · same response repeated {count}×", most_common
    return "", ""


def render_evaluation_metadata(ev: dict, merged: dict) -> None:
    """Compact verdict-first block: failures + reasoning without heavy score UI."""
    score_raw = merged.get("overall_score", ev.get("overall_score"))
    try:
        score = float(score_raw) if score_raw is not None else 0.0
    except (TypeError, ValueError):
        score = 0.0

    failure_list = [
        fd for fd in (ev.get("failure_descriptions") or [])
        if isinstance(fd, str) and fd.strip()
    ]
    resolution = merged.get("resolution_achieved", ev.get("resolution_achieved"))

    score_class = "score-ok" if score >= 4.5 else "score-bad"
    res_label = "Resolved" if resolution is True else "Unresolved" if resolution is False else "Unknown"

    alert_rows: list[str] = []
    if failure_list:
        for fd in failure_list:
            alert_rows.append(
                f'<div class="eval-alert">{html.escape(fd)}</div>'
            )
    elif score >= 4.5:
        alert_rows.append('<div class="eval-alert success">No failures detected.</div>')

    scratch = (merged.get("reasoning_scratchpad") or ev.get("reasoning_scratchpad") or "").strip()

    st.markdown(
        '<div class="eval-summary">'
        '<div class="eval-meta">'
        f'<span class="eval-chip {score_class}">Score {score:.1f}/5</span>'
        f'<span class="eval-chip">{html.escape(res_label)}</span>'
        f'<span class="eval-chip">{len(failure_list)} failure{"s" if len(failure_list) != 1 else ""}</span>'
        '</div>'
        f'{"".join(alert_rows)}'
        '</div>',
        unsafe_allow_html=True,
    )

    if scratch:
        safe_scratch = html.escape(scratch).replace("\n", "<br/>")
        st.markdown(
            '<details class="eval-scratch-details">'
            "<summary>Why this score?</summary>"
            f'<div class="eval-scratch-body">{safe_scratch}</div>'
            "</details>",
            unsafe_allow_html=True,
        )


def render_dimension_grid(dimensions: dict | None, n_cols: int = 3) -> None:
    """Side-by-side dimension scores with optional issue snippet."""
    if not dimensions:
        return
    items = [(k, v) for k, v in dimensions.items() if isinstance(v, dict)]
    items.sort(key=lambda x: x[0])
    if not items:
        return

    cols = st.columns(n_cols)
    for i, (key, d) in enumerate(items):
        sc = float(d.get("score", 5))
        label = humanize_dimension(key)
        val = f"{int(sc)}/5" if sc == int(sc) else f"{sc:g}/5"
        with cols[i % n_cols]:
            # st.metric does not accept `key=` on all Streamlit versions.
            st.metric(label, val)
            issues = [x for x in (d.get("issues") or []) if isinstance(x, str) and x.strip()]
            if sc < 5.0 and issues:
                snippet = issues[0]
                if len(snippet) > 80:
                    snippet = snippet[:80] + "…"
                st.caption(snippet)


def _badge_for(key: str, fallback: str, reason_text: str = "") -> str:
    rl = (reason_text or "").lower()
    if "irrelevant" in rl or "wrong product" in rl or "irrelevant product" in rl:
        return "IRRELEVANT PRODUCT"
    return BADGE_LABEL.get(key, fallback.upper())


def _group_into_turns(transcript: list[dict]) -> list[tuple[list[dict], list[dict]]]:
    """Group transcript into (user_messages, assistant_messages) exchange pairs."""
    turns: list[tuple[list[dict], list[dict]]] = []
    cur_user: list[dict] = []
    cur_asst: list[dict] = []
    for m in transcript:
        if (m.get("messageType") or "text") == "event":
            continue
        if m.get("sender") == "user":
            if cur_asst:
                turns.append((cur_user, cur_asst))
                cur_user, cur_asst = [], []
            cur_user.append(m)
        else:
            cur_asst.append(m)
    if cur_user or cur_asst:
        turns.append((cur_user, cur_asst))
    return turns


def _collect_turn_flags(
    user_msgs: list[dict],
    asst_msgs: list[dict],
    evidence_hits: dict[int, list[dict]],
    mi_to_m: dict[int, dict],
) -> list[dict]:
    """Collect deduplicated flags for all messages in this turn."""
    turn_set = {id(m) for m in user_msgs + asst_msgs}
    seen: set[str] = set()
    result: list[dict] = []
    for mi, hits in evidence_hits.items():
        m = mi_to_m.get(mi)
        if m is None or id(m) not in turn_set:
            continue
        for hit in hits:
            dk = f"{hit['key']}:{hit['reason'][:40]}"
            if dk not in seen:
                seen.add(dk)
                result.append(hit)
    return result


# ── Rendering ──

def render_conversation(ev: dict) -> None:
    """Render a single conversation in the world-class audit UI."""
    score = ev.get("overall_score")
    failures = ev.get("failure_descriptions") or []
    cid = str(ev.get("conversation_id", ""))
    transcript = msg_index.get(cid, [])

    raw_reason = failures[0] if failures else (ev.get("user_intent") or "")
    reason = raw_reason[:90].rsplit(" ", 1)[0] if len(raw_reason) > 90 else raw_reason
    repeat_note, _ = _repetition_info(transcript)
    label = f"Score {score}/5 — {reason}{repeat_note}"

    with st.expander(label):
        st.caption(f"Conversation ID: {cid}")

        merged = merge_eval_from_store(cid, ev, eval_by_id)
        flags = collect_dimension_flags(merged)

        render_evaluation_metadata(ev, merged)

        st.divider()
        st.markdown("##### Chat transcript (proof)")

        if not transcript:
            st.caption("No transcript available.")
            return

        # Pre-compute evidence hits per message (role-filtered)
        evidence_hits: dict[int, list[dict]] = {}
        mi_to_m: dict[int, dict] = {}
        for mi, m in enumerate(transcript):
            mi_to_m[mi] = m
            role = "User" if m.get("sender") == "user" else "Assistant"
            _, match_text, _, _ = prepare_transcript_turn(role, m.get("text") or "")
            allowed_dims = ASSISTANT_DIMS if role == "Assistant" else USER_DIMS
            hits = [
                h for h in match_flags_to_message(match_text, role, flags)
                if h.get("key", "") in allowed_dims
            ]
            if hits:
                evidence_hits[mi] = hits

        turns = _group_into_turns(transcript)

        st.markdown('<div class="chat-thread">', unsafe_allow_html=True)

        for user_msgs, asst_msgs in turns:
            for m in user_msgs:
                display_text, _, _, _ = prepare_transcript_turn("User", m.get("text") or "")
                safe_text = _md_to_html(html.escape(display_text).replace("\n", "<br/>"))
                st.markdown(
                    f'<div class="msg-row left">'
                    f'  <div class="role-tag">CUSTOMER</div>'
                    f'  <div class="msg-card"><div class="bubble">{safe_text}</div></div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

            for m in asst_msgs:
                display_text, _, _, _ = prepare_transcript_turn("Assistant", m.get("text") or "")
                safe_text = _md_to_html(html.escape(display_text).replace("\n", "<br/>"))
                st.markdown(
                    f'<div class="msg-row right">'
                    f'  <div class="role-tag">ASSISTANT</div>'
                    f'  <div class="msg-card"><div class="bubble">{safe_text}</div></div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

            turn_flags = _collect_turn_flags(user_msgs, asst_msgs, evidence_hits, mi_to_m)
            if not turn_flags:
                continue

            turn_flags.sort(key=lambda h: h.get("score", 5.0))
            top_flags = turn_flags[:2]
            is_red = any(
                h.get("score", 5.0) <= 2.0
                or h.get("key", "") in {"hallucination_check", "factual_accuracy", "cross_brand_check"}
                for h in top_flags
            )
            bar_class = "turn-verdict" if is_red else "turn-verdict amber"
            # Prefer the eval-level failure_descriptions (already a concise executive sentence)
            # over dimension issue text, which can be verbose or mid-sentence when truncated.
            failure_descs = [fd for fd in (merged.get("failure_descriptions") or []) if fd and fd.strip()]
            verdict_reason = failure_descs[0] if failure_descs else top_flags[0].get("reason", "")

            badges_html = ""
            for hit in top_flags:
                bl = _badge_for(hit.get("key", ""), hit["label"], hit.get("reason", ""))
                hit_red = (
                    hit.get("score", 5.0) <= 2.0
                    or hit.get("key", "") in {"hallucination_check", "factual_accuracy", "cross_brand_check"}
                )
                bc = "red" if hit_red else "amber"
                badges_html += f'<span class="verdict-badge {bc}">{html.escape(bl)}</span>'

            st.markdown(
                f'<div class="{bar_class}">'
                f'  {badges_html}'
                f'  <span class="verdict-reason">· {html.escape(verdict_reason)}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

        st.markdown('</div>', unsafe_allow_html=True)


# ── Initialization ──

_output_sig = _output_cache_signature()
report = load_report(_output_sig)
all_evals = load_all_evaluations(_output_sig)
eval_by_id = {str(e.get("conversation_id", "")): e for e in all_evals if e.get("conversation_id")}
msg_index = load_messages_index()

st.title("Conversation Review")
st.markdown("Focused review feed of flagged interactions.")

brand_names = [b["brand_name"] for b in report.get("brands", [])]

# Single select dropdown for the brand
selected_brand = st.sidebar.selectbox("Select Brand", options=brand_names)

review_pool = all_evals if all_evals else (report.get("worst_conversations") or [])

filtered_reviews = []
for e in review_pool:
    if e.get("brand_name") != selected_brand:
        continue

    # Only show bad interactions
    overall_score = float(e.get("overall_score", 0))
    if overall_score >= 4.0:
        continue

    cid = str(e.get("conversation_id", ""))
    merged = merge_eval_from_store(cid, e, eval_by_id)

    if is_failed_evaluation(merged):
        continue

    transcript = msg_index.get(cid, [])
    has_text_turns = any((m.get("messageType") or "text") == "text" for m in transcript)
    if not has_text_turns:
        continue

    filtered_reviews.append(e)


# ── Grouping by semantic issue pattern ──

def get_primary_issue_type(ev: dict) -> str:
    cid = str(ev.get("conversation_id", ""))

    # Check for loops first
    repeat_note, _ = _repetition_info(msg_index.get(cid, []))
    if repeat_note:
        return "Bot Stuck In Repetitive Loop"

    failures = " ".join(ev.get("failure_descriptions") or []).lower()

    # Semantic hints from AI's plain English failure descriptions
    if "wrong product" in failures or "irrelevant" in failures or "product recommendations" in failures:
        return "Suggesting Wrong / Irrelevant Products"
    if "sign in" in failures or "login" in failures:
        return "Forcing Unhelpful Sign-In Wall"
    if "delivery" in failures or "timeline" in failures or "tracking" in failures:
        return "Failing To Handle Delivery / Tracking"
    if "repeat" in failures or "loop" in failures or "same response" in failures:
        return "Bot Stuck In Repetitive Loop"

    # Fallback: map metric to human behavior
    merged = merge_eval_from_store(cid, ev, eval_by_id)
    dims = merged.get("dimensions", {})
    issues = []
    for dim_name, dim_data in dims.items():
        if dim_data.get("score", 5) < 5:
            issues.append((dim_name, float(dim_data.get("score", 5))))

    if issues:
        issues.sort(key=lambda x: x[1])
        top_dim = issues[0][0]

        dim_map = {
            "user_satisfaction_signals": "Unresolved User Frustration",
            "tone_and_helpfulness": "Unhelpful / Robotic Responses",
            "policy_compliance": "Rigid Policy Dead-Ends",
            "hallucination_check": "Making Up False Information",
            "factual_accuracy": "Wrong / Inaccurate Information",
            "cross_brand_check": "Suggesting Other Brands",
        }
        return dim_map.get(top_dim, top_dim.replace("_", " ").title())

    return "General Logic Failure"


# Sort worst to best
filtered_reviews.sort(key=lambda item: float(item.get("overall_score", 0)))

st.caption(f"Showing {len(filtered_reviews)} flagged conversations for **{selected_brand}**.")

if not filtered_reviews:
    st.info("No flagged conversations found for this brand.")
else:
    # Group by primary issue type
    grouped: dict[str, list] = {}
    for ev in filtered_reviews:
        issue_type = get_primary_issue_type(ev)
        grouped.setdefault(issue_type, []).append(ev)

    # Sort groups by frequency (highest first)
    for issue_type, group_evs in sorted(grouped.items(), key=lambda x: len(x[1]), reverse=True):
        st.markdown(
            f'<div class="pattern-header">'
            f'▸ {issue_type.upper()} <span class="pattern-count">({len(group_evs)} conversations)</span>'
            f'</div>',
            unsafe_allow_html=True
        )
        for ev in group_evs:
            render_conversation(ev)
