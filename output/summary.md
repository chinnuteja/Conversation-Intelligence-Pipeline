# Conversation Intelligence Report
Generated: 2026-05-03 12:42
Conversations analyzed: 300

## Executive Summary
Our AI is fundamentally broken for users with order status issues, getting stuck in catastrophic loops that prevent any resolution. This week's analysis of 300 conversations shows that a single, system-wide failure pattern is responsible for the most severe user problems, tanking

## Issue themes (hierarchical)
### Orders & fulfillment (546 signals)
- Clusters: Bot omits product details from catalog

## Brand Performance
### Blue Nectar
- Overall Score: **4.04/5.0**
- Resolution Rate: 76%
- Hallucination Rate: 13%
- Frustration Rate: 14%
- Add-to-Cart Rate: 23%
- Top failure clusters: Bot omits product details from catalog
- Dimension Scores: {'factual_accuracy': 4.22, 'hallucination_check': 4.3, 'policy_compliance': 4.86, 'tone_and_helpfulness': 4.22, 'user_satisfaction_signals': 4.55, 'cross_brand_check': 5.0}

### Sri Sri Tattva
- Overall Score: **4.25/5.0**
- Resolution Rate: 81%
- Hallucination Rate: 4%
- Frustration Rate: 19%
- Add-to-Cart Rate: 15%
- Top failure clusters: Bot omits product details from catalog
- Dimension Scores: {'factual_accuracy': 4.77, 'hallucination_check': 4.83, 'policy_compliance': 4.77, 'tone_and_helpfulness': 4.29, 'user_satisfaction_signals': 4.38, 'cross_brand_check': 5.0}

### Blue Tea
- Overall Score: **4.25/5.0**
- Resolution Rate: 80%
- Hallucination Rate: 8%
- Frustration Rate: 13%
- Add-to-Cart Rate: 23%
- Top failure clusters: Bot omits product details from catalog
- Dimension Scores: {'factual_accuracy': 4.61, 'hallucination_check': 4.67, 'policy_compliance': 4.93, 'tone_and_helpfulness': 4.33, 'user_satisfaction_signals': 4.59, 'cross_brand_check': 5.0}

## Discovered Issue Clusters
### Bot omits product details from catalog [Orders & fulfillment] (546 instances)
- Avg severity score: 3.37/5.0
- Affected brands: {'Sri Sri Tattva': 180, 'Blue Tea': 173, 'Blue Nectar': 193}
- Cross-brand: Yes
- Examples:
  - Assistant hallucinated an impossible future date (2026) for the user's order.
  - Assistant hallucinated a future order date (2026).
  - Assistant hallucinated a future delivery date (2026) for an order marked as delivered.

## Worst Conversations (Bottom 20)
- **69f06950e8681adac91262b2** (Sri Sri Tattva) — Score: 1.0
  Intent: The user is trying to find a recent order that is not appearing in their account's order history.
  Issue: Assistant is stuck in a loop, repeating the same 'sign in' instruction in response to different user inputs.
  Issue: Assistant completely ignored the user's explicit statement that they were 'Already sign in'.
  Issue: The user's problem of a missing order was never addressed or escalated, leading to total non-resolution.

- **69f06774e8681adac911e43d** (Sri Sri Tattva) — Score: 1.0
  Intent: The user wanted to get information about a delayed shipment and prompt action to resolve the delay.
  Issue: The assistant got stuck in a loop, repeating 'please sign in' eight times despite changing user input.
  Issue: The assistant asked for an order number but then ignored it when the user provided it, breaking the conversational flow.
  Issue: The assistant failed to recognize clear signals of user frustration and did not escalate or change its response.

- **69f01f497149e4aa909557f4** (Sri Sri Tattva) — Score: 1.0
  Intent: The user wants to find their recent order for Ghee, which they believe is not showing in their account.
  Issue: Assistant got stuck in a loop, repeating the same response after the user provided new information about their specific order.
  Issue: The assistant failed to recognize the user's problem was not solved by the initial suggestion and did not offer any alternative help or escalation path.

- **69ef8a807149e4aa908a645d** (Sri Sri Tattva) — Score: 1.0
  Intent: The user is trying to get information about an order that is not showing up in their account and was only partially delivered.
  Issue: Assistant got stuck in a loop, repeating the same 'sign in' link three times despite the user providing new information.
  Issue: Assistant failed to recognize and escalate a high-urgency order issue (missing order, partial delivery).
  Issue: Assistant ignored specific details from the user, such as the order value and the changing nature of their query.

- **69ef1382e22e8aec1619d4b7** (Sri Sri Tattva) — Score: 1.0
  Intent: User is trying to find out why their order was only partially fulfilled and where the rest of the items are.
  Issue: Assistant is stuck in a loop, repeating the same response even when the user provides new information.
  Issue: Assistant failed to address the user's specific query about an incomplete order, providing only a generic login link.

- **69f32a3767150fce80057aec** (Blue Tea) — Score: 1.0
  Intent: The user wants to track their order status.
  Issue: Assistant gets stuck in a loop, repeating the same error message that the phone number does not match.
  Issue: Assistant fails to process information provided across multiple turns, leading to a conversational breakdown.
  Issue: Assistant provides no escape hatch or alternative resolution path when its primary flow fails.

- **69f38d6a5cad2f55381238cb** (Blue Nectar) — Score: 1.0
  Intent: The user wanted to find and purchase a product for oil pulling.
  Issue: Assistant recommended a body slimming oil for oral use (oil pulling), a dangerous off-label suggestion not supported by product data.
  Issue: Assistant hallucinated that a product for external anti-cellulite massage was suitable for oil pulling.

- **69ec332149f035ad8161df10** (Blue Nectar) — Score: 1.0
  Intent: To learn how and when to apply the Blue Nectar Kumkumadi serum/tailam.
  Issue: Assistant is stuck in a loop, repeatedly asking the user to rephrase their question instead of answering.
  Issue: Assistant failed to understand a direct question about product application instructions for 'Kumkumadi gold tailam'.
  Issue: The assistant ignored the specific product details provided by the user and continued its loop.

- **69ec230949f035ad81607cd2** (Blue Nectar) — Score: 1.0
  Intent: To find out how long a specific skin oil takes to show results and if it is suitable for oily skin.
  Issue: Assistant is stuck in a loop, repeatedly asking the user to rephrase their question.
  Issue: Assistant ignored the user's added question about suitability for oily skin.
  Issue: Assistant failed to understand a clear, specific question about a product.

- **69f3578dc9c3baf2e3aae908** (Sri Sri Tattva) — Score: 1.5
  Intent: To get information or status about two different order numbers.
  Issue: Assistant gets stuck in a loop, repeating the same generic 'sign in' response.
  Issue: Assistant ignored the user's second message containing a new order number, treating it the same as the first.
  Issue: Assistant was unable to fulfill the core user intent of checking an order status.
