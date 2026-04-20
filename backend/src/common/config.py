import os
from pathlib import Path
from typing import Dict
from pydantic_settings import BaseSettings


# Calculate backend directory (parent of src) for absolute paths
# This works in both local and Docker environments
BACKEND_DIR = Path(__file__).parent.parent.parent


class Settings(BaseSettings):
    # Shared settings for all services
    secret_key: str = ""
    algorithm: str = "HS256"
    access_token_expire_seconds: int = 3600
    api_key: str = ""

    # Azure OpenAI settings (shared across services)
    AZURE_OPENAI_ENDPOINT: str = ""
    AZURE_OPENAI_API_KEY: str = ""
    AZURE_OPENAI_API_VERSION: str = "2025-01-01-preview"
    AZURE_OPENAI_DEPLOYMENT_NAME: str = ""
    azure_openai_max_completion_tokens: int = 2000
    azure_openai_temperature: float = 0.7

    # Authentication settings
    jwt_secret_key: str = "it-support-change-me-in-production-secret-key-2026"
    password_salt: str = ""

    # Encryption settings
    ENCRYPTION_KEY: str = "it-support-32-char-encrypt-key!"

    # API settings
    log_requests: bool = True
    cors_origins: str = "*"

    # Logging
    LOG_LEVEL: str = "INFO"

    class Config:
        # Point to the .env file in the project root
        env_file = str(
            Path(__file__).parent.parent.parent.parent / ".env"
        )
        env_file_encoding = 'utf-8'

    def get_azure_openai_config(self) -> Dict[str, str]:
        """
        Get Azure OpenAI configuration as a dictionary.

        Returns:
            Dict containing Azure OpenAI credentials and settings
        """
        return {
            "api_key": self.AZURE_OPENAI_API_KEY or os.getenv("AZURE_OPENAI_API_KEY", ""),
            "endpoint": self.AZURE_OPENAI_ENDPOINT or os.getenv("AZURE_OPENAI_ENDPOINT", ""),
            "api_version": self.AZURE_OPENAI_API_VERSION or os.getenv("AZURE_OPENAI_API_VERSION", "2025-01-01-preview"),
            "deployment_name": self.AZURE_OPENAI_DEPLOYMENT_NAME or os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "")
        }


settings = Settings()
