"""Request auth for Archavow API.

When ARCHAVOW_API_KEY is set, all /api/v1 routers require
Authorization: Bearer <key> (see main.py router dependencies).
When unset (local MVP), a documented stub principal is used —
never deploy that mode on a reachable network.
"""

from __future__ import annotations

import hmac
import os
from typing import Annotated, Any

from fastapi import Depends, Header, HTTPException, status


def auth_required() -> bool:
    return bool(os.environ.get("ARCHAVOW_API_KEY", "").strip())


def get_current_user(
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    expected = os.environ.get("ARCHAVOW_API_KEY", "").strip()
    if expected:
        if not authorization or not authorization.lower().startswith("bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authorization Bearer token required",
                headers={"WWW-Authenticate": "Bearer"},
            )
        token = authorization.split(" ", 1)[1].strip()
        if not hmac.compare_digest(token, expected):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return {
            "id": "api-key",
            "name": "API key user",
            "auth": "api_key",
            "roles": ["architect"],
        }
    return {
        "id": "local",
        "name": "Local architect",
        "auth": "stub",
        "roles": ["architect"],
    }


# FastAPI dependency alias
CurrentUser = Annotated[dict[str, Any], Depends(get_current_user)]
