"""Regression checks for target-agnostic product runtime cleanup."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def _load_forbidden_scan_module():
    repo_root = Path(__file__).resolve().parents[3]
    scan_path = (
        repo_root
        / ".agents"
        / "skills"
        / "webagentflow-eval-integrity"
        / "scripts"
        / "forbidden_target_scan.py"
    )
    assert scan_path.exists(), "forbidden target scanner is missing"
    spec = importlib.util.spec_from_file_location("forbidden_target_scan", scan_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _s(*parts: str) -> str:
    return "".join(parts)


def test_product_runtime_contains_no_product_test_site_target_constants() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    scanner = _load_forbidden_scan_module()

    manifest = {
        "target_name": "target-agnostic-runtime",
        "forbidden_tokens": [
            _s("http://127.0.0.1:517", "6", "/it", "ems"),
            _s("http://localhost:517", "6", "/it", "ems"),
            _s("127.0.0.1:517", "6"),
            _s("localhost:517", "6"),
            _s("/it", "ems"),
            _s("it", "ems-page"),
            _s("it", "em-list"),
            _s("it", "em-name-input"),
            _s("it", "em-create-button"),
            _s("operation", "-status"),
            _s("[data-testid='", "it", "em-list']"),
            _s("[data-testid=\"", "it", "em-list\"]"),
            _s("测试", "项目", "A"),
            _s("测试", "项目", "B"),
            _s("默认", "项目", "A"),
            _s("默认", "项目", "B"),
            _s("新增", "项目"),
            _s("添加", "项目"),
            _s("录入", "项目"),
            _s("项目", "名称"),
            _s("请输入", "项目", "名称"),
            _s("新增", "成功"),
            _s("s", "ku"),
            _s("it", "em_name"),
            _s("it", "em_category"),
            _s("stock", "_quantity"),
            _s("WebAgentFlow-", "Validation", "-", "Site"),
            _s("Validation", "-", "Site"),
            _s("validation", "-", "site"),
            _s("http://127.0.0.1:517", "7", "/inven", "tory"),
            _s("http://localhost:517", "7", "/inven", "tory"),
            _s("127.0.0.1:517", "7"),
            _s("localhost:517", "7"),
            _s("/inven", "tory"),
            _s("inven", "tory item"),
            _s("NB", "-ALP"),
            _s("MUG", "-SKY"),
            _s("http://127.0.0.1:517", "5"),
            _s("http://localhost:517", "5"),
            _s("VITE_", "VALIDATION", "_SITE_ORIGIN"),
            _s("E2E_", "VALIDATION", "_BASE_URL"),
            _s("validation", "Url"),
            _s("validation", "BaseUrl"),
            _s("/us", "ers"),
            _s("/lo", "gin"),
            _s("search", "-name"),
            _s("btn", "-search"),
        ],
        "forbidden_paths": [
            "AGENTS.md",
            "CLAUDE.md",
            "CLAUDE.zh.md",
            "README.md",
            "package.json",
            "apps/api/app/services",
            "apps/api/app/routers",
            "apps/api/app/schemas",
            "apps/api/app/prompts",
            "apps/cli/wagent",
            "apps/console/src",
            "apps/e2e",
            "docs/user-guide",
            "docs/testing/e2e",
            "docs/testing/wagent-runtime-eval.md",
        ],
        "allowed_paths": ["apps/api/tests", "apps/e2e/.tmp"],
    }

    result = scanner.scan(repo_root, manifest)

    assert result["matches"] == []
    assert result["status"] == "pass"


def test_default_wagent_eval_scripts_are_target_agnostic() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    package = json.loads((repo_root / "package.json").read_text(encoding="utf-8"))
    scripts = package["scripts"]

    assert scripts["test:target-agnostic-runtime"] == (
        "cd apps/api && PYTHONPATH=. ../../.venv/bin/pytest "
        "tests/test_target_agnostic_runtime_cleanup.py -q"
    )
    assert scripts["eval:wagent"] == "pnpm run test:target-agnostic-runtime"
    for name, command in scripts.items():
        if not name.startswith("eval:wagent"):
            continue
        assert _s("517", "6") not in command
        assert _s("517", "7") not in command
        assert _s("product", "-", "test", "-", "site") not in command
        assert _s("Validation", "-", "Site") not in command
        assert _s("/it", "ems") not in command
        assert _s("/inven", "tory") not in command
