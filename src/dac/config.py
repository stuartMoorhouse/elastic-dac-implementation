"""Configuration and settings management."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    kibana_url: str = Field(description="Full URL to Kibana instance")
    elastic_api_key: str = Field(description="Elastic API key for authentication")
    elastic_space: str = Field(default="default", description="Kibana space name")

    @property
    def kibana_api_url(self) -> str:
        """Return the base API URL for the configured space."""
        base = self.kibana_url.rstrip("/")
        if self.elastic_space == "default":
            return f"{base}/api"
        return f"{base}/s/{self.elastic_space}/api"


def get_settings() -> Settings:
    """Load and return application settings."""
    return Settings()  # type: ignore[call-arg]
