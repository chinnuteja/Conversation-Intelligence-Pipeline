"""
Streamlit Dashboard — Conversation Intelligence

Run from repo root: streamlit run dashboard/app.py
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
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


report = load_report()
all_evals = load_all_evaluations()
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


filtered_brands = [b for b in report.get("brands", []) if brand_visible(b["brand_name"])]
filtered_clusters = [
    c
    for c in report.get("discovered_clusters", [])
    if cluster_visible(c) and c.get("count", 0) >= 5
]
filtered_clusters.sort(key=lambda c: c.get("count", 0), reverse=True)

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
    rollups = report.get("cluster_theme_rollups") or []
    if rollups:
        st.divider()
        st.subheader("Issue themes (hierarchical)")
        df_r = pd.DataFrame(
            [{"theme": r["parent_theme"], "signals": r["total_count"]} for r in rollups]
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
    if rollups and filtered_brands:
        st.divider()
        st.subheader("Flow: brands → issue themes (signal counts)")
        all_clusters = report.get("discovered_clusters") or []
        brand_labels = [f"Brand: {b['brand_name']}" for b in filtered_brands]
        theme_labels = [f"Theme: {r['parent_theme']}" for r in rollups]
        labels = brand_labels + theme_labels
        label_index = {l: i for i, l in enumerate(labels)}
        source, target, value = [], [], []
        for i, b in enumerate(filtered_brands):
            bname = b["brand_name"]
            for j, r in enumerate(rollups):
                theme_name = r["parent_theme"]
                theme_clusters = [
                    c
                    for c in all_clusters
                    if (c.get("parent_theme") or "Uncategorized") == theme_name
                ]
                v = sum(
                    int((c.get("affected_brands") or {}).get(bname, 0))
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
                "count": c.get("count"),
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
        brands = ", ".join((cluster.get("affected_brands") or {}).keys())
        with st.expander(
            f"{emoji} **{cluster.get('auto_label')}** — {cluster.get('count')} | {theme} | {brands}"
        ):
            st.caption(f"Avg conversation score in cluster: {sev}/5.0")
            for ex in cluster.get("examples") or []:
                st.markdown(f"- {ex}")
            if cluster.get("is_cross_brand"):
                st.warning("Cross-brand — likely systemic.")
            ids = cluster.get("sample_conversation_ids") or []
            st.write("Sample IDs: " + ", ".join(ids[:5]))

# ── Tab: Worst conversations + transcripts ──
with tabs[3]:
    st.subheader("Lowest-scored conversations")
    worst = report.get("worst_conversations") or []
    worst_f = [
        e
        for e in worst
        if brand_visible(e.get("brand_name", "")) and score_ok(float(e.get("overall_score", 0)))
    ]
    for ev in worst_f[:20]:
        intent = (ev.get("user_intent") or "")[:80]
        with st.expander(
            f"{ev.get('overall_score')}/5 — {ev.get('brand_name')} — {intent}"
        ):
            cid = ev.get("conversation_id", "")
            st.code(cid, language="text")
            if ev.get("failure_descriptions"):
                st.error("Issues")
                for fd in ev["failure_descriptions"]:
                    st.write(f"- {fd}")
            if ev.get("frustration_signals"):
                st.warning("Frustration")
                for fs in ev["frustration_signals"]:
                    st.write(f"- {fs}")
            if ev.get("open_observations"):
                st.info(ev["open_observations"])

            transcript = msg_index.get(cid, [])
            if transcript:
                st.markdown("**Transcript** (from `data/messages.json`)")
                for m in transcript:
                    if m.get("messageType") != "text":
                        continue
                    role = "User" if m.get("sender") == "user" else "Assistant"
                    st.markdown(
                        f"**{role}** · `{m.get('timestamp', '')}`\n\n"
                        f"{(m.get('text') or '')[:4000]}"
                    )
            else:
                st.caption("No local transcript found for this conversation ID.")

st.sidebar.markdown("---")
st.sidebar.caption(f"Data dir: `{DATA_DIR}` | Output: `{OUTPUT_DIR}`")
