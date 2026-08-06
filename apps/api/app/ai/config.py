"""Resolve EffectiveAIConfig from env + workspace overrides."""

from __future__ import annotations

import os
from typing import Any, Mapping

from app.ai.schemas import ChatModelRef, EffectiveAIConfig

_SECRET_OVERRIDE_KEYS = frozenset(
    {
        "openai_api_key",
        "OPENAI_API_KEY",
        "openai_api_key_configured",
    }
)


def _env_get(env: Mapping[str, str], key: str, default: str = "") -> str:
    return str(env.get(key, default) or default).strip()


def resolve_effective_ai_config(
    env: Mapping[str, str] | None = None,
    overrides: Mapping[str, Any] | None = None,
) -> EffectiveAIConfig:
    """Merge process env (defaults/secrets) with workspace DB overrides."""
    env_map: Mapping[str, str] = env if env is not None else os.environ
    overrides = dict(overrides or {})

    # Secrets never from overrides
    for key in list(overrides):
        if key in _SECRET_OVERRIDE_KEYS:
            overrides.pop(key, None)

    chat_provider = _env_get(env_map, "AI_CHAT_PROVIDER", "ollama")
    embedding_provider = _env_get(env_map, "AI_EMBEDDING_PROVIDER", "none")
    chat_model_ollama = _env_get(env_map, "OLLAMA_CHAT_MODEL", "llama3.2")
    chat_model_openai = _env_get(env_map, "OPENAI_CHAT_MODEL", "gpt-4o-mini")
    embed_model_ollama = _env_get(env_map, "OLLAMA_EMBEDDING_MODEL", "nomic-embed-text")
    embed_model_openai = _env_get(env_map, "OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
    dims_raw = _env_get(env_map, "OPENAI_EMBEDDING_DIMENSIONS", "768")
    try:
        embedding_dimensions = int(dims_raw)
    except ValueError:
        embedding_dimensions = 768
    # pgvector column is fixed at 768 (migration 0017); reject drift.
    if embedding_dimensions != 768:
        embedding_dimensions = 768

    ollama_base_url = _env_get(env_map, "OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    openai_base_url = _env_get(env_map, "OPENAI_BASE_URL", "https://api.openai.com/v1")
    api_key = _env_get(env_map, "OPENAI_API_KEY", "")

    # Apply non-secret overrides
    if "chat_provider" in overrides and overrides["chat_provider"] is not None:
        chat_provider = str(overrides["chat_provider"])
    if "embedding_provider" in overrides and overrides["embedding_provider"] is not None:
        embedding_provider = str(overrides["embedding_provider"])
    if "embedding_dimensions" in overrides and overrides["embedding_dimensions"] is not None:
        try:
            embedding_dimensions = int(overrides["embedding_dimensions"])
        except (TypeError, ValueError):
            embedding_dimensions = 768
        if embedding_dimensions != 768:
            embedding_dimensions = 768
    if "ollama_base_url" in overrides and overrides["ollama_base_url"]:
        ollama_base_url = str(overrides["ollama_base_url"])
    if "openai_base_url" in overrides and overrides["openai_base_url"]:
        openai_base_url = str(overrides["openai_base_url"])

    # Normalize once (handles "oai" alias and casing) so every downstream use —
    # including ChatModelRef, which has no normalizing validator unlike
    # EffectiveAIConfig.chat_provider — sees a value that's actually
    # Literal["ollama", "openai"].
    chat_provider = "openai" if str(chat_provider).strip().lower() in {"openai", "oai"} else "ollama"

    # Resolve chat_model: override wins, else provider-specific env
    if overrides.get("chat_model"):
        chat_model = str(overrides["chat_model"])
    else:
        chat_model = chat_model_openai if chat_provider == "openai" else chat_model_ollama

    if overrides.get("embedding_model"):
        embedding_model = str(overrides["embedding_model"])
    else:
        norm_emb = str(embedding_provider).lower()
        if norm_emb in {"openai", "oai"}:
            embedding_model = embed_model_openai
        else:
            embedding_model = embed_model_ollama

    hld_chain_raw = overrides.get("hld_fallback_chain")
    hld_fallback_chain: list[ChatModelRef] = []
    if isinstance(hld_chain_raw, list):
        for entry in hld_chain_raw:
            if not isinstance(entry, dict):
                continue
            model_name = str(entry.get("model") or "").strip()
            if not model_name:
                continue
            provider_raw = str(entry.get("provider") or "ollama").strip().lower()
            provider = "openai" if provider_raw in {"openai", "oai"} else "ollama"
            hld_fallback_chain.append(ChatModelRef(provider=provider, model=model_name))  # type: ignore[arg-type]
    if not hld_fallback_chain:
        primary = ChatModelRef(provider=chat_provider, model=chat_model)  # type: ignore[arg-type]
        ollama_fallback = ChatModelRef(provider="ollama", model=chat_model_ollama)
        hld_fallback_chain = (
            [primary]
            if (primary.provider, primary.model) == (ollama_fallback.provider, ollama_fallback.model)
            else [primary, ollama_fallback]
        )

    return EffectiveAIConfig(
        chat_provider=chat_provider,  # type: ignore[arg-type]
        chat_model=chat_model,
        embedding_provider=embedding_provider,  # type: ignore[arg-type]
        embedding_model=embedding_model,
        embedding_dimensions=embedding_dimensions,
        ollama_base_url=ollama_base_url,
        openai_base_url=openai_base_url,
        openai_api_key_configured=bool(api_key),
        hld_fallback_chain=hld_fallback_chain,
    )
