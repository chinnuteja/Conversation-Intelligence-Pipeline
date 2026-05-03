import os
from dotenv import load_dotenv

load_dotenv()

OAI_BASE_LLM = os.getenv("OAI_BASE_LLM")
OAI_KEY_LLM = os.getenv("OAI_KEY_LLM")
OAI_VERSION = os.getenv("OAI_VERSION")

# Model config
EVAL_MODEL = "google/gemini-2.5-pro"
LABEL_MODEL = "google/gemini-2.5-pro"
SUMMARY_MODEL = "google/gemini-2.5-pro"

# Paths
DATA_DIR = "data"
OUTPUT_DIR = "output"

# Data source: "json" (flat files) or "mongodb"
DATA_SOURCE = os.getenv("DATA_SOURCE", "json").strip().lower()
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", "helio_intern")

# Optional overrides: widget_id -> display name (takes precedence over URL inference)
BRAND_MAP = {
    "680a0a8b70a26f7a0e24eedd": "Blue Tea",
    "6983153e1497a62e8542a0ad": "Blue Nectar",
    "69a92ad76dcbf2da868e0f9b": "Sri Sri Tattva",
}

# Heuristic: subdomain or domain fragment -> display name (for auto-discovery)
DOMAIN_BRAND_HINTS = [
    ("bluenectar", "Blue Nectar"),
    ("srisritattva", "Sri Sri Tattva"),
    ("bluetea", "Blue Tea"),
]

# Evaluation config (raise concurrency for faster batch eval; override with MAX_CONCURRENT_EVALS env)
MAX_CONCURRENT_EVALS = int(os.getenv("MAX_CONCURRENT_EVALS", "20"))
EMBEDDING_BATCH_SIZE = 50

# Clustering config
UMAP_N_COMPONENTS = 10
UMAP_METRIC = "cosine"
HDBSCAN_MIN_CLUSTER_SIZE = 4
HDBSCAN_MIN_SAMPLES = 2
# First-pass merge: cosine similarity between cluster label embeddings
# Default 0.65 per tuning plan; set CLUSTER_LABEL_MERGE_THRESHOLD=0.72 in .env if clusters over-merge
CLUSTER_LABEL_MERGE_THRESHOLD = float(os.getenv("CLUSTER_LABEL_MERGE_THRESHOLD", "0.80"))
# Second pass: merge clusters sharing >= this fraction of conversation IDs
CLUSTER_CONVERSATION_OVERLAP_THRESHOLD = float(
    os.getenv("CLUSTER_CONVERSATION_OVERLAP_THRESHOLD", "0.80")
)
