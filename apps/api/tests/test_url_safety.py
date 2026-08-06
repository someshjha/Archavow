"""Unit tests for AI base URL SSRF guards."""

from __future__ import annotations

import pytest

from app.ai.url_safety import UnsafeAIBaseURLError, assert_safe_ai_base_url


def test_allows_loopback_ollama() -> None:
    assert assert_safe_ai_base_url("http://127.0.0.1:11434").endswith("11434")


def test_allows_host_docker_internal(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ALLOW_PRIVATE_AI_URLS", "false")
    assert "host.docker.internal" in assert_safe_ai_base_url(
        "http://host.docker.internal:11434"
    )


def test_blocks_metadata_ip(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ALLOW_PRIVATE_AI_URLS", "true")
    with pytest.raises(UnsafeAIBaseURLError):
        assert_safe_ai_base_url("http://169.254.169.254/latest/meta-data/")


def test_blocks_non_http() -> None:
    with pytest.raises(UnsafeAIBaseURLError):
        assert_safe_ai_base_url("file:///etc/passwd")
