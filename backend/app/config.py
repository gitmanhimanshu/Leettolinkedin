"""Application configuration using Pydantic Settings with robust env parsing."""

import json
from typing import List
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Server & Environment
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    DEBUG: bool = True
    ENVIRONMENT: str = "development"
    CORS_ORIGINS: List[str] = ["*"]
    API_SHARED_SECRET: str = "code2linkedin-dev-secret-token"

    # Phase 5: xAI Grok API Configuration
    XAI_API_KEY: str = ""
    GROK_MODEL: str = "grok-2-latest"
    XAI_BASE_URL: str = "https://api.x.ai/v1"

    # Phase 6: Cloudinary Configuration
    CLOUDINARY_CLOUD_NAME: str = ""
    CLOUDINARY_API_KEY: str = ""
    CLOUDINARY_API_SECRET: str = ""

    # Phase 6: MongoDB Configuration
    MONGODB_URI: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "code2linkedin"

    # Phase 7: LinkedIn Configuration
    LINKEDIN_CLIENT_ID: str = ""
    LINKEDIN_CLIENT_SECRET: str = ""
    LINKEDIN_REDIRECT_URI: str = "https://backend-tau-five-76.vercel.app/api/auth/linkedin/callback"
    LINKEDIN_SCOPE: str = "openid profile w_member_social"
    LINKEDIN_DRAFT_MODE: bool = False
    LINKEDIN_API_VERSION: str = "202601"

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug(cls, v):
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            return v.strip().lower() in ("true", "1", "yes", "dev", "debug")
        return bool(v)

    @field_validator("PORT", mode="before")
    @classmethod
    def parse_port(cls, v):
        try:
            return int(v)
        except (ValueError, TypeError):
            return 8000

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors(cls, v):
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return parsed
            except Exception:
                pass
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return ["*"]

    @field_validator("LINKEDIN_DRAFT_MODE", mode="before")
    @classmethod
    def parse_draft(cls, v):
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            return v.strip().lower() in ("true", "1", "yes")
        return bool(v)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
