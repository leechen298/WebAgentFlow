"""
Recording Normalizer — Task Pack 6.

Converts raw recording events (device-level) into a cleaned, segmented,
semi-structured representation suitable for skill draft compilation.

Rules are intentionally explicit and rule-based (no AI/ML). Each rule is
documented so it can be inspected and tuned without mystery.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class NormalizedStep:
    """A single normalized step in a recording segment."""

    action_type: str
    """
    One of:
      navigate-page, click-button, fill-field, select-field,
      edit-richtext, open-dialog, confirm-dialog, cancel-dialog, unknown-click
    """

    timestamp: int
    url: str

    # Optional enriched fields
    page_title: str | None = None
    field_label: str | None = None
    field_prop: str | None = None
    field_required: bool | None = None
    value: str | None = None
    button_text: str | None = None
    in_iframe: bool = False
    frame_url: str | None = None
    is_richtext: bool = False
    html_content: str | None = None

    # Back-references into the original event list (0-based indices)
    raw_event_indices: list[int] = field(default_factory=list)


@dataclass
class NormalizedSegment:
    """A logical phase of the recording."""

    index: int
    type: str
    """navigation | form-fill | dialog-interaction | richtext-edit | misc"""

    title: str
    steps: list[NormalizedStep] = field(default_factory=list)


@dataclass
class NormalizationSummary:
    event_count_raw: int
    event_count_normalized: int
    page_count: int
    segment_count: int
    contains_iframe: bool
    contains_richtext: bool


@dataclass
class NormalizedRecording:
    recording_id: str
    summary: NormalizationSummary
    segments: list[NormalizedSegment]
    key_actions: list[NormalizedStep]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_SUBMIT_KEYWORDS = frozenset([
    "submit", "confirm", "save", "ok", "yes", "apply", "done",
    "提交", "确认", "保存", "确定", "完成", "好的",
])

_CANCEL_KEYWORDS = frozenset([
    "cancel", "close", "no", "dismiss", "abort",
    "取消", "关闭", "放弃",
])

_DIALOG_OPEN_KEYWORDS = frozenset([
    "add", "new", "create", "edit", "config", "manage", "upload", "import",
    "添加", "新增", "新建", "创建", "编辑", "配置", "管理", "上传", "导入", "设置",
])


def _get_str(d: dict[str, Any], *keys: str) -> str:
    """Safely get a nested/dotted string value from a dict."""
    for k in keys:
        v = d.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return ""


def _target_key(ev: dict[str, Any]) -> str:
    """Stable identity key for an event target — used for deduplication."""
    t = ev.get("target") or {}
    return "|".join([
        str(t.get("selector") or ""),
        str(t.get("name") or ""),
        str(t.get("id") or ""),
        str(ev.get("url") or ""),
        str((ev.get("frameInfo") or {}).get("frameUrl") or ""),
    ])


def _button_text(ev: dict[str, Any]) -> str:
    t = ev.get("target") or {}
    return (
        t.get("text") or t.get("label") or t.get("nearbyText") or ""
    ).strip()


def _classify_click(ev: dict[str, Any]) -> str:
    """Heuristically classify what kind of click this is."""
    text = _button_text(ev).lower()
    if any(kw in text for kw in _SUBMIT_KEYWORDS):
        return "confirm-dialog"
    if any(kw in text for kw in _CANCEL_KEYWORDS):
        return "cancel-dialog"
    if any(kw in text for kw in _DIALOG_OPEN_KEYWORDS):
        return "open-dialog"
    t = ev.get("target") or {}
    tag = (t.get("tag") or "").lower()
    if tag in ("button", "a") or t.get("role") in ("button", "link", "menuitem"):
        return "click-button"
    return "unknown-click"


def _field_label(ev: dict[str, Any]) -> str | None:
    fc = ev.get("fieldContext") or {}
    label = fc.get("fieldLabel") or ""
    if label:
        return label
    t = ev.get("target") or {}
    return t.get("label") or t.get("placeholder") or None


def _is_select_event(ev: dict[str, Any]) -> bool:
    t = ev.get("target") or {}
    tag = (t.get("tag") or "").lower()
    return tag in ("select",) or t.get("role") in ("combobox", "listbox", "option")


# ---------------------------------------------------------------------------
# Step 1: Merge & denoise raw events
# ---------------------------------------------------------------------------

def _merge_events(events: list[dict[str, Any]]) -> list[tuple[int, dict[str, Any]]]:
    """
    Return (original_index, event) pairs with noise removed.

    Rules applied in order:
    R1. Consecutive `input` events on the same target → keep only the last.
    R2. An `input` immediately followed by a `change` on the same target
        within 1 000 ms → drop the `change` (input already has the final value).
    R3. Consecutive `richtext-input` events with identical htmlContent → drop duplicates.
    R4. Consecutive identical `click` events (same target, within 300 ms) → keep first.
    """
    if not events:
        return []

    indexed = list(enumerate(events))
    result: list[tuple[int, dict[str, Any]]] = []

    i = 0
    while i < len(indexed):
        orig_i, ev = indexed[i]
        ev_type = ev.get("type", "")

        # R1: collapse consecutive input on same target
        if ev_type == "input":
            key = _target_key(ev)
            last_i, last_ev = orig_i, ev
            j = i + 1
            while j < len(indexed):
                orig_j, nxt = indexed[j]
                if nxt.get("type") == "input" and _target_key(nxt) == key:
                    last_i, last_ev = orig_j, nxt
                    j += 1
                else:
                    break
            result.append((last_i, last_ev))
            i = j
            continue

        # R2: input followed by change on same target within 1 s → drop change
        if ev_type == "change" and result:
            prev_i, prev_ev = result[-1]
            if (
                prev_ev.get("type") == "input"
                and _target_key(prev_ev) == _target_key(ev)
                and abs(ev.get("timestamp", 0) - prev_ev.get("timestamp", 0)) <= 1000
            ):
                i += 1
                continue

        # R3: consecutive richtext-input with same content
        if ev_type == "richtext-input":
            key = _target_key(ev)
            html = ev.get("htmlContent") or ""
            last_i, last_ev = orig_i, ev
            j = i + 1
            while j < len(indexed):
                orig_j, nxt = indexed[j]
                if (
                    nxt.get("type") == "richtext-input"
                    and _target_key(nxt) == key
                    and (nxt.get("htmlContent") or "") == html
                ):
                    last_i, last_ev = orig_j, nxt
                    j += 1
                elif (
                    nxt.get("type") == "richtext-input"
                    and _target_key(nxt) == key
                ):
                    # Different content — keep accumulating
                    html = nxt.get("htmlContent") or ""
                    last_i, last_ev = orig_j, nxt
                    j += 1
                else:
                    break
            result.append((last_i, last_ev))
            i = j
            continue

        # R4: consecutive duplicate clicks within 300 ms
        if ev_type == "click" and result:
            prev_i, prev_ev = result[-1]
            if (
                prev_ev.get("type") == "click"
                and _target_key(prev_ev) == _target_key(ev)
                and abs(ev.get("timestamp", 0) - prev_ev.get("timestamp", 0)) <= 300
            ):
                i += 1
                continue

        result.append((orig_i, ev))
        i += 1

    return result


# ---------------------------------------------------------------------------
# Step 2: Convert merged events to NormalizedSteps
# ---------------------------------------------------------------------------

def _to_step(orig_idx: int, ev: dict[str, Any]) -> NormalizedStep:
    ev_type = ev.get("type", "")
    url = ev.get("url") or ""
    ts = int(ev.get("timestamp") or 0)
    fi = ev.get("frameInfo") or {}
    in_iframe = bool(fi.get("isIframe"))
    frame_url = fi.get("frameUrl") or None
    fc = ev.get("fieldContext") or {}

    if ev_type == "navigate":
        return NormalizedStep(
            action_type="navigate-page",
            timestamp=ts,
            url=url,
            page_title=ev.get("title") or None,
            in_iframe=in_iframe,
            frame_url=frame_url,
            raw_event_indices=[orig_idx],
        )

    if ev_type == "richtext-input":
        return NormalizedStep(
            action_type="edit-richtext",
            timestamp=ts,
            url=url,
            field_label=_field_label(ev),
            field_prop=fc.get("fieldProp") or None,
            value=ev.get("value") or None,
            in_iframe=in_iframe,
            frame_url=frame_url,
            is_richtext=True,
            html_content=ev.get("htmlContent") or None,
            raw_event_indices=[orig_idx],
        )

    if ev_type in ("input", "change"):
        action = "select-field" if _is_select_event(ev) else "fill-field"
        return NormalizedStep(
            action_type=action,
            timestamp=ts,
            url=url,
            field_label=_field_label(ev),
            field_prop=fc.get("fieldProp") or None,
            field_required=fc.get("fieldRequired"),
            value=ev.get("value") or fc.get("fieldValueText") or None,
            in_iframe=in_iframe,
            frame_url=frame_url,
            raw_event_indices=[orig_idx],
        )

    if ev_type == "click":
        action = _classify_click(ev)
        return NormalizedStep(
            action_type=action,
            timestamp=ts,
            url=url,
            button_text=_button_text(ev) or None,
            field_label=_field_label(ev),
            in_iframe=in_iframe,
            frame_url=frame_url,
            raw_event_indices=[orig_idx],
        )

    return NormalizedStep(
        action_type="unknown",
        timestamp=ts,
        url=url,
        in_iframe=in_iframe,
        frame_url=frame_url,
        raw_event_indices=[orig_idx],
    )


# ---------------------------------------------------------------------------
# Step 3: Segment steps into logical phases
# ---------------------------------------------------------------------------

def _segment_steps(steps: list[NormalizedStep]) -> list[NormalizedSegment]:
    """
    Group steps into segments.

    Segmentation triggers:
    S1. navigate-page → always starts a new `navigation` segment.
    S2. open-dialog → starts a `dialog-interaction` segment.
    S3. confirm-dialog / cancel-dialog → closes the dialog segment (next step
        may start a new segment).
    S4. edit-richtext → starts a `richtext-edit` segment if not already in one.
    S5. After confirm/cancel, the next step starts a new segment.
    S6. If no segment yet → start a `misc` segment.

    The logic is intentionally simple: rule-based, no heuristics about
    what "should" be a form vs. navigation.
    """
    if not steps:
        return []

    segments: list[NormalizedSegment] = []
    current_type: str = ""
    current_steps: list[NormalizedStep] = []
    in_dialog = False
    after_dialog_close = False

    def _flush(seg_type: str, title: str) -> None:
        nonlocal current_type, current_steps
        if current_steps:
            seg = NormalizedSegment(
                index=len(segments),
                type=seg_type,
                title=title,
                steps=list(current_steps),
            )
            segments.append(seg)
        current_steps = []
        current_type = seg_type

    def _segment_title(seg_type: str, step: NormalizedStep) -> str:
        if seg_type == "navigation":
            return f"Navigate to: {step.page_title or step.url}"
        if seg_type == "dialog-interaction":
            trigger_text = step.button_text or step.field_label or "dialog"
            return f"Dialog: {trigger_text}"
        if seg_type == "richtext-edit":
            label = step.field_label or "rich text"
            return f"Rich-text edit: {label}"
        return "Form fill"

    for step in steps:
        at = step.action_type

        # S1: navigation always starts fresh
        if at == "navigate-page":
            _flush(current_type or "misc", _segment_title("misc", step) if current_type else "Preamble")
            current_type = "navigation"
            current_steps.append(step)
            after_dialog_close = False
            in_dialog = False
            continue

        # S5: after dialog close, start fresh
        if after_dialog_close:
            _flush(current_type or "misc", "Dialog interaction")
            current_type = ""
            in_dialog = False
            after_dialog_close = False

        # S2: open-dialog
        if at == "open-dialog":
            if current_type != "dialog-interaction":
                _flush(current_type or "form-fill", _segment_title("form-fill", step) if current_type in ("form-fill", "") else current_type)
                current_type = "dialog-interaction"
            in_dialog = True
            current_steps.append(step)
            continue

        # S3: confirm / cancel
        if at in ("confirm-dialog", "cancel-dialog"):
            current_steps.append(step)
            after_dialog_close = True
            continue

        # S4: richtext-edit
        if at == "edit-richtext":
            if current_type != "richtext-edit":
                _flush(current_type or "form-fill", _segment_title("form-fill", step) if current_type in ("form-fill", "") else current_type)
                current_type = "richtext-edit"
            current_steps.append(step)
            continue

        # Default: fill-field, select-field, unknown-click, click-button → form-fill
        if current_type not in ("form-fill", "dialog-interaction"):
            _flush(current_type or "misc", current_type or "misc")
            current_type = "form-fill"
        current_steps.append(step)

    # Flush remaining
    if current_steps:
        if not current_type:
            current_type = "misc"
        _flush(current_type, current_type)

    # Title cleanup pass — always regenerate titles from type + content
    for seg in segments:
        first = seg.steps[0] if seg.steps else None
        if seg.type == "navigation" and first:
            seg.title = f"Navigate to: {first.page_title or first.url}"
        elif seg.type == "form-fill":
            seg.title = "Form fill"
        elif seg.type == "dialog-interaction":
            first_open = next(
                (s for s in seg.steps if s.action_type == "open-dialog"), first
            )
            seg.title = f"Dialog: {first_open.button_text or 'interaction'}" if first_open else "Dialog interaction"
        elif seg.type == "richtext-edit":
            seg.title = f"Rich-text edit: {first.field_label or 'content'}" if first else "Rich-text edit"
        else:
            seg.title = "Misc"

    return segments


# ---------------------------------------------------------------------------
# Step 4: Extract key actions
# ---------------------------------------------------------------------------

_KEY_ACTION_TYPES = frozenset([
    "navigate-page",
    "open-dialog",
    "confirm-dialog",
    "cancel-dialog",
    "edit-richtext",
])

_KEY_FILL_TYPES = frozenset(["fill-field", "select-field"])


def _extract_key_actions(steps: list[NormalizedStep]) -> list[NormalizedStep]:
    """
    A step is a key action if:
    K1. Its action_type is in _KEY_ACTION_TYPES.
    K2. It is a fill-field/select-field with a non-empty field_label.
    K3. It is a click-button whose button_text matches submit/confirm keywords.

    Duplicates (same action_type + field_label + value) are deduplicated.
    """
    seen: set[tuple[str, str | None, str | None]] = set()
    key: list[NormalizedStep] = []

    for step in steps:
        at = step.action_type
        is_key = False

        if at in _KEY_ACTION_TYPES:
            is_key = True
        elif at in _KEY_FILL_TYPES and step.field_label:
            is_key = True
        elif at == "click-button" and step.button_text:
            bt = step.button_text.lower()
            if any(kw in bt for kw in _SUBMIT_KEYWORDS | _CANCEL_KEYWORDS):
                is_key = True

        if is_key:
            dedup_key = (at, step.field_label, step.value)
            if dedup_key not in seen:
                seen.add(dedup_key)
                key.append(step)

    return key


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def normalize_recording(
    recording_id: str,
    events: list[dict[str, Any]],
) -> NormalizedRecording:
    """
    Main entry point: takes raw recording events and returns a NormalizedRecording.

    Parameters
    ----------
    recording_id : str
        The recording's UUID (used for reference in the output).
    events : list[dict]
        Raw events as stored in the DB (may be dicts with camelCase keys from
        the browser extension).
    """
    if not events:
        return NormalizedRecording(
            recording_id=recording_id,
            summary=NormalizationSummary(
                event_count_raw=0,
                event_count_normalized=0,
                page_count=0,
                segment_count=0,
                contains_iframe=False,
                contains_richtext=False,
            ),
            segments=[],
            key_actions=[],
        )

    # --- Merge & denoise ---
    merged = _merge_events(events)

    # --- Convert to NormalizedSteps ---
    steps = [_to_step(orig_idx, ev) for orig_idx, ev in merged]

    # --- Segment ---
    segments = _segment_steps(steps)

    # --- Key actions ---
    key_actions = _extract_key_actions(steps)

    # --- Summary stats ---
    urls = {ev.get("url") for _, ev in merged if ev.get("type") == "navigate"}
    page_count = max(1, len(urls))
    contains_iframe = any(
        bool((ev.get("frameInfo") or {}).get("isIframe"))
        for _, ev in merged
    )
    contains_richtext = any(
        ev.get("type") == "richtext-input" for _, ev in merged
    )

    summary = NormalizationSummary(
        event_count_raw=len(events),
        event_count_normalized=len(steps),
        page_count=page_count,
        segment_count=len(segments),
        contains_iframe=contains_iframe,
        contains_richtext=contains_richtext,
    )

    return NormalizedRecording(
        recording_id=recording_id,
        summary=summary,
        segments=segments,
        key_actions=key_actions,
    )


# ---------------------------------------------------------------------------
# Serialization helper (dataclass → plain dict for API response)
# ---------------------------------------------------------------------------

def _step_to_dict(step: NormalizedStep) -> dict[str, Any]:
    return {
        "action_type": step.action_type,
        "timestamp": step.timestamp,
        "url": step.url,
        "page_title": step.page_title,
        "field_label": step.field_label,
        "field_prop": step.field_prop,
        "field_required": step.field_required,
        "value": step.value,
        "button_text": step.button_text,
        "in_iframe": step.in_iframe,
        "frame_url": step.frame_url,
        "is_richtext": step.is_richtext,
        "html_content": step.html_content,
        "raw_event_indices": step.raw_event_indices,
    }


def normalized_recording_to_dict(nr: NormalizedRecording) -> dict[str, Any]:
    return {
        "recording_id": nr.recording_id,
        "summary": {
            "event_count_raw": nr.summary.event_count_raw,
            "event_count_normalized": nr.summary.event_count_normalized,
            "page_count": nr.summary.page_count,
            "segment_count": nr.summary.segment_count,
            "contains_iframe": nr.summary.contains_iframe,
            "contains_richtext": nr.summary.contains_richtext,
        },
        "segments": [
            {
                "index": seg.index,
                "type": seg.type,
                "title": seg.title,
                "steps": [_step_to_dict(s) for s in seg.steps],
            }
            for seg in nr.segments
        ],
        "key_actions": [_step_to_dict(s) for s in nr.key_actions],
    }
