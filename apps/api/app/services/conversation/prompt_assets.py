"""Versioned prompt asset loader for LLM-backed conversation Agents."""

from __future__ import annotations

import hashlib
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class PromptAssetError(RuntimeError):
    pass


@dataclass(frozen=True)
class PromptAsset:
    prompt_id: str
    version: str
    agent_role: str
    schema_name: str
    runtime_policy: str
    prompt_sha256: str
    prompt_body_sha256: str
    shared_fragment_sha256: tuple[tuple[str, str], ...]
    assembled_prompt_sha256: str
    prompt_path: Path
    metadata_path: Path
    shared_fragment_paths: tuple[Path, ...]
    prompt_body: str
    shared_fragments: tuple[str, ...]
    metadata: dict[str, Any]

    @property
    def assembled_prompt(self) -> str:
        return _assemble_prompt(self.shared_fragments, self.prompt_body)


class PromptAssetLoader:
    def __init__(self, root: Path | None = None) -> None:
        self._root = root or Path(__file__).resolve().parents[2] / "prompts"

    def load(self, prompt_id: str, *, version: str | None = None) -> PromptAsset:
        registry = self._load_toml(self._root / "registry.toml")
        prompts = registry.get("prompts")
        if not isinstance(prompts, dict) or prompt_id not in prompts:
            raise PromptAssetError(f"prompt is not registered: {prompt_id}")
        entry = prompts[prompt_id]
        if not isinstance(entry, dict):
            raise PromptAssetError(f"prompt registry entry is invalid: {prompt_id}")
        prompt_version = str(entry.get("version") or "")
        if version is not None and prompt_version != version:
            raise PromptAssetError(
                f"prompt version mismatch: {prompt_id} {prompt_version} != {version}"
            )

        prompt_path = self._root / str(entry.get("path") or "")
        metadata_path = self._root / str(entry.get("metadata") or "")
        prompt_body = _read_text(prompt_path)
        metadata = self._load_toml(metadata_path)
        shared_paths = tuple(
            self._root / str(path)
            for path in (entry.get("shared_fragments") or [])
        )
        shared_fragments = tuple(_read_text(path) for path in shared_paths)
        prompt_body_hash = _sha256_text(prompt_body)
        shared_fragment_hashes = tuple(
            (_display_path(self._root, path), _sha256_text(fragment))
            for path, fragment in zip(shared_paths, shared_fragments, strict=True)
        )
        assembled_prompt = _assemble_prompt(shared_fragments, prompt_body)
        actual_hash = _sha256_text(assembled_prompt)
        expected_hash = str(entry.get("prompt_sha256") or "")
        if not expected_hash:
            raise PromptAssetError(f"prompt hash is missing: {prompt_id}")
        if actual_hash != expected_hash:
            raise PromptAssetError(f"prompt hash mismatch: {prompt_id}")

        _require_metadata(prompt_id, metadata)
        return PromptAsset(
            prompt_id=prompt_id,
            version=prompt_version,
            agent_role=str(metadata["agent_role"]),
            schema_name=str(metadata["schema_name"]),
            runtime_policy=str(metadata["runtime_policy"]),
            prompt_sha256=actual_hash,
            prompt_body_sha256=prompt_body_hash,
            shared_fragment_sha256=shared_fragment_hashes,
            assembled_prompt_sha256=actual_hash,
            prompt_path=prompt_path,
            metadata_path=metadata_path,
            shared_fragment_paths=shared_paths,
            prompt_body=prompt_body,
            shared_fragments=shared_fragments,
            metadata=metadata,
        )

    def _load_toml(self, path: Path) -> dict[str, Any]:
        try:
            return tomllib.loads(_read_text(path))
        except tomllib.TOMLDecodeError as exc:
            raise PromptAssetError(f"invalid prompt TOML: {path}") from exc


def load_prompt_asset(prompt_id: str, *, version: str | None = None) -> PromptAsset:
    return PromptAssetLoader().load(prompt_id, version=version)


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise PromptAssetError(f"prompt file is missing: {path}") from exc


def _assemble_prompt(shared_fragments: tuple[str, ...], prompt_body: str) -> str:
    return "\n\n".join([*shared_fragments, prompt_body]).strip()


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _display_path(root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _require_metadata(prompt_id: str, metadata: dict[str, Any]) -> None:
    required = {
        "prompt_id",
        "version",
        "agent_role",
        "schema_name",
        "runtime_policy",
        "allowed_inputs",
        "forbidden_outputs",
        "sensitive_context_policy",
    }
    missing = sorted(name for name in required if not metadata.get(name))
    if missing:
        raise PromptAssetError(
            f"prompt metadata missing fields for {prompt_id}: {', '.join(missing)}"
        )
