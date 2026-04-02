"""Pydantic model validation tests."""

import pytest
from pydantic import ValidationError

from src.models import DimensionEval, ConversationEvaluation


def test_dimension_eval_score_bounds():
    DimensionEval(score=0, issues=[], evidence=[])
    DimensionEval(score=5, issues=[], evidence=[])
    with pytest.raises(ValidationError):
        DimensionEval(score=5.1, issues=[], evidence=[])


def test_conversation_evaluation_minimal():
    ev = ConversationEvaluation(
        conversation_id="c",
        brand_name="B",
        widget_id="w",
        overall_score=3.0,
        resolution_achieved=False,
        dimensions={},
        user_intent="u",
    )
    assert ev.failure_descriptions == []
