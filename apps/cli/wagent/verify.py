"""``wagent verify`` — run one autonomous exploration via the HTTP API.

Thin client around ``/exploration/autonomous-run``. Used as the backing
command for the ``verify-scenario`` Claude Code skill so that an AI
coding agent can ask WebAgentFlow to verify a scenario without
participating in the run itself.

Contract (see the generated SKILL.md for the full policy):

    stdout  — one JSON object with the trimmed summary (or full
              snapshot with ``--full``). Machine-readable, no log noise.
    stderr  — one human-readable banner (``✓/✗ verdict — scorecard``)
              plus any error messages. Safe to ignore when parsing.
    exit    — 0 if verdict == 'success', 1 if verdict ∈ {partial_success,
              failure, uncertain}, 2 for CLI / network / spec errors.

The command does NOT start the API, does NOT drive Playwright in-process,
does NOT touch the DB directly. If the API is down, exits 2 with a clear
message. Keeping it this thin means every run is persisted the same way
a workbench run is, and the run shows up in
``/exploration/autonomous/history`` like any other.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

import httpx

# Shared vocabulary with the rule + supervisor sides — see
# apps/api/app/schemas/page_analysis.py (OutcomeVerdict).
_SUCCESS_VERDICT = "success"
_NON_SUCCESS_VERDICTS = {"partial_success", "failure", "uncertain"}

# Long enough for a full run (planner + Playwright + LLM supervisor)
# plus some margin. The workbench SSE typically finishes in 30–90s.
_DEFAULT_TIMEOUT_SEC = 300.0


# ───────────────────────────────────────────────────────────────────
# Argument parsing
# ───────────────────────────────────────────────────────────────────


def _parse_kv_json(raw: str | None) -> dict[str, str] | None:
    """Decode a --fill-values / --toggle-values JSON arg.

    Accepts either a JSON object literal (``'{"name":"alice"}'``) or
    ``@path/to/file.json`` for larger payloads. Returns None when
    the arg is omitted so the server-side default kicks in.
    """
    if raw is None or raw == "":
        return None
    if raw.startswith("@"):
        path = raw[1:]
        with open(path, encoding="utf-8") as f:
            raw = f.read()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise argparse.ArgumentTypeError(
            f"Invalid JSON: {exc.msg} (pos {exc.pos})",
        ) from exc
    if not isinstance(data, dict):
        raise argparse.ArgumentTypeError(
            "Expected a JSON object mapping role → value.",
        )
    # Coerce values to strings — the API's Pydantic schema expects
    # dict[str, str]. Boolean / numeric toggle values round-trip as
    # the stringified form.
    return {str(k): str(v) for k, v in data.items()}


def configure_parser(parser: argparse.ArgumentParser) -> None:
    """Attach ``verify``'s arguments to a subparser.

    Kept as a standalone function so the top-level ``wagent`` dispatcher
    in ``main.py`` can wire it as a subcommand without importing
    argparse internals.
    """
    parser.add_argument(
        "--spec-id",
        help=(
            "Spec id (e.g. 'login' / 'users'). Pairs with --scenario. "
            "Omit for an ad-hoc run against --url."
        ),
    )
    parser.add_argument(
        "--scenario",
        help="Scenario key within the spec (e.g. 'valid_credentials').",
    )
    parser.add_argument(
        "--url",
        help=(
            "Target URL. Required for ad-hoc runs; when --spec-id is "
            "also set, takes precedence over the spec's url_pattern."
        ),
    )
    parser.add_argument(
        "--goal",
        default="",
        help="Optional human-readable goal (passed verbatim to the planner).",
    )
    parser.add_argument(
        "--fill-values",
        type=_parse_kv_json,
        default=None,
        help=(
            "Text-input values keyed by semantic role, e.g. "
            "'{\"username\":\"admin\",\"password\":\"123456\"}'. "
            "Prefix a filename with @ to read from disk."
        ),
    )
    parser.add_argument(
        "--toggle-values",
        type=_parse_kv_json,
        default=None,
        help=(
            "Native toggle selections keyed by group role, e.g. "
            "'{\"status\":\"active\"}'. Prefix a filename with @ to "
            "read from disk."
        ),
    )
    parser.add_argument(
        "--headless",
        dest="headless",
        action="store_true",
        default=True,
        help="Run Playwright headless (default).",
    )
    parser.add_argument(
        "--headed",
        dest="headless",
        action="store_false",
        help="Show the Playwright window on the API host (debugging).",
    )
    parser.add_argument(
        "--language",
        default=None,
        help=(
            "Language hint for the supervisor LLM's natural-language "
            "output (e.g. 'en' / 'zh' / 'ja')."
        ),
    )
    parser.add_argument(
        "--api-base",
        default=os.environ.get("WBAF_API_BASE", "http://localhost:8001"),
        help=(
            "Base URL of the WebAgentFlow API "
            "(env: WBAF_API_BASE, default http://localhost:8001)."
        ),
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=_DEFAULT_TIMEOUT_SEC,
        help=f"HTTP timeout in seconds (default {_DEFAULT_TIMEOUT_SEC:.0f}).",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help=(
            "Emit the full run snapshot (page_analysis + all steps + "
            "verification) instead of the trimmed summary."
        ),
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Indent the JSON output for human reading.",
    )


# ───────────────────────────────────────────────────────────────────
# Argument validation
# ───────────────────────────────────────────────────────────────────


def _validate_args(args: argparse.Namespace) -> None:
    """Fail fast on combinations the API would reject anyway.

    CLI-level errors exit 2 (distinct from verdict-failure exit 1).
    """
    if args.spec_id and not args.scenario:
        print(
            "wagent verify: --spec-id requires --scenario.\n"
            "Either pass both, or drop --spec-id for an ad-hoc run.",
            file=sys.stderr,
        )
        raise SystemExit(2)
    if not args.spec_id and not args.url:
        print(
            "wagent verify: need either --spec-id/--scenario "
            "(to run a known spec) or --url (ad-hoc).",
            file=sys.stderr,
        )
        raise SystemExit(2)


# ───────────────────────────────────────────────────────────────────
# Response formatting
# ───────────────────────────────────────────────────────────────────


def _trim_result(result: dict[str, Any]) -> dict[str, Any]:
    """Strip the heavy parts of the run snapshot for default output.

    Keeps: run_id, verdict, summary, final state basics, supervisor
    verdict / summary / anomalies / suggestions, scorecard top-level
    scores. Drops: full step log, page_analysis element lists,
    supervisor `_thinking`, screenshots.

    The full payload is still accessible via ``--full`` or
    ``GET /exploration/autonomous-runs/get?run_id=…``.
    """
    verification = result.get("verification") or {}
    scorecard = verification.get("scorecard") or {}
    supervisor = result.get("supervisor") or {}

    # scorecard trimmed to the 5 top-level score blocks — each
    # carries { score, weight_note }; the per-element / per-action
    # check details are in the full snapshot.
    score_keys = (
        "element_recognition",
        "action_coverage",
        "verdict_accuracy",
        "distraction_avoidance",
        "supervisor_agreement",
    )
    scorecard_summary = {
        k: {
            "score": (scorecard.get(k) or {}).get("score"),
            "weight_note": (scorecard.get(k) or {}).get("weight_note"),
        }
        for k in score_keys
        if k in scorecard
    }

    # Scenario-match awareness: for spec-driven runs, the rubric
    # already computes whether the run satisfied the scenario's
    # expectation (invalid_credentials scenario expects a login wall;
    # no_match scenario expects zero rows; etc.). Surface that
    # boolean so the CLI can exit 0 when a negative scenario behaves
    # as designed, even though the rule-side top-level verdict is
    # "failure". See scorecard.verdict_check.matches_expectation in
    # page_verification.py.
    vc = scorecard.get("verdict_check") or {}
    scenario_matched: bool | None = None
    if "matches_expectation" in vc:
        scenario_matched = bool(vc.get("matches_expectation"))

    # Strict pass gate — the authoritative pass/fail/unverified outcome
    # the CLI uses for its exit code. See PassGate in
    # apps/api/app/schemas/page_verification.py for the product
    # rationale. Runs without a gate (ad-hoc, pre-feature) fall back
    # to scenario_matched + verdict-based exit.
    pg = scorecard.get("pass_gate") or {}
    pass_gate_status: str | None = pg.get("status")
    pass_gate_reasons: list[str] = list(pg.get("reasons") or [])

    supervisor_source: str | None = None
    if supervisor:
        supervisor_source = supervisor.get("_supervisor_source")

    return {
        "run_id": result.get("run_id"),
        "verdict": result.get("verdict"),
        "success": result.get("success"),
        "scenario_matched": scenario_matched,
        "pass_gate": {
            "status": pass_gate_status,
            "reasons": pass_gate_reasons,
        } if pass_gate_status else None,
        "summary": result.get("summary"),
        "final_url": result.get("final_url"),
        "final_title": result.get("final_title"),
        "total_steps": result.get("total_steps"),
        "elapsed_ms": result.get("elapsed_ms"),
        "supervisor": {
            "verdict": supervisor.get("verdict"),
            "confidence": supervisor.get("confidence"),
            "summary": supervisor.get("summary"),
            "anomalies": supervisor.get("anomalies") or [],
            "suggestions": supervisor.get("suggestions") or [],
            "source": supervisor_source,
            "error_kind": supervisor.get("_supervisor_error_kind"),
        } if supervisor else None,
        "scorecard": {
            "page_id": scorecard.get("page_id"),
            "scenario": scorecard.get("scenario"),
            **scorecard_summary,
        } if scorecard else None,
    }


def _banner(result: dict[str, Any]) -> str:
    """One-line human banner written to stderr for Claude / operator.

    Reads from the trimmed result only — keep this cheap and safe
    against partial data.

    Priority for the glyph + status word:
      1. Pass gate (``result.pass_gate.status``) — the authoritative
         pass/fail/unverified outcome for spec-driven runs.
      2. Scenario match (legacy runs without a gate) — handles ad-hoc
         or pre-feature persistence.
      3. Raw verdict (ad-hoc runs with no spec at all).
    """
    verdict = result.get("verdict") or "unknown"
    scenario_matched = result.get("scenario_matched")
    gate = result.get("pass_gate") or {}
    gate_status = gate.get("status")

    if gate_status == "pass":
        glyph, status_word = "✓", "pass"
    elif gate_status == "fail":
        glyph, status_word = "✗", "fail"
    elif gate_status == "unverified":
        glyph, status_word = "⚠", "unverified"
    elif scenario_matched is True:
        glyph, status_word = "✓", "scenario-matched"
    elif scenario_matched is False:
        glyph, status_word = "✗", "scenario-mismatch"
    elif verdict == _SUCCESS_VERDICT:
        glyph, status_word = "✓", "success"
    else:
        glyph, status_word = "✗", verdict

    run_id = result.get("run_id") or "<no-run-id>"
    sc = result.get("scorecard") or {}
    scores = [
        sc.get(k, {}).get("score")
        for k in (
            "element_recognition", "action_coverage", "verdict_accuracy",
            "distraction_avoidance", "supervisor_agreement",
        )
    ]
    filled = [s for s in scores if isinstance(s, (int, float))]
    score_str = ""
    if filled:
        passed = sum(1 for s in filled if s >= 1.0)
        score_str = f" scorecard={passed}/{len(filled)}"

    return f"{glyph} run={run_id} {status_word} verdict={verdict}{score_str}"


def _exit_code_for(
    verdict: str | None,
    scenario_matched: bool | None = None,
    pass_gate_status: str | None = None,
) -> int:
    """Map the result to a POSIX exit code.

    Authoritative: ``pass_gate.status``. ``pass`` → 0; ``fail`` or
    ``unverified`` → 1. Scenario-match fallback for legacy / gate-
    less runs; then plain verdict check. Unverified deliberately
    exits non-zero because "LLM couldn't cross-check" is not a pass —
    that was the whole point of introducing the gate.
    """
    if pass_gate_status == "pass":
        return 0
    if pass_gate_status in ("fail", "unverified"):
        return 1
    if scenario_matched is True:
        return 0
    if scenario_matched is False:
        return 1
    if verdict == _SUCCESS_VERDICT:
        return 0
    if verdict in _NON_SUCCESS_VERDICTS:
        return 1
    # Missing verdict / unknown value → treat as non-success, distinct
    # from CLI-level errors which always exit 2.
    return 1


# ───────────────────────────────────────────────────────────────────
# Spec-driven hydration + HTTP
# ───────────────────────────────────────────────────────────────────


def _build_payload(args: argparse.Namespace) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "url": args.url or "",
        "goal": args.goal or "",
        "headless": args.headless,
    }
    if args.fill_values is not None:
        payload["fill_values"] = args.fill_values
    if args.toggle_values is not None:
        payload["toggle_values"] = args.toggle_values
    if args.spec_id:
        payload["spec_id"] = args.spec_id
    if args.scenario:
        payload["scenario"] = args.scenario
    if args.language:
        payload["language"] = args.language
    return payload


def _resolve_url_from_spec(
    client: httpx.Client, spec_id: str,
) -> str | None:
    """When --spec-id is set but --url is not, resolve the target URL
    from the spec's ``url_pattern``.

    A spec's ``url_pattern`` is a *match pattern* used by the workbench
    to auto-pick a spec for an operator-typed URL — it can be a bare
    path like ``/login``. Only absolute ``http(s)://`` values are safe
    to navigate to; for path-style patterns this returns None and
    emits a stderr hint telling the caller to pass ``--url`` explicitly.
    """
    try:
        r = client.get(f"/exploration/specs/{spec_id}")
        r.raise_for_status()
        body = r.json()
        data = (body or {}).get("data") or {}
        raw = (data.get("url_pattern") or "").strip()
    except Exception:
        return None
    if not raw:
        return None
    if raw.startswith(("http://", "https://")):
        return raw
    print(
        f"wagent verify: spec '{spec_id}' has a path-style url_pattern "
        f"('{raw}'); pass --url explicitly, e.g. "
        f"--url http://localhost:5175{raw}",
        file=sys.stderr,
    )
    return None


def _hydrate_values_from_spec(
    client: httpx.Client, spec_id: str, scenario: str,
) -> tuple[dict[str, str] | None, dict[str, str] | None]:
    """Pull fill_values / selections from the spec's scenario when the
    operator didn't override them on the command line. Mirrors what
    the workbench does when the user picks a scenario.
    """
    try:
        r = client.get(f"/exploration/specs/{spec_id}")
        r.raise_for_status()
        body = r.json()
        data = (body or {}).get("data") or {}
        scenarios = data.get("scenarios") or []
        sc = next((s for s in scenarios if s.get("key") == scenario), None)
        if sc is None:
            return None, None
        inputs = sc.get("inputs") or None
        selections = sc.get("selections") or None
        inputs = {str(k): str(v) for k, v in inputs.items()} if inputs else None
        selections = {str(k): str(v) for k, v in selections.items()} if selections else None
        return inputs, selections
    except Exception:
        return None, None


def run(args: argparse.Namespace) -> int:
    """Entry point called by ``wagent``'s top-level dispatcher."""
    _validate_args(args)

    api_base = args.api_base.rstrip("/")

    # One long-lived httpx.Client so connection reuse + timeout are
    # centralised. The exploration request itself is a single POST.
    with httpx.Client(base_url=api_base, timeout=args.timeout) as client:
        # Spec-driven hydration: if operator passed --spec-id/--scenario
        # but omitted --url / --fill-values / --toggle-values, fill in
        # the gaps from the spec JSON.
        if args.spec_id and args.scenario:
            if not args.url:
                resolved_url = _resolve_url_from_spec(client, args.spec_id)
                if resolved_url:
                    args.url = resolved_url
            if args.fill_values is None or args.toggle_values is None:
                inputs, selections = _hydrate_values_from_spec(
                    client, args.spec_id, args.scenario,
                )
                if args.fill_values is None and inputs is not None:
                    args.fill_values = inputs
                if args.toggle_values is None and selections is not None:
                    args.toggle_values = selections

        if not args.url:
            print(
                "wagent verify: could not determine target URL. "
                "Pass --url explicitly or verify the spec's url_pattern.",
                file=sys.stderr,
            )
            return 2

        payload = _build_payload(args)

        try:
            response = client.post("/exploration/autonomous-run", json=payload)
        except httpx.ConnectError as exc:
            print(
                f"wagent verify: cannot reach API at {api_base}. "
                f"Is WebAgentFlow running? ({exc})",
                file=sys.stderr,
            )
            return 2
        except httpx.HTTPError as exc:
            print(f"wagent verify: HTTP error — {exc}", file=sys.stderr)
            return 2

        if response.status_code >= 400:
            print(
                f"wagent verify: API returned {response.status_code} — "
                f"{response.text[:300]}",
                file=sys.stderr,
            )
            return 2

        try:
            envelope = response.json()
        except json.JSONDecodeError as exc:
            print(f"wagent verify: malformed response — {exc}", file=sys.stderr)
            return 2

        if envelope.get("code") != 0:
            print(
                f"wagent verify: API business error code={envelope.get('code')} "
                f"msg={envelope.get('msg')!r}",
                file=sys.stderr,
            )
            return 2

        result = envelope.get("data") or {}
        trimmed = _trim_result(result)
        output = result if args.full else trimmed

        if args.pretty:
            print(json.dumps(output, ensure_ascii=False, indent=2))
        else:
            print(json.dumps(output, ensure_ascii=False))

        print(_banner(trimmed), file=sys.stderr)

        return _exit_code_for(
            result.get("verdict"),
            scenario_matched=trimmed.get("scenario_matched"),
            pass_gate_status=(trimmed.get("pass_gate") or {}).get("status"),
        )
