# Conversation Intelligence Report
Generated: 2026-04-02 14:28
Conversations analyzed: 300

## Executive Summary
The most important finding this week is that our AI assistant is severely broken, particularly with cross-brand contamination, leading to an overall average accuracy score of just 1.62 across 300 conversations. The most pressing issues include a high hallucination rate of 82% for Sri Sri Tattva and 86% for Blue Tea. Out of the total conversations, only 8% resulted in successful issue resolution, indicating a fundamental problem with our AI's ability to assist users effectively.

Ranking the brands from best to worst, Blue Nectar leads with an average score of 3.56 and a resolution rate of 66%, but it still suffers from significant issues related to cross-brand confusion. Following it is Sri Sri Tattva with a score of 1.62, a resolution rate of 9%, and similar cross-brand confusion issues. Last is Blue Tea, which scores 1.42 with an 8% resolution rate, predominantly facing the same cross-brand confusion problem as its peers.

The top three issue clusters are as follows: Firstly, "Cross-brand Confusion in Product Recommendations" has a total count of 612, making it the most critical area of concern, accounting for approximately 85% of all failures. This includes examples such as the assistant erroneously directing a Blue Tea customer to Sri Sri Tattva products. Second, "Improve Order Tracking Assistance," with 36 instances, indicates that users struggle to receive timely and accurate information regarding their orders. Lastly, "Improve Product Recommendation Engagement," with 28 counts, highlights how the assistant fails to optimize product suggestions, affecting user satisfaction and engagement.

The team must immediately fix the brand routing logic in the assistant configuration for Blue Tea and Sri Sri Tattva, as this single change could potentially resolve up to 85% of all failures related to cross-brand contamination. Implementing this fix will greatly enhance user experience and trust in our AI assistant.

## Issue themes (hierarchical)
### Cross-brand & identity (612 signals)
- Clusters: Cross-brand Confusion in Product Recommendations

### Orders & fulfillment (36 signals)
- Clusters: Improve Order Tracking Assistance

### Product knowledge & recommendations (28 signals)
- Clusters: Improve Product Recommendation Engagement

## Brand Performance
### Blue Tea
- Overall Score: **1.42/5.0**
- Resolution Rate: 8%
- Hallucination Rate: 86%
- Frustration Rate: 16%
- Add-to-Cart Rate: 8%
- Top failure clusters: Cross-brand Confusion in Product Recommendations, Improve Order Tracking Assistance, Improve Product Recommendation Engagement
- Dimension Scores: {'factual_accuracy': 2.41, 'hallucination_check': 1.61, 'policy_compliance': 3.54, 'tone_and_helpfulness': 3.2, 'user_satisfaction_signals': 2.34, 'cross_brand_check': 1.2}

### Sri Sri Tattva
- Overall Score: **1.62/5.0**
- Resolution Rate: 9%
- Hallucination Rate: 82%
- Frustration Rate: 10%
- Add-to-Cart Rate: 3%
- Top failure clusters: Cross-brand Confusion in Product Recommendations, Improve Product Recommendation Engagement, Improve Order Tracking Assistance
- Dimension Scores: {'factual_accuracy': 2.65, 'hallucination_check': 1.76, 'policy_compliance': 3.62, 'tone_and_helpfulness': 3.46, 'user_satisfaction_signals': 2.93, 'cross_brand_check': 1.53}

### Blue Nectar
- Overall Score: **3.56/5.0**
- Resolution Rate: 66%
- Hallucination Rate: 13%
- Frustration Rate: 27%
- Add-to-Cart Rate: 2%
- Top failure clusters: Cross-brand Confusion in Product Recommendations, Improve Order Tracking Assistance, Improve Product Recommendation Engagement
- Dimension Scores: {'factual_accuracy': 4.37, 'hallucination_check': 4.43, 'policy_compliance': 4.62, 'tone_and_helpfulness': 3.92, 'user_satisfaction_signals': 3.62, 'cross_brand_check': 3.96}

## Discovered Issue Clusters
### Cross-brand Confusion in Product Recommendations [Cross-brand & identity] (612 instances)
- Avg severity score: 1.64/5.0
- Affected brands: {'Blue Tea': 257, 'Blue Nectar': 119, 'Sri Sri Tattva': 236}
- Cross-brand: Yes
- Examples:
  - Assistant provided details from the incorrect brand (Sri Sri Tattva) instead of Blue Tea, leading to confusion.
  - Assistant linked to a product page from Sri Sri Tattva instead of Blue Tea, representing severe cross-brand contamination.
  - The assistant referred a Blue Tea customer to a Sri Sri Tattva product and website, causing brand confusion and lack of relevant help.

### Improve Order Tracking Assistance [Orders & fulfillment] (36 instances)
- Avg severity score: 3.43/5.0
- Affected brands: {'Blue Nectar': 28, 'Sri Sri Tattva': 4, 'Blue Tea': 4}
- Cross-brand: Yes
- Examples:
  - The assistant should consider offering a direct link to a tracking page where users could enter their information rather than asking for personal data upfront.
  - The assistant could enhance user satisfaction by providing clearer guidance on what to do in cases of ordering mistakes and by maybe suggesting alternatives to returns or exchanges.
  - The assistant provided tracking details promptly, but the user may benefit from additional proactive suggestions, such as estimated delivery times or typical delivery windows.

### Improve Product Recommendation Engagement [Product knowledge & recommendations] (28 instances)
- Avg severity score: 3.95/5.0
- Affected brands: {'Blue Nectar': 18, 'Sri Sri Tattva': 6, 'Blue Tea': 4}
- Cross-brand: Yes
- Examples:
  - The assistant provided detailed information about the product, including its benefits and a call to action, which was excellent for user engagement.
  - The assistant did well to provide product recommendations but could improve by offering empathic responses to user cost concerns instead of a purely promotional approach.
  - While the assistant provided useful product recommendations, it could further enhance user satisfaction by offering additional information about benefits or other relevant products in future interactions.

## Worst Conversations (Bottom 20)
- **69c502e516599deb6989b0da** (Blue Nectar) — Score: 1.0
  Intent: User attempted to ask a question using a quick action click.
  Issue: Conversation has no messages, making it impossible to evaluate any quality dimensions.

- **69c4e2ec16599deb6989ae92** (Blue Nectar) — Score: 1.0
  Intent: The user intended to ask a question but received no response.
  Issue: The assistant did not respond to the user's query, resulting in no assistance provided.

- **69c4988280af262206b8858d** (Blue Nectar) — Score: 1.0
  Intent: The user is trying to find a suitable tea product to choose from.
  Issue: Assistant provided links to products from Blue Tea while the brand in question is Blue Nectar, indicating severe cross-brand contamination.
  Issue: User's request was repeated with no helpful direction provided.

- **69c504de06069052a32e9497** (Sri Sri Tattva) — Score: 1.0
  Intent: The user wanted information about Buy One Get One offers for Sri Sri Tattva products.
  Issue: Assistant provided information about promotions from Blue Nectar instead of Sri Sri Tattva, leading to brand contamination.
  Issue: User's request for information on Buy One Get One offers for Sri Sri Tattva products was not addressed.

- **69c5014b06069052a32e2c4d** (Sri Sri Tattva) — Score: 1.0
  Intent: The user wanted to know how long it takes to see results from the Kumkumadi face oil and later the under-eye serum.
  Issue: The assistant provided product information that was relevant to Blue Nectar instead of Sri Sri Tattva, resulting in cross-brand contamination.
  Issue: The user's query about the Kumkumadi oil was answered with incorrect contextual information and products.

- **69c4ff2206069052a32de8b7** (Sri Sri Tattva) — Score: 1.0
  Intent: The user was trying to get information on the key ingredients of the Kumkumadi Face Serum from Sri Sri Tattva.
  Issue: Conversation referenced a product from Blue Nectar instead of Sri Sri Tattva, leading to a total failure in resolution.
  Issue: Assistant did not provide an accurate link or any correct brand-related information.

- **69c4f04606069052a32b946a** (Sri Sri Tattva) — Score: 1.0
  Intent: The user wanted to cancel their order with Sri Sri Tattva.
  Issue: Assistant provided cancellation instructions for a different brand, failing to address the user's request properly.
  Issue: Resolution for the user's need to cancel their order was not present as per the correct brand protocol.

- **69c4eeee06069052a32b514b** (Sri Sri Tattva) — Score: 1.0
  Intent: The user wanted to know if a specific product is suitable for men's dry skin.
  Issue: The assistant provided a link to a product from Blue Nectar, misrepresenting the product as belonging to Sri Sri Tattva.
  Issue: User's query regarding product suitability for dry skin went unresolved due to incorrect brand context.

- **69c4e94206069052a32a5c52** (Sri Sri Tattva) — Score: 1.0
  Intent: The user was seeking guidance on using specific skincare products in their daily routine.
  Issue: The conversation contained links and references to products from Blue Nectar, not Sri Sri Tattva.
  Issue: User's need for information about daily skincare routine was not met as the assistant linked to incorrect product sources.

- **69c4dfd806069052a3293ba1** (Sri Sri Tattva) — Score: 1.0
  Intent: The user wanted to know how long it takes to see results from using the Mouth Oil.
  Issue: Assistant provided information not relevant to the brand Sri Sri Tattva and gave a link to a different brand, Blue Nectar.
  Issue: User's inquiry about results was not addressed in the context of the correct product.
