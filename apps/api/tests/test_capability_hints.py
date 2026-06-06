from __future__ import annotations

from app.schemas.capability_hints import CapabilityHintSet, SampleValueSourceHint
from app.schemas.page_analysis import DiscoveredElement, PageAnalysis
from app.services.learning.capability_hints import (
    assert_redacted_refs,
    build_capability_hints,
    resolve_control_hint,
)


def _input(
    *,
    selector: str = "#customer-name",
    label: str = "Customer name",
    element_id: str = "customer-name",
) -> DiscoveredElement:
    return DiscoveredElement(
        category="fillable",
        tag="input",
        element_type="text",
        id=element_id,
        name=element_id,
        label_text=label,
        selector=selector,
        rect={"x": 10, "y": 20, "w": 200, "h": 32},
        reason="test input",
    )


def test_capability_hint_set_defaults_are_safe() -> None:
    hints = CapabilityHintSet()

    assert hints.version == "capability_hints.v1"
    assert hints.page_purpose == "unknown"
    assert hints.controls == []
    assert hints.sample_value_sources == []


def test_capability_hints_redact_public_refs_but_resolve_execution_binding() -> None:
    analysis = PageAnalysis(
        url="http://example.test/admin/customers?tab=list",
        title="Customers",
        fillable=[_input()],
        submit=[
            DiscoveredElement(
                category="submit",
                tag="button",
                element_type="submit",
                text="Search customers",
                selector="#customer-search",
                rect={"x": 10, "y": 80, "w": 120, "h": 32},
                reason="test submit",
            )
        ],
        total_discovered=2,
        total_visible=2,
    )

    hints = build_capability_hints(analysis)
    dumped = hints.model_dump_json()
    refs = [
        *(region.region_id for region in hints.regions),
        *(control.control_ref for control in hints.controls),
        *(target.target_id for target in hints.terminal_targets),
        *(source.source_id for source in hints.sample_value_sources),
    ]

    assert hints.page_purpose == "list_management"
    assert assert_redacted_refs(refs)
    assert "#customer-name" not in dumped
    assert "#customer-search" not in dumped
    assert "Customer name" not in dumped
    assert "Search customers" not in dumped
    assert hints.controls[0].capability_kind == "control_input"
    assert hints.controls[0].support_status == "supported"

    resolved = resolve_control_hint(analysis, hints.controls[0].control_ref)
    assert resolved is not None
    assert resolved.selector == "#customer-name"


def test_existing_option_sample_values_are_redacted_and_not_materialized() -> None:
    analysis = PageAnalysis(
        url="http://example.test/admin/customers",
        title="Customers",
        select=[
            DiscoveredElement(
                category="select",
                tag="select",
                id="status",
                name="status",
                label_text="Account status",
                selector="#status",
                element_value="vip-only",
                rect={"x": 10, "y": 20, "w": 160, "h": 32},
                reason="test select",
            )
        ],
        total_discovered=1,
        total_visible=1,
    )

    hints = build_capability_hints(analysis)
    source = hints.sample_value_sources[0]

    assert source.source_kind == "existing_option_value_redacted"
    assert source.materializable_from_serialized_hint is False
    assert source.redacted is True
    assert "vip-only" not in hints.model_dump_json()


def test_combobox_hint_is_unsupported_until_full_adapter_chain_exists() -> None:
    analysis = PageAnalysis(
        url="http://example.test/admin/customers",
        title="Customers",
        fillable=[
            DiscoveredElement(
                category="fillable",
                tag="input",
                element_type="search",
                role="combobox",
                id="customer-role",
                name="customer_role",
                label_text="Customer role",
                selector="#customer-role",
                rect={"x": 10, "y": 20, "w": 160, "h": 32},
                reason="combobox filter",
            )
        ],
        total_discovered=1,
        total_visible=1,
    )

    hints = build_capability_hints(analysis)

    assert hints.controls[0].adapter_type == "unsupported"
    assert hints.controls[0].support_status == "unsupported"
    assert "combobox adapter" in hints.controls[0].warnings[0]


def test_sample_value_source_kind_validation_rejects_unknown_kind() -> None:
    try:
        SampleValueSourceHint(
            source_id="sample_0000000000000000",
            source_kind="target_seed_value",  # type: ignore[arg-type]
            control_ref="control_0000000000000000",
        )
    except Exception as exc:
        assert "target_seed_value" in str(exc)
    else:  # pragma: no cover - defensive guard for schema regression.
        raise AssertionError("unknown sample source kind should be rejected")


def test_public_hint_schema_rejects_raw_selector_refs() -> None:
    try:
        CapabilityHintSet.model_validate(
            {
                "controls": [
                    {
                        "hint_id": "hint_0000000000000000",
                        "capability_kind": "control_input",
                        "region_ref": "region_0000000000000000",
                        "control_ref": "#customer-name",
                        "adapter_type": "fill",
                        "support_status": "supported",
                    }
                ]
            }
        )
    except Exception as exc:
        assert "stable redacted id" in str(exc)
    else:  # pragma: no cover - defensive guard for schema regression.
        raise AssertionError("raw selector refs should be rejected")


def test_range_pair_dependency_hints_use_redacted_source_refs() -> None:
    analysis = PageAnalysis(
        url="http://example.test/orders",
        title="Orders",
        fillable=[
            _input(selector="#created-from", label="Created from", element_id="created_from"),
            _input(selector="#created-to", label="Created to", element_id="created_to"),
        ],
        total_discovered=2,
        total_visible=2,
    )

    hints = build_capability_hints(analysis)

    assert len(hints.dependency_groups) == 1
    group = hints.dependency_groups[0]
    assert group.dependency_kind == "range_pair"
    assert assert_redacted_refs(group.source_refs)
    assert "#created-from" not in hints.model_dump_json()
    assert "#created-to" not in hints.model_dump_json()
