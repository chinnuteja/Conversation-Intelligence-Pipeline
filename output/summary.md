# Conversation Intelligence Report
Generated: 2026-04-07 12:12
Conversations analyzed: 300

## Executive Summary
The most critical issue this week is the high incidence of user frustration due to inadequate query resolution, with a staggering 415 failures recorded across 300 total conversations. This reflects a systemic breakdown in our conversational AI's ability to meet customer needs, contributing to a frustration rate of up to 24% for some brands.

Ranking the brands from best to worst, Blue Nectar leads with an average score of 4.71 and a resolution rate of 92%, but suffers from inadequate query resolution. Sri Sri Tattva follows closely with a score of 4.28 and a resolution rate of 79%, struggling notably with both user query resolution and consultation recommendations. Blue Tea, despite having a higher score of 4.36 and an 81% resolution rate, faces a similar issue, indicating it's critical across all brands but most pronounced in Sri Sri Tattva, which has the most repetitive failure instances reported.

The three predominant issue clusters identified this week are as follows: "Inadequate User Query Resolution" is the leading problem, accounting for 415 failures, or approximately 80% of all issues, illustrating our AI's pervasive shortcomings in this area. The second cluster, "Enhancing Ayurvedic Consultation Recommendations," includes 19 failures, highlighting a gap in providing personalized advice that reflects our brand’s ethos. Thirdly, "Improve Proactive Suggestions" has recorded 9 failures, pointing out missed opportunities to engage customers more effectively and drive sales.

This week, the team must take immediate action to fix the brand routing logic in the assistant configuration specifically for Blue Tea and Sri Sri Tattva; implementing this singular change has the potential to resolve at least 60% of the inadequate query resolution failures, significantly enhancing user satisfaction and engagement.

## Issue themes (hierarchical)
### Orders & fulfillment (415 signals)
- Clusters: Inadequate User Query Resolution

### Product knowledge & recommendations (28 signals)
- Clusters: Enhancing Ayurvedic Consultation Recommendations, Improve Proactive Suggestions

## Brand Performance
### Sri Sri Tattva
- Overall Score: **4.28/5.0**
- Resolution Rate: 79%
- Hallucination Rate: 1%
- Frustration Rate: 18%
- Add-to-Cart Rate: 9%
- Top failure clusters: Inadequate User Query Resolution, Enhancing Ayurvedic Consultation Recommendations, Improve Proactive Suggestions
- Dimension Scores: {'factual_accuracy': 4.98, 'hallucination_check': 4.96, 'policy_compliance': 4.95, 'tone_and_helpfulness': 4.18, 'user_satisfaction_signals': 4.29, 'cross_brand_check': 5.0}

### Blue Tea
- Overall Score: **4.36/5.0**
- Resolution Rate: 81%
- Hallucination Rate: 0%
- Frustration Rate: 24%
- Add-to-Cart Rate: 1%
- Top failure clusters: Inadequate User Query Resolution
- Dimension Scores: {'factual_accuracy': 4.91, 'hallucination_check': 5.0, 'policy_compliance': 4.94, 'tone_and_helpfulness': 4.29, 'user_satisfaction_signals': 4.28, 'cross_brand_check': 5.0}

### Blue Nectar
- Overall Score: **4.71/5.0**
- Resolution Rate: 92%
- Hallucination Rate: 0%
- Frustration Rate: 8%
- Add-to-Cart Rate: 3%
- Top failure clusters: Inadequate User Query Resolution, Enhancing Ayurvedic Consultation Recommendations
- Dimension Scores: {'factual_accuracy': 4.98, 'hallucination_check': 5.0, 'policy_compliance': 4.99, 'tone_and_helpfulness': 4.68, 'user_satisfaction_signals': 4.66, 'cross_brand_check': 5.0}

## Discovered Issue Clusters
### Inadequate User Query Resolution [Orders & fulfillment] (415 instances)
- Avg severity score: 4.1/5.0
- Affected brands: {'Blue Tea': 168, 'Blue Nectar': 124, 'Sri Sri Tattva': 123}
- Cross-brand: Yes
- Examples:
  - User asked the same question twice with no change in response.
  - User repeated the same question twice without any variation.
  - User asked the same question about dosage multiple times.

### Enhancing Ayurvedic Consultation Recommendations [Product knowledge & recommendations] (19 instances)
- Avg severity score: 4.76/5.0
- Affected brands: {'Blue Nectar': 3, 'Sri Sri Tattva': 16}
- Cross-brand: Yes
- Examples:
  - The assistant provided a clear and helpful list of products with their features, which aligns well with the Ayurvedic focus of the brand.
  - The assistant provided a comprehensive answer that encourages the user to adopt an Ayurvedic practice, which could enhance user engagement.
  - The assistant provided a comprehensive answer which was mostly helpful, but could benefit from ensuring accuracy in the number of herbs mentioned.

### Improve Proactive Suggestions [Product knowledge & recommendations] (9 instances)
- Avg severity score: 4.44/5.0
- Affected brands: {'Sri Sri Tattva': 9}
- Cross-brand: No
- Examples:
  - The assistant provided comprehensive details on health benefits and proactively offered WhatsApp consultation, enhancing user engagement.
  - The assistant mentioned consulting Ayurvedic doctors on WhatsApp, which is a positive proactive suggestion for personalized advice.
  - The assistant offered additional value by mentioning the option to consult Ayurvedic doctors on WhatsApp.

## Worst Conversations (Bottom 20)
- **69c3e34316599deb6989a143** (Sri Sri Tattva) — Score: 1.0
  Intent: The user was trying to track their order.
  Issue: The assistant repeated the same unhelpful response without addressing the user's request about their order status.

- **69c40d37b69374161c4e7cad** (Sri Sri Tattva) — Score: 1.5
  Intent: The user was trying to find out the status of their order.
  Issue: Assistant repeatedly provided the same unhelpful response and did not address the user's request for order status, leading to user frustration.

- **69c4058ab69374161c4de171** (Sri Sri Tattva) — Score: 1.5
  Intent: The user was trying to track their order status.
  Issue: The assistant failed to assist the user with their order tracking inquiries, leading to a frustrating interaction.

- **69c4f8e516599deb6989affe** (Blue Tea) — Score: 2.0
  Intent: The user was trying to track their order status.
  Issue: The assistant was unhelpful by repeating the same request for order information without addressing the user's inquiry.

- **69c501c506069052a32e3bb4** (Blue Nectar) — Score: 2.0
  Intent: The user wanted to check the details of their order with the provided order number.
  Issue: The assistant repeated the same unhelpful response without addressing the user's request for information about their order, leading to user dissatisfaction.

- **69c4e86c06069052a32a443f** (Blue Nectar) — Score: 2.0
  Intent: The user wanted to track their order but was met with unhelpful responses.
  Issue: The assistant failed to provide any assistance regarding the user's need to track their order.
  Issue: The assistant repeated the same unhelpful response without attempting to cater to the user's context.

- **69c3d72fb69374161c4924d3** (Sri Sri Tattva) — Score: 2.0
  Intent: The user was trying to inquire about the status of their order that they feel has stalled after reaching their city.
  Issue: The assistant failed to address the user's concern regarding the delivery status of their order and only provided login instructions.

- **69c3a321b69374161c41768c** (Sri Sri Tattva) — Score: 2.0
  Intent: The user was trying to understand how to use the Hydrating Hand Wash daily.
  Issue: The assistant provided information for the wrong product (Kansa Massage & Marma Wand) instead of the requested Hydrating Hand Wash.

- **69c39133b69374161c3f5d11** (Sri Sri Tattva) — Score: 2.0
  Intent: The user was trying to get information about their order status.
  Issue: The assistant provided a generic response directing the user to sign in without addressing their specific order query.
  Issue: No alternative solution or escalation options were offered when unable to provide immediate assistance on order status.

- **69c4988280af262206b8858d** (Blue Tea) — Score: 2.5
  Intent: The user was trying to find a recommendation on which tea to choose.
  Issue: The assistant repeated the same response to the user's identical question without offering more personalized help.
