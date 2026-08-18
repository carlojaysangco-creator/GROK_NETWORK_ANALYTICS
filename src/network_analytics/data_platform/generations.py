"""Immutable generation store with atomic promotion and last-known-good."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .manifest import (
    GenerationManifest,
    GenerationStatus,
    SourceIdentity,
    ValidationSummary,
    deserialize_manifest,
    serialize_manifest,
    utc_now_iso,
)


class GenerationError(Exception):
    """Base generation error."""


class GenerationNotFound(GenerationError):
    """Requested generation does not exist."""


class GenerationIntegrityError(GenerationError):
    """Manifest or inventory failed integrity checks."""


class GenerationConflict(GenerationError):
    """Promotion or state transition conflict."""


@dataclass(frozen=True, slots=True)
class GenerationReference:
    dataset_name: str
    generation_id: str
    path: Path
    manifest: GenerationManifest


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class GenerationStore:
    """Target-owned immutable generation lifecycle.

    Readers resolve only promoted or last-known-good generations.
    Newest directory / mtime is never authoritative.
    """

    def __init__(self, root: Path, *, control_db: Path | None = None) -> None:
        self.root = root.expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.control_db = (control_db or (self.root / "_control.sqlite3")).resolve()
        self._init_control()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.control_db)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _init_control(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS pointers (
                    dataset_name TEXT NOT NULL,
                    pointer_type TEXT NOT NULL CHECK (pointer_type IN ('promoted', 'lkg')),
                    generation_id TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (dataset_name, pointer_type)
                );
                CREATE TABLE IF NOT EXISTS generation_index (
                    dataset_name TEXT NOT NULL,
                    generation_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    path TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (dataset_name, generation_id)
                );
                """
            )

    def _dataset_dir(self, dataset_name: str) -> Path:
        safe = dataset_name.strip().replace("..", "_").replace("/", "_").replace("\\", "_")
        path = (self.root / safe).resolve()
        path.relative_to(self.root)  # must stay inside root
        return path

    def _generation_dir(self, dataset_name: str, generation_id: str) -> Path:
        return self._dataset_dir(dataset_name) / generation_id

    def create_candidate(
        self,
        *,
        dataset_name: str,
        schema_version: str,
        producer_version: str,
        parser_version: str | None = None,
        source: SourceIdentity | None = None,
        metadata: dict | None = None,
    ) -> GenerationReference:
        generation_id = f"gen-{utc_now_iso().replace(':', '').replace('+', 'p')}-{uuid.uuid4().hex[:8]}"
        path = self._generation_dir(dataset_name, generation_id)
        if path.exists():
            raise GenerationConflict(f"generation path already exists: {path}")
        path.mkdir(parents=True, exist_ok=False)
        (path / "data").mkdir()
        (path / "rejected").mkdir()

        manifest = GenerationManifest(
            dataset_name=dataset_name,
            schema_version=schema_version,
            generation_id=generation_id,
            producer_version=producer_version,
            parser_version=parser_version,
            status=GenerationStatus.BUILDING,
            created_at=utc_now_iso(),
            source=source,
            metadata=dict(metadata or {}),
        )
        self._write_manifest(path, manifest)
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO generation_index(dataset_name, generation_id, status, path, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (dataset_name, generation_id, manifest.status.value, str(path), manifest.created_at),
            )
        return GenerationReference(dataset_name, generation_id, path, manifest)

    def _manifest_path(self, generation_path: Path) -> Path:
        return generation_path / "manifest.json"

    def _write_manifest(self, generation_path: Path, manifest: GenerationManifest) -> None:
        text = serialize_manifest(manifest)
        self._manifest_path(generation_path).write_text(text, encoding="utf-8")

    def load_manifest(self, generation_path: Path) -> GenerationManifest:
        path = self._manifest_path(generation_path)
        if not path.is_file():
            raise GenerationNotFound(f"manifest missing: {path}")
        return deserialize_manifest(path.read_text(encoding="utf-8"))

    def add_data_file(self, ref: GenerationReference, relative_name: str, content: bytes) -> str:
        if ".." in relative_name or relative_name.startswith(("/", "\\")):
            raise GenerationIntegrityError(f"unsafe relative path: {relative_name}")
        target = (ref.path / "data" / relative_name).resolve()
        target.relative_to((ref.path / "data").resolve())
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        return _sha256_bytes(content)

    def finalize_inventory(self, ref: GenerationReference) -> GenerationManifest:
        data_root = ref.path / "data"
        inventory: dict[str, str] = {}
        if data_root.is_dir():
            for file_path in sorted(data_root.rglob("*")):
                if file_path.is_file():
                    rel = file_path.relative_to(data_root).as_posix()
                    inventory[rel] = _sha256_file(file_path)
        manifest = self.load_manifest(ref.path)
        manifest.file_inventory = inventory
        self._write_manifest(ref.path, manifest)
        return manifest

    def mark_validated(
        self,
        ref: GenerationReference,
        *,
        input_count: int,
        accepted_count: int,
        rejected_count: int = 0,
        duplicate_key_count: int = 0,
        validation: ValidationSummary | None = None,
    ) -> GenerationManifest:
        manifest = self.load_manifest(ref.path)
        if manifest.status not in {GenerationStatus.BUILDING, GenerationStatus.VALIDATING}:
            raise GenerationConflict(f"cannot validate from status {manifest.status}")
        manifest.status = GenerationStatus.VALIDATED
        manifest.input_count = input_count
        manifest.accepted_count = accepted_count
        manifest.rejected_count = rejected_count
        manifest.duplicate_key_count = duplicate_key_count
        if validation is not None:
            manifest.validation = validation
        self._write_manifest(ref.path, manifest)
        self._update_index_status(ref.dataset_name, ref.generation_id, manifest.status)
        return manifest

    def mark_rejected(self, ref: GenerationReference, issues: Iterable[str]) -> GenerationManifest:
        manifest = self.load_manifest(ref.path)
        manifest.status = GenerationStatus.REJECTED
        manifest.validation.issues = list(issues)
        self._write_manifest(ref.path, manifest)
        self._update_index_status(ref.dataset_name, ref.generation_id, manifest.status)
        return manifest

    def publish(self, ref: GenerationReference) -> GenerationManifest:
        manifest = self.finalize_inventory(ref)
        if manifest.status != GenerationStatus.VALIDATED:
            raise GenerationConflict("only validated generations may be published")
        if not manifest.file_inventory and manifest.accepted_count > 0:
            raise GenerationIntegrityError("validated generation has accepted rows but empty inventory")
        # Verify inventory hashes still match
        data_root = ref.path / "data"
        for rel, expected in manifest.file_inventory.items():
            actual = _sha256_file(data_root / rel)
            if actual != expected:
                raise GenerationIntegrityError(f"inventory mismatch for {rel}")
        manifest.status = GenerationStatus.PUBLISHED
        manifest.published_at = utc_now_iso()
        self._write_manifest(ref.path, manifest)
        self._update_index_status(ref.dataset_name, ref.generation_id, manifest.status)
        return manifest

    def promote(self, dataset_name: str, generation_id: str) -> GenerationManifest:
        path = self._generation_dir(dataset_name, generation_id)
        if not path.is_dir():
            raise GenerationNotFound(generation_id)
        manifest = self.load_manifest(path)
        if manifest.status not in {GenerationStatus.PUBLISHED, GenerationStatus.PROMOTED}:
            raise GenerationConflict("only published generations may be promoted")

        # Re-verify inventory before promotion
        data_root = path / "data"
        for rel, expected in manifest.file_inventory.items():
            if _sha256_file(data_root / rel) != expected:
                raise GenerationIntegrityError(f"inventory mismatch before promotion: {rel}")

        now = utc_now_iso()
        with self._connect() as conn:
            # Current promoted becomes LKG if present and different
            row = conn.execute(
                "SELECT generation_id FROM pointers WHERE dataset_name=? AND pointer_type='promoted'",
                (dataset_name,),
            ).fetchone()
            if row and row["generation_id"] != generation_id:
                conn.execute(
                    "INSERT INTO pointers(dataset_name, pointer_type, generation_id, updated_at) "
                    "VALUES (?, 'lkg', ?, ?) "
                    "ON CONFLICT(dataset_name, pointer_type) DO UPDATE SET "
                    "generation_id=excluded.generation_id, updated_at=excluded.updated_at",
                    (dataset_name, row["generation_id"], now),
                )
            conn.execute(
                "INSERT INTO pointers(dataset_name, pointer_type, generation_id, updated_at) "
                "VALUES (?, 'promoted', ?, ?) "
                "ON CONFLICT(dataset_name, pointer_type) DO UPDATE SET "
                "generation_id=excluded.generation_id, updated_at=excluded.updated_at",
                (dataset_name, generation_id, now),
            )

        manifest.status = GenerationStatus.PROMOTED
        manifest.promoted_at = now
        self._write_manifest(path, manifest)
        self._update_index_status(dataset_name, generation_id, manifest.status)
        return manifest

    def _update_index_status(self, dataset_name: str, generation_id: str, status: GenerationStatus) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE generation_index SET status=? WHERE dataset_name=? AND generation_id=?",
                (status.value, dataset_name, generation_id),
            )

    def get_pointer(self, dataset_name: str, pointer_type: str) -> str | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT generation_id FROM pointers WHERE dataset_name=? AND pointer_type=?",
                (dataset_name, pointer_type),
            ).fetchone()
        return str(row["generation_id"]) if row else None

    def resolve_promoted(self, dataset_name: str) -> GenerationReference | None:
        generation_id = self.get_pointer(dataset_name, "promoted")
        if not generation_id:
            return None
        return self._load_ref(dataset_name, generation_id)

    def resolve_lkg(self, dataset_name: str) -> GenerationReference | None:
        generation_id = self.get_pointer(dataset_name, "lkg")
        if not generation_id:
            # Fall back to promoted if no separate LKG yet
            return self.resolve_promoted(dataset_name)
        return self._load_ref(dataset_name, generation_id)

    def resolve_readable(self, dataset_name: str) -> GenerationReference | None:
        """Preferred read path: promoted, else last-known-good."""
        return self.resolve_promoted(dataset_name) or self.resolve_lkg(dataset_name)

    def _load_ref(self, dataset_name: str, generation_id: str) -> GenerationReference:
        path = self._generation_dir(dataset_name, generation_id)
        if not path.is_dir():
            raise GenerationNotFound(generation_id)
        manifest = self.load_manifest(path)
        return GenerationReference(dataset_name, generation_id, path, manifest)

    def list_generations(self, dataset_name: str) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT generation_id, status, path, created_at FROM generation_index "
                "WHERE dataset_name=? ORDER BY created_at DESC",
                (dataset_name,),
            ).fetchall()
        return [dict(row) for row in rows]
