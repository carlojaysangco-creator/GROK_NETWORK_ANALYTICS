"""GenerationStore lifecycle tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from network_analytics.data_platform import (
    GenerationConflict,
    GenerationStore,
    SourceIdentity,
    ValidationSummary,
)


@pytest.fixture
def store(tmp_path: Path) -> GenerationStore:
    return GenerationStore(tmp_path / "generations")


def test_full_lifecycle_promote_and_lkg(store: GenerationStore) -> None:
    ref = store.create_candidate(
        dataset_name="demo_fact",
        schema_version="v1",
        producer_version="0.1.0.dev0",
        source=SourceIdentity(system="test", path_or_job="fixture", sha256="abc"),
    )
    assert ref.manifest.status.value == "building"

    digest = store.add_data_file(ref, "rows.parquet", b"fake-parquet-bytes")
    assert len(digest) == 64

    store.mark_validated(
        ref,
        input_count=10,
        accepted_count=9,
        rejected_count=1,
        validation=ValidationSummary(issues=[]),
    )
    published = store.publish(ref)
    assert published.status.value == "published"
    assert "rows.parquet" in published.file_inventory

    promoted = store.promote("demo_fact", ref.generation_id)
    assert promoted.status.value == "promoted"

    readable = store.resolve_readable("demo_fact")
    assert readable is not None
    assert readable.generation_id == ref.generation_id

    # Second generation becomes promoted; first becomes LKG
    ref2 = store.create_candidate(
        dataset_name="demo_fact",
        schema_version="v1",
        producer_version="0.1.0.dev0",
    )
    store.add_data_file(ref2, "rows.parquet", b"second-generation")
    store.mark_validated(ref2, input_count=5, accepted_count=5)
    store.publish(ref2)
    store.promote("demo_fact", ref2.generation_id)

    assert store.get_pointer("demo_fact", "promoted") == ref2.generation_id
    assert store.get_pointer("demo_fact", "lkg") == ref.generation_id


def test_cannot_publish_unvalidated(store: GenerationStore) -> None:
    ref = store.create_candidate(
        dataset_name="x",
        schema_version="v1",
        producer_version="0.1.0.dev0",
    )
    with pytest.raises(GenerationConflict):
        store.publish(ref)


def test_resolve_missing_returns_none(store: GenerationStore) -> None:
    assert store.resolve_readable("does_not_exist") is None
