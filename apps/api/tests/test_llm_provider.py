"""Tests for the LLM provider layer.

All tests use mock/fake — no real LLM calls.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from openai import APIConnectionError, APIStatusError, APITimeoutError
from openai.types.chat import ChatCompletion, ChatCompletionMessage
from openai.types.chat.chat_completion import Choice
from openai.types.completion_usage import CompletionUsage

from app.schemas.llm import LlmMessage, LlmRequest
from app.services.llm_provider import (
    build_request,
    generate_structured,
    generate_text,
    reset_client,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _reset():
    """Ensure each test gets a fresh client."""
    reset_client()
    yield
    reset_client()


def _make_completion(content: str, model: str = "MiniMax-M2.7") -> ChatCompletion:
    return ChatCompletion(
        id="chatcmpl-test",
        created=1700000000,
        model=model,
        object="chat.completion",
        choices=[
            Choice(
                index=0,
                finish_reason="stop",
                message=ChatCompletionMessage(role="assistant", content=content),
            )
        ],
        usage=CompletionUsage(prompt_tokens=10, completion_tokens=20, total_tokens=30),
    )


# ---------------------------------------------------------------------------
# generate_text
# ---------------------------------------------------------------------------

class TestGenerateText:
    @patch("app.services.llm_provider._get_client")
    def test_success(self, mock_get_client: MagicMock):
        client = MagicMock()
        client.chat.completions.create.return_value = _make_completion("Hello world")
        mock_get_client.return_value = client

        req = build_request("Say hello")
        resp = generate_text(req)

        assert resp.ok is True
        assert resp.text == "Hello world"
        assert resp.error is None
        assert resp.usage.total_tokens == 30
        assert resp.model == "MiniMax-M2.7"

    @patch("app.services.llm_provider._get_client")
    def test_system_prompt_included(self, mock_get_client: MagicMock):
        client = MagicMock()
        client.chat.completions.create.return_value = _make_completion("ok")
        mock_get_client.return_value = client

        req = build_request("hi", system="You are helpful")
        generate_text(req)

        call_kwargs = client.chat.completions.create.call_args[1]
        assert call_kwargs["messages"][0] == {"role": "system", "content": "You are helpful"}
        assert call_kwargs["messages"][1] == {"role": "user", "content": "hi"}
        # response_format should NOT be present for text calls
        assert "response_format" not in call_kwargs

    @patch("app.services.llm_provider._get_client")
    def test_per_request_timeout_is_forwarded(self, mock_get_client: MagicMock):
        client = MagicMock()
        client.chat.completions.create.return_value = _make_completion("ok")
        mock_get_client.return_value = client

        req = LlmRequest(
            messages=[LlmMessage(role="user", content="hi")],
            timeout=1.5,
        )
        generate_text(req)

        call_kwargs = client.chat.completions.create.call_args[1]
        assert call_kwargs["timeout"] == 1.5

    @patch("app.services.llm_provider._get_client")
    def test_timeout_error(self, mock_get_client: MagicMock):
        client = MagicMock()
        client.chat.completions.create.side_effect = APITimeoutError(request=MagicMock())
        mock_get_client.return_value = client

        resp = generate_text(build_request("hi"))

        assert resp.ok is False
        assert resp.error is not None
        assert resp.error.kind == "timeout"
        assert resp.error.retryable is True

    @patch("app.services.llm_provider._get_client")
    def test_connection_error(self, mock_get_client: MagicMock):
        client = MagicMock()
        client.chat.completions.create.side_effect = APIConnectionError(request=MagicMock())
        mock_get_client.return_value = client

        resp = generate_text(build_request("hi"))

        assert resp.ok is False
        assert resp.error.kind == "provider_error"
        assert resp.error.retryable is True

    @patch("app.services.llm_provider._get_client")
    def test_auth_error(self, mock_get_client: MagicMock):
        client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.headers = {}
        mock_response.json.return_value = {"error": {"message": "invalid key"}}
        client.chat.completions.create.side_effect = APIStatusError(
            message="Unauthorized",
            response=mock_response,
            body={"error": {"message": "invalid key"}},
        )
        mock_get_client.return_value = client

        resp = generate_text(build_request("hi"))

        assert resp.ok is False
        assert resp.error.kind == "auth_error"
        assert resp.error.retryable is False

    @patch("app.services.llm_provider._get_client")
    def test_rate_limit_error(self, mock_get_client: MagicMock):
        client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.headers = {}
        mock_response.json.return_value = {}
        client.chat.completions.create.side_effect = APIStatusError(
            message="Rate limited",
            response=mock_response,
            body={},
        )
        mock_get_client.return_value = client

        resp = generate_text(build_request("hi"))

        assert resp.ok is False
        assert resp.error.kind == "rate_limit"
        assert resp.error.retryable is True


# ---------------------------------------------------------------------------
# generate_structured
# ---------------------------------------------------------------------------

SIMPLE_SCHEMA = {
    "title": "greeting",
    "type": "object",
    "properties": {
        "message": {"type": "string"},
        "mood": {"type": "string"},
    },
    "required": ["message", "mood"],
}


class TestGenerateStructured:
    @patch("app.services.llm_provider._get_client")
    def test_success(self, mock_get_client: MagicMock):
        client = MagicMock()
        json_str = '{"message": "hello", "mood": "happy"}'
        client.chat.completions.create.return_value = _make_completion(json_str)
        mock_get_client.return_value = client

        req = build_request("greet me", response_schema=SIMPLE_SCHEMA)
        resp = generate_structured(req)

        assert resp.ok is True
        assert resp.parsed == {"message": "hello", "mood": "happy"}
        assert resp.text == json_str
        assert resp.usage.total_tokens == 30

        # Verify response_format was passed
        call_kwargs = client.chat.completions.create.call_args[1]
        rf = call_kwargs["response_format"]
        assert rf["type"] == "json_object"
        # Schema is injected into system prompt, not response_format
        system_msg = call_kwargs["messages"][0]
        assert system_msg["role"] == "system"
        assert "JSON Schema" in system_msg["content"]

    @patch("app.services.llm_provider._get_client")
    def test_json_parse_failure(self, mock_get_client: MagicMock):
        client = MagicMock()
        client.chat.completions.create.return_value = _make_completion("not valid json {{{")
        mock_get_client.return_value = client

        req = build_request("greet me", response_schema=SIMPLE_SCHEMA)
        resp = generate_structured(req)

        assert resp.ok is False
        assert resp.error.kind == "parse_error"
        assert "Failed to parse JSON" in resp.error.message
        assert resp.text == "not valid json {{{"  # raw text preserved for debugging

    def test_missing_schema_returns_error(self):
        req = build_request("greet me")  # no response_schema
        resp = generate_structured(req)

        assert resp.ok is False
        assert resp.error.kind == "parse_error"
        assert "response_schema is required" in resp.error.message

    @patch("app.services.llm_provider._get_client")
    def test_empty_response(self, mock_get_client: MagicMock):
        client = MagicMock()
        client.chat.completions.create.return_value = _make_completion("")
        mock_get_client.return_value = client

        req = build_request("greet me", response_schema=SIMPLE_SCHEMA)
        resp = generate_structured(req)

        assert resp.ok is False
        assert resp.error.kind == "parse_error"
        assert "Empty response" in resp.error.message

    @patch("app.services.llm_provider._get_client")
    def test_provider_500_error(self, mock_get_client: MagicMock):
        client = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.headers = {}
        mock_response.json.return_value = {}
        client.chat.completions.create.side_effect = APIStatusError(
            message="Internal Server Error",
            response=mock_response,
            body={},
        )
        mock_get_client.return_value = client

        req = build_request("greet me", response_schema=SIMPLE_SCHEMA)
        resp = generate_structured(req)

        assert resp.ok is False
        assert resp.error.kind == "provider_error"
        assert resp.error.retryable is True

    @patch("app.services.llm_provider._get_client")
    def test_markdown_fenced_json_is_parsed(self, mock_get_client: MagicMock):
        # Reasoning-oriented providers (MiniMax-M2.x notably) wrap JSON in
        # ```json ... ``` fences even when response_format: json_object is
        # requested. The structured path must peel the fence before
        # json.loads, otherwise every supervisor call falls back to
        # rule-based mirroring — see project_wagent_followup.md Bug C.
        client = MagicMock()
        fenced = '```json\n{"verdict": "success", "confidence": "high"}\n```'
        client.chat.completions.create.return_value = _make_completion(fenced)
        mock_get_client.return_value = client

        req = build_request("assess this", response_schema=SIMPLE_SCHEMA)
        resp = generate_structured(req)

        assert resp.ok is True
        assert resp.parsed == {"verdict": "success", "confidence": "high"}
        # Raw text is retained so debugging output still shows the fence.
        assert resp.text == fenced

    @patch("app.services.llm_provider._get_client")
    def test_fence_with_thinking_block(self, mock_get_client: MagicMock):
        # Full shape seen in the wild: <think>…</think> followed by a
        # fenced JSON block. Both wrappers must be stripped in order.
        client = MagicMock()
        payload = (
            "<think>reasoning about how to respond…</think>\n"
            '```json\n{"verdict": "partial_success"}\n```'
        )
        client.chat.completions.create.return_value = _make_completion(payload)
        mock_get_client.return_value = client

        req = build_request("assess this", response_schema=SIMPLE_SCHEMA)
        resp = generate_structured(req)

        assert resp.ok is True
        assert resp.parsed == {"verdict": "partial_success"}
        assert resp.thinking is not None
        assert "reasoning" in resp.thinking

    @patch("app.services.llm_provider._get_client")
    def test_bare_fence_without_language_tag(self, mock_get_client: MagicMock):
        # Some providers omit the ``json`` language tag.
        client = MagicMock()
        fenced = '```\n{"ok": true}\n```'
        client.chat.completions.create.return_value = _make_completion(fenced)
        mock_get_client.return_value = client

        req = build_request("assess this", response_schema=SIMPLE_SCHEMA)
        resp = generate_structured(req)

        assert resp.ok is True
        assert resp.parsed == {"ok": True}

    @patch("app.services.llm_provider._get_client")
    def test_fence_without_trailing_newline(self, mock_get_client: MagicMock):
        # MiniMax occasionally emits the closing fence without a
        # leading newline: ``...}````. The strict whole-response regex
        # must tolerate this; earlier versions fell back to parse_error
        # and silently rule-mirrored the supervisor verdict.
        client = MagicMock()
        payload = '```json\n{"verdict": "success"}```'
        client.chat.completions.create.return_value = _make_completion(payload)
        mock_get_client.return_value = client

        req = build_request("assess this", response_schema=SIMPLE_SCHEMA)
        resp = generate_structured(req)

        assert resp.ok is True
        assert resp.parsed == {"verdict": "success"}

    @patch("app.services.llm_provider._get_client")
    def test_json_with_surrounding_prose_is_recovered(
        self, mock_get_client: MagicMock,
    ):
        # "Here's your answer: {...}. Let me know if you need more."
        # is a real shape some providers emit when the system prompt
        # isn't strong enough. The raw-decode fallback walks to the
        # first '{' and parses the first balanced object.
        client = MagicMock()
        payload = (
            "Here's your answer: "
            '{"verdict": "failure", "confidence": "high"}'
            " — let me know if you need more detail."
        )
        client.chat.completions.create.return_value = _make_completion(payload)
        mock_get_client.return_value = client

        req = build_request("assess this", response_schema=SIMPLE_SCHEMA)
        resp = generate_structured(req)

        assert resp.ok is True
        assert resp.parsed == {"verdict": "failure", "confidence": "high"}

    @patch("app.services.llm_provider._get_client")
    def test_loose_fence_with_preamble_is_recovered(
        self, mock_get_client: MagicMock,
    ):
        # Preamble before a fenced block — the loose matcher picks up
        # the first fence anywhere inside the text.
        client = MagicMock()
        payload = (
            "Let me answer your question.\n\n"
            '```json\n{"verdict": "uncertain"}\n```\n\n'
            "Hope this helps!"
        )
        client.chat.completions.create.return_value = _make_completion(payload)
        mock_get_client.return_value = client

        req = build_request("assess this", response_schema=SIMPLE_SCHEMA)
        resp = generate_structured(req)

        assert resp.ok is True
        assert resp.parsed == {"verdict": "uncertain"}

    @patch("app.services.llm_provider._get_client")
    def test_truly_unparseable_reports_error_with_preview(
        self, mock_get_client: MagicMock,
    ):
        # When all recovery strategies fail, the error message should
        # carry a short preview of the raw text so we can diagnose
        # without replaying the run. LlmError.raw keeps the full
        # raw_text for deeper inspection.
        client = MagicMock()
        payload = "no json here, just prose and more prose, nothing to parse"
        client.chat.completions.create.return_value = _make_completion(payload)
        mock_get_client.return_value = client

        req = build_request("assess this", response_schema=SIMPLE_SCHEMA)
        resp = generate_structured(req)

        assert resp.ok is False
        assert resp.error.kind == "parse_error"
        assert "Preview" in resp.error.message
        assert resp.error.raw["raw_text"] == payload


# ---------------------------------------------------------------------------
# build_request helper
# ---------------------------------------------------------------------------

class TestBuildRequest:
    def test_minimal(self):
        req = build_request("hello")
        assert len(req.messages) == 1
        assert req.messages[0].content == "hello"
        assert req.system is None
        assert req.model is None

    def test_full(self):
        schema = {"type": "object", "properties": {}}
        req = build_request(
            "hello",
            system="be nice",
            model="custom-model",
            temperature=0.5,
            max_tokens=100,
            response_schema=schema,
            metadata={"trace_id": "abc"},
        )
        assert req.system == "be nice"
        assert req.model == "custom-model"
        assert req.temperature == 0.5
        assert req.max_tokens == 100
        assert req.response_schema == schema
        assert req.metadata == {"trace_id": "abc"}


# ---------------------------------------------------------------------------
# LlmRequest with multiple messages
# ---------------------------------------------------------------------------

class TestMultiMessageRequest:
    @patch("app.services.llm_provider._get_client")
    def test_multi_turn(self, mock_get_client: MagicMock):
        client = MagicMock()
        client.chat.completions.create.return_value = _make_completion("ok")
        mock_get_client.return_value = client

        req = LlmRequest(
            system="you are helpful",
            messages=[
                LlmMessage(role="user", content="first"),
                LlmMessage(role="assistant", content="got it"),
                LlmMessage(role="user", content="second"),
            ],
        )
        generate_text(req)

        call_kwargs = client.chat.completions.create.call_args[1]
        msgs = call_kwargs["messages"]
        assert len(msgs) == 4  # system + 3
        assert msgs[0]["role"] == "system"
        assert msgs[1]["content"] == "first"
        assert msgs[2]["content"] == "got it"
        assert msgs[3]["content"] == "second"
