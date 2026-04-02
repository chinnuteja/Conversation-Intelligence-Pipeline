"""
Stage 1: Ingest & Normalize

Reads from JSON files or MongoDB, parses conversations and messages,
splits agent messages at "End of stream" to separate
the visible response from the embedded product context JSON.
"""

import json
import logging
import re
from datetime import datetime, timezone
from collections import Counter, defaultdict
from urllib.parse import urlparse

from src.models import (
    ConversationThread,
    NormalizedMessage,
    ProductContext,
)
from src.config import (
    BRAND_MAP,
    DATA_DIR,
    DATA_SOURCE,
    DOMAIN_BRAND_HINTS,
    MONGO_DB,
    MONGO_URI,
)

logger = logging.getLogger(__name__)


def load_raw_data() -> tuple[list[dict], list[dict]]:
    """Load conversations and messages from configured source."""
    if DATA_SOURCE == "mongodb":
        return load_from_mongodb()
    with open(f"{DATA_DIR}/conversations.json", encoding="utf-8") as f:
        conversations = json.load(f)
    with open(f"{DATA_DIR}/messages.json", encoding="utf-8") as f:
        messages = json.load(f)
    return conversations, messages


def load_from_mongodb() -> tuple[list[dict], list[dict]]:
    """Load from MongoDB (assignment-compatible helio_intern DB)."""
    from pymongo import MongoClient

    client = MongoClient(MONGO_URI)
    db = client[MONGO_DB]
    conversations = list(db.conversations.find())
    messages = list(db.messages.find())
    for c in conversations:
        c["_id"] = str(c["_id"])
        c["widgetId"] = str(c.get("widgetId", ""))
        ca = c.get("createdAt")
        ua = c.get("updatedAt")
        if hasattr(ca, "isoformat"):
            c["createdAt"] = _mongo_dt_to_iso(ca)
        if hasattr(ua, "isoformat"):
            c["updatedAt"] = _mongo_dt_to_iso(ua)
    for m in messages:
        m["_id"] = str(m["_id"])
        m["conversationId"] = str(m["conversationId"])
        ts = m.get("timestamp")
        if hasattr(ts, "isoformat"):
            m["timestamp"] = _mongo_dt_to_iso(ts)
    logger.info("Loaded %d conversations, %d messages from MongoDB", len(conversations), len(messages))
    return conversations, messages


def _mongo_dt_to_iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_agent_message(text: str) -> tuple[str, list[ProductContext]]:
    """
    Split agent message at 'End of stream' delimiter.

    Returns:
        - clean_text: The response the user actually saw
        - products: Parsed product context (ground truth for hallucination checking)
    """
    products = []
    clean_text = text

    if "End of stream\n" in text:
        parts = text.split("End of stream\n", 1)
        clean_text = parts[0].strip()
        try:
            payload = json.loads(parts[1])
            raw_products = payload.get("data", {}).get("products", [])
            for p in raw_products:
                products.append(
                    ProductContext(
                        title=p.get("title", ""),
                        description=p.get("description", ""),
                        price=p.get("price", ""),
                        link=p.get("link", ""),
                        variants=[
                            {"title": v.get("title", ""), "price": v.get("price", "")}
                            for v in p.get("variants", [])
                        ],
                    )
                )
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.warning("Malformed agent product JSON: %s", e)

    return clean_text, products


_URL_RE = re.compile(r"https?://[^\s\)\]\"']+", re.IGNORECASE)


def infer_brand_from_text(text: str) -> str | None:
    """Infer brand display name from URLs in assistant/product text."""
    for m in _URL_RE.finditer(text or ""):
        try:
            host = (urlparse(m.group(0)).hostname or "").lower()
        except Exception:
            continue
        for fragment, name in DOMAIN_BRAND_HINTS:
            if fragment in host:
                return name
    return None


def build_widget_brand_hints(
    conversations: list[dict],
    messages: list[dict],
) -> dict[str, str]:
    """
    widget_id -> inferred brand name from message URLs (majority / first strong hit).
    """
    widget_texts: dict[str, list[str]] = defaultdict(list)
    convo_widget = {c["_id"]: str(c.get("widgetId", "")) for c in conversations}
    for m in messages:
        cid = m.get("conversationId")
        wid = convo_widget.get(cid)
        if not wid:
            continue
        if m.get("sender") == "agent" and m.get("messageType") == "text":
            widget_texts[wid].append(m.get("text") or "")

    hints: dict[str, str] = {}
    for wid, texts in widget_texts.items():
        votes: dict[str, int] = defaultdict(int)
        for t in texts:
            name = infer_brand_from_text(t)
            if name:
                votes[name] += 1
        if votes:
            hints[wid] = max(votes.items(), key=lambda x: x[1])[0]
    return hints


def resolve_brand_name(widget_id: str, hints: dict[str, str]) -> str:
    if widget_id in BRAND_MAP:
        return BRAND_MAP[widget_id]
    if widget_id in hints:
        return hints[widget_id]
    return f"Brand-{widget_id[:8]}"


def build_conversation_threads() -> list[ConversationThread]:
    """
    Main Stage 1 function.
    Returns a list of fully normalized ConversationThread objects.
    """
    conversations, messages = load_raw_data()
    hints = build_widget_brand_hints(conversations, messages)

    # Index conversations by ID
    convo_map = {c["_id"]: c for c in conversations}

    # Group messages by conversation
    msg_groups = defaultdict(list)
    for m in messages:
        msg_groups[m["conversationId"]].append(m)

    threads = []
    for convo_id, convo in convo_map.items():
        raw_messages = sorted(
            msg_groups.get(convo_id, []),
            key=lambda m: m["timestamp"],
        )

        normalized_messages = []
        event_counts = Counter()

        for m in raw_messages:
            event_type = m.get("metadata", {}).get("eventType")

            if event_type:
                event_counts[event_type] += 1

            text = m.get("text", "")
            product_context = None
            if m["sender"] == "agent" and m["messageType"] == "text":
                text, products = parse_agent_message(text)
                product_context = products if products else None

            normalized_messages.append(
                NormalizedMessage(
                    id=str(m["_id"]),
                    sender=m["sender"],
                    text=text,
                    message_type=m["messageType"],
                    event_type=event_type,
                    timestamp=datetime.fromisoformat(
                        str(m["timestamp"]).replace("Z", "+00:00")
                    ),
                    product_context=product_context,
                )
            )

        widget_id = str(convo.get("widgetId", ""))
        user_msgs = [
            m
            for m in normalized_messages
            if m.sender == "user" and m.message_type == "text"
        ]
        agent_msgs = [
            m
            for m in normalized_messages
            if m.sender == "agent" and m.message_type == "text"
        ]

        threads.append(
            ConversationThread(
                conversation_id=str(convo_id),
                widget_id=widget_id,
                brand_name=resolve_brand_name(widget_id, hints),
                created_at=datetime.fromisoformat(
                    str(convo["createdAt"]).replace("Z", "+00:00")
                ),
                messages=normalized_messages,
                user_message_count=len(user_msgs),
                agent_message_count=len(agent_msgs),
                event_counts=dict(event_counts),
                has_add_to_cart=event_counts.get("add_to_cart_success", 0) > 0,
                has_product_view=event_counts.get("product_view", 0) > 0,
            )
        )

    return threads
