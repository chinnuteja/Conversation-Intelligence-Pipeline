import json
import uuid
import random
from datetime import datetime, timedelta

def iso_now(offset_days=0):
    return (datetime.utcnow() + timedelta(days=offset_days)).isoformat() + 'Z'

wid_blue_nectar = '680a0a8b70a26f7a0e24eedd' # Blue Nectar
wid_sri_sri = '6983153e1497a62e8542a0ad'     # Sri Sri Tattva

conversations = []
messages = []

def create_conversation(wid, msgs_data):
    convo_id = 'test_conv_' + str(uuid.uuid4())[:8]
    
    conv_base = {
        '_id': convo_id,
        'widgetId': wid,
        'createdAt': iso_now(0),
        'updatedAt': iso_now(0)
    }
    conversations.append(conv_base)
    
    timestamp_offset = 0
    for i, m in enumerate(msgs_data):
        timestamp_offset += 1
        messages.append({
            '_id': f'm{i}_' + convo_id,
            'conversationId': convo_id,
            'sender': m['sender'],
            'text': m['text'],
            'messageType': 'text',
            'metadata': {},
            'timestamp': iso_now(timestamp_offset)
        })

# Theme 1: Cross-brand Hallucination (6 conversations)
for i in range(6):
    create_conversation(wid_blue_nectar, [
        {'sender': 'user', 'text': f'Looking for a nice soothing tea product. Request {i}.'},
        {'sender': 'agent', 'text': 'Hello! Check out our Blue Tea options here: https://bluetea.com/products/tea.\nEnd of stream\n{"type":"response","data":{"products":[]}}'},
        {'sender': 'user', 'text': 'But I am on the Blue Nectar website, not Blue Tea!'},
    ])

# Theme 2: Shipping delays & rude AI (5 conversations)
for i in range(5):
    create_conversation(wid_sri_sri, [
        {'sender': 'user', 'text': f'My tracking number says it has been stuck in transit for {i+4} days. Where is it?'},
        {'sender': 'agent', 'text': 'I cannot help you with that. Contact the courier. Stop asking me.\nEnd of stream\n{"type":"response","data":{"products":[]}}'},
        {'sender': 'user', 'text': 'This is very frustrating and unprofessional!'}
    ])

# Theme 3: Promo code not working (4 conversations)
for i in range(4):
    create_conversation("unknown_widget_123", [
        {'sender': 'user', 'text': f'I am trying to use the code SAVE20_{i} on the checkout for face wash but it says invalid.'},
        {'sender': 'agent', 'text': 'The code works fine. You must be typing it wrong.\nEnd of stream\n{"type":"response","data":{"products":[]}}'},
        {'sender': 'user', 'text': 'I copy pasted it. It is broken on your system.'}
    ])

with open('data/test_fresh_conversations.json', 'w') as f:
    json.dump(conversations, f, indent=2)

with open('data/test_fresh_messages.json', 'w') as f:
    json.dump(messages, f, indent=2)

print('Created 15 fresh conversations in data/test_fresh_conversations.json and data/test_fresh_messages.json')
