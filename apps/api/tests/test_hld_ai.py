"""build_hld_markdown_ai — AI-grounded HLD with a guaranteed deterministic fallback."""

from __future__ import annotations

from app.ai.gateway import AIGateway
from app.ai.schemas import ChatModelRef, EffectiveAIConfig
from app.modules.options.generator import OptionTemplate, ProjectContext
from app.modules.options.package_builders import build_hld_markdown, build_hld_markdown_ai
from tests.fakes import FakeChatProvider, FakeEmbeddingProvider


def _ctx() -> ProjectContext:
    return ProjectContext(name="Events", tech_constraints="Kafka", preferred_cloud="Azure")


def _opt() -> OptionTemplate:
    return OptionTemplate(
        key="rec",
        title="AKS + Kafka",
        summary="Streaming",
        pros=["a", "b"],
        cons=["c", "d"],
        fit_score=86,
        cost_band="$$$",
        ops_band="high",
        recommended=True,
        stack=["aks", "kafka"],
    )


def _base_config() -> EffectiveAIConfig:
    return EffectiveAIConfig(chat_provider="ollama", chat_model="llama3.2")


_HLD_CONTENT = {
    "component_responsibilities": [
        "The ingest service owns validating and partitioning incoming events."
    ],
    "technology_choices": [
        {
            "area": "streaming",
            "technology": "Apache Kafka",
            "why": "already evidenced in constraints",
        }
    ],
    "integration_patterns": ["Producers publish to a single topic per event type."],
    "data_ownership": ["Kafka is the durable log; Postgres holds materialized read state."],
    "api_event_boundaries": ["External partners never see internal topic names."],
    "scaling_availability": ["Partition count scales with producer throughput."],
    "failure_handling": ["Consumer groups use manual offset commits after successful writes."],
    "assumptions": ["Assuming a single Azure region for the MVP."],
}

# Same as _HLD_CONTENT but fails the quality floor: one required section is empty.
_PARTIAL_HLD_CONTENT = {**_HLD_CONTENT, "scaling_availability": []}


def _throwing_chat() -> FakeChatProvider:
    chat = FakeChatProvider()
    chat.complete_json = lambda *a, **k: (_ for _ in ()).throw(  # type: ignore[method-assign]
        ConnectionError("down")
    )
    return chat


def test_ai_success_uses_grounded_content_not_deterministic_template() -> None:
    chain = [ChatModelRef(provider="ollama", model="llama3.2")]

    def factory(cfg: EffectiveAIConfig) -> AIGateway:
        return AIGateway(
            cfg, FakeChatProvider(json_response=_HLD_CONTENT), FakeEmbeddingProvider()
        )

    markdown, source, model = build_hld_markdown_ai(
        _ctx(),
        _opt(),
        citations=None,
        executive_summary=None,
        fallback_chain=chain,
        base_config=_base_config(),
        gateway_factory=factory,
    )
    assert source == "ai"
    assert model == "ollama/llama3.2"
    assert "The ingest service owns validating and partitioning" in markdown
    assert "Apache Kafka" in markdown
    # Not the deterministic template's generic line for this same input:
    assert "Messaging / events (from stack or constraints)" not in markdown


def test_ai_assumptions_are_merged_into_assumptions_section() -> None:
    """AI-generated `assumptions` must not be silently discarded — they land
    in the same `## Assumptions` section the deterministic path renders."""
    chain = [ChatModelRef(provider="ollama", model="llama3.2")]

    def factory(cfg: EffectiveAIConfig) -> AIGateway:
        return AIGateway(
            cfg, FakeChatProvider(json_response=_HLD_CONTENT), FakeEmbeddingProvider()
        )

    markdown, source, _model = build_hld_markdown_ai(
        _ctx(),
        _opt(),
        citations=None,
        executive_summary=None,
        fallback_chain=chain,
        base_config=_base_config(),
        gateway_factory=factory,
    )
    assert source == "ai"
    assumptions_section = markdown.split("## Assumptions", 1)[1].split("##", 1)[0]
    assert "Assuming a single Azure region for the MVP." in assumptions_section


def test_falls_back_to_template_when_every_model_fails() -> None:
    chain = [ChatModelRef(provider="ollama", model="llama3.2")]

    def factory(cfg: EffectiveAIConfig) -> AIGateway:
        return AIGateway(cfg, _throwing_chat(), FakeEmbeddingProvider())

    markdown, source, model = build_hld_markdown_ai(
        _ctx(),
        _opt(),
        citations=None,
        executive_summary=None,
        fallback_chain=chain,
        base_config=_base_config(),
        gateway_factory=factory,
    )
    assert source == "template"
    assert model is None
    assert markdown == build_hld_markdown(_ctx(), _opt(), citations=None, executive_summary=None)


def test_partial_response_fails_quality_floor_and_falls_back_to_template() -> None:
    """A response missing content in a required section is worse than the
    deterministic template, so it must not "win" — even though it's valid,
    non-empty JSON that satisfies the schema's `required` list."""
    chain = [ChatModelRef(provider="ollama", model="llama3.2")]

    def factory(cfg: EffectiveAIConfig) -> AIGateway:
        return AIGateway(
            cfg, FakeChatProvider(json_response=_PARTIAL_HLD_CONTENT), FakeEmbeddingProvider()
        )

    markdown, source, model = build_hld_markdown_ai(
        _ctx(),
        _opt(),
        citations=None,
        executive_summary=None,
        fallback_chain=chain,
        base_config=_base_config(),
        gateway_factory=factory,
    )
    assert source == "template"
    assert model is None
    assert markdown == build_hld_markdown(_ctx(), _opt(), citations=None, executive_summary=None)


def test_partial_response_falls_through_to_next_chain_entry() -> None:
    """The quality floor rejects the first entry's partial response but the
    chain still tries the next entry rather than giving up immediately."""
    chain = [
        ChatModelRef(provider="ollama", model="llama3.2"),
        ChatModelRef(provider="openai", model="gpt-4o-mini"),
    ]

    def factory(cfg: EffectiveAIConfig) -> AIGateway:
        if cfg.chat_provider == "ollama":
            chat = FakeChatProvider(json_response=_PARTIAL_HLD_CONTENT)
        else:
            chat = FakeChatProvider(json_response=_HLD_CONTENT)
        return AIGateway(cfg, chat, FakeEmbeddingProvider())

    # This test exercises chain progression to an openai entry specifically,
    # so mark the key as configured — otherwise the openai entry is skipped
    # outright (see fallback.py's openai_api_key_configured guard) and this
    # would fall to the template for an unrelated reason.
    base_config = _base_config().model_copy(update={"openai_api_key_configured": True})
    markdown, source, model = build_hld_markdown_ai(
        _ctx(),
        _opt(),
        citations=None,
        executive_summary=None,
        fallback_chain=chain,
        base_config=base_config,
        gateway_factory=factory,
    )
    assert source == "ai"
    assert model == "openai/gpt-4o-mini"
    assert "The ingest service owns validating and partitioning" in markdown


def test_deterministic_build_hld_markdown_is_unchanged_by_this_refactor() -> None:
    """Regression guard: the plain function's output for a known input must
    be byte-for-byte identical to what it produced before hld.py was split
    into _template_sections/_render helpers. This golden string was captured
    by running build_hld_markdown() against the pre-refactor implementation
    with these exact inputs — not hand-written."""
    ctx = ProjectContext(name="Batch", tech_constraints="Postgres")
    option = OptionTemplate(
        key="t",
        title="T",
        summary="S",
        pros=["a", "b"],
        cons=["c", "d"],
        fit_score=3,
        cost_band="$$",
        ops_band="medium",
        recommended=True,
        stack=["postgres"],
        origin="template",
    )
    hld = build_hld_markdown(ctx, option)
    expected = (
        "# Batch — High-level design\n"
        "\n"
        "> **Working draft.** This came from a starter template, not a ranked "
        "bake-off. Treat the pieces below as a sketch until the interview "
        "fills the gaps.\n"
        "\n"
        "## Option we're packing\n"
        "**T** (draft rank 3/3; cost $$; ops medium)\n"
        "\n"
        "S\n"
        "\n"
        "### Why it might work\n"
        "- a\n"
        "- b\n"
        "\n"
        "### What you'll pay for it\n"
        "- c\n"
        "- d\n"
        "\n"
        "## Design constraints\n"
        "- _(none recorded on this option — see intake constraints above)_\n"
        "\n"
        "## Assumptions\n"
        "- How callers authenticate is still fuzzy\n"
        "- No hard RTO/RPO or backup story yet\n"
        "- Observability / on-call still blank\n"
        "- Private networking / segmentation not spelled out\n"
        "\n"
        "## Key decisions to lock\n"
        "- _(none recorded — ADRs below capture contested choices)_\n"
        "\n"
        "## Where this sits\n"
        "- Objective: —\n"
        "- Problem: —\n"
        "- Cloud: **not picked yet**\n"
        "- Constraints: Postgres\n"
        "- Scale: —\n"
        "\n"
        "## Requirements on the board\n"
        "- _(nothing captured yet)_\n"
        "\n"
        "## Standards we pulled in\n"
        "- _(none yet — drop org standards into Knowledge if you want citations here)_\n"
        "\n"
        "## Component responsibilities\n"
        "- Stack on the table: postgres\n"
        "- System of record (a data store showed up in intake/stack)\n"
        "\n"
        "## Technology choices\n"
        "- Selected stack tags: postgres\n"
        "- Landing zone: not picked yet\n"
        "- Cost / ops bands: $$ / medium\n"
        "\n"
        "## Integration patterns\n"
        "- Prefer sync APIs for request/response user paths; async messaging "
        "where fan-out, buffering, or decoupling is evidenced.\n"
        "- Keep correlation IDs across edge → services → bus → SoR.\n"
        "\n"
        "## Data ownership and storage\n"
        "- System of record: Postgres (or the store named in constraints/stack) "
        "owns authoritative writes.\n"
        "- Derived views / consumers must not silently become a second SoR.\n"
        "\n"
        "## API and event boundaries\n"
        "- External clients enter via the edge/API only.\n"
        "- Domain events (if any) are contracts — version payloads; don't leak "
        "internal tables.\n"
        "\n"
        "## Scaling and availability strategy\n"
        "- Scale note: _(still open — close in interview)_\n"
        "- Ops band **medium** drives on-call and capacity discipline.\n"
        "\n"
        "## Failure-handling approach\n"
        "- Timeouts and retries with backoff on outbound calls; idempotent "
        "writes where at-least-once delivery applies.\n"
        "- DLQ / poison handling for messaging; documented rollback on cutover "
        "(see migration plan).\n"
        "\n"
        "## Suggested next step\n"
        "Finish open interview questions, walk ADRs and risks, then export the "
        "handoff package for review.\n"
    )
    assert hld == expected
