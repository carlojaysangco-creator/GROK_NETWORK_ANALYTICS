"""Allowlist model for gated live topology (no device I/O)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class LiveAllowlist:
    version: str
    device_ids: tuple[str, ...]
    command_profiles: tuple[str, ...]
    jump_hosts: tuple[str, ...] = ()
    max_devices_per_job: int = 5
    job_timeout_seconds: int = 300

    def allows_device(self, device_id: str) -> bool:
        return device_id.strip().upper() in {d.upper() for d in self.device_ids}

    def allows_profile(self, profile: str) -> bool:
        return profile.strip().lower() in {p.lower() for p in self.command_profiles}


def default_allowlist() -> LiveAllowlist:
    return LiveAllowlist(
        version="v0-empty",
        device_ids=(),
        command_profiles=("interfaces", "lldp"),
        jump_hosts=(),
        max_devices_per_job=5,
        job_timeout_seconds=300,
    )


def load_allowlist(path: Path) -> LiveAllowlist:
    if not path.is_file():
        return default_allowlist()
    raw = json.loads(path.read_text(encoding="utf-8"))
    return LiveAllowlist(
        version=str(raw.get("version") or "v0"),
        device_ids=tuple(raw.get("device_ids") or ()),
        command_profiles=tuple(raw.get("command_profiles") or ("interfaces",)),
        jump_hosts=tuple(raw.get("jump_hosts") or ()),
        max_devices_per_job=int(raw.get("max_devices_per_job") or 5),
        job_timeout_seconds=int(raw.get("job_timeout_seconds") or 300),
    )


def validate_request_against_allowlist(
    allowlist: LiveAllowlist,
    *,
    device_ids: tuple[str, ...],
    command_profile: str,
) -> tuple[bool, tuple[str, ...]]:
    errors: list[str] = []
    if len(device_ids) == 0:
        errors.append("no devices requested")
    if len(device_ids) > allowlist.max_devices_per_job:
        errors.append(f"device count exceeds max_devices_per_job={allowlist.max_devices_per_job}")
    for d in device_ids:
        if not allowlist.allows_device(d):
            errors.append(f"device not allowlisted: {d}")
    if not allowlist.allows_profile(command_profile):
        errors.append(f"command profile not allowlisted: {command_profile}")
    return (not errors, tuple(errors))
