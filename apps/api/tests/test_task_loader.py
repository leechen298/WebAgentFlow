"""
Tests for the task loader service.

Covers:
1. load_task_from_file with valid JSON -> correct TaskDefinition
2. load_task_from_file with missing file -> FileNotFoundError
3. load_task_from_file with invalid JSON -> error
4. load_task_from_file with schema-violating JSON -> ValidationError
5. load_task_by_id finds a task from custom search directories
6. load_task_by_id with nonexistent ID -> FileNotFoundError
7. load_task_by_id skips malformed files without crashing
8. load_task_by_id with custom search_dirs
9. list_tasks returns all tasks from a directory
10. list_tasks with no valid directory -> empty list
11. list_tasks skips malformed files gracefully
12. resolve_step_value: value_from takes precedence over value
13. resolve_step_value: missing variable falls back to value
14. resolve_step_value: both None returns None
15. resolve_step_value: value_from with no match and no value -> None
16. resolve_step_value: non-string variable is coerced to str
"""

import json
from pathlib import Path

import pytest

from app.schemas.task_definition import TaskDefinition
from app.services.task_loader import list_tasks, load_task_by_id, load_task_from_file, resolve_step_value


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

MINIMAL_TASK = {
    "id": "test-minimal",
    "name": "Minimal Task",
    "target_url": "https://example.com",
}

FULL_TASK = {
    "id": "test-full",
    "name": "Full Task",
    "description": "A comprehensive test task.",
    "target_url": "https://example.com",
    "variables": {"query": "hello"},
    "steps": [
        {
            "intent": "fill_input",
            "action_type": "fill",
            "target_hint": {"role": "textbox", "name": "search"},
            "value_from": "query",
        },
        {
            "intent": "submit",
            "action_type": "press",
            "value": "Enter",
        },
    ],
    "global_success_criteria": {
        "conditions": [
            {"type": "url_changed", "required": True},
        ],
    },
    "source": "user",
    "provenance": "user_authored",
    "revision": 2,
}


def _write_json(path: Path, data: object) -> Path:
    """Write a Python object as JSON to the given path."""
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# load_task_from_file
# ---------------------------------------------------------------------------


class TestLoadTaskFromFile:
    """Tests for load_task_from_file."""

    def test_valid_minimal_json(self, tmp_path: Path) -> None:
        f = _write_json(tmp_path / "task.json", MINIMAL_TASK)
        task = load_task_from_file(f)

        assert isinstance(task, TaskDefinition)
        assert task.id == "test-minimal"
        assert task.name == "Minimal Task"
        assert task.target_url == "https://example.com"
        assert task.steps == []
        assert task.variables == {}
        assert task.source == "builtin"  # default
        assert task.revision == 1  # default

    def test_valid_full_json(self, tmp_path: Path) -> None:
        f = _write_json(tmp_path / "task.json", FULL_TASK)
        task = load_task_from_file(f)

        assert task.id == "test-full"
        assert task.description == "A comprehensive test task."
        assert task.variables == {"query": "hello"}
        assert len(task.steps) == 2
        assert task.steps[0].intent == "fill_input"
        assert task.steps[0].action_type == "fill"
        assert task.steps[0].value_from == "query"
        assert task.steps[0].target_hint is not None
        assert task.steps[0].target_hint.role == "textbox"
        assert task.steps[1].value == "Enter"
        assert task.global_success_criteria is not None
        assert len(task.global_success_criteria.conditions) == 1
        assert task.source == "user"
        assert task.revision == 2

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError, match="Task file not found"):
            load_task_from_file(tmp_path / "nonexistent.json")

    def test_invalid_json_raises(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.json"
        bad.write_text("{not valid json!!!", encoding="utf-8")

        with pytest.raises(json.JSONDecodeError):
            load_task_from_file(bad)

    def test_schema_violation_raises(self, tmp_path: Path) -> None:
        """JSON is valid but missing required fields (id, name, target_url)."""
        f = _write_json(tmp_path / "task.json", {"description": "no id"})

        with pytest.raises(Exception):
            # Pydantic ValidationError (a subclass of ValueError in v2)
            load_task_from_file(f)

    def test_accepts_string_path(self, tmp_path: Path) -> None:
        f = _write_json(tmp_path / "task.json", MINIMAL_TASK)
        task = load_task_from_file(str(f))
        assert task.id == "test-minimal"

class TestLoadTaskById:
    """Tests for load_task_by_id."""

    def test_finds_task_in_custom_dir(self, tmp_path: Path) -> None:
        _write_json(tmp_path / "alpha.json", {**MINIMAL_TASK, "id": "alpha"})
        _write_json(tmp_path / "beta.json", {**MINIMAL_TASK, "id": "beta"})

        task = load_task_by_id("beta", search_dirs=[tmp_path])
        assert task.id == "beta"

    def test_nonexistent_id_raises(self, tmp_path: Path) -> None:
        _write_json(tmp_path / "alpha.json", {**MINIMAL_TASK, "id": "alpha"})

        with pytest.raises(FileNotFoundError, match="Task with id='nope'"):
            load_task_by_id("nope", search_dirs=[tmp_path])

    def test_empty_dir_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            load_task_by_id("anything", search_dirs=[tmp_path])

    def test_nonexistent_dir_raises(self, tmp_path: Path) -> None:
        fake_dir = tmp_path / "does_not_exist"
        with pytest.raises(FileNotFoundError):
            load_task_by_id("anything", search_dirs=[fake_dir])

    def test_skips_malformed_files(self, tmp_path: Path) -> None:
        """Malformed JSON files are skipped; the valid file is still found."""
        bad = tmp_path / "aaa_bad.json"
        bad.write_text("<<<not json>>>", encoding="utf-8")
        _write_json(tmp_path / "bbb_good.json", {**MINIMAL_TASK, "id": "good"})

        task = load_task_by_id("good", search_dirs=[tmp_path])
        assert task.id == "good"

    def test_first_match_wins_across_dirs(self, tmp_path: Path) -> None:
        dir1 = tmp_path / "dir1"
        dir2 = tmp_path / "dir2"
        dir1.mkdir()
        dir2.mkdir()
        _write_json(dir1 / "t.json", {**MINIMAL_TASK, "id": "dup", "name": "First"})
        _write_json(dir2 / "t.json", {**MINIMAL_TASK, "id": "dup", "name": "Second"})

        task = load_task_by_id("dup", search_dirs=[dir1, dir2])
        assert task.name == "First"

class TestListTasks:
    """Tests for list_tasks."""

    def test_lists_all_tasks(self, tmp_path: Path) -> None:
        _write_json(tmp_path / "a.json", {**MINIMAL_TASK, "id": "a"})
        _write_json(tmp_path / "b.json", {**MINIMAL_TASK, "id": "b"})

        tasks = list_tasks(search_dirs=[tmp_path])
        ids = [t.id for t in tasks]

        assert len(tasks) == 2
        assert "a" in ids
        assert "b" in ids

    def test_empty_dir_returns_empty(self, tmp_path: Path) -> None:
        assert list_tasks(search_dirs=[tmp_path]) == []

    def test_nonexistent_dir_returns_empty(self, tmp_path: Path) -> None:
        fake = tmp_path / "nope"
        assert list_tasks(search_dirs=[fake]) == []

    def test_skips_malformed_files(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.json"
        bad.write_text("not json", encoding="utf-8")
        _write_json(tmp_path / "good.json", {**MINIMAL_TASK, "id": "ok"})

        tasks = list_tasks(search_dirs=[tmp_path])
        assert len(tasks) == 1
        assert tasks[0].id == "ok"

    def test_ignores_non_json_files(self, tmp_path: Path) -> None:
        """Only .json files are scanned; .txt etc. are ignored."""
        (tmp_path / "readme.txt").write_text("hello", encoding="utf-8")
        _write_json(tmp_path / "task.json", {**MINIMAL_TASK, "id": "only"})

        tasks = list_tasks(search_dirs=[tmp_path])
        assert len(tasks) == 1
        assert tasks[0].id == "only"

    def test_multiple_dirs_merged(self, tmp_path: Path) -> None:
        d1 = tmp_path / "d1"
        d2 = tmp_path / "d2"
        d1.mkdir()
        d2.mkdir()
        _write_json(d1 / "x.json", {**MINIMAL_TASK, "id": "x"})
        _write_json(d2 / "y.json", {**MINIMAL_TASK, "id": "y"})

        tasks = list_tasks(search_dirs=[d1, d2])
        ids = [t.id for t in tasks]
        assert "x" in ids
        assert "y" in ids

    def test_default_search_dirs_can_be_empty(self) -> None:
        """User-managed data directories are optional in the repository."""
        tasks = list_tasks()
        assert isinstance(tasks, list)


# ---------------------------------------------------------------------------
# resolve_step_value
# ---------------------------------------------------------------------------


class TestResolveStepValue:
    """Tests for resolve_step_value."""

    def test_value_from_takes_precedence(self) -> None:
        result = resolve_step_value(
            value="fallback",
            value_from="query",
            variables={"query": "hello"},
        )
        assert result == "hello"

    def test_missing_variable_falls_back_to_value(self) -> None:
        result = resolve_step_value(
            value="fallback",
            value_from="missing_key",
            variables={"other": "data"},
        )
        assert result == "fallback"

    def test_both_none_returns_none(self) -> None:
        result = resolve_step_value(
            value=None,
            value_from=None,
            variables={},
        )
        assert result is None

    def test_value_from_none_returns_value(self) -> None:
        result = resolve_step_value(
            value="static",
            value_from=None,
            variables={},
        )
        assert result == "static"

    def test_value_from_missing_and_no_value(self) -> None:
        result = resolve_step_value(
            value=None,
            value_from="nonexistent",
            variables={},
        )
        assert result is None

    def test_non_string_variable_coerced(self) -> None:
        result = resolve_step_value(
            value=None,
            value_from="count",
            variables={"count": 42},
        )
        assert result == "42"

    def test_empty_value_from_treated_as_falsy(self) -> None:
        """An empty string value_from is falsy, so value is returned."""
        result = resolve_step_value(
            value="static",
            value_from="",
            variables={"": "sneaky"},
        )
        assert result == "static"

    def test_variable_none_falls_back_to_value(self) -> None:
        """If the variable exists but its value is None, fall back to value."""
        result = resolve_step_value(
            value="fallback",
            value_from="key",
            variables={"key": None},
        )
        assert result == "fallback"

    def test_empty_variables_dict(self) -> None:
        result = resolve_step_value(
            value="default",
            value_from="key",
            variables={},
        )
        assert result == "default"
