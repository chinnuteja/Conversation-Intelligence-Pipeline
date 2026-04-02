"""
Stage 3: Embed, Cluster & Discover

Takes all failure_descriptions + open_observations from Stage 2,
embeds them, clusters with HDBSCAN, and asks an LLM to label each cluster.

This is where "unknown unknowns" surface.
"""

import json
import logging
import asyncio
import numpy as np
from collections import Counter

from openai import AsyncAzureOpenAI
from sklearn.metrics.pairwise import cosine_similarity
import umap
import hdbscan

from src.config import (
    OAI_BASE_LLM,
    OAI_KEY_LLM,
    OAI_VERSION,
    LABEL_MODEL,
    UMAP_N_COMPONENTS,
    UMAP_METRIC,
    HDBSCAN_MIN_CLUSTER_SIZE,
    HDBSCAN_MIN_SAMPLES,
    CLUSTER_LABEL_MERGE_THRESHOLD,
    CLUSTER_CONVERSATION_OVERLAP_THRESHOLD,
)
from src.models import ConversationEvaluation, DiscoveredCluster
from src.prompts import CLUSTER_LABELER_PROMPT
from src.text_utils import strip_code_fences

logger = logging.getLogger(__name__)

client = AsyncAzureOpenAI(
    azure_endpoint=OAI_BASE_LLM,
    api_key=OAI_KEY_LLM,
    api_version=OAI_VERSION,
)

_embedding_model = None


def get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        from sentence_transformers import SentenceTransformer

        _embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
    return _embedding_model


def collect_textual_signals(evaluations: list[ConversationEvaluation]) -> list[dict]:
    """
    Extract all free-text signals from evaluations.
    Each signal tracks which conversation and brand it came from.
    """
    signals = []
    for ev in evaluations:
        for fd in ev.failure_descriptions:
            if fd and not fd.startswith("EVALUATION_ERROR"):
                signals.append(
                    {
                        "text": fd,
                        "conversation_id": ev.conversation_id,
                        "brand_name": ev.brand_name,
                        "overall_score": ev.overall_score,
                    }
                )
        for fs in ev.frustration_signals:
            if fs:
                signals.append(
                    {
                        "text": fs,
                        "conversation_id": ev.conversation_id,
                        "brand_name": ev.brand_name,
                        "overall_score": ev.overall_score,
                    }
                )
        if ev.open_observations and len(ev.open_observations) > 10:
            signals.append(
                {
                    "text": ev.open_observations,
                    "conversation_id": ev.conversation_id,
                    "brand_name": ev.brand_name,
                    "overall_score": ev.overall_score,
                }
            )
    return signals


async def embed_texts(texts: list[str]) -> np.ndarray:
    """Embed texts using Sentence Transformers locally."""
    model = get_embedding_model()
    embeddings = model.encode(texts, show_progress_bar=True, batch_size=32)
    return np.array(embeddings)


def cluster_signals(embeddings: np.ndarray) -> np.ndarray:
    """Reduce dimensionality with UMAP, then cluster with HDBSCAN."""
    n_samples = len(embeddings)
    n_neighbors = min(15, n_samples - 1)
    n_components = min(UMAP_N_COMPONENTS, n_samples - 2)

    if n_samples < 5:
        return np.full(n_samples, -1)

    reducer = umap.UMAP(
        n_components=n_components,
        n_neighbors=n_neighbors,
        metric=UMAP_METRIC,
        random_state=42,
    )
    reduced = reducer.fit_transform(embeddings)

    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=HDBSCAN_MIN_CLUSTER_SIZE,
        min_samples=HDBSCAN_MIN_SAMPLES,
        metric="euclidean",
    )
    labels = clusterer.fit_predict(reduced)
    return labels


async def label_cluster(examples: list[str]) -> dict:
    """Ask an LLM to generate a human-readable label for a cluster."""
    examples_text = "\n".join(f"- {ex}" for ex in examples[:8])
    prompt = CLUSTER_LABELER_PROMPT.format(examples=examples_text)

    try:
        response = await client.chat.completions.create(
            model=LABEL_MODEL,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = strip_code_fences(response.choices[0].message.content.strip())
        return json.loads(raw)
    except Exception as e:
        logger.warning("Cluster label failed: %s", e)
        return {"label": "Unlabeled cluster", "description": str(e), "severity": "medium"}


def _merge_discovered_pair(c1: DiscoveredCluster, c2: DiscoveredCluster) -> DiscoveredCluster:
    keep_label = c1.auto_label if c1.count >= c2.count else c2.auto_label
    merged_brands = dict(c1.affected_brands)
    for brand, count in c2.affected_brands.items():
        merged_brands[brand] = merged_brands.get(brand, 0) + count
    total_count = c1.count + c2.count
    merged_severity = round(
        (c1.severity_avg * c1.count + c2.severity_avg * c2.count) / total_count,
        2,
    )
    merged_convo = list(set(c1.conversation_ids + c2.conversation_ids))
    merged_examples = (c1.examples + c2.examples)[:5]
    sample = merged_convo[:5]
    return DiscoveredCluster(
        cluster_id=c1.cluster_id,
        auto_label=keep_label,
        count=total_count,
        severity_avg=merged_severity,
        examples=merged_examples,
        affected_brands=merged_brands,
        is_cross_brand=len(merged_brands) > 1,
        sample_conversation_ids=sample,
        conversation_ids=merged_convo,
        parent_theme=c1.parent_theme or c2.parent_theme,
    )


async def merge_similar_clusters(clusters: list[DiscoveredCluster]) -> list[DiscoveredCluster]:
    """
    1) Iterative embedding-based merge (configurable threshold)
    2) LLM-based semantic merge by root cause
    """
    if len(clusters) <= 1:
        return clusters

    model = get_embedding_model()
    threshold = CLUSTER_LABEL_MERGE_THRESHOLD

    merged = True
    while merged:
        merged = False
        labels = [c.auto_label for c in clusters]
        label_embeddings = model.encode(labels)
        sim_matrix = cosine_similarity(label_embeddings)

        best_sim = 0.0
        best_pair = None
        for i in range(len(clusters)):
            for j in range(i + 1, len(clusters)):
                if sim_matrix[i][j] > best_sim:
                    best_sim = sim_matrix[i][j]
                    best_pair = (i, j)

        if best_pair and best_sim > threshold:
            merged = True
            i, j = best_pair
            c1, c2 = clusters[i], clusters[j]
            new_cluster = _merge_discovered_pair(c1, c2)
            clusters = [c for idx, c in enumerate(clusters) if idx not in (i, j)]
            clusters.append(new_cluster)

    all_labels = [c.auto_label for c in clusters]
    if len(all_labels) > 3:
        label_list = "\n".join(f"- {l}" for l in all_labels)
        merge_prompt = f"""You merge duplicate issue themes from an e-commerce AI assistant QA system.

Rules (be conservative):
- Only merge two labels if the SAME concrete engineering fix would resolve both (e.g. two phrasings of "wrong brand checkout URL").
- Do NOT merge clusters that share a broad theme but need different fixes (e.g. "wrong brand URL" vs "user repeated question with no new answer" vs "wrong support email" — keep separate).
- Do NOT merge "cross-brand" style issues with order-tracking or product-recommendation quality unless the label text clearly names the same bug.
- When in doubt, do not merge.

Labels:
{label_list}

Return ONLY JSON: {{"merge_groups": [["label A", "label B"], ["label C", "label D"]]}}
Use exact label strings from the list. If nothing should merge, return {{"merge_groups": []}}."""

        try:
            response = await client.chat.completions.create(
                model=LABEL_MODEL,
                messages=[{"role": "user", "content": merge_prompt}],
            )
            raw = strip_code_fences(response.choices[0].message.content.strip())
            merge_data = json.loads(raw)

            for group in merge_data.get("merge_groups", []):
                matching = [c for c in clusters if c.auto_label in group]
                if len(matching) < 2:
                    continue
                matching.sort(key=lambda c: c.count, reverse=True)
                acc = matching[0]
                for secondary in matching[1:]:
                    acc = _merge_discovered_pair(acc, secondary)
                for m in matching:
                    if m in clusters:
                        clusters.remove(m)
                label_info = await label_cluster(acc.examples)
                acc.auto_label = label_info.get("label", acc.auto_label)
                assign_parent_themes([acc])
                clusters.append(acc)
        except Exception as e:
            logger.warning("LLM merge pass failed: %s", e)

    return clusters


def merge_clusters_by_conversation_overlap(
    clusters: list[DiscoveredCluster],
    overlap_threshold: float = CLUSTER_CONVERSATION_OVERLAP_THRESHOLD,
) -> list[DiscoveredCluster]:
    """Merge clusters when they share a large fraction of the same conversations."""
    if len(clusters) <= 1:
        return clusters

    merged = True
    while merged:
        merged = False
        for i in range(len(clusters)):
            for j in range(i + 1, len(clusters)):
                a, b = clusters[i], clusters[j]
                sa, sb = set(a.conversation_ids), set(b.conversation_ids)
                if not sa or not sb:
                    continue
                inter = len(sa & sb)
                smaller = min(len(sa), len(sb))
                if smaller == 0:
                    continue
                if inter / smaller >= overlap_threshold:
                    new_c = _merge_discovered_pair(a, b)
                    clusters = [c for idx, c in enumerate(clusters) if idx not in (i, j)]
                    clusters.append(new_c)
                    merged = True
                    break
            if merged:
                break
    return clusters


def assign_parent_themes(clusters: list[DiscoveredCluster]) -> None:
    """Tag each cluster with a coarse theme for hierarchical reporting."""
    cross_kw = (
        "wrong brand",
        "cross-brand",
        "cross brand",
        "misidentif",
        "contamination",
        "different brand",
        "another brand",
        "integrity and alignment",
        "brand integrity",
        "incorrect contact",
        "wrong contact",
        "wrong email",
        "wrong url",
        "wrong link",
    )
    order_kw = (
        "order",
        "cancel",
        "track",
        "shipping",
        "delivery",
        "edit",
        "refund",
        "fulfillment",
    )
    product_kw = (
        "usage",
        "unanswered",
        "ingredient",
        "product",
        "recommend",
        "result",
        "how to",
    )
    for c in clusters:
        blob = (c.auto_label + " " + " ".join(c.examples[:5])).lower()
        if any(k in blob for k in cross_kw):
            c.parent_theme = "Cross-brand & identity"
        elif any(k in blob for k in order_kw):
            c.parent_theme = "Orders & fulfillment"
        elif any(k in blob for k in product_kw):
            c.parent_theme = "Product knowledge & recommendations"
        else:
            c.parent_theme = "General quality & engagement"


def filter_noise_clusters(clusters: list[DiscoveredCluster]) -> list[DiscoveredCluster]:
    """Drop clusters dominated by pipeline/evaluation errors."""
    failure_keywords = (
        "evaluation failed",
        "manual review",
        "evaluation_error",
        "content_filter_blocked",
    )

    filtered = []
    for cluster in clusters:
        failure_count = sum(
            1 for ex in cluster.examples if any(kw in ex.lower() for kw in failure_keywords)
        )
        failure_ratio = failure_count / len(cluster.examples) if cluster.examples else 1.0

        if failure_ratio >= 0.5:
            logger.info(
                'Filtered noise cluster "%s" (%d/%d failures)',
                cluster.auto_label,
                failure_count,
                len(cluster.examples),
            )
        else:
            filtered.append(cluster)
    return filtered


async def discover_patterns(evaluations: list[ConversationEvaluation]) -> list[DiscoveredCluster]:
    """Collect signals → embed → cluster → label → merge → overlap merge → themes → filter."""
    logger.info("Stage 3: Discovering failure patterns...")

    signals = collect_textual_signals(evaluations)
    logger.info("Collected %d textual signals from evaluations", len(signals))

    if len(signals) < 5:
        logger.warning("Too few signals for meaningful clustering")
        return []

    texts = [s["text"] for s in signals]
    embeddings = await embed_texts(texts)
    logger.info("Embedded %d signals into %d-dim space", len(texts), embeddings.shape[1])

    labels = cluster_signals(embeddings)
    unique_labels = set(labels)
    n_clusters = len(unique_labels) - (1 if -1 in unique_labels else 0)
    n_noise = list(labels).count(-1)
    logger.info("Found %d initial clusters (%d noise points)", n_clusters, n_noise)

    clusters = []
    for label in sorted(unique_labels):
        if label == -1:
            continue

        members = [signals[i] for i, l in enumerate(labels) if l == label]
        member_texts = [m["text"] for m in members]
        member_brands = Counter(m["brand_name"] for m in members)
        avg_score = np.mean([m["overall_score"] for m in members])
        convo_ids = list({m["conversation_id"] for m in members})

        label_info = await label_cluster(member_texts)

        clusters.append(
            DiscoveredCluster(
                cluster_id=int(label),
                auto_label=label_info.get("label", f"Cluster {label}"),
                count=len(members),
                severity_avg=round(float(avg_score), 2),
                examples=member_texts[:5],
                affected_brands=dict(member_brands),
                is_cross_brand=len(member_brands) > 1,
                sample_conversation_ids=convo_ids[:5],
                conversation_ids=convo_ids,
            )
        )

    logger.info("Labeled %d initial clusters", len(clusters))

    clusters = await merge_similar_clusters(clusters)
    clusters = merge_clusters_by_conversation_overlap(clusters)
    assign_parent_themes(clusters)
    clusters = filter_noise_clusters(clusters)

    clusters.sort(key=lambda c: c.count * (6 - c.severity_avg), reverse=True)
    return clusters
