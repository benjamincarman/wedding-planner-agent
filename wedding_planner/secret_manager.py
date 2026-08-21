"""Secure Secret Management for API Keys and Credentials."""

import os
from typing import Optional
from dotenv import load_dotenv
from wedding_planner.observability.logging import logger

# Load local environment variables if available
load_dotenv()


def get_secret(secret_key: str, default: Optional[str] = None) -> Optional[str]:
    """Securely fetches secret from GCP Secret Manager if available, or falls back to environment variables.

    Never logs secret values in plaintext.
    """
    # 1. Check local environment variable
    env_val = os.getenv(secret_key)
    if env_val:
        return env_val

    # 2. Check GCP Secret Manager if in GCP Cloud Run / Vertex environment
    gcp_project = os.getenv("GCP_PROJECT_ID")
    if gcp_project:
        try:
            from google.cloud import secretmanager
            client = secretmanager.SecretManagerServiceClient()
            name = f"projects/{gcp_project}/secrets/{secret_key}/versions/latest"
            response = client.access_secret_version(request={"name": name})
            secret_value = response.payload.data.decode("UTF-8")
            logger.info(f"Successfully retrieved secret '{secret_key}' from GCP Secret Manager")
            return secret_value
        except Exception as e:
            logger.debug(f"Secret Manager lookup skipped for '{secret_key}': {str(e)}")

    if default is not None:
        return default

    return None
