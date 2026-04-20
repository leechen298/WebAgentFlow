"""Tests for scripts/install_skill.py.

The installer generates skill files at Claude Code's user-global skill
directory. Tests point it at a tmp dir and verify file contents, the
absolute-path embedding in run.sh, executable mode, and uninstall's
refusal to clobber unknown files.
"""

from __future__ import annotations

import os
import stat
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import install_skill as isk  # noqa: E402


# ───────────────────────────────────────────────────────────────────
# Template rendering
# ───────────────────────────────────────────────────────────────────


def test_run_sh_embeds_absolute_paths(tmp_path: Path) -> None:
    python = tmp_path / ".venv" / "bin" / "python"
    cli = tmp_path / "apps" / "cli" / "verify_scenario.py"
    rendered = isk._render_run_sh(python, cli, tmp_path)
    assert str(python) in rendered
    assert str(cli) in rendered
    # Must NOT rely on `which python` — that resolves to system
    # Python in Claude Code's bash environment where the venv isn't
    # sourced.
    assert "which python" not in rendered
    # Forwards all positional args via "$@".
    assert '"$@"' in rendered


def test_run_sh_quotes_paths_with_spaces(tmp_path: Path) -> None:
    path_with_space = tmp_path / "My Projects" / "WebAgentFlow"
    rendered = isk._render_run_sh(
        path_with_space / ".venv/bin/python",
        path_with_space / "apps/cli/verify_scenario.py",
        path_with_space,
    )
    # Space-containing paths must be shell-quoted so `set -e` + exec
    # don't mis-split them.
    assert "'" in rendered or '"' in rendered
    # Sanity: the repo path is retrievable literally.
    assert "My Projects" in rendered


def test_shell_quote_simple_path() -> None:
    assert isk._shell_quote("/usr/bin/python") == "/usr/bin/python"


def test_shell_quote_path_with_space() -> None:
    out = isk._shell_quote("/Users/li chen/repo")
    # The quoted form must start and end with a single quote so the
    # space is treated as part of a single argument by the shell.
    assert out.startswith("'") and out.endswith("'")
    # Value round-trips when shell evaluates the quoted form.
    assert "/Users/li chen/repo" in out


def test_shell_quote_path_with_single_quote() -> None:
    out = isk._shell_quote("can't/touch/this")
    # Single quotes inside a single-quoted string must be escaped via
    # the close-then-reopen dance.
    assert "'\\''" in out


def test_skill_md_mentions_repo_and_api_base(tmp_path: Path) -> None:
    rendered = isk._render_skill_md(
        tmp_path / ".claude" / "skills" / isk.SKILL_NAME / "run.sh",
        tmp_path / "repo",
        "http://api.local:8001",
    )
    assert str(tmp_path / "repo") in rendered
    assert "http://api.local:8001" in rendered
    assert "pnpm run skill:install" in rendered


def test_skill_md_has_reporting_contract(tmp_path: Path) -> None:
    # The contract section is the policy half of this skill — dropping
    # it silently would reintroduce the "AI fakes the verdict" risk
    # the whole design tries to prevent.
    text = isk._render_skill_md(
        tmp_path / "run.sh",
        tmp_path / "repo",
        "http://localhost:8001",
    )
    assert "Reporting contract" in text
    assert "supervisor.verdict" in text
    assert "scorecard" in text
    assert "history_url" in text
    # Must forbid fake-pass / fake-fail summaries.
    assert "MUST NOT" in text


def test_skill_md_frontmatter_has_name_and_description(tmp_path: Path) -> None:
    text = isk._render_skill_md(
        tmp_path / "run.sh", tmp_path / "repo", "http://a",
    )
    lines = text.splitlines()
    # YAML frontmatter fence at line 0.
    assert lines[0] == "---"
    # Name + description are mandatory for Claude Code skill discovery.
    assert any(line.startswith("name:") for line in lines[:10])
    assert any(line.startswith("description:") for line in lines[:10])


# ───────────────────────────────────────────────────────────────────
# Install / uninstall round-trip
# ───────────────────────────────────────────────────────────────────


def test_install_writes_files_with_executable_shim(
    tmp_path: Path, monkeypatch,
) -> None:
    # Point the installer at a tmp dest so we don't touch the real
    # ~/.claude. Monkeypatch the repo-root resolver so the rendered
    # paths are fake-but-consistent.
    fake_repo = tmp_path / "repo"
    fake_repo.mkdir()
    (fake_repo / ".venv" / "bin").mkdir(parents=True)
    py = fake_repo / ".venv" / "bin" / "python"
    py.touch()
    cli_dir = fake_repo / "apps" / "cli"
    cli_dir.mkdir(parents=True)
    (cli_dir / "verify_scenario.py").touch()

    monkeypatch.setattr(isk, "_repo_root", lambda: fake_repo)

    dest = tmp_path / "claude-skills"
    rc = isk.main(["install", "--dest", str(dest), "--api-base", "http://t:8001"])
    assert rc == 0

    skill_dir = dest / isk.SKILL_NAME
    run_sh = skill_dir / "run.sh"
    skill_md = skill_dir / "SKILL.md"
    assert run_sh.exists()
    assert skill_md.exists()

    # run.sh must be executable so Claude Code's Bash tool can exec it.
    mode = run_sh.stat().st_mode
    assert mode & stat.S_IXUSR, "run.sh not marked executable"

    # Absolute paths baked in — re-running skill from any cwd works.
    text = run_sh.read_text()
    assert str(py) in text
    assert str(fake_repo / "apps/cli/verify_scenario.py") in text


def test_install_is_idempotent(tmp_path: Path, monkeypatch) -> None:
    fake_repo = tmp_path / "repo"
    (fake_repo / "apps/cli").mkdir(parents=True)
    monkeypatch.setattr(isk, "_repo_root", lambda: fake_repo)

    dest = tmp_path / "claude-skills"
    assert isk.main(["install", "--dest", str(dest)]) == 0
    # Second run must not error, must not change any file content for
    # the same inputs.
    skill_md = dest / isk.SKILL_NAME / "SKILL.md"
    content_first = skill_md.read_text()
    assert isk.main(["install", "--dest", str(dest)]) == 0
    content_second = skill_md.read_text()
    assert content_first == content_second


def test_uninstall_removes_skill_files(tmp_path: Path, monkeypatch) -> None:
    fake_repo = tmp_path / "repo"
    (fake_repo / "apps/cli").mkdir(parents=True)
    monkeypatch.setattr(isk, "_repo_root", lambda: fake_repo)

    dest = tmp_path / "claude-skills"
    isk.main(["install", "--dest", str(dest)])
    assert (dest / isk.SKILL_NAME).exists()

    rc = isk.main(["uninstall", "--dest", str(dest)])
    assert rc == 0
    assert not (dest / isk.SKILL_NAME).exists()


def test_uninstall_refuses_to_clobber_unknown_files(
    tmp_path: Path, monkeypatch,
) -> None:
    fake_repo = tmp_path / "repo"
    (fake_repo / "apps/cli").mkdir(parents=True)
    monkeypatch.setattr(isk, "_repo_root", lambda: fake_repo)

    dest = tmp_path / "claude-skills"
    isk.main(["install", "--dest", str(dest)])

    # Operator left a note in the skill dir — installer should refuse
    # to delete it so custom state isn't silently lost.
    (dest / isk.SKILL_NAME / "operator-notes.md").write_text("keep me")

    rc = isk.main(["uninstall", "--dest", str(dest)])
    assert rc == 2
    assert (dest / isk.SKILL_NAME).exists()
    assert (dest / isk.SKILL_NAME / "operator-notes.md").exists()


def test_uninstall_on_missing_skill_is_noop(tmp_path: Path, monkeypatch) -> None:
    fake_repo = tmp_path / "repo"
    monkeypatch.setattr(isk, "_repo_root", lambda: fake_repo)

    rc = isk.main(["uninstall", "--dest", str(tmp_path / "claude-skills")])
    # Not an error — nothing to do, exit 0.
    assert rc == 0


# ───────────────────────────────────────────────────────────────────
# Python resolver
# ───────────────────────────────────────────────────────────────────


def test_resolve_python_prefers_env_override(
    tmp_path: Path, monkeypatch,
) -> None:
    monkeypatch.setenv("WBAF_PYTHON", "/custom/python")
    assert isk._resolve_python(tmp_path) == Path("/custom/python")


def test_resolve_python_uses_venv_when_present(
    tmp_path: Path, monkeypatch,
) -> None:
    monkeypatch.delenv("WBAF_PYTHON", raising=False)
    venv = tmp_path / ".venv" / "bin" / "python"
    venv.parent.mkdir(parents=True)
    venv.touch()
    assert isk._resolve_python(tmp_path) == venv


def test_resolve_python_falls_back_to_sys_executable(
    tmp_path: Path, monkeypatch,
) -> None:
    monkeypatch.delenv("WBAF_PYTHON", raising=False)
    # No venv exists under tmp_path → falls back to sys.executable.
    resolved = isk._resolve_python(tmp_path)
    assert resolved == Path(os.sys.executable)
