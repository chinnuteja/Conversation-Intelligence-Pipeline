import json
import asyncio
import sys

from src.stage1_ingest import build_conversation_threads
import src.stage1_ingest as ing
from src.stage2_evaluate import run_evaluations
from src.stage3_discover import discover_patterns

async def main():
    # 1. Patch Stage 1 data loading
    with open('data/test_fresh_conversations.json') as f:
        conv = json.load(f)
    with open('data/test_fresh_messages.json') as f:
        msgs = json.load(f)
        
    ing.load_raw_data = lambda: (conv, msgs)

    print("=== STAGE 1: INGEST ===")
    threads = build_conversation_threads()
    for t in threads:
        print(f"ID: {t.conversation_id} | Inferred Brand: {t.brand_name}")
        for m in t.messages:
            if m.sender == "agent":
                print(f"   Agent Payload: {[p.title for p in (m.product_context or [])]}")
                print(f"   Agent Text (Visible): {m.text[:100]}...")
    
    print("\n=== STAGE 2: EVALUATE (LLM as Judge) ===")
    evals = await run_evaluations(threads)
    for ev in evals:
        print(f"ID: {ev.conversation_id} | Expected Brand: {ev.brand_name}")
        print(f"  Score: {ev.overall_score}/5 | Resolved: {ev.resolution_achieved}")
        print(f"  Failures: {ev.failure_descriptions}")
        print(f"  Frustration: {ev.frustration_signals}")
        print("-" * 40)
        
    print("\n=== STAGE 3: CLUSTER & DISCOVER ===")
    clusters = await discover_patterns(evals)
    # The clustering won't work perfectly on just 3 items because of HDBSCAN minimum size
    # But it will tag them as Noise (-1) or try to clump them. Let's see what happens.
    for c in clusters:
        print(f"Cluster: {c.auto_label} | Count: {c.count} | Theme: {c.parent_theme}")
        print(f"  Affected Brands: {c.affected_brands}")
        
    print("Done")

if __name__ == "__main__":
    asyncio.run(main())
