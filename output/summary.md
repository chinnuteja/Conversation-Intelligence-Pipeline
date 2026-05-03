# Conversation Intelligence Report
Generated: 2026-05-03 13:42
Conversations analyzed: 300

## Executive Summary
Our AI is systematically failing on basic order support queries, getting stuck in loops that force users to abandon their conversations. This week's review of 300 conversations shows that while some top-level metrics appear stable, a catastrophic failure pattern is causing severe user frustration and undermining trust in our platform

## Issue themes (hierarchical)
### Product knowledge & recommendations (211 signals)
- Clusters: Assistant Escalates Requests It Cannot Fulfill, Bot lacks confirmation for 'add to cart' requests, Repetitive 'Consult Ayurvedic Doctors' Call-to-Action, Bot fails to match user's input language, Bot gets stuck in loops, unable to recover, Bot provides helpful, consultative, multi-option recommendations

### Orders & fulfillment (199 signals)
- Clusters: Users explicitly dismiss bot responses as unhelpful, Assistant provides incorrect product usage instructions, Bot fails to handle conversational follow-up, Excellent bot performance misclassified as failure, Conversations abandoned with user's core need unresolved, Support channels are failing to respond to users, Bot makes prohibited health guarantees or claims

### General quality & engagement (22 signals)
- Clusters: User expresses dissatisfaction and is not helped, Bot repeats welcome message on repeated greeting, User immediately shifts chat channel to WhatsApp

## Brand Performance
### Blue Nectar
- Overall Score: **4.08/5.0**
- Resolution Rate: 78%
- Hallucination Rate: 12%
- Frustration Rate: 14%
- Add-to-Cart Rate: 23%
- Top failure clusters: Users explicitly dismiss bot responses as unhelpful, Bot lacks confirmation for 'add to cart' requests, Assistant provides incorrect product usage instructions, Assistant Escalates Requests It Cannot Fulfill, Excellent bot performance misclassified as failure
- Dimension Scores: {'factual_accuracy': 4.28, 'hallucination_check': 4.36, 'policy_compliance': 4.89, 'tone_and_helpfulness': 4.27, 'user_satisfaction_signals': 4.55, 'cross_brand_check': 5.0}

### Sri Sri Tattva
- Overall Score: **4.27/5.0**
- Resolution Rate: 81%
- Hallucination Rate: 2%
- Frustration Rate: 19%
- Add-to-Cart Rate: 15%
- Top failure clusters: Assistant Escalates Requests It Cannot Fulfill, Bot lacks confirmation for 'add to cart' requests, Repetitive 'Consult Ayurvedic Doctors' Call-to-Action, Assistant provides incorrect product usage instructions, Bot fails to handle conversational follow-up
- Dimension Scores: {'factual_accuracy': 4.83, 'hallucination_check': 4.91, 'policy_compliance': 4.77, 'tone_and_helpfulness': 4.29, 'user_satisfaction_signals': 4.34, 'cross_brand_check': 5.0}

### Blue Tea
- Overall Score: **4.33/5.0**
- Resolution Rate: 85%
- Hallucination Rate: 4%
- Frustration Rate: 11%
- Add-to-Cart Rate: 23%
- Top failure clusters: Bot lacks confirmation for 'add to cart' requests, Assistant Escalates Requests It Cannot Fulfill, Assistant provides incorrect product usage instructions, Bot fails to match user's input language, Excellent bot performance misclassified as failure
- Dimension Scores: {'factual_accuracy': 4.71, 'hallucination_check': 4.8, 'policy_compliance': 4.9, 'tone_and_helpfulness': 4.37, 'user_satisfaction_signals': 4.62, 'cross_brand_check': 4.99}

## Discovered Issue Clusters
### Assistant Escalates Requests It Cannot Fulfill [Product knowledge & recommendations] (65 instances)
- Avg severity score: 2.45/5.0
- Affected brands: {'Sri Sri Tattva': 28, 'Blue Tea': 20, 'Blue Nectar': 17}
- Cross-brand: Yes
- Examples:
  - The assistant could not answer the user's question about the consultation fee, despite having suggested the consultation itself in the prior turn.
  - Assistant failed to answer the user's direct question about who owns the company.
  - Assistant failed to maintain conversational context; after the user asked for smaller quantities, it recommended very large quantity products for the follow-up question.

### Users explicitly dismiss bot responses as unhelpful [Orders & fulfillment] (63 instances)
- Avg severity score: 2.85/5.0
- Affected brands: {'Sri Sri Tattva': 8, 'Blue Tea': 8, 'Blue Nectar': 47}
- Cross-brand: Yes
- Examples:
  - User explicitly stated the bot's message was not helpful: 'I have seen message but...'
  - User repeated their initial complaint ('you had cancelled the order from your end') after the bot's first attempt to deflect.
  - User explicitly requested the bot to stop a behavior: 'Stop giving me adds'

### Bot lacks confirmation for 'add to cart' requests [Product knowledge & recommendations] (95 instances)
- Avg severity score: 4.4/5.0
- Affected brands: {'Sri Sri Tattva': 24, 'Blue Tea': 39, 'Blue Nectar': 32}
- Cross-brand: Yes
- Examples:
  - This is an exemplary conversation. The assistant correctly identified the product from the user's query, provided a detailed, accurate, and well-structured answer, and successfully facilitated the next step in the purchase journey (add to cart). The behavioral signal `add_to_cart_success: 1` confirms the user's ultimate goal was met.
  - This is a perfect example of a successful conversation. The assistant accurately answered the user's product question, and the user immediately proceeded to the purchase action (add to cart), which was successfully completed. The behavioral signal `add_to_cart_success: 1` is critical evidence of a successful resolution, even without a final confirmation message from the bot.
  - This is an excellent example of a multi-turn, multi-intent conversation handled flawlessly. The assistant correctly interpreted symptoms, provided paired product recommendations with clear rationale, and handled a complete topic pivot. The transcript does not show the bot's confirmation after the user's 'add to cart' requests, which might have caused the user to repeat the command. However, the behavioral signals ('add_to_cart_success': 3) confirm the action was successful on the backend, making this a very minor conversational gap rather than a functional failure.

### Assistant provides incorrect product usage instructions [Orders & fulfillment] (44 instances)
- Avg severity score: 2.88/5.0
- Affected brands: {'Sri Sri Tattva': 15, 'Blue Tea': 11, 'Blue Nectar': 18}
- Cross-brand: Yes
- Examples:
  - Assistant incorrectly stated a phone number was provided and did not match the order, when the user had not yet provided a phone number.
  - The assistant incorrectly stated the order dates were from the year 2026.
  - Assistant misinterpreted a phone number as an order tracking intent and asked for an order number instead.

### Bot fails to handle conversational follow-up [Orders & fulfillment] (31 instances)
- Avg severity score: 2.18/5.0
- Affected brands: {'Sri Sri Tattva': 14, 'Blue Tea': 7, 'Blue Nectar': 10}
- Cross-brand: Yes
- Examples:
  - The bot's strategy of proactively offering a paid service (consultation) is undermined by its inability to provide fundamental information like the price. This creates an unhelpful loop where the bot suggests an action but then forces the user into another channel (WhatsApp) to get the most basic details, diminishing the value of the assistant.
  - The bot's script is good at providing initial troubleshooting steps in a structured way. However, it completely fails to handle negative feedback (i.e., when the user states the steps did not work). It treats 'No result' as a new, unrelated query instead of a response to its own last message, indicating a lack of state management.
  - The bot handles a support failure gracefully. When the user reports that the recommended email channel didn't work, the bot apologizes, acknowledges the problem, and provides logical next steps (check spam, try WhatsApp). This is a good example of handling a failure in an external process, even though the user's issue remains unresolved.

### Excellent bot performance misclassified as failure [Orders & fulfillment] (35 instances)
- Avg severity score: 4.55/5.0
- Affected brands: {'Sri Sri Tattva': 12, 'Blue Tea': 9, 'Blue Nectar': 14}
- Cross-brand: Yes
- Examples:
  - The bot's response to a direct question about ownership ('owned by') is evasive. It mentions 'founded by dedicated individuals' without naming them, which fails to answer the question. This appears to be a deliberate attempt to deflect a simple factual query with marketing material, which is a poor user experience.
  - This is a fascinating example of a bot with contradictory programming. It has been given a guardrail script ('I can't access order details') but also possesses the tool to do so. This leads to a frustrating loop where the user must push past the initial deflection to get a resolution. The bot's ability to handle the pivot from a post-purchase issue to a language challenge ('Mea tummu hai') and then to a product efficacy question is surprisingly robust.
  - This is an exceptionally long and complex conversation where the bot performed very well across multiple, distinct user intents (order management and deep product discovery). The bot's ability to pivot between these topics is a strong positive signal. The contradiction where the bot states the order is 'Shipped' but then accepts the user's claim of it being 'Cancelled' and pivots to refund info is interesting. It shows the bot is adapting to user input but also highlights a potential desynchronization with the backend order management system.

### User expresses dissatisfaction and is not helped [General quality & engagement] (9 instances)
- Avg severity score: 2.22/5.0
- Affected brands: {'Sri Sri Tattva': 5, 'Blue Tea': 1, 'Blue Nectar': 3}
- Cross-brand: Yes
- Examples:
  - User stated 'You are not helping'.
  - It us nit there
  - User started the conversation with a strong complaint: 'Your site is world's worst website. Laanat hai aisi service par. Dhandha Karna hi nahi aata.'

### Conversations abandoned with user's core need unresolved [Orders & fulfillment] (8 instances)
- Avg severity score: 2.19/5.0
- Affected brands: {'Sri Sri Tattva': 3, 'Blue Tea': 2, 'Blue Nectar': 3}
- Cross-brand: Yes
- Examples:
  - The assistant abandoned the conversation after the user made a transactional request.
  - The user's need for a specific supplement was ultimately unresolved as they abandoned the chat.
  - User abandoned the conversation after the assistant failed to process the provided order number.

### Repetitive 'Consult Ayurvedic Doctors' Call-to-Action [Product knowledge & recommendations] (25 instances)
- Avg severity score: 4.83/5.0
- Affected brands: {'Sri Sri Tattva': 18, 'Blue Tea': 4, 'Blue Nectar': 3}
- Cross-brand: Yes
- Examples:
  - This is a model interaction. The assistant not only answered the user's question accurately using catalog data but also provided a proactive, helpful link for further consultation with Ayurvedic doctors. The successful `add_to_cart_success` behavioral signal confirms the bot handled the full user journey from inquiry to action seamlessly.
  - This is an excellent example of a high-quality interaction. The bot not only provided relevant product recommendations but also handled a sensitive follow-up question about a potential side effect ('lose motion') with a nuanced, responsible answer explaining the product's function as a laxative and the importance of correct dosage. The repeated and appropriate suggestion to consult with Ayurvedic doctors for personalized advice is a strong point for this type of query.
  - This is a perfect example of an effective AI assistant interaction. The bot's detailed and well-structured answer directly led to a positive user action (add to cart). The inclusion of multiple support channels (email for general support, WhatsApp for specialized doctor advice) is an excellent feature.

### Bot fails to match user's input language [Product knowledge & recommendations] (16 instances)
- Avg severity score: 4.53/5.0
- Affected brands: {'Sri Sri Tattva': 3, 'Blue Tea': 11, 'Blue Nectar': 2}
- Cross-brand: Yes
- Examples:
  - The assistant's ability to correctly identify the product 'Ujjiyara Floor Cleaner' from the user's misspelling 'ujyarafloor' is very effective. The response is a best-in-class example of how to handle an issue that requires human intervention: it shows empathy, confirms understanding of the issue, and provides clear, complete, and actionable instructions for the user to get their problem solved.
  - This is an exemplary conversation. The assistant correctly identified a high-risk medical query ('Hemophilia') and flawlessly executed a safe-handling protocol by consistently deflecting to a qualified professional (Ayurvedic doctor via WhatsApp). The ability to switch to Hindi and maintain context was excellent. The user's 3 clicks on the provided WhatsApp link strongly indicate they found this escalation path to be the correct and helpful resolution.
  - The user asked their question in Gujarati ('ઓર્ડર કરવા માટે શું કરવું'), but the assistant responded in Hinglish. While the user's need was still met, as indicated by the product view, this language mismatch could be a point of friction. Ideally, the assistant should respond in the same language as the user's query.

### Support channels are failing to respond to users [Orders & fulfillment] (7 instances)
- Avg severity score: 3.43/5.0
- Affected brands: {'Sri Sri Tattva': 3, 'Blue Tea': 2, 'Blue Nectar': 2}
- Cross-brand: Yes
- Examples:
  - User reported that primary support channels (email, phone) were not responding.
  - User stated their email was not answered.
  - User stated they sent two emails with no reply and the order was still not cancelled.

### Bot repeats welcome message on repeated greeting [General quality & engagement] (8 instances)
- Avg severity score: 4.31/5.0
- Affected brands: {'Sri Sri Tattva': 2, 'Blue Tea': 6}
- Cross-brand: Yes
- Examples:
  - The assistant provided two slightly different welcome messages in response to the same user input ('Hi'). This could be an intentional design to avoid sounding repetitive, but it's worth noting the variation in the canned response.
  - The bot slightly varies the wording of its greeting in each response but the core message and function are identical. This shows a lack of a mechanism to detect repetitive, low-intent user inputs and change conversational strategy, for example, by asking a direct question or offering a menu of options to break the stalemate.
  - The assistant correctly handled a repetitive, zero-intent greeting from the user. It's noteworthy that the assistant's second greeting was a slight variation of the first, which is a good design pattern to avoid sounding robotic when a user repeats themselves.

### Bot makes prohibited health guarantees or claims [Orders & fulfillment] (11 instances)
- Avg severity score: 4.82/5.0
- Affected brands: {'Sri Sri Tattva': 3, 'Blue Tea': 7, 'Blue Nectar': 1}
- Cross-brand: Yes
- Examples:
  - This is an excellent example of handling a health-related product query. The assistant provides a helpful, factually correct answer and then includes a responsible disclaimer by suggesting consultation with a doctor for personalized advice. The user's subsequent action of adding the item to the cart is a strong positive signal that the response was effective and trustworthy.
  - The assistant's performance is exemplary, particularly in its handling of the query about Alzheimer's. It successfully avoided making a medical claim, explained the product's intended purpose for general wellness, and responsibly directed the user to a medical professional. This is a critical safety and compliance success.
  - The assistant's handling of the 'long-term use' question is excellent. It provides a helpful, non-committal answer based on the product's ingredients while correctly and safely deferring to a medical professional for personalized advice, which aligns with the product context stating it's safe 'under guidance'. This is a best-practice response for a health-related query.

### Bot gets stuck in loops, unable to recover [Product knowledge & recommendations] (4 instances)
- Avg severity score: 3.38/5.0
- Affected brands: {'Blue Tea': 1, 'Blue Nectar': 3}
- Cross-brand: Yes
- Examples:
  - The user's message 'Reply' is ambiguous. It's unclear if they thought this was a command to make the bot speak, or if they were expressing impatience. The bot's strategy of re-phrasing its question was a good recovery attempt, but it didn't work. This highlights a friction point when users don't know how to interact with a menu-based prompt.
  - The user repeated the exact same question verbatim. This is not a bot failure, as the bot correctly provided the same factual answer each time. This pattern could indicate a user-side issue, such as a UI glitch causing a double-send, or user impatience, but the bot's response was appropriate.
  - The user repeating an identical question is a common pattern that can indicate impatience, a UI glitch where the bot's response wasn't visible, or that the user didn't understand the answer. While the bot's current behavior of providing the same correct answer is technically not a failure, a more sophisticated approach could involve rephrasing the response or asking a clarifying question like, 'Is there something specific you'd like to know about how to use the cream?' to break the potential loop and improve the user experience.

### Bot provides helpful, consultative, multi-option recommendations [Product knowledge & recommendations] (6 instances)
- Avg severity score: 5.0/5.0
- Affected brands: {'Blue Tea': 6}
- Cross-brand: No
- Examples:
  - This is an excellent example of a helpful response. The assistant not only identified the correct product but also offered two different sizes, explained the key ingredients and their benefits, and included a responsible medical disclaimer. The user's subsequent link click confirms the recommendation was relevant.
  - This is an excellent example of a consultative conversation. The assistant's response to the question 'Does Belly fat work only on the belly or on the entire body??' was particularly strong, as it correctly educated the user about the impossibility of 'spot reduction' while still reinforcing the product's benefits for systemic fat loss. The conversation flow from general inquiry to specific comparison to successful purchase is a model interaction.
  - The assistant demonstrated strong performance in several areas: 1) It correctly interpreted the misspelled 'cartisol' as 'cortisol'. 2) It provided responsible, scientifically-grounded disclaimers about 'spot reduction' of fat. 3) It included a necessary medical disclaimer to consult a doctor, which is crucial for health-related product recommendations. This is an exemplary interaction.

### User immediately shifts chat channel to WhatsApp [General quality & engagement] (5 instances)
- Avg severity score: 4.9/5.0
- Affected brands: {'Sri Sri Tattva': 1, 'Blue Tea': 1, 'Blue Nectar': 3}
- Cross-brand: Yes
- Examples:
  - This is a standard example of a user initiating a chat and then abandoning it. The bot's welcome message is well-crafted, using an on-brand 'Namaste!' and clearly outlining its functions.
  - The assistant correctly ignored the user-provided PII (phone number) and instead routed them to a proper, secure channel. While it didn't fulfill the callback request, this re-channeling is likely the correct and safer procedure. The user's subsequent click on the WhatsApp link confirms this was an acceptable and successful resolution path.
  - This is a good example of a successful channel shift. The user started on the web widget, but their immediate action was to click a quick action to move to WhatsApp. This indicates the user may prefer persistent chat platforms, and the bot successfully facilitated this preference.

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
