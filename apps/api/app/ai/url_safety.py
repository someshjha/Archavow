"""Validate AI provider base URLs to reduce SSRF risk."""

from __future__ import annotations

import ipaddress
import os
import socket
from urllib.parse import urlparse


class UnsafeAIBaseURLError(ValueError):
    """Raised when a configured AI base URL is not safe to fetch."""


def assert_safe_ai_base_url(url: str) -> str:
    """Allow http(s) to loopback/public hosts; block metadata and (by default) private nets.

    Set ALLOW_PRIVATE_AI_URLS=true to reach LAN Ollama/OpenAI-compatible gateways.
    Cloud metadata endpoints are always rejected.
    """
    raw = (url or "").strip()
    if not raw:
        raise UnsafeAIBaseURLError("empty AI base URL")
    parsed = urlparse(raw)
    if parsed.scheme not in {"http", "https"}:
        raise UnsafeAIBaseURLError("AI base URL must be http or https")
    host = (parsed.hostname or "").strip().lower()
    if not host:
        raise UnsafeAIBaseURLError("AI base URL missing host")
    if host in {"metadata.google.internal", "metadata", "instance-data"}:
        raise UnsafeAIBaseURLError("metadata hosts are not allowed")
    # Docker Desktop / Compose host gateway — treated like loopback for local Ollama
    if host in {"host.docker.internal", "localhost", "127.0.0.1", "::1"}:
        return raw.rstrip("/")

    allow_private = os.environ.get("ALLOW_PRIVATE_AI_URLS", "false").lower() in {
        "1",
        "true",
        "yes",
    }
    try:
        infos = socket.getaddrinfo(host, parsed.port or 80, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise UnsafeAIBaseURLError(f"AI base URL host could not be resolved: {host}") from exc

    for info in infos:
        sockaddr = info[4]
        ip_str = sockaddr[0]
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            continue
        if ip.is_loopback:
            continue
        if ip.is_link_local or ip_str.startswith("169.254."):
            raise UnsafeAIBaseURLError("link-local / cloud-metadata addresses are not allowed")
        if ip.is_private or ip.is_reserved or ip.is_multicast:
            if not allow_private:
                raise UnsafeAIBaseURLError(
                    "private AI base URLs require ALLOW_PRIVATE_AI_URLS=true"
                )
            continue
        # public address — ok
    return raw.rstrip("/")
