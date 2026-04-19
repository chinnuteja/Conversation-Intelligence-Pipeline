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

CUSTOM_CSS = """
<style>
    .block-container { padding-top: 1.2rem; padding-bottom: 2rem; }
    
    /* Layout */
    .review-wrapper {
        display: flex;
        flex-direction: column;
        gap: 24px;
        margin-bottom: 30px;
        font-family: 'Inter', -apple-system, sans-serif;
    }

    .msg-group {
        display: flex;
        flex-direction: column;
        width: 100%;
    }

    /* Alignment */
    .align-left { align-items: flex-start; }
    .align-right { align-items: flex-end; }

    /* Role Label */
    .role-label {
        font-size: 0.65rem;
        font-weight: 800;
        letter-spacing: 0.1rem;
        color: #888;
        margin-bottom: 6px;
        text-transform: uppercase;
        margin-left: 12px;
        margin-right: 12px;
    }

    /* The Capsule */
    .chat-capsule {
        max-width: 80%;
        padding: 14px 18px;
        border-radius: 18px;
        font-size: 0.95rem;
        line-height: 1.5;
        position: relative;
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.2); /* Darkened for visibility */
        color: inherit;
    }

    /* Coloring */
    .theme-red { border-color: #ff4b4b; background: rgba(255, 75, 75, 0.05); }
    .theme-gold { border-color: #ffbd45; background: rgba(255, 189, 69, 0.05); }

    /* Audit Badge */
    .audit-badge {
        display: inline-block;
        margin-top: 10px;
        padding: 2px 10px;
        border-radius: 6px;
        font-size: 0.7rem;
        font-weight: 800;
        text-transform: uppercase;
        border: 1px solid transparent;
        margin-left: 4px;
    }

    .badge-red { color: #ff4b4b; border-color: #ff4b4b; background: rgba(255, 75, 75, 0.1); }
    .badge-gold { color: #ffbd45; border-color: #ffbd45; background: rgba(255, 189, 69, 0.1); }

    /* Reasoning Text */
    .audit-reason {
        display: block;
        margin-top: 6px;
        font-size: 0.8rem;
        font-style: italic;
        opacity: 0.9;
        max-width: 85%;
        margin-left: 8px;
        margin-right: 8px;
    }

    .reason-red { color: #ff4b4b; }
    .reason-gold { color: #ffbd45; }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


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
                        reason = row.get("issues", ["Flagged by AI"])[0]
                        score_val = row.get("score", 0.0)
                        # Create a premium-looking tag for the issue
                        matched.append({
                            "label": row['label'],
                            "reason": reason,
                            "score": score_val
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


def render_review_conversation(ev: dict) -> None:
    score = ev.get("overall_score")
    failures = ev.get("failure_descriptions") or []
    cid = str(ev.get("conversation_id", ""))
    transcript = msg_index.get(cid, [])

    # Fix 1: truncate at word boundary
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

        # Find which messages triggered flags
        focal_indices = []
        for mi, m in enumerate(transcript):
            role = "User" if m.get("sender") == "user" else "Assistant"
            _, match_text, _, _ = prepare_transcript_turn(role, m.get("text") or "")
            if match_flags_to_message(match_text, flags):
                focal_indices.append(mi)

        # Pair each flagged message with its counterpart (user↔agent)
        bad_indices: set[int] = set()
        for idx in focal_indices:
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

        # Fix 3: if repetition detected, include all occurrences so the "repeated N×" note is visible
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

        bad_indices_set = bad_indices or set()

        # Show FULL conversation — highlight the bad parts, keep the rest for context
        st.markdown('<div class="review-wrapper">', unsafe_allow_html=True)
        
        # Performance/UX: Track which audit insights we've already shown for this convo 
        # so we don't repeat the same "User Satisfaction" text 5 times.
        shown_insights = set()
        
        # Get dimensions that actually failed for fallback
        failed_assistant_dims = [f for f in flags if f.get("score", 5) < 4 and f.get("key") != "user_satisfaction_signals"]
        assistant_fallback_shown = False

        for mi, m in enumerate(transcript):
            # Skip non-text events (clicks, etc.) to keep it clean
            mtype = m.get("messageType") or "text"
            if mtype == "event":
                continue

            role = "User" if m.get("sender") == "user" else "Assistant"
            display_text, match_text, _, _ = prepare_transcript_turn(role, m.get("text") or "")
            hits = match_flags_to_message(match_text, flags)
            is_bad = bool(hits) or mi in bad_indices_set

            # Build the components
            safe_text = html.escape(display_text).replace("\n", "<br/>")
            align_class = "align-left" if role == "User" else "align-right"
            display_role = "CUSTOMER" if role == "User" else "ASSISTANT"
            
            # Determine theme
            theme_class = ""
            badge_html = ""
            reason_html = ""
            
            # Use Red for Customer (Frustration/Mistakes), Gold for Assistant (Logic/Tone)
            use_red = (role == "User")
            b_theme = "badge-red" if use_red else "badge-gold"
            r_theme = "reason-red" if use_red else "reason-gold"

            if is_bad:
                theme_class = "theme-red" if use_red else "theme-gold"
                
                # Logic for audit badges
                current_insignts = []
                if hits:
                    current_insignts = hits
                elif not use_red and not assistant_fallback_shown and failed_assistant_dims and mi in bad_indices_set:
                    # Assistant Fallback: If AI graded this convo as bad for helpfullness but 
                    # we didn't find the exact quote match, attach it to the first assistant failure
                    current_insignts = [{"label": failed_assistant_dims[0]["label"], "reason": failed_assistant_dims[0].get("issues", ["Logic Failure"])[0]}]
                    assistant_fallback_shown = True
                elif use_red and not hits and mi in bad_indices_set:
                    # Generic User Frustration fallback
                    current_insignts = [{"label": "FRUSTRATION", "reason": ev.get("user_satisfaction_signals_reason", "User interaction flagged for follow-up.")}]

                for ins in current_insignts:
                    # DE-DUPLICATION: Only show unique insights once per conversation
                    insight_key = (ins["label"], ins["reason"][:50])
                    if insight_key not in shown_insights:
                        badge_html += f'<div class="audit-badge {b_theme}">{ins["label"]}</div>'
                        reason_html += f'<div class="audit-reason {r_theme}">{ins["reason"]}</div>'
                        shown_insights.add(insight_key)

            # Render the capsule
            st.markdown(
                f'<div class="msg-group {align_class}">'
                f'  <div class="role-label">{display_role}</div>'
                f'  <div class="chat-capsule {theme_class}">{safe_text}</div>'
                f'  {badge_html}'
                f'  {reason_html}'
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

# Helper to group by issue pattern semantically instead of metric name
def get_primary_issue_type(ev: dict) -> str:
    cid = str(ev.get("conversation_id", ""))
    
    # Check for loops first natively from the transcript
    repeat_note, _ = _repetition_info(msg_index.get(cid, []))
    if repeat_note:
        return "Bot Stuck In Repetitive Loop"
        
    failures = " ".join(ev.get("failure_descriptions") or []).lower()
    
    # 1. Look for semantic hints in the AI's plain English failure descriptions
    if "wrong product" in failures or "irrelevant" in failures or "product recommendations" in failures:
        return "Suggesting Wrong/Irrelevant Products"
    if "sign in" in failures or "login" in failures:
        return "Forcing Unhelpful Sign-In Wall"
    if "delivery" in failures or "timeline" in failures or "tracking" in failures:
        return "Failing To Handle Delivery/Tracking"
    if "repeat" in failures or "loop" in failures or "same response" in failures:
        return "Bot Stuck In Repetitive Loop"
        
    # 2. Fallback to mapping the metric to a human behavior
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
            "cross_brand_reference": "Suggesting Other Brands"
        }
        return dim_map.get(top_dim, top_dim.replace("_", " ").title())
        
    return "General Logic Failure"

# Sort worst to best before grouping
filtered_reviews.sort(key=lambda item: float(item.get("overall_score", 0)))

st.caption(f"Showing {len(filtered_reviews)} flagged conversations for **{selected_brand}**.")

if not filtered_reviews:
    st.info("No flagged conversations found for this brand.")
else:
    # Group by primary issue type
    grouped = {}
    for ev in filtered_reviews:
        issue_type = get_primary_issue_type(ev)
        grouped.setdefault(issue_type, []).append(ev)
        
    # Sort groups by frequency (highest first)
    for issue_type, group_evs in sorted(grouped.items(), key=lambda x: len(x[1]), reverse=True):
        st.markdown(f"<h4 style='color: #c0392b; margin-top: 30px; border-bottom: 1px solid #ddd; padding-bottom: 5px;'>👇 ISSUE PATTERN: {issue_type.upper()} ({len(group_evs)}) 👇</h4>", unsafe_allow_html=True)
        for ev in group_evs:
            render_review_conversation(ev)
        st.markdown("<br/>", unsafe_allow_html=True)
