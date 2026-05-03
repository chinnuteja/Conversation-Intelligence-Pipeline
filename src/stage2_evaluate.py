"""
Stage 2: LLM-as-a-Judge Evaluation Engine

Sends each conversation to Azure OpenAI API for structured evaluation.
Uses async batching for speed.
"""

import json
import asyncio
import logging
import openai
from openai import AsyncOpenAI
from tqdm.asyncio import tqdm_asyncio

from src.config import (
    EVAL_MODEL,
    MAX_CONCURRENT_EVALS,
)
from src.auth import get_vertex_token, get_vertex_base_url
from src.evaluation_schema import build_conversation_evaluation_json_schema
from src.models import ConversationThread, ConversationEvaluation, DimensionEval
from src.prompts import (
    EVALUATOR_SYSTEM_PROMPT,
    EVALUATOR_FEW_SHOT,
    build_evaluator_user_prompt,
)

logger = logging.getLogger(__name__)

client = AsyncOpenAI(
    base_url=get_vertex_base_url(),
    api_key=get_vertex_token(),
)
semaphore = asyncio.Semaphore(MAX_CONCURRENT_EVALS)

EVALUATION_JSON_SCHEMA = build_conversation_evaluation_json_schema()


def handle_eval_error(thread: ConversationThread, error_msg: str) -> ConversationEvaluation:
    logger.warning("Evaluation failed for %s: %s", thread.conversation_id, error_msg)
    return ConversationEvaluation(
        conversation_id=thread.conversation_id,
        brand_name=thread.brand_name,
        widget_id=thread.widget_id,
        overall_score=0.0,
        resolution_achieved=False,
        dimensions={},
        failure_descriptions=[f"EVALUATION_ERROR: {error_msg}"],
        user_intent="Unknown",
        frustration_signals=[],
        open_observations="Evaluation failed — needs manual review.",
        has_add_to_cart=thread.has_add_to_cart,
        event_counts=thread.event_counts,
    )


async def evaluate_single_conversation(thread: ConversationThread) -> ConversationEvaluation:
    """Evaluate a single conversation using Azure OpenAI as a judge with Structured Outputs."""
    async with semaphore:
        system = EVALUATOR_SYSTEM_PROMPT.format(brand_name=thread.brand_name)
        system += "\n\n" + EVALUATOR_FEW_SHOT

        user_prompt = build_evaluator_user_prompt(thread)

        for attempt, delay in enumerate([5, 15, 45, 0]):
            try:
                response = await client.chat.completions.create(
                    model=EVAL_MODEL,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user_prompt},
                    ],
                    response_format={
                        "type": "json_schema",
                        "json_schema": EVALUATION_JSON_SCHEMA,
                    },
                )

                eval_data = json.loads(response.choices[0].message.content)

                dimensions = {}
                for dim_name, dim_data in eval_data.get("dimensions", {}).items():
                    dimensions[dim_name] = DimensionEval(
                        score=dim_data.get("score", 3.0),
                        issues=dim_data.get("issues", []),
                        evidence=dim_data.get("evidence", []),
                    )

                return ConversationEvaluation(
                    conversation_id=thread.conversation_id,
                    brand_name=thread.brand_name,
                    widget_id=thread.widget_id,
                    reasoning_scratchpad=eval_data.get("reasoning_scratchpad", ""),
                    overall_score=eval_data.get("overall_score", 3.0),
                    resolution_achieved=eval_data.get("resolution_achieved", False),
                    dimensions=dimensions,
                    failure_descriptions=eval_data.get("failure_descriptions", []),
                    user_intent=eval_data.get("user_intent", "Unknown"),
                    frustration_signals=eval_data.get("frustration_signals", []),
                    open_observations=eval_data.get("open_observations", ""),
                    has_add_to_cart=thread.has_add_to_cart,
                    event_counts=thread.event_counts,
                )

            except openai.RateLimitError as e:
                if delay > 0:
                    logger.info(
                        "RateLimit retry %s in %ds (attempt %d)",
                        thread.conversation_id,
                        delay,
                        attempt + 1,
                    )
                    await asyncio.sleep(delay)
                else:
                    return handle_eval_error(thread, str(e))
            except openai.APIStatusError as e:
                if delay > 0:
                    logger.info(
                        "APIStatusError retry %s in %ds (attempt %d)",
                        thread.conversation_id,
                        delay,
                        attempt + 1,
                    )
                    await asyncio.sleep(delay)
                else:
                    return handle_eval_error(thread, str(e))
            except openai.BadRequestError as e:
                err_msg = str(e)
                if "content management policy" in err_msg.lower():
                    return ConversationEvaluation(
                        conversation_id=thread.conversation_id,
                        brand_name=thread.brand_name,
                        widget_id=thread.widget_id,
                        overall_score=2.5,
                        resolution_achieved=False,
                        dimensions={},
                        failure_descriptions=[
                            "CONTENT_FILTER_BLOCKED: The response triggered Azure OpenAI's content management policy."
                        ],
                        user_intent="Unknown",
                        frustration_signals=[],
                        open_observations="Evaluation was filtered by Azure OpenAI's content policy.",
                        has_add_to_cart=thread.has_add_to_cart,
                        event_counts=thread.event_counts,
                    )
                return handle_eval_error(thread, str(e))
            except Exception as e:
                return handle_eval_error(thread, str(e))


async def run_evaluations(threads: list[ConversationThread]) -> list[ConversationEvaluation]:
    """Evaluate all conversations concurrently with progress bar."""
    logger.info("Stage 2: Evaluating %d conversations...", len(threads))
    tasks = [evaluate_single_conversation(t) for t in threads]
    evaluations = await tqdm_asyncio.gather(*tasks, desc="Evaluating")
    logger.info("Completed %d evaluations", len(evaluations))
    return evaluations
