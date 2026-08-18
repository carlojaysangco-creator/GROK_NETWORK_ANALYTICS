"""Generation manifest contracts."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
import json


class GenerationStatus(StrEnum):
    BUILDING = "building"
    VALIDATING = "validating"
    VALIDATED = "validated"
    REJECTED = "rejected"
    PUBLISHED = "published"
    PROMOTED = "promoted"


@dataclass(slots=True)
class SourceIdentity:
    system: str
    path_or_job: str
    sha256: str
    collected_at: str | None = None
    business_time: str | None = None


@dataclass(slots=True)
class ValidationSummary:
    required_columns_ok: bool = True
    datatype_ok: bool = True
    null_ok: bool = True
    uniqueness_ok: bool = True
    timestamp_range_ok: bool = True
    issues: list[str] = field(default_factory=list)


@dataclass(slots=True)
class GenerationManifest:
    dataset_name: str
    schema_version: str
    generation_id: str
    producer_version: str
    parser_version: str | None
    status: GenerationStatus
    created_at: str
    published_at: str | None = None
    promoted_at: str | None = None
    source: SourceIdentity | None = None
    input_count: int = 0
    accepted_count: int = 0
    rejected_count: int = 0
    duplicate_key_count: int = 0
    validation: ValidationSummary = field(default_factory=ValidationSummary)
    file_inventory: dict[str, str] = field(default_factory=dict)  # relative_path -> sha256
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["status"] = self.status.value
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GenerationManifest":
        source_raw = data.get("source")
        source = SourceIdentity(**source_raw) if source_raw else None
        validation_raw = data.get("validation") or {}
        validation = ValidationSummary(
            required_columns_ok=bool(validation_raw.get("required_columns_ok", True)),
            datatype_ok=bool(validation_raw.get("datatype_ok", True)),
            null_ok=bool(validation_raw.get("null_ok", True)),
            uniqueness_ok=bool(validation_raw.get("uniqueness_ok", True)),
            timestamp_range_ok=bool(validation_raw.get("timestamp_range_ok", True)),
            issues=list(validation_raw.get("issues") or []),
        )
        return cls(
            dataset_name=str(data["dataset_name"]),
            schema_version=str(data["schema_version"]),
            generation_id=str(data["generation_id"]),
            producer_version=str(data["producer_version"]),
            parser_version=data.get("parser_version"),
            status=GenerationStatus(str(data["status"])),
            created_at=str(data["created_at"]),
            published_at=data.get("published_at"),
            promoted_at=data.get("promoted_at"),
            source=source,
            input_count=int(data.get("input_count") or 0),
            accepted_count=int(data.get("accepted_count") or 0),
            rejected_count=int(data.get("rejected_count") or 0),
            duplicate_key_count=int(data.get("duplicate_key_count") or 0),
            validation=validation,
            file_inventory=dict(data.get("file_inventory") or {}),
            metadata=dict(data.get("metadata") or {}),
        )


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def serialize_manifest(manifest: GenerationManifest) -> str:
    return json.dumps(manifest.to_dict(), indent=2, sort_keys=True) + "\n"


def deserialize_manifest(text: str) -> GenerationManifest:
    return GenerationManifest.from_dict(json.loads(text))
