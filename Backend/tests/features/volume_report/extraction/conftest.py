"""Phase 0 tests are pure (no DB, no network): shadow the suite-wide autouse DB fixtures."""

import pytest


@pytest.fixture(scope="session", autouse=True)
def _create_test_database() -> None:
    return None


@pytest.fixture(autouse=True)
def _reset_schema() -> None:
    yield
