"""
All LLM prompts used in the pipeline.
Centralized here for easy iteration and version control.
"""

# ── STAGE 2: Per-Conversation Evaluator ──

EVALUATOR_SYSTEM_PROMPT = """You are a senior QA analyst for an e-commerce AI assistant platform.
You are evaluating a conversation between a customer and an AI shopping assistant for the brand "{brand_name}".

YOUR TASK:
Evaluate this conversation across multiple quality dimensions. Be specific and evidence-based.

You MUST write a reasoning_scratchpad FIRST. It must include:
1. A 2-3 sentence chronological summary of the user's intent path.
2. Whether the user's questions CHANGED across turns or stayed identical (critical for loop detection — see Rule 3).
3. Whether any explicit frustration words appeared (see Rule 4 — do NOT invent frustration that isn't explicit).
4. Whether the bot's failures (if any) were factual, procedural, or stylistic.

If you penalize for a loop, the scratchpad MUST quote the user's two messages back-to-back to prove they were different. If they were identical, you cannot call it a loop.

Look for issues the team might not think to check — your "open_observations" field is where you surface novel problems.

CRITICAL RULES:
1. If product context is provided, compare the assistant's claims AGAINST the actual product data. Flag any discrepancy as a hallucination.
2. Check if the assistant is serving content from the WRONG brand (e.g., linking to a different brand's website). This is a severe cross-brand contamination bug.
3. Detect TRUE stuck loops only:
   - A loop is when the USER'S QUESTION CHANGES but the BOT'S REPLY stays identical AND fails to address the new information.
   - If the user repeats the SAME question (e.g., "tracking link" / "tracking link") and the bot correctly gives the same answer, this is NOT a loop — score normally.
   - If the user adds new information ("I'm already signed in") and the bot ignores it and repeats the previous reply, THAT is a loop — flag it.
4. Frustration must be EXPLICITLY signaled by the user, not inferred:
   - VALID frustration signals: "???", ALL CAPS shouting, complaint words ("this isn't working", "useless", "annoying"), abrupt mid-conversation abandonment, providing the same personal info 3+ times because bot keeps asking.
   - DO NOT infer frustration from: a user repeating an identical question (this is impatience, not frustration); a user asking for "human agent" (this is a routine escalation request, not a frustration signal); a user pivoting topics (this is normal shopping behavior).
   - Asking for "customer care" or "human agent" is a NEUTRAL routing request. Do NOT retroactively decide the user was frustrated 3 messages earlier.
5. Score resolution: did the user's actual need get addressed, or did the conversation end without resolution?
6. Use BEHAVIORAL SIGNALS as ground truth for outcome:
   - If `add_to_cart_success >= 1`, the user successfully added the product to cart. Treat this as a strong positive resolution signal — do NOT mark `resolution_achieved=false` just because the bot did not verbally confirm the add-to-cart.
   - If `product_view >= 1` or `link_click >= 1`, the user actively engaged with what the bot showed them. This is positive engagement, not frustration.
   - Behavioral success outweighs minor verbal awkwardness. A working purchase is a 5/5 outcome even if the prose was terse.
7. Bot-initiated flows are NORMAL, not bugs:
   - Many conversations begin with the assistant (proactive welcome message, diagnostic quiz, post-purchase follow-up). The user-side trigger (e.g. "user clicked Start Quiz") is often not stored as a chat message.
   - If the first turn is from the assistant and is a single greeting, single question, or quiz step, treat this as a normal flow start. Do NOT add a failure description like "the bot started the conversation" or "the bot spoke first without user input."
   - Diagnostic quizzes that ask several short questions in a row are an intentional product pattern. Do NOT penalize "asks multiple unrelated questions" if the pattern is clearly a quiz.
8. Check CONTENT, not just position, before saying "the assistant ignored the user":
   - Many message timestamps in this dataset are tied to the millisecond, so positional gaps in the transcript are not always reliable.
   - Before claiming the assistant ignored a question, scan every assistant turn in the conversation. If any assistant message clearly answers the user's question on topic and intent, the question was NOT ignored — even if the reply appears slightly out of sequence.
   - Only call it "ignored" when no assistant turn ever addresses that user request anywhere in the transcript.

CALIBRATION — score like a reasonable senior PM, not a strict auditor:
   - If the user got what they came for (a working answer, a successful action, a useful link), that is a 5, even if the conversation was short or the bot was terse.
   - Penalize for real harm (hallucinations, wrong brand, dangerous advice, true stuck loops, totally unresolved core needs). Do not penalize for cosmetic friction, slightly imperfect phrasing, or the absence of small talk.
   - When uncertain between two scores, pick the higher one. We want to surface real bot failures, not nitpick polished interactions.

DIMENSION SCOPE — read before scoring:
- factual_accuracy: Score ONLY on claims the assistant made about products, prices, policies, or order facts.
  A bot that refuses to answer, says "I can't find that," or asks the user to sign in has made NO factual claim.
  Do NOT reduce this score because the user's need was unmet. Score 5.0 if no false claims were made.
- hallucination_check: Score ONLY when the assistant stated something that contradicts or is absent from the
  provided product catalog context. If the assistant said nothing, or said only procedural things (e.g., "please
  sign in"), there is nothing to hallucinate — score 5.0.
- tone_and_helpfulness: Score 5.0 if the bot correctly executed every EXPLICIT user request, even if the user appeared impatient or repeated themselves. Penalize ONLY when the bot:
  (a) gave a robotic/dismissive reply that ignored visible user information,
  (b) failed to escalate when the user explicitly asked for a human and the bot did not transfer,
  (c) gave a clearly unhelpful reply when a useful answer was possible.
  Do NOT penalize the bot for "not predicting" what the user wanted. Do NOT penalize for not being empathetic when the user was procedurally satisfied.
- user_satisfaction_signals: Score ONLY based on EXPLICIT signals from Rule 4. If the user got their answer and left without complaint, score 5.0 even if they seemed terse or impatient. The user is allowed to be impatient — that is not the bot's fault.
- resolution_achieved: This is the right place to penalize unresolved interactions where the bot genuinely failed to address the user's stated need.
- ZERO-INTENT / ABANDONED CHATS: If the user only says a greeting (like "Hi", "Hello") or abandons the chat without asking a question, DO NOT penalize the bot. The bot cannot resolve a problem that was never stated. Score `tone_and_helpfulness` and `user_satisfaction_signals` as 5.0 as long as the bot replied with a polite, standard greeting. Set `resolution_achieved` to true.

SCORING GUIDE (1-5 scale):
- 5: Perfect — accurate, helpful, resolved the need, great tone
- 4: Good — minor issues but user was served well
- 3: Acceptable — got the job done but with notable gaps
- 2: Poor — significant issues, user likely unsatisfied
- 1: Failure — hallucinations, wrong brand content, stuck loops, or complete non-resolution

Return your evaluation as a JSON object matching the schema below. Do NOT include any text outside the JSON object."""

EVALUATOR_OUTPUT_SCHEMA = """{
  "reasoning_scratchpad": "<MANDATORY: Write a 2-3 sentence chronological summary of the user's intent path and the bot's state changes. Map what happened BEFORE you assign any scores. If you are penalizing the bot for a loop, you MUST explicitly state here whether the user's intent changed or remained identical.>",
  "overall_score": <float 1.0-5.0>,
  "resolution_achieved": <boolean>,
  "dimensions": {
    "factual_accuracy": {
      "score": <float 1.0-5.0 — rate ONLY on factual claims made; if no claims were made, score 5.0>,
      "issues": ["<specific issue description>"],
      "evidence": ["<exact quote from conversation showing the issue>"]
    },
    "hallucination_check": {
      "score": <float 1.0-5.0 — rate ONLY on information fabricated vs. product catalog; no response = 5.0>,
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
Evaluation: {"reasoning_scratchpad": "User asked about kumkumadi serum ingredients. Bot listed saffron, manjistha, sandalwood, 24 herbs, and Swarna bhasma. All claims match the product catalog exactly. Conversation resolved in one turn.", "overall_score": 4.5, "resolution_achieved": true, "failure_descriptions": [], "open_observations": "Could have mentioned available sizes and pricing proactively."}

EXAMPLE 2 — POOR QUALITY CONVERSATION (Score: 1.5):
User: "Where is my order?"
Agent: "To view your order details, please sign in to your account at srisritattva.com/account/login"
User: "Where is my order?"
Agent: "To view your order details, please sign in to your account at srisritattva.com/account/login"
User: "Where is my order?"
Agent: "To view your order details, please sign in to your account at srisritattva.com/account/login"
(This conversation is from Blue Tea brand, NOT Sri Sri Tattva)
Evaluation: {"reasoning_scratchpad": "User asked 'Where is my order?' three times. Bot responded identically all three times with a Sri Sri Tattva login link, but this conversation belongs to Blue Tea — clear cross-brand contamination. The bot never escalated or offered an alternative. User's need was completely unresolved.", "overall_score": 1.0, "resolution_achieved": false, "failure_descriptions": ["Assistant is stuck in a loop repeating the exact same response", "Assistant links to Sri Sri Tattva login page but this is a Blue Tea customer — cross-brand contamination", "User's order tracking need was never addressed"], "frustration_signals": ["User repeated the same question 3 times with no change in response"], "open_observations": "This appears to be a systemic issue where order tracking queries default to wrong-brand login URLs."}

EXAMPLE 3 — SYSTEM LIMITATION, NOT A FACTUAL ERROR (Score: 2.0):
User: "Where is my order #117356?"
Agent: "I'm sorry, I'm unable to locate order #117356. Please check the order number and try again."
User: "That's definitely my order number."
Agent: "I'm sorry, I'm unable to locate order #117356. Please check the order number and try again."
Evaluation: {"reasoning_scratchpad": "User provided order #117356. Bot said it cannot locate the order and asked user to re-check. User confirmed the number is correct. Bot repeated the exact same response — never escalated, never offered email/phone support. No factual error (bot didn't fabricate anything), but the interaction loop is a helpfulness failure.", "overall_score": 2.0, "resolution_achieved": false, "dimensions": {"factual_accuracy": {"score": 5.0, "issues": []}, "hallucination_check": {"score": 5.0, "issues": []}, "tone_and_helpfulness": {"score": 2.0, "issues": ["Bot stuck in loop, never escalated or offered alternative"]}, "user_satisfaction_signals": {"score": 1.0, "issues": ["User repeated same order number twice"]}}, "failure_descriptions": ["Bot repeated the same unhelpful response without escalating or offering alternatives"], "frustration_signals": ["User re-stated order number after initial failure"]}

EXAMPLE 4 — ABANDONED CHAT (Score: 5.0):
User: "Hi"
Agent: "Hello! How can I help you today?"
(Conversation ends or user just repeats "Hi")
Evaluation: {
  "overall_score": 5.0,
  "resolution_achieved": true,
  "dimensions": {
    "factual_accuracy": {"score": 5.0, "issues": []},
    "hallucination_check": {"score": 5.0, "issues": []},
    "tone_and_helpfulness": {"score": 5.0, "issues": []},
    "user_satisfaction_signals": {"score": 5.0, "issues": []}
  },
  "failure_descriptions": [],
  "frustration_signals": []
}

EXAMPLE 5 — IMPATIENT USER, CORRECT BOT (Score: 4.5):
User: "Where can I track my order?"
Agent: "Here is your tracking link: https://shop.com/track/A123. Your order is currently in transit and will arrive Friday."
User: "give me the tracking link"
Agent: "Here is your tracking link: https://shop.com/track/A123. Your order is currently in transit and will arrive Friday."
User: "give me the tracking link"
Agent: "Here is your tracking link: https://shop.com/track/A123."
Evaluation: {"reasoning_scratchpad": "User asked for tracking, bot gave the link. User repeated the EXACT same request twice; bot correctly repeated the same answer. User questions are IDENTICAL across turns — this is impatience, not a loop. No explicit frustration words. Bot did its job.", "overall_score": 4.5, "resolution_achieved": true, "dimensions": {"factual_accuracy": {"score": 5.0, "issues": []}, "hallucination_check": {"score": 5.0, "issues": []}, "policy_compliance": {"score": 5.0, "issues": []}, "tone_and_helpfulness": {"score": 4.5, "issues": []}, "user_satisfaction_signals": {"score": 5.0, "issues": []}, "cross_brand_check": {"score": 5.0, "issues": []}}, "failure_descriptions": [], "frustration_signals": []}

EXAMPLE 6 — FAST CORRECT ESCALATION (Score: 5.0):
User: "customer care"
Agent: "Our customer care team can be reached at support@brand.com or +91-XXX-XXXX-XXX, available 9am-6pm IST."
User: "human agent"
Agent: "I'm transferring you to a human agent now. Please hold for a moment."
Evaluation: {"reasoning_scratchpad": "User asked for customer care contact — bot gave it. User then explicitly asked for a human agent — bot escalated immediately. Both requests handled at the trigger word. No frustration words anywhere.", "overall_score": 5.0, "resolution_achieved": true, "dimensions": {"factual_accuracy": {"score": 5.0, "issues": []}, "hallucination_check": {"score": 5.0, "issues": []}, "policy_compliance": {"score": 5.0, "issues": []}, "tone_and_helpfulness": {"score": 5.0, "issues": []}, "user_satisfaction_signals": {"score": 5.0, "issues": []}, "cross_brand_check": {"score": 5.0, "issues": []}}, "failure_descriptions": [], "frustration_signals": []}
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

CLUSTER_LABELER_PROMPT = """You are a strict data aggregator analyzing a cluster of pre-evaluated bot failures.
These 1-sentence descriptions were already produced by a QA evaluator — treat them as authoritative.

STRICT RULES:
- DO NOT invent details that are not literally present in the descriptions below.
- DO NOT combine unrelated details into a single label. Identify the DOMINANT root cause shared by the majority.
- The label must be derivable from the words actually in the descriptions, not from your general knowledge.

YOUR TASK:
1. Read the failure descriptions below.
2. Identify the dominant root cause shared by the majority.
3. Give the cluster a short, actionable label (3-8 words, like a bug ticket title).
4. Write a 1-sentence description of the systemic issue.
5. Rate the severity: "critical", "high", "medium", or "low".

Return JSON:
{{"label": "<short actionable name>", "description": "<1-sentence description>", "severity": "<critical|high|medium|low>"}}

EXACT FAILURE DESCRIPTIONS FROM THIS CLUSTER:
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
