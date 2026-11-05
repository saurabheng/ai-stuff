"""Central configuration loaded from environment variables / .env file."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # LLM selection
    llm_provider: str = Field(default="groq")

    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"

    google_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"

    openrouter_api_key: str = ""
    openrouter_model: str = "meta-llama/llama-3.3-70b-instruct:free"

    ollama_model: str = "llama3.1"
    ollama_base_url: str = "http://localhost:11434"

    # LinkedIn official API
    linkedin_access_token: str = ""
    linkedin_author_urn: str = ""

    # Profile data
    profile_path: str = "./config/profile.json"

    def load_profile(self) -> dict[str, Any]:
        """Read the user's profile JSON; fall back to the example file."""
        path = Path(self.profile_path)
        if not path.exists():
            example = Path("./config/profile.example.json")
            path = example if example.exists() else path
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))


@lru_cache
def get_settings() -> Settings:
    return Settings()
