"""Factory that builds a LangChain chat model from whichever FREE provider is configured.

Supported (all have free tiers / are free):
    - groq      : Groq cloud, free tier, extremely fast Llama models
    - gemini    : Google Gemini, free tier
    - openrouter: OpenRouter, several ":free" models
    - ollama    : fully local & offline, no API key, no cost
"""
from __future__ import annotations

from langchain_core.language_models.chat_models import BaseChatModel

from career_agents.config import Settings, get_settings


def build_llm(settings: Settings | None = None, *, temperature: float = 0.4) -> BaseChatModel:
    settings = settings or get_settings()
    provider = settings.llm_provider.lower().strip()

    if provider == "groq":
        from langchain_groq import ChatGroq

        if not settings.groq_api_key:
            raise RuntimeError("GROQ_API_KEY is not set. Get a free key at https://console.groq.com/keys")
        return ChatGroq(
            model=settings.groq_model,
            api_key=settings.groq_api_key,
            temperature=temperature,
        )

    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI

        if not settings.google_api_key:
            raise RuntimeError("GOOGLE_API_KEY is not set. Get a free key at https://aistudio.google.com/apikey")
        return ChatGoogleGenerativeAI(
            model=settings.gemini_model,
            google_api_key=settings.google_api_key,
            temperature=temperature,
        )

    if provider == "openrouter":
        from langchain_openai import ChatOpenAI

        if not settings.openrouter_api_key:
            raise RuntimeError("OPENROUTER_API_KEY is not set. Get a free key at https://openrouter.ai/keys")
        return ChatOpenAI(
            model=settings.openrouter_model,
            api_key=settings.openrouter_api_key,
            base_url="https://openrouter.ai/api/v1",
            temperature=temperature,
        )

    if provider == "ollama":
        from langchain_ollama import ChatOllama

        return ChatOllama(
            model=settings.ollama_model,
            base_url=settings.ollama_base_url,
            temperature=temperature,
        )

    raise ValueError(f"Unknown LLM_PROVIDER '{provider}'. Use groq | gemini | openrouter | ollama.")
