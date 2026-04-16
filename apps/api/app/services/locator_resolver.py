"""Compat re-export — module moved to app.services.execution.locator_resolver."""
from app.services.execution.locator_resolver import *  # noqa: F401,F403
from app.services.execution.locator_resolver import (  # noqa: F401,F811
    _count_matches,
    _css_escape,
    _css_escape_attr,
    _get_element_info,
    _parse_target_description,
    _scope_to_region,
    _tag_to_role,
    _try_client_ast_match,
    _try_fallback_selector,
    _try_region_scoped,
    _try_server_ast_match,
    _try_strong_attribute,
    _try_tag_text_label,
    resolve_locator,
    to_playwright_locator,
)
