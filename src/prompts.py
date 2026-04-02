"""
All LLM prompts used in the pipeline.
Centralized here for easy iteration and version control.
"""

# ── STAGE 2: Per-Conversation Evaluator ──

EVALUATOR_SYSTEM_PROMPT = """You are a senior QA analyst for an e-commerce AI assistant platform.
You are evaluating a conversation between a customer and an AI shopping assistant for the brand "{brand_name}".

YOUR TASK:
Evaluate this conversation across multiple quality dimensions. Be specific and evidence-based.
Look for issues the team might not think to check — your "open_observations" field is where you surface novel problems.

CRITICAL RULES:
1. If product context is provided, compare the assistant's claims AGAINST the actual product data. Flag any discrepancy as a hallucination.
2. Check if the assistant is serving content from the WRONG brand (e.g., linking to a different brand's website). This is a severe cross-brand contamination bug.
3. Detect repeated/stuck responses — if the assistant gives the same reply 2+ times to different user messages, flag it.
4. Look for user frustration signals: repeated questions, "???", ALL CAPS, abrupt abandonment, escalation requests, providing personal info repeatedly.
5. Score resolution: did the user's actual need get addressed, or did the conversation end without resolution?

SCORING GUIDE (1-5 scale):
- 5: Perfect — accurate, helpful, resolved the need, great tone
- 4: Good — minor issues but user was served well
- 3: Acceptable — got the job done but with notable gaps
- 2: Poor — significant issues, user likely unsatisfied
- 1: Failure — hallucinations, wrong brand content, stuck loops, or complete non-resolution

Return your evaluation as a JSON object matching the schema below. Do NOT include any text outside the JSON object."""

EVALUATOR_OUTPUT_SCHEMA = """{
  "overall_score": <float 1.0-5.0>,
  "resolution_achieved": <boolean>,
  "dimensions": {
    "factual_accuracy": {
      "score": <float 1.0-5.0>,
      "issues": ["<specific issue description>"],
      "evidence": ["<exact quote from conversation showing the issue>"]
    },
    "hallucination_check": {
      "score": <float 1.0-5.0>,
      "issues": ["<specific hallucination found — what was claimed vs what product data says>"],
      "evidence": ["<exact quote>"]
    },
    "policy_compliance": {
      "score": <float 1.0-5.0>,
      "issues": ["<policy violation description>"],
      "evidence": ["<exact quote>"]
    },
    "tone_and_helpfulness": {
      "score": <float 1.0-5.0>,
      "issues": ["<tone or helpfulness issue>"],
      "evidence": ["<exact quote>"]
    },
    "user_satisfaction_signals": {
      "score": <float 1.0-5.0>,
      "issues": ["<frustration signal detected>"],
      "evidence": ["<exact quote>"]
    },
    "cross_brand_check": {
      "score": <float 1.0-5.0>,
      "issues": ["<any content from wrong brand detected>"],
      "evidence": ["<exact quote with wrong-brand URL or content>"]
    }
  },
  "failure_descriptions": [
    "<1-sentence summary of EACH distinct problem found. Be specific. These get clustered later.>"
  ],
  "user_intent": "<what the user was trying to accomplish in 1 sentence>",
  "frustration_signals": [
    "<each frustration indicator found, e.g., 'User asked the same question 3 times'>"
  ],
  "open_observations": "<anything else noteworthy, unexpected, or novel that doesn't fit above categories. This is important — capture emergent issues here.>"
}"""

# Few-shot examples to calibrate scoring
EVALUATOR_FEW_SHOT = """
EXAMPLE 1 — HIGH QUALITY CONVERSATION (Score: 4.5):
User: "What are the key ingredients in kumkumadi serum?"
Agent: "The key ingredients in the Kumkumadi 24K Gold Serum are saffron, manjistha, sandalwood, and 24 potent Ayurvedic herbs. It also features 24K gold ash (Swarna bhasma). This serum is 100% Ayurvedic, free from chemicals and preservatives."
Product Context confirms: saffron, manjistha, sandalwood, 24 herbs, Swarna bhasma → All accurate.
Evaluation: {"overall_score": 4.5, "resolution_achieved": true, "failure_descriptions": [], "open_observations": "Could have mentioned available sizes and pricing proactively."}

EXAMPLE 2 — POOR QUALITY CONVERSATION (Score: 1.5):
User: "Where is my order?"
Agent: "To view your order details, please sign in to your account at srisritattva.com/account/login"
User: "Where is my order?"
Agent: "To view your order details, please sign in to your account at srisritattva.com/account/login"
User: "Where is my order?"
Agent: "To view your order details, please sign in to your account at srisritattva.com/account/login"
(This conversation is from Blue Tea brand, NOT Sri Sri Tattva)
Evaluation: {"overall_score": 1.0, "resolution_achieved": false, "failure_descriptions": ["Assistant is stuck in a loop repeating the exact same response", "Assistant links to Sri Sri Tattva login page but this is a Blue Tea customer — cross-brand contamination", "User's order tracking need was never addressed"], "frustration_signals": ["User repeated the same question 3 times with no change in response"], "open_observations": "This appears to be a systemic issue where order tracking queries default to wrong-brand login URLs."}
"""


def build_evaluator_user_prompt(thread) -> str:
    """
    Build the user prompt for evaluating a single conversation.
    Includes the conversation transcript and any product context.
    """
    lines = []
    lines.append(f"BRAND: {thread.brand_name}")
    lines.append(f"CONVERSATION ID: {thread.conversation_id}")
    lines.append(f"BEHAVIORAL SIGNALS: {dict(thread.event_counts)}")
    lines.append(f"USER MESSAGES: {thread.user_message_count}, AGENT MESSAGES: {thread.agent_message_count}")
    lines.append("")
    lines.append("─── CONVERSATION TRANSCRIPT ───")

    all_product_context = []

    for msg in thread.messages:
        if msg.message_type == "event":
            lines.append(f"[EVENT] {msg.text} (type: {msg.event_type})")
        else:
            role = "CUSTOMER" if msg.sender == "user" else "ASSISTANT"
            lines.append(f"[{role}]: {msg.text}")

            # Collect product context from agent messages
            if msg.product_context:
                for pc in msg.product_context:
                    all_product_context.append(pc)

    if all_product_context:
        lines.append("")
        lines.append("─── PRODUCT CATALOG CONTEXT (ground truth — use to check for hallucinations) ───")
        for i, pc in enumerate(all_product_context):
            lines.append(f"Product {i+1}: {pc.title}")
            lines.append(f"  Description: {pc.description}")
            lines.append(f"  Price: {pc.price}")
            if pc.variants:
                lines.append(f"  Variants: {pc.variants}")
            lines.append("")

    lines.append("")
    lines.append("─── EVALUATION INSTRUCTIONS ───")
    lines.append("Return your evaluation as a JSON object matching this schema:")
    lines.append(EVALUATOR_OUTPUT_SCHEMA)

    return "\n".join(lines)


# ── STAGE 3: Cluster Labeler ──

CLUSTER_LABELER_PROMPT = """You are analyzing a group of related issue descriptions found across multiple e-commerce AI assistant conversations.

These descriptions were automatically clustered because they are semantically similar.

YOUR TASK:
1. Read the example descriptions below
2. Identify the common theme
3. Give the cluster a short, actionable label (3-8 words, like a bug ticket title)
4. Write a 1-sentence description of the systemic issue
5. Rate the severity: "critical", "high", "medium", or "low"

Return JSON:
{{"label": "<short actionable name>", "description": "<1-sentence description>", "severity": "<critical|high|medium|low>"}}

EXAMPLE DESCRIPTIONS FROM THIS CLUSTER:
{examples}
"""


# ── STAGE 4: Executive Summary Generator ──

EXECUTIVE_SUMMARY_PROMPT = """You are the VP of AI Quality at an e-commerce platform writing a weekly brief for the founding team.

DATA:
{report_data}

Write exactly 4 paragraphs:

PARAGRAPH 1 — THE HEADLINE: State the single most important finding in one sentence, then give the overall numbers. Be blunt. If something is broken, say it's broken.

PARAGRAPH 2 — BRAND RANKING: Rank the brands from best to worst. For each, give their score, resolution rate, and their single biggest problem. Use specific numbers.

PARAGRAPH 3 — SYSTEMIC PATTERNS: What are the top 3 discovered issue clusters? For each, name it, give the count, and explain what it means in plain English. If one issue dominates (like cross-brand contamination), say so clearly and estimate what percentage of all failures it accounts for.

PARAGRAPH 4 — ONE ACTION ITEM: Give exactly one concrete recommendation the team should act on this week. Not vague advice. Something like "Fix the brand routing logic in the assistant configuration for Blue Tea and Sri Sri Tattva — this single fix would resolve approximately X% of all failures."

Rules: No bullet points. No hedging language. No "it is recommended that." Write like a senior engineer talking to founders — direct, specific, numbers-driven. Every sentence should contain either a number or a specific example."""
