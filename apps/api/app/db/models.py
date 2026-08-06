"""ORM models — S0 + S1."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import EmbeddingVector, JSONType, UUIDType

# Keep in sync with migration 0017 and default embedding_dimensions.
EMBEDDING_VECTOR_DIM = 768

# Partial unique indexes: Postgres + SQLite (unit tests).
_INTERVIEW_SOURCE_WHERE = text("source LIKE 'interview:%'")
_SELECTED_OPTION_WHERE = text("selected IS TRUE")


class ProjectRow(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(UUIDType, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    stack_tags: Mapped[list] = mapped_column(JSONType, nullable=False, default=list)
    business_objective: Mapped[str | None] = mapped_column(Text, nullable=True)
    problem_statement: Mapped[str | None] = mapped_column(Text, nullable=True)
    preferred_cloud: Mapped[str | None] = mapped_column(String(64), nullable=True)
    scale_availability: Mapped[str | None] = mapped_column(Text, nullable=True)
    tech_constraints: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class WorkspaceSettingsRow(Base):
    __tablename__ = "workspace_settings"

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    ai_overrides: Mapped[dict] = mapped_column(JSONType, nullable=False, default=dict)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class RequirementRow(Base):
    __tablename__ = "requirements"
    __table_args__ = (
        # Interview answers are one row per question code; intake/other sources may repeat.
        Index(
            "uq_requirements_project_interview_source",
            "project_id",
            "source",
            unique=True,
            postgresql_where=_INTERVIEW_SOURCE_WHERE,
            sqlite_where=_INTERVIEW_SOURCE_WHERE,
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUIDType, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    kind: Mapped[str] = mapped_column(String(32), nullable=False, default="nfr")  # fr|nfr|security|other
    text: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(64), nullable=False, default="intake")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ClarificationQuestionRow(Base):
    __tablename__ = "clarification_questions"
    __table_args__ = (
        Index(
            "uq_clarification_questions_project_code",
            "project_id",
            "code",
            unique=True,
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUIDType, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(32), nullable=False, default="nfrs")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open")  # open|answered|skipped
    answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ArchitectureOptionRow(Base):
    __tablename__ = "architecture_options"
    __table_args__ = (
        Index(
            "uq_architecture_options_one_selected",
            "project_id",
            unique=True,
            postgresql_where=_SELECTED_OPTION_WHERE,
            sqlite_where=_SELECTED_OPTION_WHERE,
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUIDType, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    key: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    pros: Mapped[list] = mapped_column(JSONType, nullable=False, default=list)
    cons: Mapped[list] = mapped_column(JSONType, nullable=False, default=list)
    fit_score: Mapped[int] = mapped_column(nullable=False, default=0)
    cost_band: Mapped[str] = mapped_column(String(16), nullable=False, default="$$$")
    ops_band: Mapped[str] = mapped_column(String(32), nullable=False, default="medium")
    recommended: Mapped[bool] = mapped_column(nullable=False, default=False)
    selected: Mapped[bool] = mapped_column(nullable=False, default=False)
    stack: Mapped[list] = mapped_column(JSONType, nullable=False, default=list)
    design: Mapped[dict] = mapped_column(JSONType, nullable=False, default=dict)
    origin: Mapped[str] = mapped_column(String(16), nullable=False, default="template")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ArchitecturePackageRow(Base):
    __tablename__ = "architecture_packages"

    id: Mapped[uuid.UUID] = mapped_column(UUIDType, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    option_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType, ForeignKey("architecture_options.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    hld_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    mermaid: Mapped[str] = mapped_column(Text, nullable=False)
    mermaid_sequence: Mapped[str] = mapped_column(Text, nullable=False, default="")
    mermaid_deploy: Mapped[str] = mapped_column(Text, nullable=False, default="")
    mermaid_container: Mapped[str] = mapped_column(Text, nullable=False, default="")
    adrs: Mapped[list] = mapped_column(JSONType, nullable=False, default=list)
    risks: Mapped[list] = mapped_column(JSONType, nullable=False, default=list)
    citations: Mapped[list] = mapped_column(JSONType, nullable=False, default=list)
    quality_score: Mapped[dict] = mapped_column(JSONType, nullable=False, default=dict)
    backlog: Mapped[list] = mapped_column(JSONType, nullable=False, default=list)
    epics: Mapped[list] = mapped_column(JSONType, nullable=False, default=list)
    threats: Mapped[list] = mapped_column(JSONType, nullable=False, default=list)
    documents: Mapped[dict] = mapped_column(JSONType, nullable=False, default=dict)
    retrieval_status: Mapped[str] = mapped_column(String(32), nullable=False, default="ok")
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    provenance: Mapped[dict] = mapped_column(JSONType, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class KnowledgeDocumentRow(Base):
    __tablename__ = "knowledge_documents"

    id: Mapped[uuid.UUID] = mapped_column(UUIDType, primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    source_class: Mapped[str] = mapped_column(String(32), nullable=False, default="org")  # org|seed|project
    source_key: Mapped[str | None] = mapped_column(String(512), nullable=True, unique=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ready")
    chunk_count: Mapped[int] = mapped_column(nullable=False, default=0)
    embedding_model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class KnowledgeChunkRow(Base):
    __tablename__ = "knowledge_chunks"

    id: Mapped[uuid.UUID] = mapped_column(UUIDType, primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType,
        ForeignKey("knowledge_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_index: Mapped[int] = mapped_column(nullable=False, default=0)
    heading: Mapped[str | None] = mapped_column(String(256), nullable=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list | None] = mapped_column(JSONType, nullable=True)
    embedding_vec = mapped_column(EmbeddingVector(EMBEDDING_VECTOR_DIM), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ArtifactRow(Base):
    __tablename__ = "artifacts"

    id: Mapped[uuid.UUID] = mapped_column(UUIDType, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    filename: Mapped[str] = mapped_column(String(256), nullable=False)
    language: Mapped[str] = mapped_column(String(64), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ReviewRunRow(Base):
    __tablename__ = "review_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUIDType, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    artifact_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType, ForeignKey("artifacts.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="completed")
    finding_count: Mapped[int] = mapped_column(nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ReviewFindingRow(Base):
    __tablename__ = "review_findings"

    id: Mapped[uuid.UUID] = mapped_column(UUIDType, primary_key=True, default=uuid.uuid4)
    review_run_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType, ForeignKey("review_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    evidence: Mapped[str] = mapped_column(Text, nullable=False)
    impact: Mapped[str] = mapped_column(Text, nullable=False)
    action: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(nullable=False, default=0.5)
    line_hint: Mapped[int | None] = mapped_column(nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open")
    owner: Mapped[str | None] = mapped_column(String(128), nullable=True)


class ExportRunRow(Base):
    __tablename__ = "export_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUIDType, primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    layout: Mapped[str] = mapped_column(String(16), nullable=False, default="folder")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ready")
    includes: Mapped[dict] = mapped_column(JSONType, nullable=False, default=dict)
    files: Mapped[list] = mapped_column(JSONType, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
