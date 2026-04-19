"""
Minimal Streamlit Dashboard — Conversation Review Feed
Focuses entirely on reviewing bad interactions per brand.
"""

from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.stage1_ingest import parse_agent_message

OUTPUT_DIR = ROOT / "output"
DATA_DIR = ROOT / "data"

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

    /* ── Chat Bubble ── */
    .bubble {
        max-width: 75%;
        padding: 10px 14px;
        border-radius: 16px;
        font-family: 'Inter', sans-serif;
        font-size: 0.88rem;
        line-height: 1.55;
        color: #1a1a2e;
        word-wrap: break-word;
    }

    /* Neutral */
    .bubble.neutral {
        background: #f8f9fa;
        border: 1px solid #e0e0e0;
    }

    /* Flagged Customer — soft red */
    .bubble.flagged-customer {
        background: #fff5f5;
        border: 1.5px solid #ff6b6b;
    }

    /* Flagged Assistant — soft amber */
    .bubble.flagged-assistant {
        background: #fffbf0;
        border: 1.5px solid #f0a500;
    }

    /* ── Audit Insight (badge + reason in one clean line) ── */
    .audit-insight {
        display: flex;
        align-items: baseline;
        gap: 8px;
        margin-top: 4px;
        margin-bottom: 2px;
        padding-left: 6px;
        padding-right: 6px;
        flex-wrap: wrap;
    }

    .insight-badge {
        font-family: 'Inter', sans-serif;
        font-size: 0.62rem;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        padding: 2px 8px;
        border-radius: 4px;
        white-space: nowrap;
    }

    .insight-badge.red {
        color: #d63031;
        background: rgba(214, 48, 49, 0.08);
        border: 1px solid rgba(214, 48, 49, 0.3);
    }

    .insight-badge.amber {
        color: #e17055;
        background: rgba(225, 112, 85, 0.08);
        border: 1px solid rgba(225, 112, 85, 0.3);
    }

    .insight-reason {
        font-family: 'Inter', sans-serif;
        font-size: 0.75rem;
        font-style: italic;
        color: #666;
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


# ── Data Loading ──

def _output_cache_signature() -> tuple[float, float, float]:
    paths = (
        OUTPUT_DIR / "report.json",
        OUTPUT_DIR / "all_evaluations.json",
        OUTPUT_DIR / "clusters.json",
    )

    def _mtime(p: Path) -> float:
        return p.stat().st_mtime if p.is_file() else 0.0

    return (_mtime(paths[0]), _mtime(paths[1]), _mtime(paths[2]))


@st.cache_data(show_spinner=False)
def load_report(_output_sig: tuple[float, float, float]):
    path = OUTPUT_DIR / "report.json"
    if not path.exists():
        st.error(f"Missing {path}. Run `python pipeline.py` first.")
        st.stop()
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@st.cache_data(show_spinner=False)
def load_all_evaluations(_output_sig: tuple[float, float, float]):
    path = OUTPUT_DIR / "all_evaluations.json"
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@st.cache_data
def load_messages_index():
    path = DATA_DIR / "messages.json"
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    idx: dict[str, list[dict]] = {}
    for m in raw:
        cid = str(m.get("conversationId", ""))
        idx.setdefault(cid, []).append(
            {
                "sender": m.get("sender"),
                "text": (m.get("text") or "")[:8000],
                "timestamp": str(m.get("timestamp", "")),
                "messageType": m.get("messageType", "text"),
            }
        )
    for cid in idx:
        idx[cid].sort(key=lambda x: x["timestamp"])
    return idx


# ── Text Processing ──

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
                "label": key.replace("_", " ").title(),
                "score": score,
                "issues": issues,
                "evidence": evidence,
            }
        )
    return out


def match_flags_to_message(msg_text: str, flags: list[dict]) -> list[dict]:
    """Return list of {label, reason, score} for flags whose evidence matches this message."""
    nmsg = _norm_text(msg_text)
    if len(nmsg) < 5:
        return []
    matched: list[dict] = []
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
                        reason = row.get("issues", ["Flagged by AI"])[0]
                        matched.append({
                            "label": row["label"],
                            "reason": reason,
                            "score": row.get("score", 0.0),
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


# ── Rendering ──

def render_conversation(ev: dict) -> None:
    """Render a single conversation in the world-class audit UI."""
    score = ev.get("overall_score")
    failures = ev.get("failure_descriptions") or []
    cid = str(ev.get("conversation_id", ""))
    transcript = msg_index.get(cid, [])

    raw_reason = failures[0] if failures else (ev.get("user_intent") or "")
    reason = raw_reason[:90].rsplit(" ", 1)[0] if len(raw_reason) > 90 else raw_reason
    repeat_note, repeated_text = _repetition_info(transcript)
    label = f"Score {score}/5 — {reason}{repeat_note}"

    with st.expander(label):
        st.markdown(f"**Conversation ID:** `{cid}`")

        merged = merge_eval_from_store(cid, ev, eval_by_id)
        flags = collect_dimension_flags(merged)

        if not transcript:
            st.caption("No transcript available.")
            return

        # ── Step 1: Find which messages have REAL evidence matches ──
        evidence_hits: dict[int, list[dict]] = {}
        for mi, m in enumerate(transcript):
            role = "User" if m.get("sender") == "user" else "Assistant"
            _, match_text, _, _ = prepare_transcript_turn(role, m.get("text") or "")
            hits = match_flags_to_message(match_text, flags)
            if hits:
                evidence_hits[mi] = hits

        # ── Step 2: Mark bad indices (evidence + their counterpart) ──
        bad_indices: set[int] = set()
        for idx in evidence_hits:
            bad_indices.add(idx)
            if transcript[idx].get("sender") == "user":
                nxt = idx + 1
                while nxt < len(transcript) and transcript[nxt].get("sender") == "user":
                    nxt += 1
                if nxt < len(transcript):
                    bad_indices.add(nxt)
            else:
                prv = idx - 1
                while prv >= 0 and transcript[prv].get("sender") != "user":
                    prv -= 1
                if prv >= 0:
                    bad_indices.add(prv)

        # Step 2b: Include repeated responses
        if repeated_text:
            for mi, m in enumerate(transcript):
                if m.get("sender") != "user":
                    _, clean, _, _ = prepare_transcript_turn("Assistant", m.get("text") or "")
                    if " ".join(clean.lower().split())[:120] == repeated_text:
                        bad_indices.add(mi)
                        prv = mi - 1
                        while prv >= 0 and transcript[prv].get("sender") != "user":
                            prv -= 1
                        if prv >= 0:
                            bad_indices.add(prv)

        # ── Step 3: Prepare assistant-facing flags for smart routing ──
        # Separate flags into user-facing vs assistant-facing categories
        ASSISTANT_DIMS = {"tone_and_helpfulness", "policy_compliance", "hallucination", "cross_brand_reference"}
        USER_DIMS = {"user_satisfaction_signals"}

        assistant_flags = [f for f in flags if f["key"] in ASSISTANT_DIMS and f.get("score", 5) < 4]
        user_flags = [f for f in flags if f["key"] in USER_DIMS and f.get("score", 5) < 4]

        shown_insights: set[str] = set()  # de-duplication
        assistant_flag_queue = list(assistant_flags)  # queue to attach to assistant messages

        st.markdown('<div class="chat-thread">', unsafe_allow_html=True)

        for mi, m in enumerate(transcript):
            mtype = m.get("messageType") or "text"
            if mtype == "event":
                continue

            role = "User" if m.get("sender") == "user" else "Assistant"
            display_text, _, _, _ = prepare_transcript_turn(role, m.get("text") or "")
            is_bad = mi in bad_indices
            hits = evidence_hits.get(mi, [])

            # Prepare text: escape HTML then convert markdown to clickable links
            safe_text = html.escape(display_text).replace("\n", "<br/>")
            safe_text = _md_to_html(safe_text)

            # Choose bubble style
            if is_bad and role == "User":
                bubble_class = "flagged-customer"
            elif is_bad:
                bubble_class = "flagged-assistant"
            else:
                bubble_class = "neutral"

            align = "left" if role == "User" else "right"
            display_role = "CUSTOMER" if role == "User" else "ASSISTANT"

            # ── Build insight badges ──
            insight_html = ""

            if hits:
                # Direct evidence match — use it
                for hit in hits:
                    dedup_key = f"{hit['label']}:{hit['reason'][:40]}"
                    if dedup_key not in shown_insights:
                        shown_insights.add(dedup_key)
                        badge_color = "red" if role == "User" else "amber"
                        insight_html += (
                            f'<div class="audit-insight">'
                            f'  <span class="insight-badge {badge_color}">{hit["label"]}</span>'
                            f'  <span class="insight-reason">{html.escape(hit["reason"])}</span>'
                            f'</div>'
                        )

            elif is_bad and role == "Assistant" and assistant_flag_queue:
                # SMART FALLBACK: Assistant is flagged (amber border) but no direct text match.
                # Attach the next unused assistant-facing dimension flag.
                flag = assistant_flag_queue[0]
                reason_text = flag["issues"][0] if flag.get("issues") else "Flagged by AI evaluator"
                dedup_key = f"{flag['label']}:{reason_text[:40]}"
                if dedup_key not in shown_insights:
                    shown_insights.add(dedup_key)
                    insight_html += (
                        f'<div class="audit-insight">'
                        f'  <span class="insight-badge amber">{flag["label"]}</span>'
                        f'  <span class="insight-reason">{html.escape(reason_text)}</span>'
                        f'</div>'
                    )
                    # Only pop after successfully showing — so it doesn't show again
                    assistant_flag_queue.pop(0)

            elif is_bad and role == "User" and user_flags:
                # SMART FALLBACK for user: attach user-facing flag if no direct match
                flag = user_flags[0]
                reason_text = flag["issues"][0] if flag.get("issues") else "User expressed frustration"
                dedup_key = f"{flag['label']}:{reason_text[:40]}"
                if dedup_key not in shown_insights:
                    shown_insights.add(dedup_key)
                    insight_html += (
                        f'<div class="audit-insight">'
                        f'  <span class="insight-badge red">{flag["label"]}</span>'
                        f'  <span class="insight-reason">{html.escape(reason_text)}</span>'
                        f'</div>'
                    )

            st.markdown(
                f'<div class="msg-row {align}">'
                f'  <div class="role-tag">{display_role}</div>'
                f'  <div class="bubble {bubble_class}">{safe_text}</div>'
                f'  {insight_html}'
                f'</div>',
                unsafe_allow_html=True
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
            "hallucination": "Making Up False Information",
            "cross_brand_reference": "Suggesting Other Brands",
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
