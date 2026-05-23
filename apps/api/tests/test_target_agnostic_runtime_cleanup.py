"""Regression checks for target-agnostic product runtime cleanup."""

from __future__ import annotations

import importlib.util
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


def test_product_runtime_contains_no_product_test_site_target_constants() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    scanner = _load_forbidden_scan_module()

    manifest = {
        "target_name": "product-test-site-items",
        "forbidden_tokens": [
            "http://127.0.0.1:5176/items",
            "http://localhost:5176/items",
            "127.0.0.1:5176",
            "localhost:5176",
            "/items",
            "items-page",
            "item-list",
            "item-name-input",
            "item-create-button",
            "operation-status",
            "[data-testid='item-list']",
            "[data-testid=\"item-list\"]",
            "测试项目A",
            "测试项目B",
            "默认项目A",
            "默认项目B",
            "新增项目",
            "添加项目",
            "录入项目",
            "项目名称",
            "请输入项目名称",
            "新增成功",
            "item_name",
        ],
        "forbidden_paths": [
            "apps/api/app/services",
            "apps/api/app/routers",
            "apps/api/app/schemas",
            "apps/api/app/prompts",
            "apps/cli/wagent",
            "apps/console/src",
        ],
        "allowed_paths": [
            "apps/product-test-site",
            "scripts/evals",
            "apps/api/tests",
            "docs",
            "artifacts",
        ],
    }

    result = scanner.scan(repo_root, manifest)

    assert result["matches"] == []
    assert result["status"] == "pass"
