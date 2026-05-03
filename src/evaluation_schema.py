"""
OpenAI/Azure structured-output JSON schema for conversation evaluation.
Built programmatically so dimension keys stay in sync with prompts.
"""

DIMENSION_KEYS = [
    "factual_accuracy",
    "hallucination_check",
    "policy_compliance",
    "tone_and_helpfulness",
    "user_satisfaction_signals",
    "cross_brand_check",
]


def _dimension_schema() -> dict:
    return {
        "type": "object",
        "properties": {
            "score": {"type": "number"},
            "issues": {"type": "array", "items": {"type": "string"}},
            "evidence": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["score", "issues", "evidence"],
        "additionalProperties": False,
    }


def build_conversation_evaluation_json_schema() -> dict:
    """Return the json_schema wrapper for chat.completions response_format."""
    dim_props = {key: _dimension_schema() for key in DIMENSION_KEYS}
    inner = {
        "type": "object",
        "properties": {
            "reasoning_scratchpad": {
                "type": "string",
                "description": "MANDATORY: Write a 2-3 sentence chronological summary of the user's intent path and the bot's state changes. Reason through what happened BEFORE scoring. If you are penalizing the bot for a loop, you MUST explicitly state here whether the user's intent changed or remained identical.",
            },
            "overall_score": {
                "type": "number",
                "description": "1.0-5.0 overall quality score",
            },
            "resolution_achieved": {
                "type": "boolean",
                "description": "Was the user's need met?",
            },
            "dimensions": {
                "type": "object",
                "properties": dim_props,
                "required": DIMENSION_KEYS,
                "additionalProperties": False,
            },
            "failure_descriptions": {
                "type": "array",
                "items": {"type": "string"},
                "description": "1-sentence summary of each distinct problem found",
            },
            "user_intent": {
                "type": "string",
                "description": "What the user was trying to accomplish",
            },
            "frustration_signals": {"type": "array", "items": {"type": "string"}},
            "open_observations": {
                "type": "string",
                "description": "Anything noteworthy not covered above",
            },
        },
        "required": [
            "reasoning_scratchpad",
            "overall_score",
            "resolution_achieved",
            "dimensions",
            "failure_descriptions",
            "user_intent",
            "frustration_signals",
            "open_observations",
        ],
        "additionalProperties": False,
    }
    return {
        "name": "conversation_evaluation",
        "strict": True,
        "schema": inner,
    }
