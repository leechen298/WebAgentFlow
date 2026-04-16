"""Task definition loader.

Loads TaskDefinition from JSON files. Handles:
  - Loading from a specific file path
  - Scanning the data/tasks/ directory
  - Variable resolution (value_from)

Keeps schema and I/O separate — schemas/ defines structure, this module
handles file access.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from app.schemas.task_definition import TaskDefinition

logger = logging.getLogger(__name__)

# Default task directories, searched in order.
# First match wins.
_PROJECT_ROOT = Path(__file__).resolve().parents[4]  # apps/api/app/services/ → project root
_DEFAULT_TASK_DIRS = [
    _PROJECT_ROOT / "data" / "tasks",
]


def load_task_from_file(path: str | Path) -> TaskDefinition:
    """Load a TaskDefinition from a JSON file.

    Raises FileNotFoundError or ValueError on problems.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Task file not found: {p}")

    with p.open("r", encoding="utf-8") as f:
        data = json.load(f)

    return TaskDefinition(**data)


def load_task_by_id(
    task_id: str,
    search_dirs: list[Path] | None = None,
) -> TaskDefinition:
    """Find and load a task by its ID.

    Scans directories for JSON files, loads each, and returns the first
    whose ``id`` matches ``task_id``.
    """
    dirs = search_dirs or _DEFAULT_TASK_DIRS

    for d in dirs:
        if not d.is_dir():
            continue
        for f in sorted(d.glob("*.json")):
            try:
                task = load_task_from_file(f)
                if task.id == task_id:
                    return task
            except Exception as e:
                logger.debug("Skipping %s: %s", f, e)
                continue

    raise FileNotFoundError(
        f"Task with id='{task_id}' not found in {[str(d) for d in dirs]}"
    )


def list_tasks(
    search_dirs: list[Path] | None = None,
) -> list[TaskDefinition]:
    """List all available task definitions."""
    dirs = search_dirs or _DEFAULT_TASK_DIRS
    tasks: list[TaskDefinition] = []

    for d in dirs:
        if not d.is_dir():
            continue
        for f in sorted(d.glob("*.json")):
            try:
                tasks.append(load_task_from_file(f))
            except Exception as e:
                logger.debug("Skipping %s: %s", f, e)

    return tasks


def resolve_step_value(
    value: str | None,
    value_from: str | None,
    variables: dict[str, Any],
) -> str | None:
    """Resolve a step's value, with value_from taking precedence."""
    if value_from:
        resolved = variables.get(value_from)
        if resolved is not None:
            return str(resolved)
        logger.warning("value_from='%s' not found in variables", value_from)
    return value
