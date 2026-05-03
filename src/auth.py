"""
Authentication helper for Google Cloud ADC and Vertex AI.
Generates OAuth tokens to be used as API keys for the OpenAI-compatible Vertex endpoint.
"""

import os
import google.auth
from google.auth.transport.requests import Request
import logging

logger = logging.getLogger(__name__)

def get_vertex_token() -> str:
    """Fetch a fresh OAuth token from Google Cloud ADC."""
    try:
        credentials, _ = google.auth.default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        credentials.refresh(Request())
        return credentials.token
    except Exception as e:
        logger.error("Failed to fetch Vertex AI token. Ensure GOOGLE_APPLICATION_CREDENTIALS is set. Error: %s", e)
        raise

def get_vertex_base_url() -> str:
    """Construct the Vertex AI OpenAI-compatible base URL."""
    project = os.getenv("GOOGLE_CLOUD_PROJECT", "pipeline-bot-495204")
    location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
    return f"https://{location}-aiplatform.googleapis.com/v1beta1/projects/{project}/locations/{location}/endpoints/openapi"
