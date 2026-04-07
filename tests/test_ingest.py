"""Tests for Stage 1 ingest and parsing."""

import json

import pytest

from src.stage1_ingest import (
    parse_agent_message,
    resolve_brand_name,
    infer_brand_from_text,
)


def test_parse_agent_message_plain():
    text = "Hello, how can I help?"
    clean, products = parse_agent_message(text)
    assert clean == "Hello, how can I help?"
    assert products == []


def test_parse_agent_message_with_products():
    payload = {"type": "response", "data": {"products": [{"title": "Tea", "description": "Nice", "price": "10", "link": "https://bluetea.com/p", "variants": []}]}}
    text = "Try this tea.\nEnd of stream\n" + json.dumps(payload)
    clean, products = parse_agent_message(text)
    assert "Try this tea" in clean
    assert len(products) == 1
    assert products[0].title == "Tea"
    assert products[0].link == "https://bluetea.com/p"


def test_parse_agent_message_malformed_json():
    text = "Hi\nEnd of stream\n{not json"
    clean, products = parse_agent_message(text)
    assert clean == "Hi"
    assert products == []


def test_infer_brand_from_url():
    assert infer_brand_from_text("See https://www.bluenectar.co.in/x") == "Blue Nectar"
    assert infer_brand_from_text("https://shop.srisritattva.com/") == "Sri Sri Tattva"


def test_resolve_brand_name_override_and_fallback():
    hints = {"w1": "Inferred Co"}
    assert resolve_brand_name("680a0a8b70a26f7a0e24eedd", hints) == "Blue Tea"
    assert resolve_brand_name("6983153e1497a62e8542a0ad", hints) == "Blue Nectar"
    assert resolve_brand_name("69a92ad76dcbf2da868e0f9b", hints) == "Sri Sri Tattva"
    assert resolve_brand_name("w1", hints) == "Inferred Co"
    assert resolve_brand_name("unknownid1234567890", {}) == "Brand-unknowni"


def test_build_conversation_threads_minimal(monkeypatch, tmp_path):
    """Single conversation with one user and one agent message."""
    from src import stage1_ingest as ing

    convs = [
        {
            "_id": "c1",
            "widgetId": "680a0a8b70a26f7a0e24eedd",
            "createdAt": "2026-01-01T00:00:00.000Z",
            "updatedAt": "2026-01-01T00:00:00.000Z",
        }
    ]
    msgs = [
        {
            "_id": "m1",
            "conversationId": "c1",
            "sender": "user",
            "text": "Hi",
            "messageType": "text",
            "metadata": {},
            "timestamp": "2026-01-01T00:00:01.000Z",
        },
        {
            "_id": "m2",
            "conversationId": "c1",
            "sender": "agent",
            "text": "Hello https://www.bluenectar.co.in/x",
            "messageType": "text",
            "metadata": {},
            "timestamp": "2026-01-01T00:00:02.000Z",
        },
    ]

    def fake_load():
        return convs, msgs

    monkeypatch.setattr(ing, "load_raw_data", fake_load)
    threads = ing.build_conversation_threads()
    assert len(threads) == 1
    assert threads[0].conversation_id == "c1"
    assert threads[0].brand_name == "Blue Tea"
    assert threads[0].user_message_count == 1
    assert threads[0].agent_message_count == 1
