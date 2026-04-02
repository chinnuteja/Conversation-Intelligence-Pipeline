"""Tests for Stage 3 signal collection."""

from src.models import ConversationEvaluation, DimensionEval
from src.stage3_discover import collect_textual_signals


def test_collect_textual_signals_filters_errors_and_open_obs():
    ev = ConversationEvaluation(
        conversation_id="c1",
        brand_name="B",
        widget_id="w",
        overall_score=2.0,
        resolution_achieved=False,
        dimensions={},
        failure_descriptions=["EVALUATION_ERROR: x", "Real issue"],
        user_intent="u",
        frustration_signals=["User repeated question"],
        open_observations="short",
    )
    sigs = collect_textual_signals([ev])
    texts = [s["text"] for s in sigs]
    assert "EVALUATION_ERROR: x" not in texts
    assert "Real issue" in texts
    assert "User repeated question" in texts
    assert "short" not in texts

    ev2 = ConversationEvaluation(
        conversation_id="c2",
        brand_name="B",
        widget_id="w",
        overall_score=3.0,
        resolution_achieved=True,
        dimensions={},
        failure_descriptions=[],
        user_intent="u",
        frustration_signals=[],
        open_observations="This is a longer observation that should be included.",
    )
    sigs2 = collect_textual_signals([ev2])
    assert any("longer observation" in s["text"] for s in sigs2)
