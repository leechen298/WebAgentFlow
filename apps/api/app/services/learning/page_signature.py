"""Stable identity signatures for a learned page.

Three pure functions back the LearnedPath dedup quadruple:

- :func:`path_template` normalises a URL path so e.g. ``/detail/1`` and
  ``/detail/2`` collapse into ``/detail/:num``.
- :func:`query_signature` canonicalises query parameters. Whitelisted
  "semantic switch" values (short, alphabetic) are preserved; concrete
  data values (numbers, UUIDs, CJK text, long tokens) are replaced with
  ``"*"``.
- :func:`dom_fingerprint` hashes the structural shape of a
  :class:`~app.schemas.page_analysis.PageAnalysis` — form controls,
  buttons, toggles, selects — ignoring instance-specific noise
  (``css-dev-only-do-not-override-*`` classes, ``rc_*`` auto-ids, row
  data values).

These three functions are the only signature producers in the codebase;
the LearnedPath repo and any future Phase 3 lookup path must call them
rather than inventing local variants.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable
from urllib.parse import parse_qsl, urlsplit

from app.schemas.page_analysis import DiscoveredElement, PageAnalysis

__all__ = [
    "path_template",
    "query_signature",
    "dom_fingerprint",
    "QUERY_KEEP_MAX_LEN",
]

# ---------------------------------------------------------------------------
# path_template
# ---------------------------------------------------------------------------

_NUMERIC_SEGMENT_RE = re.compile(r"^\d+$")
_UUID_SEGMENT_RE = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}"
    r"-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)


def path_template(url_or_path: str) -> str:
    """Return a path with volatile segments normalised.

    - Pure-digit segments → ``:num``
    - UUID v4 segments   → ``:uuid``
    - Trailing slash is removed except for the root.
    - Empty / malformed input (no scheme, doesn't start with ``/``)
      returns ``"/"`` per the spec — concrete paths must be at least
      ``/something``.
    """
    if not url_or_path:
        return "/"
    try:
        parsed = urlsplit(url_or_path)
    except ValueError:
        return "/"

    has_scheme_or_host = bool(parsed.scheme or parsed.netloc)
    raw_path = parsed.path if has_scheme_or_host else url_or_path
    if "?" in raw_path:
        raw_path = raw_path.split("?", 1)[0]
    if "#" in raw_path:
        raw_path = raw_path.split("#", 1)[0]

    if not raw_path or raw_path == "/":
        return "/"

    # Reject inputs that don't look like paths at all — bare strings
    # without a leading slash and without a scheme/host can't be made
    # into a meaningful template, so we collapse to "/" rather than
    # echo garbage back.
    if not has_scheme_or_host and not raw_path.startswith("/"):
        return "/"

    segments = raw_path.split("/")
    normalised: list[str] = []
    for seg in segments:
        if not seg:
            normalised.append(seg)
            continue
        if _NUMERIC_SEGMENT_RE.match(seg):
            normalised.append(":num")
        elif _UUID_SEGMENT_RE.match(seg):
            normalised.append(":uuid")
        else:
            normalised.append(seg)

    result = "/".join(normalised)
    if result.endswith("/") and result != "/":
        result = result.rstrip("/")
    return result or "/"


# ---------------------------------------------------------------------------
# query_signature
# ---------------------------------------------------------------------------

QUERY_KEEP_MAX_LEN = 8


def query_signature(url_or_query: str) -> dict[str, str]:
    """Return a canonicalised ``{key: normalized_value}`` mapping.

    Heuristic: a value is preserved (lower-cased) iff it is short
    (``len <= QUERY_KEEP_MAX_LEN``) AND entirely ASCII-alphabetic.
    Everything else becomes ``"*"`` so the signature is stable across
    concrete data values.

    - Repeated keys collapse to the first-seen value.
    - Keys are lower-cased; the returned dict iterates in sorted order.
    - Fragment (``#...``) is stripped before parsing so
      ``?type=edit#frag`` does not leak the hash into the value.

    Known limitations (tracked in the iteration's ``review.md``):

    - Mixed alphanumeric semantic flags like ``type=edit2`` fall to
      ``"*"`` even though they may be stable. Add explicit exceptions
      only after real traffic shows them.
    """
    if not url_or_query:
        return {}

    # Use urlsplit so we get a clean query segment regardless of
    # whether the caller passed a full URL, a "?foo=bar" bit, or a
    # bare "foo=bar". Fragment is dropped automatically; it must not
    # bleed into the last value.
    split = urlsplit(url_or_query)
    if split.query:
        query = split.query
    elif "=" in url_or_query and "?" not in url_or_query:
        # Bare "key=value" with no leading "?" — parse as-is.
        query = url_or_query
        if "#" in query:
            query = query.split("#", 1)[0]
    else:
        query = ""

    if not query:
        return {}

    pairs = parse_qsl(query, keep_blank_values=True)
    seen: dict[str, str] = {}
    for raw_key, raw_value in pairs:
        key = raw_key.lower()
        if key in seen:
            continue
        seen[key] = _normalise_query_value(raw_value)
    return {k: seen[k] for k in sorted(seen.keys())}


def _normalise_query_value(value: str) -> str:
    # Restrict the whitelist to ASCII letters so CJK/emoji/accented
    # tokens collapse to ``"*"`` — Python's ``.isalpha()`` alone
    # returns True for Chinese characters and other non-Latin scripts,
    # which aren't the kind of "short semantic flag" this rule is
    # meant to preserve.
    if (
        value
        and len(value) <= QUERY_KEEP_MAX_LEN
        and value.isascii()
        and value.isalpha()
    ):
        return value.lower()
    return "*"


# ---------------------------------------------------------------------------
# dom_fingerprint
# ---------------------------------------------------------------------------

_DEV_CLASS_RE = re.compile(r"^css-dev-only-do-not-override-[0-9a-z]+$")
_RC_ID_RE = re.compile(r"^rc[_-][a-z0-9_-]+$", re.IGNORECASE)
_LONG_HEX_RE = re.compile(r"^[0-9a-f]{12,}$", re.IGNORECASE)


def dom_fingerprint(analysis: PageAnalysis) -> str:
    """Hash the stable structural shape of a PageAnalysis.

    The fingerprint covers form controls (kind + label), visible button
    labels, toggle groups, and select widgets. Per-render noise (auto
    ids, dev-only class markers, data values, row counts) is excluded
    by construction — we never read ``DiscoveredElement.id`` directly.
    """
    payload = {
        "title": (analysis.title or "").strip(),
        "forms": _stable_sorted(_form_key(el) for el in analysis.fillable),
        "buttons": _stable_sorted(
            _button_label(el)
            for el in (*analysis.submit, *analysis.clickable)
            if _button_label(el)
        ),
        "toggles": _stable_sorted(_toggle_key(el) for el in analysis.toggle),
        "selects": _stable_sorted(_select_key(el) for el in analysis.select),
    }
    raw = json.dumps(
        payload,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _stable_sorted(items: Iterable[str]) -> list[str]:
    return sorted(filter(None, items))


def _form_key(element: DiscoveredElement) -> str:
    role = (
        element.semantic_role
        or _clean(element.element_type)
        or element.tag
        or "field"
    )
    label = (
        _clean(element.label_text)
        or _clean(element.name)
        or _clean(element.placeholder)
        or _clean(element.aria_label)
    )
    return f"{role}::{label}"


def _button_label(element: DiscoveredElement) -> str:
    return (
        _clean(element.text)
        or _clean(element.aria_label)
        or _clean(element.label_text)
        or ""
    )


def _toggle_key(element: DiscoveredElement) -> str:
    role = element.semantic_role or _clean(element.element_type) or "toggle"
    label = (
        _clean(element.label_text)
        or _clean(element.name)
        or _clean(element.aria_label)
        or _clean(element.placeholder)
    )
    return f"{role}::{label}"


def _select_key(element: DiscoveredElement) -> str:
    label = (
        _clean(element.label_text)
        or _clean(element.name)
        or _clean(element.aria_label)
        or _clean(element.placeholder)
    )
    return f"select::{label}"


def _clean(value: str | None) -> str:
    if not value:
        return ""
    stripped = value.strip()
    # Drop tokens that look like per-render garbage so two loads of the
    # same page collide deterministically.
    tokens = stripped.split()
    kept = [
        tok
        for tok in tokens
        if not _DEV_CLASS_RE.match(tok)
        and not _RC_ID_RE.match(tok)
        and not _LONG_HEX_RE.match(tok)
    ]
    return " ".join(kept)
