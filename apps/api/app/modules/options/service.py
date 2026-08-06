"""Architecture options + package generation (S2).

This module is kept as a thin backward-compatible re-export. The
implementation now lives in sibling modules:
- schemas.py — OptionOut, AdrOut, RiskOut, CitationOut, PackageOut
- options_ops.py — option generation, listing, selection
- package_ops.py — package generation and retrieval
"""

from __future__ import annotations

# Re-exported (not just referenced) so callers/tests may monkeypatch
# `app.modules.options.service.build_gateway` and have it take effect in
# options_ops/package_ops, which look it up through this module at call time.
from app.ai.gateway import build_gateway
from app.modules.options.options_ops import generate_options, list_options, select_option
from app.modules.options.package_ops import generate_package, get_package
from app.modules.options.schemas import AdrOut, CitationOut, OptionOut, PackageOut, RiskOut

__all__ = [
    "OptionOut",
    "AdrOut",
    "RiskOut",
    "CitationOut",
    "PackageOut",
    "generate_options",
    "list_options",
    "select_option",
    "generate_package",
    "get_package",
    # Re-exported so `service.build_gateway` remains monkeypatchable.
    "build_gateway",
]
