"""
Generate a self-contained shareable HTML results page from report.json.

Run automatically after the pipeline, or standalone:
    python -m src.generate_results_page
"""

from __future__ import annotations

import html
import json
import logging
import os
from pathlib import Path

from src.config import OUTPUT_DIR

logger = logging.getLogger(__name__)

# Short labels for cluster brand columns (matches common brand names in dataset)
BRAND_ABBREV = {
    "Blue Nectar": "BN",
    "Sri Sri Tattva": "SST",
    "Blue Tea": "BT",
}


def _esc(s: str) -> str:
    return html.escape(s or "", quote=True)


def _abbrev_brands(affected: dict) -> str:
    parts = []
    for name, count in sorted(affected.items(), key=lambda x: -x[1]):
        ab = BRAND_ABBREV.get(name, name[:3].upper())
        parts.append(f"{ab}: {count}")
    return " | ".join(parts)


def _load_eval_stats(output_dir: str) -> tuple[int, float, int]:
    """(failed_evals, avg_overall_score, total_evaluated) from all_evaluations.json if present."""
    path = os.path.join(output_dir, "all_evaluations.json")
    if not os.path.isfile(path):
        return 0, 0.0, 0
    with open(path, encoding="utf-8") as f:
        evs = json.load(f)
    n = len(evs)
    if n == 0:
        return 0, 0.0, 0
    failed = 0
    scores = []
    for e in evs:
        sc = float(e.get("overall_score", 0))
        fds = e.get("failure_descriptions") or []
        if sc <= 0 or any(
            isinstance(x, str) and x.startswith("EVALUATION_ERROR") for x in fds
        ):
            failed += 1
        if sc > 0:
            scores.append(sc)
    avg = sum(scores) / len(scores) if scores else 0.0
    return failed, round(avg, 2), n


def _weighted_avg_from_report(report: dict) -> float:
    brands = report.get("brands") or []
    total_w = 0
    s = 0.0
    for b in brands:
        w = int(b.get("conversation_count", 0))
        total_w += w
        s += float(b.get("avg_overall_score", 0)) * w
    return round(s / total_w, 2) if total_w else 0.0


def generate_results_html(output_dir: str | None = None) -> Path:
    out = Path(output_dir or OUTPUT_DIR)
    out.mkdir(parents=True, exist_ok=True)
    report_path = out / "report.json"
    if not report_path.is_file():
        raise FileNotFoundError(f"Missing {report_path}; run pipeline first.")

    with open(report_path, encoding="utf-8") as f:
        report = json.load(f)

    total_conv = int(report.get("total_conversations", 0))
    clusters = report.get("discovered_clusters") or []
    n_clusters = len(clusters)
    failed_evals, avg_score, n_eval = _load_eval_stats(str(out))
    if n_eval == 0:
        avg_score = _weighted_avg_from_report(report)
        n_eval = total_conv
        failed_evals = 0
    success_pct = (
        round(100.0 * (n_eval - failed_evals) / n_eval, 1) if n_eval else 100.0
    )

    exec_summary = report.get("executive_summary") or ""
    brands = sorted(
        report.get("brands") or [],
        key=lambda b: -float(b.get("avg_overall_score", 0)),
    )
    worst = report.get("worst_conversations") or []

    # Brand table header order
    brand_headers = [
        "Brand",
        "Overall score",
        "Resolution",
        "Hallucination",
        "Frustration",
        "Cross-brand",
        "Factual accuracy",
        "Add-to-cart",
    ]
    brand_rows_html = []
    for b in brands:
        dims = b.get("dimension_scores") or {}
        brand_rows_html.append(
            "<tr>"
            f"<td><strong>{_esc(b.get('brand_name', ''))}</strong></td>"
            f"<td>{b.get('avg_overall_score', 0):.2f} / 5.0</td>"
            f"<td>{b.get('resolution_rate', 0):.0%}</td>"
            f"<td>{b.get('hallucination_rate', 0):.0%}</td>"
            f"<td>{b.get('frustration_rate', 0):.0%}</td>"
            f"<td>{dims.get('cross_brand_check', 0):.2f} / 5.0</td>"
            f"<td>{dims.get('factual_accuracy', 0):.2f} / 5.0</td>"
            f"<td>{b.get('add_to_cart_rate', 0):.0%}</td>"
            "</tr>"
        )

    cluster_rows_html = []
    for c in sorted(clusters, key=lambda x: -int(x.get("count", 0))):
        cluster_rows_html.append(
            "<tr>"
            f"<td>{_esc(c.get('auto_label', ''))}</td>"
            f"<td class='num'>{c.get('count', 0)}</td>"
            f"<td class='num'>{c.get('severity_avg', 0):.2f}</td>"
            f"<td class='small'>{_esc(_abbrev_brands(c.get('affected_brands') or {}))}</td>"
            "</tr>"
        )

    worst_rows_html = []
    for ev in worst[:12]:
        cid = str(ev.get("conversation_id", ""))
        cid_short = cid[:10] + "…" if len(cid) > 10 else cid
        fds = ev.get("failure_descriptions") or []
        primary = fds[0] if fds else (ev.get("user_intent") or "")
        worst_rows_html.append(
            "<tr>"
            f"<td class='mono'>{_esc(cid_short)}</td>"
            f"<td>{_esc(ev.get('brand_name', ''))}</td>"
            f"<td class='num'>{ev.get('overall_score', 0)}</td>"
            f"<td>{_esc(primary[:200])}</td>"
            "</tr>"
        )

    generated = _esc(str(report.get("generated_at", "")))

    html_doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Conversation Intelligence — Results</title>
  <style>
    :root {{
      --bg: #f6f7f9;
      --card: #fff;
      --text: #1a1a1a;
      --muted: #5c6370;
      --accent: #1e3a5f;
      --border: #e2e5eb;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      font-family: "Segoe UI", system-ui, -apple-system, sans-serif;
      color: var(--text);
      background: var(--bg);
      line-height: 1.5;
      margin: 0;
      padding: 2rem;
      max-width: 960px;
      margin-left: auto;
      margin-right: auto;
    }}
    h1 {{
      font-size: 1.5rem;
      margin: 0 0 0.25rem 0;
      color: var(--accent);
    }}
    .subtitle {{ color: var(--muted); font-size: 0.95rem; margin-bottom: 1.5rem; }}
    .meta {{ font-size: 0.85rem; color: var(--muted); margin-bottom: 2rem; }}
    section {{
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 1.25rem 1.5rem;
      margin-bottom: 1.5rem;
      page-break-inside: avoid;
    }}
    section h2 {{
      font-size: 1.05rem;
      margin: 0 0 1rem 0;
      padding-bottom: 0.5rem;
      border-bottom: 2px solid var(--accent);
      color: var(--accent);
    }}
    .metrics {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
      gap: 0.75rem;
      margin-bottom: 1.25rem;
    }}
    .metric {{
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 6px;
      padding: 0.75rem;
      text-align: center;
    }}
    .metric .val {{ font-size: 1.35rem; font-weight: 700; color: var(--accent); }}
    .metric .lbl {{ font-size: 0.75rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.03em; }}
    .exec {{
      white-space: pre-wrap;
      font-size: 0.95rem;
      color: #333;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 0.88rem;
    }}
    th, td {{
      border: 1px solid var(--border);
      padding: 0.5rem 0.65rem;
      text-align: left;
    }}
    th {{
      background: #eef1f6;
      font-weight: 600;
      color: var(--accent);
    }}
    tr:nth-child(even) {{ background: #fafbfc; }}
    .num {{ text-align: right; }}
    .small {{ font-size: 0.82rem; }}
    .mono {{ font-family: ui-monospace, monospace; font-size: 0.85rem; }}
    .stage {{
      border-left: 4px solid var(--accent);
      padding-left: 1rem;
      margin-bottom: 1rem;
    }}
    .stage h3 {{ margin: 0 0 0.35rem 0; font-size: 0.95rem; }}
    .stage .tech {{ font-size: 0.82rem; color: var(--muted); }}
    ul.decisions {{ margin: 0; padding-left: 1.2rem; }}
    ul.decisions li {{ margin-bottom: 0.5rem; }}
    footer {{
      text-align: center;
      font-size: 0.8rem;
      color: var(--muted);
      margin-top: 2rem;
    }}
    @media print {{
      body {{ background: #fff; padding: 1rem; }}
      section {{ box-shadow: none; page-break-inside: avoid; }}
      .metrics {{ break-inside: avoid; }}
    }}
  </style>
</head>
<body>
  <h1>Conversation Intelligence Pipeline — Automated Analysis Report</h1>
  <p class="subtitle">{total_conv} conversations across {len(brands)} e-commerce brands<br/>
  Four-stage pipeline: ingest, LLM-as-judge evaluation (structured JSON), semantic clustering (UMAP + HDBSCAN), aggregate &amp; executive summary.</p>
  <p class="meta">Generated: {generated}</p>

  <section>
    <h2>At a glance</h2>
    <div class="metrics">
      <div class="metric"><div class="val">{total_conv}</div><div class="lbl">Conversations</div></div>
      <div class="metric"><div class="val">{n_clusters}</div><div class="lbl">Issue clusters</div></div>
      <div class="metric"><div class="val">{failed_evals}</div><div class="lbl">Failed evaluations</div></div>
      <div class="metric"><div class="val">{avg_score}</div><div class="lbl">Avg score (1–5)</div></div>
      <div class="metric"><div class="val">{success_pct}%</div><div class="lbl">Eval success rate</div></div>
    </div>
    <h2 style="border:none;padding:0;margin-top:0">Executive summary</h2>
    <div class="exec">{_esc(exec_summary)}</div>
  </section>

  <section>
    <h2>Brand performance</h2>
    <table>
      <thead><tr>{''.join(f'<th>{_esc(h)}</th>' for h in brand_headers)}</tr></thead>
      <tbody>{''.join(brand_rows_html)}</tbody>
    </table>
  </section>

  <section>
    <h2>Discovered issue clusters</h2>
    <p class="small" style="margin-top:0;color:var(--muted)">Themes from embedded failure signals + HDBSCAN; labels merged conservatively (embedding similarity + LLM pass).</p>
    <table>
      <thead>
        <tr><th>Cluster</th><th>Count</th><th>Severity avg</th><th>Brands affected</th></tr>
      </thead>
      <tbody>{''.join(cluster_rows_html)}</tbody>
    </table>
  </section>

  <section>
    <h2>Worst conversations (sample)</h2>
    <table>
      <thead>
        <tr><th>Conversation</th><th>Brand</th><th>Score</th><th>Primary failure</th></tr>
      </thead>
      <tbody>{''.join(worst_rows_html)}</tbody>
    </table>
  </section>

  <section>
    <h2>System architecture</h2>
    <div class="stage">
      <h3>Stage 1 — Ingest &amp; normalize</h3>
      <p>Parse conversations and messages; split agent text at <code>End of stream</code> for visible reply vs product JSON (hallucination ground truth).</p>
      <p class="tech">Python · Pydantic · JSON or MongoDB (optional)</p>
    </div>
    <div class="stage">
      <h3>Stage 2 — LLM-as-judge</h3>
      <p>Per-conversation structured evaluation (Azure OpenAI, <code>json_schema</code> response format): factual accuracy, hallucination vs catalog, policy, tone, satisfaction signals, cross-brand check.</p>
      <p class="tech">Azure OpenAI · asyncio · concurrent evaluations</p>
    </div>
    <div class="stage">
      <h3>Stage 3 — Embed, cluster, discover</h3>
      <p>Embed failure text with sentence-transformers; UMAP reduction; HDBSCAN; LLM cluster labels; conservative merge + overlap pass.</p>
      <p class="tech">sentence-transformers · UMAP · HDBSCAN</p>
    </div>
    <div class="stage">
      <h3>Stage 4 — Aggregate &amp; report</h3>
      <p>Brand rollups, top failure clusters per brand, executive summary LLM pass; JSON + Markdown + Streamlit dashboard + this HTML page.</p>
      <p class="tech">pandas · Streamlit · Plotly</p>
    </div>
  </section>

  <section>
    <h2>Key design decisions</h2>
    <ul class="decisions">
      <li><strong>Structured JSON output</strong> — Guarantees parseable evaluations vs free-form JSON that can break downstream aggregation.</li>
      <li><strong>HDBSCAN over k-means</strong> — No fixed cluster count; handles noise points suitable for exploratory issue discovery.</li>
      <li><strong>Local embeddings</strong> — <code>all-MiniLM-L6-v2</code> on CPU: fast, no extra API cost for clustering text.</li>
      <li><strong>Thin orchestration</strong> — Direct SDK calls where a single structured completion suffices; avoids heavy framework overhead for this pipeline.</li>
    </ul>
  </section>

  <section>
    <h2>Scalability &amp; path to production (sketch)</h2>
    <table>
      <thead>
        <tr><th>Dimension</th><th>MVP (this project)</th><th>Production direction</th></tr>
      </thead>
      <tbody>
        <tr><td>Data</td><td>JSON files or Mongo toggle</td><td>Incremental sync; warehouse / API</td></tr>
        <tr><td>Processing</td><td><code>python pipeline.py</code></td><td>Queue workers; scheduled or near-real-time</td></tr>
        <tr><td>Evaluation</td><td>Full LLM pass per conversation + disk cache</td><td>Triage heuristics + LLM on subset; batch API at scale</td></tr>
        <tr><td>Dashboard</td><td>Streamlit local</td><td>Auth, roles, alerts on threshold breaches</td></tr>
      </tbody>
    </table>
  </section>

  <footer>
    Conversation Intelligence Pipeline — shareable results page (open in browser; Print → Save as PDF if needed).
  </footer>
</body>
</html>
"""

    dest = out / "results.html"
    dest.write_text(html_doc, encoding="utf-8")
    logger.info("Wrote shareable results page: %s", dest)
    return dest


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    generate_results_html()


if __name__ == "__main__":
    main()
