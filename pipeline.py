"""
Main Pipeline Orchestrator

Runs all 4 stages in sequence.

Usage:
    python pipeline.py
"""

import asyncio
import json
import logging
import os
import time

from src.logging_config import setup_logging

setup_logging()

from src.stage1_ingest import build_conversation_threads
from src.stage2_evaluate import run_evaluations
from src.stage3_discover import discover_patterns
from src.stage4_aggregate import build_report
from src.generate_results_page import generate_results_html
from src.config import OUTPUT_DIR

logger = logging.getLogger(__name__)


async def run_pipeline():
    """Execute the full pipeline."""
    start = time.time()

    logger.info("=" * 60)
    logger.info("  CONVERSATION INTELLIGENCE PIPELINE")
    logger.info("=" * 60)

    logger.info("Stage 1: Ingesting and normalizing data...")
    threads = build_conversation_threads()
    logger.info("Built %d conversation threads", len(threads))
    for brand in set(t.brand_name for t in threads):
        count = sum(1 for t in threads if t.brand_name == brand)
        logger.info("  %s: %d conversations", brand, count)

    eval_path = os.path.join(OUTPUT_DIR, "all_evaluations.json")
    if os.path.exists(eval_path):
        logger.info("Loading cached evaluations from %s", eval_path)
        with open(eval_path, encoding="utf-8") as f:
            from src.models import ConversationEvaluation

            eval_data = json.load(f)
            evaluations = [ConversationEvaluation.model_validate(e) for e in eval_data]
    else:
        evaluations = await run_evaluations(threads)

        os.makedirs(OUTPUT_DIR, exist_ok=True)
        with open(eval_path, "w", encoding="utf-8") as f:
            json.dump(
                [e.model_dump(mode="json") for e in evaluations],
                f,
                indent=2,
                default=str,
            )
        logger.info("Saved all evaluations to %s", eval_path)

    clusters = await discover_patterns(evaluations)
    report = await build_report(evaluations, clusters)

    try:
        generate_results_html(OUTPUT_DIR)
    except Exception as e:
        logger.warning("Could not generate results.html: %s", e)

    elapsed = time.time() - start
    logger.info("=" * 60)
    logger.info("PIPELINE COMPLETE in %.0fs", elapsed)
    logger.info("Report: %s/report.json", OUTPUT_DIR)
    logger.info("Results page: %s/results.html", OUTPUT_DIR)
    logger.info("Summary: %s/summary.md", OUTPUT_DIR)
    logger.info("Dashboard: streamlit run dashboard/app.py")
    logger.info("=" * 60)
    return report


if __name__ == "__main__":
    asyncio.run(run_pipeline())
