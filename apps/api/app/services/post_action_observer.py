"""Compat re-export — module moved to app.services.execution.post_action_observer."""
from app.services.execution.post_action_observer import *  # noqa: F401,F403
from app.services.execution.post_action_observer import (  # noqa: F811
    execute_and_observe,
    observe_post_action,
)
