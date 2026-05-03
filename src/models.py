from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


# ── Stage 1: Normalized data models ──

class ProductContext(BaseModel):
    """Product data extracted from agent message JSON."""
    title: str
    description: str
    price: str
    link: Optional[str] = None
    variants: list[dict] = []

class NormalizedMessage(BaseModel):
    """A single message, cleaned and ready for evaluation."""
    id: str
    sender: str                          # "user" or "agent"
    text: str                            # Clean text (no embedded JSON)
    message_type: str                    # "text" or "event"
    event_type: Optional[str] = None     # e.g., "product_view", "add_to_cart_success"
    timestamp: datetime
    product_context: Optional[list[ProductContext]] = None  # Only for agent messages

class ConversationThread(BaseModel):
    """A full conversation, normalized and ready for evaluation."""
    conversation_id: str
    widget_id: str
    brand_name: str
    created_at: datetime
    messages: list[NormalizedMessage]
    # Derived behavioral signals
    user_message_count: int = 0
    agent_message_count: int = 0
    event_counts: dict[str, int] = {}    # e.g., {"add_to_cart_success": 1, "link_click": 3}
    has_add_to_cart: bool = False
    has_product_view: bool = False


# ── Stage 2: Evaluation models ──

class DimensionEval(BaseModel):
    """Evaluation of a single rubric dimension."""
    score: float = Field(ge=0, le=5)
    issues: list[str] = []
    evidence: list[str] = []

class ConversationEvaluation(BaseModel):
    """Complete evaluation output for one conversation."""
    conversation_id: str
    brand_name: str
    widget_id: str
    reasoning_scratchpad: str = ""     # LLM's chain-of-thought before scoring
    overall_score: float = Field(ge=0, le=5)
    resolution_achieved: bool
    dimensions: dict[str, DimensionEval]   # Keys: factual_accuracy, policy_compliance, etc.
    failure_descriptions: list[str] = []   # Free-text, 1 sentence each
    user_intent: str
    frustration_signals: list[str] = []
    open_observations: str = ""
    # Behavioral signals carried from Stage 1
    has_add_to_cart: bool = False
    event_counts: dict[str, int] = {}


# ── Stage 3: Clustering models ──

class DiscoveredCluster(BaseModel):
    """A cluster of related failure descriptions, auto-labeled."""
    cluster_id: int
    auto_label: str                      # LLM-generated human-readable name
    count: int
    severity_avg: float                  # Average overall_score of parent conversations
    examples: list[str]                  # Sample failure descriptions
    affected_brands: dict[str, int] = {} # Brand → count
    is_cross_brand: bool = False         # Appears in 2+ brands
    sample_conversation_ids: list[str] = []
    conversation_ids: list[str] = []     # All unique conversation ids (merge / analytics)
    parent_theme: Optional[str] = None   # Hierarchical grouping, e.g. cross-brand contamination


class ClusterThemeRollup(BaseModel):
    """Rollup of clusters under a parent theme for reporting / UI."""
    parent_theme: str
    cluster_labels: list[str] = []
    total_count: int = 0


# ── Stage 4: Report models ──

class BrandReport(BaseModel):
    """Aggregated stats for one brand."""
    brand_name: str
    widget_id: str
    conversation_count: int
    avg_overall_score: float
    resolution_rate: float
    hallucination_rate: float
    frustration_rate: float
    add_to_cart_rate: float
    top_failure_clusters: list[str] = []
    dimension_scores: dict[str, float] = {}

class PipelineReport(BaseModel):
    """The full output of the pipeline."""
    generated_at: datetime
    total_conversations: int
    brands: list[BrandReport]
    discovered_clusters: list[DiscoveredCluster]
    cluster_theme_rollups: list[ClusterThemeRollup] = []
    worst_conversations: list[ConversationEvaluation] = []  # Bottom 20 by score
    executive_summary: str = ""
