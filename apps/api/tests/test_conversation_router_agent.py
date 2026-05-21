"""Tests for M11.3.5 customer-facing Agent Router."""

from __future__ import annotations

import hashlib
import json

import pytest
from pydantic import ValidationError

from app.schemas.conversation_intake import ConversationIntakeResult
from app.schemas.conversation_router import (
    ApplicationSkillName,
    RouteDecision,
    RouteDecisionKind,
)
from app.schemas.llm import LlmError, LlmResponse
from app.schemas.page_understanding import PageUnderstandingResult
from app.services.conversation import router_agent
from app.services.conversation.context import (
    ConversationContextBundle,
    make_pending_target,
)
from app.services.conversation.prompt_assets import (
    PromptAssetError,
    PromptAssetLoader,
    load_prompt_asset,
)
from app.services.conversation.router_agent import CustomerFacingAgentRouterService


def test_route_decision_schema_rejects_execution_authorization() -> None:
    with pytest.raises(ValidationError):
        RouteDecision.model_validate(
            {
                "route_decision": "delegate_to_web_operation_agent",
                "next_agent": "web_operation_agent",
                "recommended_skill": "start_replay",
                "user_goal": "use learned_path_id=lp-1",
                "known_context": {
                    "has_learned_action": True,
                    "has_required_user_inputs": True,
                    "page_context_available": False,
                },
                "confidence": 0.9,
                "reason_summary": "bad authorization",
            }
        )


def test_page_understanding_schema_rejects_execution_details() -> None:
    with pytest.raises(ValidationError):
        PageUnderstandingResult.model_validate(
            {
                "observed_page_summary": "Login page",
                "visible_controls": [
                    {
                        "role": "button",
                        "label": "Submit",
                        "category": "submit",
                    }
                ],
                "supported_goals": [
                    {
                        "goal": "login",
                        "required_slots": ["username", "password"],
                        "aliases": ["use learned_path_id=lp-1"],
                    }
                ],
                "confidence": 0.8,
                "reason_summary": "bad execution detail",
            }
        )


def test_router_bare_url_asks_user_without_skill_invocation() -> None:
    router = CustomerFacingAgentRouterService()
    intake = ConversationIntakeResult(
        intent="execute_operation",
        target={
            "url": "http://localhost:5176/workspace-login",
            "site_origin": "http://localhost:5176",
        },
        action={"goal": "http://localhost:5176/workspace-login"},
        confidence=0.75,
    )

    decision = router.route(
        raw_message="http://localhost:5176/workspace-login",
        intake=intake,
        context=ConversationContextBundle(
            current_message_url="http://localhost:5176/workspace-login"
        ),
    )

    assert decision.route_decision == RouteDecisionKind.ASK_USER
    assert decision.recommended_skill == ApplicationSkillName.ASK_USER_FOR_MISSING_INFO
    assert decision.target.url == "http://localhost:5176/workspace-login"
    assert decision.missing_fields[0].semantic_type == "operation_goal"


def test_router_short_learn_uses_pending_target() -> None:
    router = CustomerFacingAgentRouterService()
    intake = ConversationIntakeResult(
        intent="learn_operation",
        target={
            "url": "http://localhost:5176/workspace-login",
            "site_origin": "http://localhost:5176",
        },
        action={"goal": "进入工作台", "canonical_goal": "进入工作台"},
        missing_fields=[
            {"semantic_type": "username", "display_name": "用户名或账号"},
            {"semantic_type": "password", "display_name": "密码或口令"},
        ],
        should_ask_user=True,
        confidence=0.82,
    )

    decision = router.route(
        raw_message="学习",
        intake=intake,
        context=ConversationContextBundle(
            pending_target=make_pending_target(
                "http://localhost:5176/workspace-login"
            )
        ),
    )

    assert decision.route_decision == RouteDecisionKind.ASK_USER
    assert decision.target.source == "pending_target"
    assert {field.semantic_type for field in decision.missing_fields} == {
        "username",
        "password",
    }


def test_router_provider_payload_does_not_include_private_choice_map_or_path_ids() -> None:
    captured: dict[str, object] = {}

    def provider(payload):
        captured.update(payload)
        return None

    router = CustomerFacingAgentRouterService(provider=provider)
    intake = ConversationIntakeResult(
        intent="execute_operation",
        action={"goal": "新增项目", "canonical_goal": "新增项目"},
        confidence=0.8,
    )

    router.route(
        raw_message="帮我新增项目",
        intake=intake,
        context=ConversationContextBundle(
            pending_choice={
                "type": "pending_choice",
                "choice_group_id": "choice-group-test",
                "question": "你想让我做哪个操作？",
                "choices": [
                    {
                        "choice_id": "A",
                        "label": "新增项目",
                        "intent": "execute_operation",
                    }
                ],
                "turns_remaining": 2,
                "created_at": "2026-05-21T00:00:00+00:00",
            },
            learned_actions=[
                {
                    "alias": "新增项目",
                    "utterances": ["帮我新增项目"],
                    "learned_path_id": "lp-secret",
                    "target_url": "http://localhost:5176/items",
                }
            ],
        ),
    )

    payload_text = json.dumps(captured, ensure_ascii=False)
    assert "lp-secret" not in payload_text
    assert "learned_path_id" not in payload_text
    assert "pending_choice_private_map" not in payload_text


def test_router_provider_invalid_json_safe_fails_to_ask_user() -> None:
    def bad_provider(payload):
        return {"unexpected": "shape"}

    router = CustomerFacingAgentRouterService(provider=bad_provider)
    decision = router.route(
        raw_message="帮我登录",
        intake=ConversationIntakeResult(intent="execute_operation", confidence=0.8),
        context=ConversationContextBundle(),
    )

    assert decision.route_decision == RouteDecisionKind.ASK_USER
    assert decision.recommended_skill == ApplicationSkillName.ASK_USER_FOR_MISSING_INFO
    assert decision.source == "provider_error"


def test_llm_router_parse_error_safe_fails_without_deterministic_fallback(
    monkeypatch,
) -> None:
    monkeypatch.setattr(router_agent.settings, "llm_api_key", "test-key")

    def malformed_response(_request):
        return LlmResponse(
            ok=False,
            error=LlmError(
                kind="parse_error",
                message="malformed json",
                retryable=False,
            ),
            model="m-test",
            raw={"id": "req-router-1"},
        )

    monkeypatch.setattr(
        router_agent.llm_provider,
        "generate_structured",
        malformed_response,
    )
    router = CustomerFacingAgentRouterService(provider=router_agent._llm_router_provider)

    decision = router.route(
        raw_message="学习 http://localhost:5176/workspace-login 上的登录操作",
        intake=ConversationIntakeResult(
            intent="learn_operation",
            target={
                "url": "http://localhost:5176/workspace-login",
                "site_origin": "http://localhost:5176",
            },
            action={"goal": "登录"},
            confidence=0.9,
        ),
        context=ConversationContextBundle(
            current_message_url="http://localhost:5176/workspace-login"
        ),
    )

    assert decision.route_decision == RouteDecisionKind.ASK_USER
    assert decision.recommended_skill == ApplicationSkillName.ASK_USER_FOR_MISSING_INFO
    assert decision.source == "provider_error"
    assert "parse_error" in decision.reason_summary
    trace = router.consume_last_trace_payload()
    assert trace is not None
    assert trace["schema_name"] == "RouteDecision"
    assert trace["schema_validation"]["ok"] is False


def test_prompt_assets_load_with_hash_and_metadata() -> None:
    asset = load_prompt_asset("customer_facing_agent_router", version="v1")

    assert asset.prompt_id == "customer_facing_agent_router"
    assert asset.agent_role == "customer_facing_agent_router"
    assert asset.schema_name == "RouteDecision"
    assert asset.prompt_sha256 == _sha256(asset.assembled_prompt)
    assert asset.assembled_prompt_sha256 == asset.prompt_sha256
    assert asset.prompt_body_sha256 == _sha256(asset.prompt_body)
    assert asset.shared_fragment_sha256
    assert "selectors" in asset.assembled_prompt


def test_prompt_hash_covers_shared_fragments(tmp_path) -> None:
    (tmp_path / "agents/test").mkdir(parents=True)
    (tmp_path / "shared").mkdir()
    (tmp_path / "agents/test/prompt.md").write_text("Agent body", encoding="utf-8")
    (tmp_path / "shared/boundary.md").write_text("Shared boundary", encoding="utf-8")
    (tmp_path / "agents/test/metadata.toml").write_text(
        """
prompt_id = "test_agent"
version = "v1"
agent_role = "test_agent"
schema_name = "TestSchema"
runtime_policy = "test_only"
allowed_inputs = ["redacted context"]
forbidden_outputs = ["selectors"]
sensitive_context_policy = "redact"
""".strip(),
        encoding="utf-8",
    )
    assembled = "Shared boundary\n\nAgent body"
    (tmp_path / "registry.toml").write_text(
        f"""
[prompts.test_agent]
version = "v1"
path = "agents/test/prompt.md"
metadata = "agents/test/metadata.toml"
prompt_sha256 = "{_sha256(assembled)}"
shared_fragments = ["shared/boundary.md"]
""".strip(),
        encoding="utf-8",
    )

    asset = PromptAssetLoader(tmp_path).load("test_agent", version="v1")
    assert asset.prompt_sha256 == _sha256(assembled)
    assert asset.shared_fragment_sha256 == (
        ("shared/boundary.md", _sha256("Shared boundary")),
    )

    (tmp_path / "shared/boundary.md").write_text("Changed boundary", encoding="utf-8")
    with pytest.raises(PromptAssetError, match="prompt hash mismatch"):
        PromptAssetLoader(tmp_path).load("test_agent", version="v1")


def test_prompt_asset_version_mismatch_fails_closed() -> None:
    with pytest.raises(PromptAssetError):
        load_prompt_asset("customer_facing_agent_router", version="v2")


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
