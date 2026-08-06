"""Options + package Pydantic schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class OptionDesignOut(BaseModel):
    approach: str = ""
    assumptions: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    key_decisions: list[str] = Field(default_factory=list)


class OptionOut(BaseModel):
    id: str
    key: str
    title: str
    summary: str
    pros: list[str]
    cons: list[str]
    fit_score: int
    cost_band: str
    ops_band: str
    recommended: bool
    selected: bool
    stack: list[str] = Field(default_factory=list)
    origin: str = "template"  # template | ai
    design: OptionDesignOut = Field(default_factory=OptionDesignOut)


class AdrOut(BaseModel):
    id: str
    title: str
    status: str
    context: str
    decision: str
    consequences: list[str] = Field(default_factory=list)
    rationale: str = ""
    alternatives: list[str] = Field(default_factory=list)
    owner: str | None = None


class RiskOut(BaseModel):
    id: str
    title: str
    category: str = ""
    severity: str
    likelihood: str = ""
    impact: str
    mitigation: str
    residual_risk: str = ""
    owner: str | None = None
    target_date: str | None = None


class CitationOut(BaseModel):
    document_id: str
    chunk_id: str
    title: str
    source_class: str
    citation: str
    excerpt: str
    score: float


class PackageOut(BaseModel):
    id: str
    status: str
    option_id: str
    hld_markdown: str
    mermaid: str
    mermaid_sequence: str = ""
    mermaid_deploy: str = ""
    mermaid_container: str = ""
    adrs: list[AdrOut] = Field(default_factory=list)
    risks: list[RiskOut] = Field(default_factory=list)
    citations: list[CitationOut] = Field(default_factory=list)
    quality_score: dict = Field(default_factory=dict)
    backlog: list[dict] = Field(default_factory=list)
    epics: list[dict] = Field(default_factory=list)
    threats: list[dict] = Field(default_factory=list)
    documents: dict[str, str] = Field(default_factory=dict)
    retrieval_status: str = "ok"
    ai_summary: str | None = None
    ai_assist: dict = Field(default_factory=lambda: {"status": "skipped"})
    provenance: dict
