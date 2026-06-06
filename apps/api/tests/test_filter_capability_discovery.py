from __future__ import annotations

from app.schemas.page_analysis import DiscoveredElement, PageAnalysis
from app.services.learning.capability_discovery import (
    build_filter_inventory,
    generate_filter_scenarios,
)
from app.services.learning.capability_hints import build_capability_hints


def _fillable(index: int) -> DiscoveredElement:
    return DiscoveredElement(
        category="fillable",
        tag="input",
        element_type="text",
        id=f"filter-{index}",
        name=f"filter_{index}",
        placeholder=f"Filter {index}",
        selector=f"#filter-{index}",
        label_text=f"Filter {index}",
        semantic_role="text",
        rect={"x": 10, "y": 20 + index * 40, "w": 220, "h": 32},
        reason="test filter input",
    )


def test_filter_inventory_generates_single_pairwise_and_smoke_scenarios() -> None:
    analysis = PageAnalysis(
        url="http://example.test/admin/users",
        title="Users",
        fillable=[_fillable(index) for index in range(9)],
        submit=[
            DiscoveredElement(
                category="submit",
                tag="button",
                element_type="submit",
                text="Search",
                selector="#search",
                rect={"x": 10, "y": 420, "w": 100, "h": 32},
                reason="test submit",
            )
        ],
        total_discovered=10,
        total_visible=10,
    )

    inventory = build_filter_inventory(analysis)
    scenarios = generate_filter_scenarios(
        inventory,
        discovery_batch_id="batch-users",
    )

    assert [cap.human_label for cap in inventory.supported_capabilities][:2] == [
        "Filter 0",
        "Filter 1",
    ]
    assert len(inventory.supported_capabilities) == 9
    assert len([s for s in scenarios if s.scenario_kind == "single_filter"]) == 9
    assert len([s for s in scenarios if s.scenario_kind == "pairwise_filter"]) == 36
    assert len([s for s in scenarios if s.scenario_kind == "all_supported_filters_smoke"]) == 1
    assert len(scenarios) == 46
    assert scenarios[0].scenario_id == scenarios[0].scenario_id
    assert all(s.discovery_batch_id == "batch-users" for s in scenarios)
    assert all(s.input_bindings for s in scenarios)


def test_filter_inventory_includes_date_month_select_and_toggle_candidates() -> None:
    analysis = PageAnalysis(
        url="http://example.test/admin/users",
        title="Users",
        fillable=[
            DiscoveredElement(
                category="fillable",
                tag="input",
                element_type="date",
                id="created-date",
                name="created_date",
                selector="#created-date",
                label_text="Created date",
                rect={"x": 10, "y": 20, "w": 180, "h": 32},
                reason="date filter",
            ),
            DiscoveredElement(
                category="fillable",
                tag="input",
                element_type="month",
                id="billing-month",
                name="billing_month",
                selector="#billing-month",
                label_text="Billing month",
                rect={"x": 10, "y": 60, "w": 180, "h": 32},
                reason="month filter",
            ),
        ],
        select=[
            DiscoveredElement(
                category="select",
                tag="select",
                id="status",
                name="status",
                selector="#status",
                label_text="Status",
                element_value="active",
                rect={"x": 10, "y": 100, "w": 180, "h": 32},
                reason="select filter",
            )
        ],
        toggle=[
            DiscoveredElement(
                category="toggle",
                tag="input",
                element_type="radio",
                name="role",
                selector="#role-admin",
                label_text="Role",
                element_value="admin",
                rect={"x": 10, "y": 140, "w": 20, "h": 20},
                reason="radio filter",
            )
        ],
        submit=[
            DiscoveredElement(
                category="submit",
                tag="button",
                element_type="submit",
                text="Search",
                selector="#search",
                rect={"x": 10, "y": 180, "w": 100, "h": 32},
                reason="test submit",
            )
        ],
        total_discovered=5,
        total_visible=5,
    )

    inventory = build_filter_inventory(analysis)
    scenarios = generate_filter_scenarios(inventory, discovery_batch_id="batch-mixed")

    supported_types = {cap.control_type for cap in inventory.supported_capabilities}
    adapters = {cap.control_type: cap.adapter_type for cap in inventory.supported_capabilities}
    assert supported_types == {"date_picker", "month_picker", "select", "toggle"}
    assert adapters["select"] == "select"
    assert len(inventory.unsupported_capabilities) == 0
    assert len([s for s in scenarios if s.scenario_kind == "single_filter"]) == 4
    assert len([s for s in scenarios if s.scenario_kind == "pairwise_filter"]) == 6
    assert len([s for s in scenarios if s.scenario_kind == "all_supported_filters_smoke"]) == 1


def test_filter_inventory_counts_validation_users_filter_controls() -> None:
    analysis = PageAnalysis(
        url="http://example.test/users",
        title="Users",
        fillable=[
            DiscoveredElement(
                category="fillable",
                tag="input",
                element_type="search",
                role="combobox",
                id="rc_select_0",
                selector="#rc_select_0",
                rect={"x": 10, "y": 10, "w": 120, "h": 32},
                readonly=True,
                reason="language switcher outside search form",
            ),
            DiscoveredElement(
                category="fillable",
                tag="input",
                element_type="text",
                id="search-name",
                selector="#search-name",
                label_text="姓名",
                semantic_role="name",
                rect={"x": 10, "y": 100, "w": 200, "h": 32},
                reason="name filter",
            ),
            DiscoveredElement(
                category="fillable",
                tag="input",
                element_type="text",
                id="search-email",
                selector="#search-email",
                label_text="邮箱",
                semantic_role="email",
                rect={"x": 220, "y": 100, "w": 200, "h": 32},
                reason="email filter",
            ),
            DiscoveredElement(
                category="fillable",
                tag="input",
                element_type="search",
                role="combobox",
                id="search-role",
                selector="#search-role",
                label_text="角色",
                semantic_role="role",
                readonly=True,
                rect={"x": 430, "y": 100, "w": 200, "h": 32},
                reason="role combobox filter",
            ),
            DiscoveredElement(
                category="fillable",
                tag="input",
                id="search-registered-from",
                selector="#search-registered-from",
                label_text="注册开始",
                placeholder="请选择日期",
                readonly=True,
                rect={"x": 10, "y": 160, "w": 200, "h": 32},
                reason="date picker filter",
            ),
            DiscoveredElement(
                category="fillable",
                tag="input",
                id="search-registered-to",
                selector="#search-registered-to",
                label_text="注册结束",
                placeholder="请选择日期",
                readonly=True,
                rect={"x": 220, "y": 160, "w": 200, "h": 32},
                reason="date picker filter",
            ),
            DiscoveredElement(
                category="fillable",
                tag="input",
                element_type="search",
                role="combobox",
                id="search-region",
                selector="#search-region",
                label_text="地区",
                readonly=False,
                rect={"x": 430, "y": 160, "w": 200, "h": 32},
                reason="region combobox filter",
            ),
            DiscoveredElement(
                category="fillable",
                tag="input",
                id="search-month",
                selector="#search-month",
                label_text="月份",
                placeholder="请选择月份",
                readonly=True,
                rect={"x": 10, "y": 220, "w": 200, "h": 32},
                reason="month picker filter",
            ),
            DiscoveredElement(
                category="fillable",
                tag="input",
                element_type="search",
                role="combobox",
                id="rc_select_3",
                selector="#rc_select_3",
                label_text="部门",
                readonly=True,
                rect={"x": 220, "y": 220, "w": 40, "h": 32},
                reason="department combobox filter",
            ),
        ],
        toggle=[
            DiscoveredElement(
                category="toggle",
                tag="input",
                element_type="radio",
                selector='input[type="radio"][value="active"]',
                label_text="状态",
                semantic_role="status",
                element_value="active",
                rect={"x": 430, "y": 220, "w": 20, "h": 20},
                reason="status radio filter",
            )
        ],
        submit=[
            DiscoveredElement(
                category="submit",
                tag="button",
                element_type="submit",
                text="搜索",
                selector="#btn-search",
                rect={"x": 10, "y": 300, "w": 80, "h": 32},
                reason="search button",
            )
        ],
    )

    inventory = build_filter_inventory(analysis)
    scenarios = generate_filter_scenarios(inventory, discovery_batch_id="batch-users-shape")

    labels = {cap.human_label for cap in inventory.supported_capabilities}
    assert labels == {
        "姓名",
        "邮箱",
        "状态: active",
        "注册开始",
        "注册结束",
        "月份",
    }
    assert len(inventory.supported_capabilities) == 6
    assert len(inventory.unsupported_capabilities) == 3
    assert {cap.adapter_type for cap in inventory.unsupported_capabilities} == {"unsupported"}
    assert len(scenarios) == 22


def test_filter_inventory_uses_redacted_hints_with_executable_bindings() -> None:
    analysis = PageAnalysis(
        url="http://example.test/admin/customers",
        title="Customers",
        fillable=[_fillable(0)],
        total_discovered=1,
        total_visible=1,
    )
    analysis.capability_hints = build_capability_hints(analysis)

    inventory = build_filter_inventory(analysis)
    scenarios = generate_filter_scenarios(inventory, discovery_batch_id="batch-hints")

    public_hint_dump = analysis.capability_hints.model_dump_json()
    assert "#filter-0" not in public_hint_dump
    assert "Filter 0" not in public_hint_dump
    assert len(inventory.supported_capabilities) == 1
    assert inventory.supported_capabilities[0].capability_id == (
        analysis.capability_hints.controls[0].hint_id
    )
    assert scenarios[0].input_bindings[0]["selector"] == "#filter-0"


def test_filter_inventory_skips_hint_when_private_binding_is_missing() -> None:
    analysis = PageAnalysis(
        url="http://example.test/admin/customers",
        title="Customers",
        fillable=[_fillable(0)],
        total_discovered=1,
        total_visible=1,
    )
    hints = build_capability_hints(analysis)
    hints.controls[0].control_ref = "control_missing"
    analysis.capability_hints = hints

    inventory = build_filter_inventory(analysis)
    scenarios = generate_filter_scenarios(inventory, discovery_batch_id="batch-missing")

    assert inventory.supported_capabilities == []
    assert len(inventory.unsupported_capabilities) == 1
    assert inventory.unsupported_capabilities[0].support_reason == (
        "capability hint has no current executable binding"
    )
    assert scenarios == []


def test_hint_mode_dependency_pairs_require_explicit_dependency_hints() -> None:
    analysis = PageAnalysis(
        url="http://example.test/admin/customers",
        title="Customers",
        fillable=[_fillable(0), _fillable(1)],
        total_discovered=2,
        total_visible=2,
    )
    analysis.capability_hints = build_capability_hints(analysis)

    inventory = build_filter_inventory(analysis)
    scenarios = generate_filter_scenarios(inventory, discovery_batch_id="batch-independent")

    assert len(inventory.supported_capabilities) == 2
    assert len([s for s in scenarios if s.scenario_kind == "single_filter"]) == 2
    assert len([s for s in scenarios if s.scenario_kind == "pairwise_filter"]) == 0


def test_hint_mode_emits_dependency_pair_when_range_hint_exists() -> None:
    analysis = PageAnalysis(
        url="http://example.test/admin/orders",
        title="Orders",
        fillable=[
            DiscoveredElement(
                category="fillable",
                tag="input",
                element_type="date",
                id="created-from",
                name="created_from",
                label_text="Created from",
                selector="#created-from",
                rect={"x": 10, "y": 20, "w": 160, "h": 32},
                reason="from date",
            ),
            DiscoveredElement(
                category="fillable",
                tag="input",
                element_type="date",
                id="created-to",
                name="created_to",
                label_text="Created to",
                selector="#created-to",
                rect={"x": 180, "y": 20, "w": 160, "h": 32},
                reason="to date",
            ),
        ],
        total_discovered=2,
        total_visible=2,
    )
    analysis.capability_hints = build_capability_hints(analysis)

    inventory = build_filter_inventory(analysis)
    scenarios = generate_filter_scenarios(inventory, discovery_batch_id="batch-range")

    pairwise = [s for s in scenarios if s.scenario_kind == "pairwise_filter"]
    assert len(pairwise) == 1
    assert {binding["selector"] for binding in pairwise[0].input_bindings} == {
        "#created-from",
        "#created-to",
    }
