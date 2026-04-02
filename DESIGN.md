# Design notes

## Goal

Replace weekly manual review of assistant conversations with an automated pipeline that surfaces **actionable**, **brand-segmented** insights and emergent themes not fixed on a checklist.

## Pipeline shape

We split work into four stages so each layer stays testable and swappable:

1. **Ingest** — Normalize raw logs into threads, strip embedded product payloads for “ground truth,” and attach behavioral counters (events, add-to-cart).
2. **Evaluate** — One structured LLM judgment per conversation (rubric + evidence fields) so downstream analytics are typed JSON, not prose.
3. **Discover** — Cluster free-text failure signals to find recurring patterns across brands; merge near-duplicates (embedding + conservative LLM pass) while keeping distinct actionable themes.
4. **Aggregate** — Deterministic rollups (rates, dimension averages), then a single LLM “executive brief” constrained to be blunt and numeric.

## Key tradeoffs

**Per-conversation vs per-message scoring**  
We score at conversation granularity because resolution and user frustration are thread-level phenomena. Message-level tagging would be useful for pinpointing the first bad turn; we’d add that with more time.

**LLM judge vs heuristics**  
Heuristics excel at cheap flags (e.g. URL domain ≠ brand). The judge adds policy/tone/resolution and uses catalog JSON to separate “creative” answers from hallucinations. Cost is higher; we mitigate with mini model, concurrency limits, and evaluation cache on disk.

**HDBSCAN + UMAP vs fixed taxonomy**  
k-means needs *k* and poorly handles noise. HDBSCAN yields variable cluster counts and explicit noise points—better for exploratory issue discovery. UMAP is a pragmatic reducer before density clustering on embedding space.

**JSON files vs MongoDB**  
Local JSON keeps the take-home runnable without infra; MongoDB is supported to match the assignment’s import path and closer-to-prod operation.

## Reliability

- Structured output schema is built programmatically (single source of truth for dimension names) to avoid drift between Pydantic models and API JSON schema.
- Parse failures in agent product JSON are logged, not silent.
- Evaluation API failures are isolated per thread so one bad response does not stop the batch.

## What we’d do next

- Human spot-checks on a labeled subset; agreement metrics between judges or model versions.
- Incremental re-run (only new conversations) and dated trend lines in the dashboard.
- Stronger brand resolution (admin API or config service) instead of URL heuristics for unknown widgets.

## Scalability

**Runtime** — Stage 2 dominates: one LLM call per conversation. With `MAX_CONCURRENT_EVALS=20` (default), a full pass over ~300 threads is typically a few minutes on Azure `gpt-4o-mini`; at concurrency 5 the same work was closer to ~7 minutes. Tune via `MAX_CONCURRENT_EVALS` if your deployment’s rate limits allow higher parallelism.

**Caching** — Evaluations are written to `output/all_evaluations.json`. Re-running `pipeline.py` skips Stage 2 when that file exists, so iteration on clustering/reporting is cheap after the first full eval.

**Larger corpora (e.g. 10k–30k+ conversations)** — Same architecture scales linearly in API calls and wall time. Practical next steps: incremental runs (only new `conversation_id`s since last run), Azure Batch (or similar) for offline batches, and tiered evaluation (cheap heuristics for obvious cases, LLM only where ambiguous) to cut call count.

**Cost** — Roughly linear in conversation count with `gpt-4o-mini`; order-of-magnitude for hundreds of conversations is typically cents to low dollars depending on transcript length and pricing.

**Cluster granularity** — After HDBSCAN, embedding-based label merge uses `CLUSTER_LABEL_MERGE_THRESHOLD` (env / `src/config.py`). Higher values preserve more distinct clusters; very low values collapse many themes into one mega-cluster on this dataset. Conversation-overlap merge uses `CLUSTER_CONVERSATION_OVERLAP_THRESHOLD`.
