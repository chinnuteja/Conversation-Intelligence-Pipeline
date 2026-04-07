import json
import asyncio
import os
import sys

# Ensure src is in path
sys.path.append(os.getcwd())

async def main():
    print(">>> Starting Stage 3 & 4 Runner", flush=True)
    
    eval_path = os.path.join("output", "all_evaluations.json")
    if not os.path.exists(eval_path):
        print(f"ERROR: {eval_path} not found", flush=True)
        return

    print(f">>> Loading evaluations from {eval_path}...", flush=True)
    with open(eval_path, encoding="utf-8") as f:
        from src.models import ConversationEvaluation
        eval_data = json.load(f)
        evaluations = [ConversationEvaluation.model_validate(e) for e in eval_data]
    print(f">>> Loaded {len(evaluations)} evaluations.", flush=True)

    print(">>> Loading Stage 3 (Clustering)...", flush=True)
    # Lazy import to avoid startup hangs
    from src.stage3_discover import discover_patterns
    clusters = await discover_patterns(evaluations)
    print(f">>> Discovered {len(clusters)} clusters.", flush=True)

    print(">>> Loading Stage 4 (Aggregation)...", flush=True)
    from src.stage4_aggregate import build_report
    report = await build_report(evaluations, clusters)
    print(">>> Report generated.", flush=True)

    print(">>> Generating results.html...", flush=True)
    from src.generate_results_page import generate_results_html
    generate_results_html("output")
    print(">>> Results page generated.", flush=True)

    print(">>> PIPELINE COMPLETE.", flush=True)

if __name__ == "__main__":
    asyncio.run(main())
