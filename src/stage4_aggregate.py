"""
Stage 4: Aggregate & Report

Rolls up evaluations by brand, generates stats, and produces
the final structured report + human-readable markdown summary.
"""

import json
import logging
from collections import defaultdict
from datetime import datetime

from openai import AsyncOpenAI

from src.config import SUMMARY_MODEL, OUTPUT_DIR
from src.logging_config import setup_logging
from src.auth import get_vertex_token, get_vertex_base_url
from src.models import (
    ConversationEvaluation,
    DiscoveredCluster,
    BrandReport,
    PipelineReport,
    ClusterThemeRollup,
)
from src.prompts import EXECUTIVE_SUMMARY_PROMPT

logger = logging.getLogger(__name__)

client = AsyncOpenAI(
    base_url=get_vertex_base_url(),
    api_key=get_vertex_token(),
)


def build_cluster_theme_rollups(clusters: list[DiscoveredCluster]) -> list[ClusterThemeRollup]:
    """Group clusters by parent_theme for hierarchical reporting."""
    by_theme: dict[str, list[DiscoveredCluster]] = defaultdict(list)
    for c in clusters:
        theme = c.parent_theme or "Uncategorized"
        by_theme[theme].append(c)
    rollups = []
    for theme, members in sorted(by_theme.items(), key=lambda x: -sum(c.count for c in x[1])):
        rollups.append(
            ClusterThemeRollup(
                parent_theme=theme,
                cluster_labels=[c.auto_label for c in members],
                total_count=sum(c.count for c in members),
            )
        )
    return rollups


def aggregate_by_brand(
    evaluations: list[ConversationEvaluation],
    clusters: list[DiscoveredCluster] | None = None,
) -> list[BrandReport]:
    """Compute per-brand aggregate statistics."""
    brand_groups = defaultdict(list)
    for ev in evaluations:
        brand_groups[ev.brand_name].append(ev)

    reports = []
    for brand_name, evals in brand_groups.items():
        n = len(evals)
        valid_evals = [e for e in evals if e.overall_score > 0]

        if not valid_evals:
            continue

        avg_score = sum(e.overall_score for e in valid_evals) / len(valid_evals)
        resolution_rate = sum(1 for e in valid_evals if e.resolution_achieved) / len(valid_evals)

        hallucination_evals = [
            e
            for e in valid_evals
            if "hallucination_check" in e.dimensions
            and e.dimensions["hallucination_check"].score <= 2.0
        ]
        hallucination_rate = len(hallucination_evals) / len(valid_evals)

        frustrated = [e for e in valid_evals if len(e.frustration_signals) > 0]
        frustration_rate = len(frustrated) / len(valid_evals)

        atc = sum(1 for e in valid_evals if e.has_add_to_cart)
        atc_rate = atc / len(valid_evals)

        dim_scores = defaultdict(list)
        for e in valid_evals:
            for dim_name, dim_eval in e.dimensions.items():
                dim_scores[dim_name].append(dim_eval.score)
        avg_dim_scores = {k: round(sum(v) / len(v), 2) for k, v in dim_scores.items()}

        top_failure_clusters: list[str] = []
        if clusters:
            brand_clusters = [
                c for c in clusters if brand_name in c.affected_brands
            ]
            brand_clusters.sort(
                key=lambda c: c.affected_brands.get(brand_name, 0),
                reverse=True,
            )
            top_failure_clusters = [c.auto_label for c in brand_clusters[:5]]

        reports.append(
            BrandReport(
                brand_name=brand_name,
                widget_id=evals[0].widget_id,
                conversation_count=n,
                avg_overall_score=round(avg_score, 2),
                resolution_rate=round(resolution_rate, 3),
                hallucination_rate=round(hallucination_rate, 3),
                frustration_rate=round(frustration_rate, 3),
                add_to_cart_rate=round(atc_rate, 3),
                top_failure_clusters=top_failure_clusters,
                dimension_scores=avg_dim_scores,
            )
        )

    return sorted(reports, key=lambda r: r.avg_overall_score)


async def generate_executive_summary(report: PipelineReport) -> str:
    """Use Azure OpenAI to write a human-readable executive summary."""
    logger.info(
        "Executive summary: calling model %s (single request; may take 1–3+ min)...",
        SUMMARY_MODEL,
    )
    report_data = {
        "total_conversations": report.total_conversations,
        "brands": [
            {
                "name": b.brand_name,
                "avg_score": b.avg_overall_score,
                "resolution_rate": f"{b.resolution_rate:.0%}",
                "hallucination_rate": f"{b.hallucination_rate:.0%}",
                "frustration_rate": f"{b.frustration_rate:.0%}",
                "add_to_cart_rate": f"{b.add_to_cart_rate:.0%}",
                "dimension_scores": b.dimension_scores,
                "top_failure_clusters": b.top_failure_clusters,
            }
            for b in report.brands
        ],
        "cluster_theme_rollups": [
            {
                "theme": t.parent_theme,
                "clusters": t.cluster_labels,
                "total_count": t.total_count,
            }
            for t in report.cluster_theme_rollups[:8]
        ],
        "top_issue_clusters": [
            {
                "label": c.auto_label,
                "count": c.count,
                "severity_avg": c.severity_avg,
                "parent_theme": c.parent_theme,
                "affected_brands": c.affected_brands,
                "examples": c.examples[:3],
            }
            for c in report.discovered_clusters[:10]
        ],
        "worst_conversations": [
            {
                "id": c.conversation_id,
                "brand": c.brand_name,
                "score": c.overall_score,
                "intent": c.user_intent,
                "failures": c.failure_descriptions,
            }
            for c in report.worst_conversations[:5]
        ],
    }

    prompt = EXECUTIVE_SUMMARY_PROMPT.format(report_data=json.dumps(report_data, indent=2))

    response = await client.chat.completions.create(
        model=SUMMARY_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1500,
    )
    content = response.choices[0].message.content
    return content.strip() if content else "Executive summary could not be generated (empty response or safety filter triggered)."


async def build_report(
    evaluations: list[ConversationEvaluation],
    clusters: list[DiscoveredCluster],
) -> PipelineReport:
    """Main Stage 4 function. Aggregates everything into the final report."""
    setup_logging()
    logger.info("Stage 4: Aggregating results...")

    theme_rollups = build_cluster_theme_rollups(clusters)
    brand_reports = aggregate_by_brand(evaluations, clusters)
    worst = sorted(
        [e for e in evaluations if e.overall_score > 0],
        key=lambda e: e.overall_score,
    )[:20]

    report = PipelineReport(
        generated_at=datetime.now(),
        total_conversations=len(evaluations),
        brands=brand_reports,
        discovered_clusters=clusters,
        cluster_theme_rollups=theme_rollups,
        worst_conversations=worst,
    )

    logger.info("Generating executive summary...")
    report.executive_summary = await generate_executive_summary(report)

    save_report(report)
    logger.info("Report saved to %s/", OUTPUT_DIR)
    return report


def save_report(report: PipelineReport) -> None:
    """Write all output files."""
    import os

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    with open(f"{OUTPUT_DIR}/report.json", "w", encoding="utf-8") as f:
        json.dump(report.model_dump(mode="json"), f, indent=2, default=str)

    with open(f"{OUTPUT_DIR}/evaluations.json", "w", encoding="utf-8") as f:
        json.dump(
            [e.model_dump(mode="json") for e in report.worst_conversations],
            f,
            indent=2,
            default=str,
        )

    with open(f"{OUTPUT_DIR}/clusters.json", "w", encoding="utf-8") as f:
        json.dump(
            [c.model_dump(mode="json") for c in report.discovered_clusters],
            f,
            indent=2,
            default=str,
        )

    md = generate_markdown_summary(report)
    with open(f"{OUTPUT_DIR}/summary.md", "w", encoding="utf-8") as f:
        f.write(md)


def generate_markdown_summary(report: PipelineReport) -> str:
    """Generate a standalone markdown report."""
    lines = []
    lines.append("# Conversation Intelligence Report")
    lines.append(f"Generated: {report.generated_at.strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"Conversations analyzed: {report.total_conversations}")
    lines.append("")
    lines.append("## Executive Summary")
    lines.append(report.executive_summary)
    lines.append("")

    if report.cluster_theme_rollups:
        lines.append("## Issue themes (hierarchical)")
        for t in report.cluster_theme_rollups:
            lines.append(f"### {t.parent_theme} ({t.total_count} signals)")
            lines.append(f"- Clusters: {', '.join(t.cluster_labels[:8])}")
            lines.append("")

    lines.append("## Brand Performance")
    for b in report.brands:
        lines.append(f"### {b.brand_name}")
        lines.append(f"- Overall Score: **{b.avg_overall_score}/5.0**")
        lines.append(f"- Resolution Rate: {b.resolution_rate:.0%}")
        lines.append(f"- Hallucination Rate: {b.hallucination_rate:.0%}")
        lines.append(f"- Frustration Rate: {b.frustration_rate:.0%}")
        lines.append(f"- Add-to-Cart Rate: {b.add_to_cart_rate:.0%}")
        if b.top_failure_clusters:
            lines.append(f"- Top failure clusters: {', '.join(b.top_failure_clusters)}")
        if b.dimension_scores:
            lines.append(f"- Dimension Scores: {b.dimension_scores}")
        lines.append("")

    lines.append("## Discovered Issue Clusters")
    for c in report.discovered_clusters:
        theme = f" [{c.parent_theme}]" if c.parent_theme else ""
        lines.append(f"### {c.auto_label}{theme} ({c.count} instances)")
        lines.append(f"- Avg severity score: {c.severity_avg}/5.0")
        lines.append(f"- Affected brands: {c.affected_brands}")
        lines.append(f"- Cross-brand: {'Yes' if c.is_cross_brand else 'No'}")
        lines.append("- Examples:")
        for ex in c.examples[:3]:
            lines.append(f"  - {ex}")
        lines.append("")

    lines.append("## Worst Conversations (Bottom 20)")
    for ev in report.worst_conversations[:10]:
        lines.append(f"- **{ev.conversation_id}** ({ev.brand_name}) — Score: {ev.overall_score}")
        lines.append(f"  Intent: {ev.user_intent}")
        for fd in ev.failure_descriptions[:3]:
            lines.append(f"  Issue: {fd}")
        lines.append("")

    return "\n".join(lines)
