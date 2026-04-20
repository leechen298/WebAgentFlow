"""Tests for ``wagent skill {install,uninstall}``.

The subcommand generates skill files at Claude Code's user-global
skill directory. Tests point it at a tmp dir and verify file contents,
the absolute-path embedding in run.sh, executable mode, and
uninstall's refusal to clobber unknown files.
"""

from __future__ import annotations

import os
import stat
from pathlib import Path

from wagent import main as wagent_main
from wagent import skill


def _run(argv: list[str]) -> int:
    return wagent_main.main(["skill", *argv])


# ───────────────────────────────────────────────────────────────────
# Template rendering
# ───────────────────────────────────────────────────────────────────


def test_run_sh_embeds_absolute_path_to_wagent(tmp_path: Path) -> None:
    wagent_bin = tmp_path / ".venv" / "bin" / "wagent"
    rendered = skill._render_run_sh(wagent_bin, tmp_path)
    assert str(wagent_bin) in rendered
    # Must NOT rely on `which wagent` — that resolves against the
    # shell's PATH at invocation time, which is not guaranteed to
    # include the repo's venv in Claude Code's Bash environment.
    assert "which wagent" not in rendered
    # Forwards all positional args via "$@" after 'verify'.
    assert "verify" in rendered
    assert '"$@"' in rendered


def test_run_sh_quotes_paths_with_spaces(tmp_path: Path) -> None:
    path_with_space = tmp_path / "My Projects" / "WebAgentFlow"
    rendered = skill._render_run_sh(
        path_with_space / ".venv/bin/wagent",
        path_with_space,
    )
    # Sanity: the repo path is retrievable literally.
    assert "My Projects" in rendered
    # Space-containing path must be inside a shell-quoted string so
    # it's treated as a single argument.
    assert "'" in rendered


def test_shell_quote_simple_path() -> None:
    assert skill._shell_quote("/usr/bin/wagent") == "/usr/bin/wagent"


def test_shell_quote_path_with_space() -> None:
    out = skill._shell_quote("/Users/li chen/repo")
    assert out.startswith("'") and out.endswith("'")
    assert "/Users/li chen/repo" in out


def test_shell_quote_path_with_single_quote() -> None:
    out = skill._shell_quote("can't/touch/this")
    # Single quotes inside a single-quoted string must be escaped via
    # the close-then-reopen dance.
    assert "'\\''" in out


def test_skill_md_mentions_repo_and_api_base(tmp_path: Path) -> None:
    rendered = skill._render_skill_md(
        tmp_path / ".claude" / "skills" / skill.SKILL_NAME / "run.sh",
        tmp_path / "repo",
        "http://api.local:8001",
    )
    assert str(tmp_path / "repo") in rendered
    assert "http://api.local:8001" in rendered
    # Refresh instruction references the new CLI, not the retired
    # pnpm script.
    assert "wagent skill install" in rendered


def test_skill_md_has_reporting_contract(tmp_path: Path) -> None:
    text = skill._render_skill_md(
        tmp_path / "run.sh",
        tmp_path / "repo",
        "http://localhost:8001",
    )
    assert "Reporting contract" in text
    assert "supervisor.verdict" in text
    assert "scorecard" in text
    # Report by run_id — the CLI stays backend-only and must not
    # fabricate a frontend URL.
    assert "run_id" in text
    assert "history_url" not in text
    # Must forbid fake-pass / fake-fail summaries.
    assert "MUST NOT" in text


def test_skill_md_frontmatter_has_name_and_description(tmp_path: Path) -> None:
    text = skill._render_skill_md(
        tmp_path / "run.sh", tmp_path / "repo", "http://a",
    )
    lines = text.splitlines()
    assert lines[0] == "---"
    assert any(line.startswith("name:") for line in lines[:10])
    assert any(line.startswith("description:") for line in lines[:10])


# ───────────────────────────────────────────────────────────────────
# Install / uninstall round-trip
# ───────────────────────────────────────────────────────────────────


def test_install_writes_files_with_executable_shim(
    tmp_path: Path, monkeypatch,
) -> None:
    fake_repo = tmp_path / "repo"
    fake_repo.mkdir()
    (fake_repo / ".venv" / "bin").mkdir(parents=True)
    wagent_bin = fake_repo / ".venv" / "bin" / "wagent"
    wagent_bin.touch()

    monkeypatch.setattr(skill, "_repo_root", lambda: fake_repo)

    dest = tmp_path / "claude-skills"
    rc = _run(["install", "--dest", str(dest), "--api-base", "http://t:8001"])
    assert rc == 0

    skill_dir = dest / skill.SKILL_NAME
    run_sh = skill_dir / "run.sh"
    skill_md = skill_dir / "SKILL.md"
    assert run_sh.exists()
    assert skill_md.exists()

    # run.sh must be executable so Claude Code's Bash tool can exec it.
    mode = run_sh.stat().st_mode
    assert mode & stat.S_IXUSR, "run.sh not marked executable"

    # Absolute path to wagent binary baked in.
    text = run_sh.read_text()
    assert str(wagent_bin) in text


def test_install_is_idempotent(tmp_path: Path, monkeypatch) -> None:
    fake_repo = tmp_path / "repo"
    fake_repo.mkdir()
    monkeypatch.setattr(skill, "_repo_root", lambda: fake_repo)

    dest = tmp_path / "claude-skills"
    assert _run(["install", "--dest", str(dest)]) == 0
    skill_md = dest / skill.SKILL_NAME / "SKILL.md"
    content_first = skill_md.read_text()
    assert _run(["install", "--dest", str(dest)]) == 0
    content_second = skill_md.read_text()
    assert content_first == content_second


def test_uninstall_removes_skill_files(tmp_path: Path, monkeypatch) -> None:
    fake_repo = tmp_path / "repo"
    fake_repo.mkdir()
    monkeypatch.setattr(skill, "_repo_root", lambda: fake_repo)

    dest = tmp_path / "claude-skills"
    _run(["install", "--dest", str(dest)])
    assert (dest / skill.SKILL_NAME).exists()

    rc = _run(["uninstall", "--dest", str(dest)])
    assert rc == 0
    assert not (dest / skill.SKILL_NAME).exists()


def test_uninstall_refuses_to_clobber_unknown_files(
    tmp_path: Path, monkeypatch,
) -> None:
    fake_repo = tmp_path / "repo"
    fake_repo.mkdir()
    monkeypatch.setattr(skill, "_repo_root", lambda: fake_repo)

    dest = tmp_path / "claude-skills"
    _run(["install", "--dest", str(dest)])

    # Operator left a note in the skill dir — installer should refuse
    # to delete it so custom state isn't silently lost.
    (dest / skill.SKILL_NAME / "operator-notes.md").write_text("keep me")

    rc = _run(["uninstall", "--dest", str(dest)])
    assert rc == 2
    assert (dest / skill.SKILL_NAME).exists()
    assert (dest / skill.SKILL_NAME / "operator-notes.md").exists()


def test_uninstall_on_missing_skill_is_noop(tmp_path: Path, monkeypatch) -> None:
    fake_repo = tmp_path / "repo"
    fake_repo.mkdir()
    monkeypatch.setattr(skill, "_repo_root", lambda: fake_repo)

    rc = _run(["uninstall", "--dest", str(tmp_path / "claude-skills")])
    # Not an error — nothing to do, exit 0.
    assert rc == 0


# ───────────────────────────────────────────────────────────────────
# Binary resolver
# ───────────────────────────────────────────────────────────────────


def test_resolve_wagent_prefers_env_override(
    tmp_path: Path, monkeypatch,
) -> None:
    monkeypatch.setenv("WBAF_WAGENT", "/custom/wagent")
    assert skill._resolve_wagent_binary(tmp_path) == Path("/custom/wagent")


def test_resolve_wagent_uses_venv_when_present(
    tmp_path: Path, monkeypatch,
) -> None:
    monkeypatch.delenv("WBAF_WAGENT", raising=False)
    venv = tmp_path / ".venv" / "bin" / "wagent"
    venv.parent.mkdir(parents=True)
    venv.touch()
    assert skill._resolve_wagent_binary(tmp_path) == venv


def test_resolve_wagent_falls_back_to_which(
    tmp_path: Path, monkeypatch,
) -> None:
    monkeypatch.delenv("WBAF_WAGENT", raising=False)
    # No venv exists under tmp_path; shutil.which is consulted.
    fake_path = tmp_path / "fake-wagent-on-path"
    fake_path.touch()
    monkeypatch.setattr(
        skill.shutil, "which",
        lambda name: str(fake_path) if name == "wagent" else None,
    )
    assert skill._resolve_wagent_binary(tmp_path) == fake_path


def test_repo_root_respects_env_override(
    tmp_path: Path, monkeypatch,
) -> None:
    target = tmp_path / "custom-repo"
    target.mkdir()
    monkeypatch.setenv("WBAF_REPO", str(target))
    assert skill._repo_root() == target


# Clean up env vars the resolver tests may leak (pytest's monkeypatch
# handles this, but belt-and-suspenders so future refactors don't get
# bitten by test ordering).
def test_no_stale_env_override(monkeypatch) -> None:
    monkeypatch.delenv("WBAF_WAGENT", raising=False)
    monkeypatch.delenv("WBAF_REPO", raising=False)
    # Just confirms the env vars are cleanable; value not asserted.
    assert os.environ.get("WBAF_WAGENT") is None
    assert os.environ.get("WBAF_REPO") is None
