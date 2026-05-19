"""Tests for M11.3.5 application skill registry."""

from __future__ import annotations

from app.schemas.conversation_router import ApplicationSkillName
from app.services.conversation.skills import ApplicationSkillRegistry, SkillRuntime


def test_application_skill_registry_covers_all_contract_skills() -> None:
    registry = ApplicationSkillRegistry()

    names = {skill.name for skill in registry.list()}

    assert names == set(ApplicationSkillName)
    assert registry.get("start_learning").browser_access is True
    assert registry.get("start_learning").writes_learned_path is True
    assert registry.get("lookup_learned_actions").browser_access is False


def test_skill_runtime_executes_only_registered_skill() -> None:
    runtime = SkillRuntime(
        executors={
            ApplicationSkillName.LOOKUP_LEARNED_ACTIONS: lambda payload: {
                "items": payload.get("items", [])
            }
        }
    )

    result = runtime.execute(
        ApplicationSkillName.LOOKUP_LEARNED_ACTIONS,
        {"items": [{"alias": "登录"}]},
    )

    assert result.status == "completed"
    assert result.output == {"items": [{"alias": "登录"}]}


def test_skill_runtime_redacts_sensitive_payload() -> None:
    runtime = SkillRuntime(
        executors={
            ApplicationSkillName.RECORD_AGENT_TRACE: lambda payload: {
                "echo": payload
            }
        }
    )

    result = runtime.execute(
        ApplicationSkillName.RECORD_AGENT_TRACE,
        {"slot": {"sensitive": True, "value": "123456"}},
    )

    assert result.output["echo"]["slot"]["value"] == "[REDACTED]"
