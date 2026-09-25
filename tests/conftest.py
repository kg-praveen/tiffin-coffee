"""tests/conftest.py — shared fixtures.

The real register (db/pattaz.db) is read-only to tests: `sessions` is append-only
(CLAUDE.md §3), so a test that runs a usecase must do it on `scratch_db`. The
session-scoped guard fails the run if any test changed the real file.
"""
from __future__ import annotations

import hashlib
import shutil
from collections.abc import Iterator
from pathlib import Path

import pytest

SEED_DB = Path(__file__).parent.parent / "db" / "pattaz.db"


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture(scope="session", autouse=True)
def _real_db_untouched() -> Iterator[None]:
    before = _digest(SEED_DB)
    yield
    assert _digest(SEED_DB) == before, (
        "a test wrote to db/pattaz.db — use the scratch_db fixture"
    )


@pytest.fixture
def scratch_db(tmp_path: Path) -> Path:
    """A throwaway copy of the seeded register for tests that run usecases."""
    dst = tmp_path / "pattaz.db"
    shutil.copy(SEED_DB, dst)
    return dst
