"""Tests for Stage 4 aggregation."""

from src.models import (
    ConversationEvaluation,
    DimensionEval,
    DiscoveredCluster,
)
from src.stage4_aggregate import aggregate_by_brand, build_cluster_theme_rollups


def _dims(**scores):
    keys = [
        "factual_accuracy",
        "hallucination_check",
        "policy_compliance",
        "tone_and_helpfulness",
        "user_satisfaction_signals",
        "cross_brand_check",
    ]
    out = {}
    for k in keys:
        s = scores.get(k, 3.0)
        out[k] = DimensionEval(score=s, issues=[], evidence=[])
    return out


def test_aggregate_by_brand_rates_and_top_clusters():
    evs = [
        ConversationEvaluation(
            conversation_id="1",
            brand_name="BrandA",
            widget_id="w1",
            overall_score=4.0,
            resolution_achieved=True,
            dimensions=_dims(hallucination_check=4.0),
            failure_descriptions=[],
            user_intent="x",
            frustration_signals=[],
            open_observations="",
            has_add_to_cart=False,
            event_counts={},
        ),
        ConversationEvaluation(
            conversation_id="2",
            brand_name="BrandA",
            widget_id="w1",
            overall_score=2.0,
            resolution_achieved=False,
            dimensions=_dims(hallucination_check=1.0),
            failure_descriptions=["bad"],
            user_intent="y",
            frustration_signals=["repeat"],
            open_observations="",
            has_add_to_cart=True,
            event_counts={},
        ),
    ]
    clusters = [
        DiscoveredCluster(
            cluster_id=0,
            auto_label="Orders",
            count=5,
            severity_avg=2.0,
            examples=["e"],
            affected_brands={"BrandA": 5, "BrandB": 1},
            is_cross_brand=True,
            sample_conversation_ids=["1"],
            conversation_ids=["1", "2"],
        ),
        DiscoveredCluster(
            cluster_id=1,
            auto_label="Small",
            count=1,
            severity_avg=3.0,
            examples=["e2"],
            affected_brands={"BrandA": 1},
            is_cross_brand=False,
            sample_conversation_ids=["2"],
            conversation_ids=["2"],
        ),
    ]
    reports = aggregate_by_brand(evs, clusters)
    assert len(reports) == 1
    r = reports[0]
    assert r.brand_name == "BrandA"
    assert r.conversation_count == 2
    assert r.resolution_rate == 0.5
    assert r.hallucination_rate == 0.5
    assert r.frustration_rate == 0.5
    assert r.add_to_cart_rate == 0.5
    assert r.top_failure_clusters[0] == "Orders"


def test_build_cluster_theme_rollups():
    clusters = [
        DiscoveredCluster(
            cluster_id=0,
            auto_label="A",
            count=3,
            severity_avg=2.0,
            examples=[],
            affected_brands={"X": 3},
            is_cross_brand=False,
            sample_conversation_ids=[],
            conversation_ids=[],
            parent_theme="Theme1",
        ),
        DiscoveredCluster(
            cluster_id=1,
            auto_label="B",
            count=2,
            severity_avg=2.5,
            examples=[],
            affected_brands={"X": 2},
            is_cross_brand=False,
            sample_conversation_ids=[],
            conversation_ids=[],
            parent_theme="Theme1",
        ),
    ]
    roll = build_cluster_theme_rollups(clusters)
    assert len(roll) == 1
    assert roll[0].parent_theme == "Theme1"
    assert set(roll[0].cluster_labels) == {"A", "B"}
    assert roll[0].total_count == 5
