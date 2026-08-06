"""Round-3/4 anti-slop: diagrams, persisted origin, health mock."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.ai.assist import as_ai_failure
from app.modules.options.generator import OptionTemplate, ProjectContext
from app.modules.options.package_builders import (
    build_c4_container_mermaid,
    build_deploy_mermaid,
    build_hld_markdown,
    build_sequence_mermaid,
)


def _opt(**kwargs) -> OptionTemplate:
    base = dict(
        key="custom_fit",
        title="Custom",
        summary="AI scored recommendation for this intake",
        pros=["a", "b"],
        cons=["c", "d"],
        fit_score=88,
        cost_band="$$",
        ops_band="medium",
        recommended=True,
        stack=["postgres"],
        origin="ai",
    )
    base.update(kwargs)
    return OptionTemplate(**base)


def test_hld_ai_origin_skips_starter_disclaimer() -> None:
    ctx = ProjectContext(name="Events", tech_constraints="Kafka")
    hld = build_hld_markdown(ctx, _opt(origin="ai"))
    assert "starter template" not in hld.lower()


def test_hld_template_origin_keeps_disclaimer() -> None:
    ctx = ProjectContext(name="Batch", tech_constraints="Postgres")
    hld = build_hld_markdown(
        ctx,
        _opt(
            key="recommended_batch",
            summary="[Starter template] Baseline batch",
            origin="template",
            fit_score=1,
        ),
    )
    assert "starter template" in hld.lower()


def test_diagrams_omit_invented_event_driven_stack() -> None:
    ctx = ProjectContext(
        name="Desktop ETL",
        business_objective="Nightly file transform",
        tech_constraints="Spring Batch, Postgres",
    )
    option = _opt(stack=["postgres", "spring-batch"], origin="template")
    container = build_c4_container_mermaid(ctx, option)
    sequence = build_sequence_mermaid(ctx, option)
    deploy = build_deploy_mermaid(ctx, option)
    blob = "\n".join([container, sequence, deploy]).lower()
    assert "event bus" not in blob
    assert "kafka" not in blob
    assert "api gateway" not in blob
    assert "ingest service" not in blob
    assert "202 accepted" not in blob
    assert "postgres" in blob
    assert "client" not in blob or "scheduler" in blob
    assert "response" not in sequence.lower() or "no interactive response" in sequence.lower()
    assert "scheduler" in blob or "trigger" in blob
    assert "consumers of the system" not in container.lower()


def test_batch_sequence_has_no_interactive_client_roundtrip() -> None:
    ctx = ProjectContext(
        name="Nightly ETL",
        tech_constraints="Spring Batch, Postgres",
    )
    option = _opt(stack=["postgres", "spring-batch"], origin="template")
    sequence = build_sequence_mermaid(ctx, option).lower()
    assert "actor client" not in sequence
    assert "client->>" not in sequence
    assert "-->>client" not in sequence
    assert "trigger" in sequence or "scheduler" in sequence
    assert "unresolved" in sequence


def test_diagrams_include_kafka_when_evidenced() -> None:
    ctx = ProjectContext(name="Events", tech_constraints="Kafka, AKS, API gateway")
    option = _opt(stack=["kafka", "aks", "postgres", "gateway"], origin="ai")
    container = build_c4_container_mermaid(ctx, option)
    deploy = build_deploy_mermaid(ctx, option)
    assert "Event bus" in container or "Kafka" in container
    assert "Kafka" in deploy
    assert "API Gateway" in container or "Ingress" in deploy


def test_deploy_aks_only_does_not_invent_kafka_or_postgres() -> None:
    ctx = ProjectContext(name="Compute", tech_constraints="AKS")
    option = _opt(stack=["aks"], origin="ai")
    deploy = build_deploy_mermaid(ctx, option).lower()
    assert "kafka" not in deploy
    assert "event hubs" not in deploy
    assert "postgres" not in deploy


def test_as_ai_failure_degrades_provider_errors() -> None:
    from app.ai.gateway import EmptyAIResponseError

    status = as_ai_failure(EmptyAIResponseError("empty"))
    assert status.status == "failed"
    assert "empty" in (status.detail or "")


def test_as_ai_failure_reraises_programming_errors() -> None:
    with pytest.raises(AttributeError):
        as_ai_failure(AttributeError("bug"))


def test_probe_postgres_ok_when_schema_present_without_migrate_flag(monkeypatch) -> None:
    """Readiness follows table presence, not whether this process ran migrations."""
    import app.main as main_mod

    monkeypatch.setattr(main_mod, "_SCHEMA_READY", False)
    monkeypatch.setattr(main_mod, "_SCHEMA_DETAIL", "skipped")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://example/db")

    fake_conn = MagicMock()
    fake_conn.__enter__.return_value = fake_conn
    fake_conn.__exit__.return_value = False
    fake_conn.execute.return_value.scalar.return_value = True

    fake_engine = MagicMock()
    fake_engine.connect.return_value = fake_conn

    monkeypatch.setattr(main_mod, "get_engine", lambda: fake_engine)

    result = main_mod._probe_postgres()
    assert result.get("schema_ready") is True
    assert result.get("ok") is True


def test_consistency_gap_is_stack_neutral() -> None:
    from app.modules.requirements.gaps import IntakeSnapshot, analyze_gaps

    snap = IntakeSnapshot(
        preferred_cloud="AWS",
        tech_constraints="Python, SQS",
        requirement_texts=[],
    )
    analysis = analyze_gaps(snap)
    consistency = next(g for g in analysis.gaps if g.code == "consistency")
    assert "kafka" not in consistency.prompt.lower()
