"""
Streamlit Dashboard — Conversation Intelligence

Run from repo root: streamlit run dashboard/app.py
"""

from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.stage1_ingest import parse_agent_message

OUTPUT_DIR = ROOT / "output"
DATA_DIR = ROOT / "data"

st.set_page_config(
    page_title="Conversation Intelligence",
    layout="wide",
    page_icon="📊",
    initial_sidebar_state="expanded",
)

CUSTOM_CSS = """
<style>
    .block-container { padding-top: 1.2rem; padding-bottom: 2rem; }
    div[data-testid="stMetricValue"] { font-size: 1.6rem; }
    .report-card {
        border: 1px solid rgba(250,250,250,0.12);
        border-radius: 12px;
        padding: 1rem 1.25rem;
        margin-bottom: 1rem;
        background: rgba(255,255,255,0.03);
    }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


@st.cache_data
def load_report():
    path = OUTPUT_DIR / "report.json"
    if not path.exists():
        st.error(f"Missing {path}. Run `python pipeline.py` first.")
        st.stop()
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@st.cache_data
def load_all_evaluations():
    path = OUTPUT_DIR / "all_evaluations.json"
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@st.cache_data
def load_messages_index():
    """conversation_id -> ordered list of {sender, text, timestamp, messageType}."""
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


# ── Flagged messages (dimension evidence vs transcript) ──
_FLAG_SCORE_MAX = 3.99  # dimensions at/under this are highlighted as weak
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
    """Rows for UI: dimensions with low score and/or issues/evidence quotes."""
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
    """Return human-readable labels for dimensions whose evidence matches this message."""
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


def merge_eval_from_store(cid: str, report_ev: dict, eval_by_id: dict) -> dict:
    """Prefer full evaluation from all_evaluations.json when available."""
    full = eval_by_id.get(cid)
    if full and isinstance(full, dict) and full.get("dimensions"):
        return full
    return report_ev


def prepare_transcript_turn(role: str, raw: str) -> tuple[str, str, list, str]:
    """
    Make assistant rows readable: hide 'End of stream' + product JSON by default.

    Returns:
        display_text: what we show (visible reply for assistant).
        match_text: substring source for evidence highlighting (same as pipeline visible text).
        products: parsed ProductContext list for optional expander.
        raw_stored: original text from JSON (for unparsed tail expander).
    """
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


def render_review_conversation(ev: dict, mixed_note: str | None = None) -> None:
    """Shared UI for a single review conversation row."""
    intent = (ev.get("user_intent") or "")[:80]
    with st.expander(
        f"{ev.get('overall_score')}/5 — {ev.get('brand_name')} — {intent}"
    ):
        cid = str(ev.get("conversation_id", ""))
        merged = merge_eval_from_store(cid, ev, eval_by_id)
        flags = collect_dimension_flags(merged)
        transcript = msg_index.get(cid, [])

        st.code(cid, language="text")
        st.caption(
            "Side-by-side: **claims & evidence** (left) vs **full transcript** (right). "
            "Narrow window stacks columns automatically."
        )
        if mixed_note:
            st.warning(mixed_note)

        has_text_turns = any(
            (m.get("messageType") or "text") == "text" for m in transcript
        )
        if transcript and not has_text_turns:
            st.info(
                "**Why the left says “no messages” but you see a row on the right:** "
                "the export has **only `event` rows** (quick actions, clicks)—no **`text`** chat yet. "
                "The LLM judge uses “no messages” to mean *nothing to score as dialogue*. "
                "The right column is still **accurate**: that event is what was logged in "
                "`data/messages.json`."
            )

        col_claims, col_transcript = st.columns((1, 1), gap="large")

        with col_claims:
            st.markdown("##### Claims & flagged evidence")
            if ev.get("failure_descriptions"):
                st.error("Summary issues")
                for fd in ev["failure_descriptions"]:
                    st.write(f"- {fd}")
            if ev.get("frustration_signals"):
                st.warning("Frustration")
                for fs in ev["frustration_signals"]:
                    st.write(f"- {fs}")
            if ev.get("open_observations"):
                st.info(ev["open_observations"])

            if flags:
                st.markdown("**Dimensions** (LLM judge — compare with transcript →)")
                for row in flags:
                    st.markdown(
                        f"**{row['label']}** — `{row['score']:.1f}/5`"
                    )
                    for iss in row["issues"]:
                        st.caption(f"Issue: {iss}")
                    for q in row["evidence"]:
                        st.markdown(f"> {q}")
                st.caption(
                    "Turns whose text contains a quote above are highlighted in the transcript."
                )
            elif merged.get("dimensions"):
                st.caption("No dimension flags (scores & evidence empty for this conversation).")

        with col_transcript:
            st.markdown("##### Full transcript")
            if transcript:
                st.caption(
                    "From `data/messages.json`. **Assistant** rows show only the reply the shopper "
                    "would see. Product details appear only when the payload contains actual items."
                )
                for mi, m in enumerate(transcript):
                    role = "User" if m.get("sender") == "user" else "Assistant"
                    mtype = m.get("messageType") or "text"
                    meta = m.get("metadata") if isinstance(m.get("metadata"), dict) else {}
                    ev_t = meta.get("eventType")
                    type_note = ""
                    if mtype != "text":
                        type_note = f" · **{mtype}**"
                        if ev_t:
                            type_note += f" (`{ev_t}`)"
                    raw_full = m.get("text") or ""
                    display_text, match_text, products, _raw_stored = prepare_transcript_turn(
                        role, raw_full
                    )
                    hit_labels = match_flags_to_message(match_text, flags)
                    if hit_labels:
                        labels_html = " · ".join(html.escape(x) for x in hit_labels)
                        body = html.escape(display_text).replace("\n", "<br/>")
                        ts_esc = html.escape(str(m.get("timestamp", "")))
                        role_esc = html.escape(role)
                        type_esc = (
                            html.escape(f" · {mtype}" + (f" ({ev_t})" if ev_t else ""))
                            if mtype != "text"
                            else ""
                        )
                        st.markdown(
                            f'<div style="border-left:4px solid #c0392b;padding:10px 12px;margin:8px 0;'
                            f'background:rgba(192,57,43,0.07);border-radius:4px">'
                            f"<strong>{role_esc}</strong>{type_esc} · "
                            f"<code>{ts_esc}</code>"
                            f'<br/><span style="font-size:0.85rem;color:#922;">Matches: {labels_html}</span>'
                            f"<br/><br/>{body}</div>",
                            unsafe_allow_html=True,
                        )
                    else:
                        st.markdown(
                            f"**{role}**{type_note} · `{m.get('timestamp', '')}`\n\n{display_text}"
                        )

                    _row_key = f"{cid}_{mi}_{m.get('_id', '')}"
                    if role == "Assistant" and products:
                        if st.checkbox(
                            f"Show product payload ({len(products)} items)",
                            key=f"pl_{_row_key}",
                            value=False,
                        ):
                            for p in products:
                                st.markdown(
                                    f"**{p.title}** · `{p.price}`"
                                    + (f"  \n{p.link}" if p.link else "")
                                )
            else:
                st.caption("No local transcript found for this conversation ID.")


report = load_report()
all_evals = load_all_evaluations()
eval_by_id = {str(e.get("conversation_id", "")): e for e in all_evals if e.get("conversation_id")}
msg_index = load_messages_index()

# ── Sidebar filters ──
st.sidebar.header("Filters")
brand_names = [b["brand_name"] for b in report.get("brands", [])]
sel_brands = st.sidebar.multiselect(
    "Brands",
    options=brand_names,
    default=brand_names,
)
score_min, score_max = st.sidebar.slider(
    "Overall score range",
    min_value=0.0,
    max_value=5.0,
    value=(0.0, 5.0),
    step=0.5,
)
cluster_themes = sorted(
    {c.get("parent_theme") or "Uncategorized" for c in report.get("discovered_clusters", [])}
)
theme_filter = st.sidebar.multiselect(
    "Cluster themes",
    options=cluster_themes,
    default=cluster_themes,
)

st.title("Conversation Intelligence")
st.caption(
    f"Generated: {report.get('generated_at', '')} | "
    f"{report.get('total_conversations', 0)} conversations analyzed"
)

tabs = st.tabs(["Overview", "Brand deep-dive", "Clusters", "Worst conversations"])

# Filter helpers
def brand_visible(name: str) -> bool:
    return name in sel_brands


def score_ok(score: float) -> bool:
    return score_min <= score <= score_max


def cluster_visible(c: dict) -> bool:
    th = c.get("parent_theme") or "Uncategorized"
    return th in theme_filter


def cluster_brand_breakdown(c: dict) -> dict[str, int]:
    affected = c.get("affected_brands") or {}
    return {
        b: int(affected.get(b, 0))
        for b in sel_brands
        if int(affected.get(b, 0)) > 0
    }


def cluster_display_count(c: dict) -> int:
    scoped = cluster_brand_breakdown(c)
    if scoped:
        return sum(scoped.values())
    return int(c.get("count", 0))


THEME_CROSS = "Cross-brand & identity"
THEME_ORDERS = "Orders & fulfillment"
THEME_PRODUCT = "Product knowledge & recommendations"
KNOWN_THEMES = [THEME_CROSS, THEME_ORDERS, THEME_PRODUCT]


def _joined_eval_text(ev: dict) -> str:
    parts: list[str] = []
    parts.extend(ev.get("failure_descriptions") or [])
    parts.extend(ev.get("frustration_signals") or [])
    parts.append(ev.get("user_intent") or "")
    parts.append(ev.get("open_observations") or "")
    for dim in (ev.get("dimensions") or {}).values():
        if not isinstance(dim, dict):
            continue
        parts.extend(dim.get("issues") or [])
        parts.extend(dim.get("evidence") or [])
    return " ".join(p for p in parts if p).lower()


def _keyword_hits(text: str, keywords: tuple[str, ...]) -> int:
    return sum(1 for kw in keywords if kw in text)


def classify_eval_theme(ev: dict) -> dict:
    """Pick the strongest visible theme for review purposes."""
    dims = ev.get("dimensions") or {}

    def dim_score(name: str, default: float = 5.0) -> float:
        d = dims.get(name) or {}
        try:
            return float(d.get("score", default))
        except Exception:
            return default

    blob = _joined_eval_text(ev)
    scores = {theme: 0.0 for theme in KNOWN_THEMES}

    cross_keywords = (
        "cross-brand",
        "wrong brand",
        "different brand",
        "belongs to a different brand",
        "brand contamination",
        "blue nectar",
        "blue tea",
        "sri sri tattva",
    )
    order_keywords = (
        "order",
        "tracking",
        "track",
        "cancel",
        "refund",
        "return",
        "exchange",
        "dispatch",
        "delivery",
        "shipment",
        "shipped",
    )
    product_keywords = (
        "product",
        "ingredient",
        "benefit",
        "suitable",
        "safe",
        "long-term",
        "recommend",
        "recommendation",
        "shampoo",
        "tea",
        "serum",
        "cream",
        "soap",
        "usage",
        "price",
    )

    cross_dim = dim_score("cross_brand_check")
    hall_dim = dim_score("hallucination_check")
    fact_dim = dim_score("factual_accuracy")
    policy_dim = dim_score("policy_compliance")
    resolution = bool(ev.get("resolution_achieved"))

    scores[THEME_CROSS] += max(0.0, 5.0 - cross_dim) * 3.0
    scores[THEME_CROSS] += _keyword_hits(blob, cross_keywords) * 2.5

    order_hit_count = _keyword_hits(blob, order_keywords)
    scores[THEME_ORDERS] += order_hit_count * 1.6
    if order_hit_count and not resolution:
        scores[THEME_ORDERS] += 1.2
    if order_hit_count and policy_dim < 4.0:
        scores[THEME_ORDERS] += 0.8

    product_hit_count = _keyword_hits(blob, product_keywords)
    scores[THEME_PRODUCT] += max(0.0, 5.0 - fact_dim) * 1.5
    scores[THEME_PRODUCT] += max(0.0, 5.0 - hall_dim) * 1.2
    scores[THEME_PRODUCT] += product_hit_count * 0.8

    ranked = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
    primary_theme, primary_score = ranked[0]
    secondary_theme, secondary_score = ranked[1]
    return {
        "primary_theme": primary_theme if primary_score > 0 else None,
        "primary_score": primary_score,
        "secondary_theme": secondary_theme if secondary_score > 0 else None,
        "secondary_score": secondary_score,
        "scores": scores,
    }


filtered_brands = [b for b in report.get("brands", []) if brand_visible(b["brand_name"])]
theme_filter_active = len(theme_filter) < len(cluster_themes)
theme_scoped_conversation_ids: set[str] = set()
if sel_brands:
    for c in report.get("discovered_clusters", []):
        if not cluster_visible(c):
            continue
        if not cluster_brand_breakdown(c):
            continue
        theme_scoped_conversation_ids.update(str(cid) for cid in (c.get("conversation_ids") or []))

filtered_clusters = []
if sel_brands:
    for c in report.get("discovered_clusters", []):
        if not cluster_visible(c):
            continue
        scoped_brands = cluster_brand_breakdown(c)
        if not scoped_brands:
            continue
        display_count = cluster_display_count(c)
        if display_count < 5:
            continue
        c_view = dict(c)
        c_view["_display_count"] = display_count
        c_view["_display_brands"] = scoped_brands
        filtered_clusters.append(c_view)
filtered_clusters.sort(key=lambda c: c.get("_display_count", c.get("count", 0)), reverse=True)

filtered_rollups: list[dict] = []
rollup_map: dict[str, dict] = {}
for c in filtered_clusters:
    theme = c.get("parent_theme") or "Uncategorized"
    row = rollup_map.setdefault(theme, {"parent_theme": theme, "cluster_labels": [], "total_count": 0})
    row["cluster_labels"].append(c.get("auto_label", ""))
    row["total_count"] += int(c.get("_display_count", c.get("count", 0)))
filtered_rollups = sorted(rollup_map.values(), key=lambda r: r["total_count"], reverse=True)

# ── Tab: Overview ──
with tabs[0]:
    st.subheader("Executive pulse")
    n_br = max(len(filtered_brands), 1)
    cols = st.columns(min(n_br + 1, 5))
    with cols[0]:
        if filtered_brands:
            avg_all = sum(b["avg_overall_score"] for b in filtered_brands) / len(filtered_brands)
        else:
            avg_all = 0.0
        st.metric("Avg score (filtered brands)", f"{avg_all:.2f}/5.0")
        st.metric("Clusters (filtered)", len(filtered_clusters))
    for i, brand in enumerate(filtered_brands[:4]):
        with cols[i + 1] if i + 1 < len(cols) else cols[-1]:
            st.markdown(f"**{brand['brand_name']}**")
            st.metric("Score", f"{brand['avg_overall_score']}/5.0")
            st.caption(f"Resolution {brand['resolution_rate']:.0%}")

    st.divider()
    st.subheader("Executive summary")
    st.write(report.get("executive_summary", ""))

    st.divider()
    st.subheader("Score distribution")
    ev_scores = []
    if all_evals:
        for e in all_evals:
            if not brand_visible(e.get("brand_name", "")):
                continue
            s = float(e.get("overall_score", 0))
            if score_ok(s):
                ev_scores.append({"brand": e.get("brand_name"), "score": s})
    else:
        st.info("Run the full pipeline to generate `output/all_evaluations.json` for per-conversation histograms.")
    if ev_scores:
        df_s = pd.DataFrame(ev_scores)
        fig_hist = px.histogram(
            df_s,
            x="score",
            color="brand",
            nbins=20,
            opacity=0.75,
            title="Overall score distribution by brand",
        )
        fig_hist.update_layout(bargap=0.05, height=400)
        st.plotly_chart(fig_hist, use_container_width=True)

    st.divider()
    st.subheader("Brand × dimension heatmap")
    heatmap_data = []
    for brand in filtered_brands:
        for dim, score in brand.get("dimension_scores", {}).items():
            heatmap_data.append(
                {
                    "Brand": brand["brand_name"],
                    "Dimension": dim.replace("_", " ").title(),
                    "Score": score,
                }
            )
    if heatmap_data:
        df_heat = pd.DataFrame(heatmap_data)
        pivot = df_heat.pivot(index="Brand", columns="Dimension", values="Score")
        fig_h = px.imshow(
            pivot,
            color_continuous_scale="RdYlGn",
            zmin=1,
            zmax=5,
            text_auto=".1f",
            aspect="auto",
            title="Quality scores (1=worst, 5=best)",
        )
        fig_h.update_layout(height=380)
        st.plotly_chart(fig_h, use_container_width=True)

    # Theme rollups
    if filtered_rollups:
        st.divider()
        st.subheader("Issue themes (hierarchical)")
        df_r = pd.DataFrame(
            [{"theme": r["parent_theme"], "signals": r["total_count"]} for r in filtered_rollups]
        )
        fig_bar = px.bar(
            df_r,
            x="theme",
            y="signals",
            title="Signal volume by parent theme",
            color="signals",
            color_continuous_scale="Reds",
        )
        fig_bar.update_layout(height=400, showlegend=False, xaxis_tickangle=-25)
        st.plotly_chart(fig_bar, use_container_width=True)

    # Sankey: brand -> theme (link values = sum of affected_brands per cluster in that theme)
    if filtered_rollups and filtered_brands:
        st.divider()
        st.subheader("Flow: brands → issue themes (signal counts)")
        brand_labels = [f"Brand: {b['brand_name']}" for b in filtered_brands]
        theme_labels = [f"Theme: {r['parent_theme']}" for r in filtered_rollups]
        labels = brand_labels + theme_labels
        label_index = {l: i for i, l in enumerate(labels)}
        source, target, value = [], [], []
        for i, b in enumerate(filtered_brands):
            bname = b["brand_name"]
            for j, r in enumerate(filtered_rollups):
                theme_name = r["parent_theme"]
                theme_clusters = [
                    c
                    for c in filtered_clusters
                    if (c.get("parent_theme") or "Uncategorized") == theme_name
                ]
                v = sum(
                    int((c.get("_display_brands") or {}).get(bname, 0))
                    for c in theme_clusters
                )
                if v > 0:
                    source.append(label_index[brand_labels[i]])
                    target.append(label_index[theme_labels[j]])
                    value.append(v)
        if source:
            fig_sk = go.Figure(
                data=[
                    go.Sankey(
                        node=dict(label=labels, pad=12, thickness=10),
                        link=dict(source=source, target=target, value=value),
                    )
                ]
            )
            fig_sk.update_layout(height=450, title_text="")
            st.plotly_chart(fig_sk, use_container_width=True)
        else:
            st.caption("No brand–theme links to plot (try widening brand filters).")

# ── Tab: Brand deep-dive ──
with tabs[1]:
    st.subheader("Radar: dimension profiles")
    dim_names = None
    for b in filtered_brands:
        if b.get("dimension_scores"):
            dim_names = list(b["dimension_scores"].keys())
            break
    if dim_names:
        fig = go.Figure()
        for b in filtered_brands:
            scores = [b.get("dimension_scores", {}).get(d, 0) for d in dim_names]
            fig.add_trace(
                go.Scatterpolar(
                    r=scores + [scores[0]],
                    theta=[d.replace("_", " ") for d in dim_names] + [dim_names[0].replace("_", " ")],
                    fill="toself",
                    name=b["brand_name"],
                )
            )
        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 5])),
            showlegend=True,
            height=520,
            title="Dimension comparison (0–5)",
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No dimension scores in report.")

    for b in filtered_brands:
        with st.expander(f"{b['brand_name']} — metrics"):
            c1, c2, c3 = st.columns(3)
            c1.metric("Resolution", f"{b['resolution_rate']:.0%}")
            c2.metric("Hallucination (dim≤2)", f"{b['hallucination_rate']:.0%}")
            c3.metric("Frustration", f"{b['frustration_rate']:.0%}")
            tops = b.get("top_failure_clusters") or []
            if tops:
                st.write("**Top failure clusters:** " + ", ".join(tops))

# ── Tab: Clusters ──
with tabs[2]:
    st.subheader("Discovered clusters")
    if not filtered_clusters:
        st.warning("No clusters match filters (try widening theme filter or lowering min count).")
    df_c = pd.DataFrame(
        [
            {
                "label": c.get("auto_label"),
                "count": c.get("_display_count", c.get("count")),
                "severity": c.get("severity_avg"),
                "theme": c.get("parent_theme") or "Uncategorized",
                "cross_brand": c.get("is_cross_brand"),
            }
            for c in filtered_clusters
        ]
    )
    if not df_c.empty:
        fig_treemap = px.treemap(
            df_c,
            path=["theme", "label"],
            values="count",
            color="severity",
            color_continuous_scale="RdYlGn_r",
            title="Clusters by theme (size = count, color = avg severity)",
        )
        fig_treemap.update_layout(height=520)
        st.plotly_chart(fig_treemap, use_container_width=True)

        fig_bar2 = px.bar(
            df_c.sort_values("count", ascending=True).tail(15),
            x="count",
            y="label",
            orientation="h",
            color="severity",
            color_continuous_scale="RdYlGn_r",
            title="Top clusters by volume",
        )
        fig_bar2.update_layout(height=480, yaxis_title="")
        st.plotly_chart(fig_bar2, use_container_width=True)

    for cluster in filtered_clusters[:25]:
        theme = cluster.get("parent_theme") or ""
        sev = float(cluster.get("severity_avg", 3))
        emoji = "🔴" if sev < 2.5 else "🟡" if sev < 3.5 else "🟢"
        brands_map = cluster.get("_display_brands") or (cluster.get("affected_brands") or {})
        brands = ", ".join(brands_map.keys())
        with st.expander(
            f"{emoji} **{cluster.get('auto_label')}** — {cluster.get('_display_count', cluster.get('count'))} | {theme} | {brands}"
        ):
            st.caption(f"Avg conversation score in cluster: {sev}/5.0")
            for ex in cluster.get("examples") or []:
                st.markdown(f"- {ex}")
            if cluster.get("is_cross_brand"):
                st.warning("Cross-brand — likely systemic.")
            if brands_map:
                st.caption(
                    "Brand counts in current filter: "
                    + ", ".join(f"{k}: {v}" for k, v in brands_map.items())
                )
            ids = cluster.get("sample_conversation_ids") or []
            st.write("Sample IDs: " + ", ".join(ids[:5]))

# ── Tab: Worst conversations + transcripts ──
with tabs[3]:
    st.subheader("Lowest-scored conversations")
    review_pool = all_evals if all_evals else (report.get("worst_conversations") or [])
    primary_reviews = []
    mixed_reviews = []
    excluded_no_text = 0
    for e in review_pool:
        if not brand_visible(e.get("brand_name", "")):
            continue
        if not score_ok(float(e.get("overall_score", 0))):
            continue
        cid = str(e.get("conversation_id", ""))
        if theme_filter_active and cid not in theme_scoped_conversation_ids:
            continue
        transcript = msg_index.get(cid, [])
        has_text_turns = any((m.get("messageType") or "text") == "text" for m in transcript)
        if not has_text_turns:
            excluded_no_text += 1
            continue
        merged = merge_eval_from_store(cid, e, eval_by_id)
        theme_meta = classify_eval_theme(merged)
        if theme_filter_active and theme_meta["primary_theme"] not in theme_filter:
            mixed_reviews.append((e, theme_meta))
        else:
            primary_reviews.append((e, theme_meta))

    primary_reviews.sort(
        key=lambda item: (
            float(item[0].get("overall_score", 0)),
            str(item[0].get("brand_name", "")),
            str(item[0].get("conversation_id", "")),
        )
    )
    mixed_reviews.sort(
        key=lambda item: (
            float(item[0].get("overall_score", 0)),
            str(item[0].get("brand_name", "")),
            str(item[0].get("conversation_id", "")),
        )
    )

    if excluded_no_text:
        st.caption(
            f"Excluded {excluded_no_text} event-only / no-text sessions from this review list."
        )
    if not all_evals:
        st.info(
            "Showing only the saved `report.json` worst sample. Run the full pipeline to refresh "
            "`output/all_evaluations.json` and browse all conversations here."
        )
    if not primary_reviews and not mixed_reviews:
        st.warning("No reviewable conversations match the current filters.")
    else:
        st.caption(
            f"Showing {len(primary_reviews) + len(mixed_reviews)} reviewable conversations after filters."
        )
        if theme_filter_active:
            st.caption("Primary matches are shown first. Mixed-theme conversations are separated below.")

    if primary_reviews:
        st.markdown("#### Primary theme matches")
        for ev, _theme_meta in primary_reviews:
            render_review_conversation(ev)

    if mixed_reviews:
        st.divider()
        st.markdown("#### Mixed-theme conversations")
        st.caption(
            "These conversations belong to the selected cluster theme(s) by clustering, "
            "but their strongest visible issue reads as another theme."
        )
        for ev, theme_meta in mixed_reviews:
            primary_theme = theme_meta.get("primary_theme") or "another theme"
            render_review_conversation(
                ev,
                mixed_note=(
                    f"This conversation is linked to the selected theme by clustering, "
                    f"but its strongest visible issue reads as **{primary_theme}**."
                ),
            )

st.sidebar.markdown("---")
st.sidebar.caption(f"Data dir: `{DATA_DIR}` | Output: `{OUTPUT_DIR}`")
