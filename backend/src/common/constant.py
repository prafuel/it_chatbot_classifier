"""
Application constants for IT Support services.
Values are sourced from environment variables via config.settings.
"""

from app.common.config import settings

# JWT Configuration
JWT_SECRET_KEY = settings.jwt_secret_key
API_ALGORITHM = settings.algorithm
API_ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_seconds // 60

# Encryption
ENCRYPTION_KEY = settings.ENCRYPTION_KEY

# Logging
LOG_LEVELS = ["INFO", "DEBUG", "ERROR"]
