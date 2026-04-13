"""Root conftest for amkb-sdk.

Provides the ``store`` fixture that the ``amkb.conformance`` suite
consumes. Placed at the repo root so that ``pytest --pyargs
amkb.conformance`` picks it up regardless of where the installed
package lives on disk.
"""

from __future__ import annotations

import pytest

from amkb.conformance.fixtures import actor  # noqa: F401  (re-export for pytest)
from tests.impls.dict_store import DictStore


@pytest.fixture
def store() -> DictStore:
    """A fresh DictStore for each test."""

    return DictStore()
