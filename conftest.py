"""Root conftest for amkb-sdk's own dev loop.

Provides the ``store`` fixture that the ``amkb.conformance`` suite
consumes when this repo's own baseline is run (``pytest tests
src/amkb/conformance``). This is NOT the pattern third-party
implementations should copy. A bare ``conftest.py`` at a consumer's
repo root does not "just work" against an installed package: pytest
only loads conftests that are filesystem ancestors of the collected
test files, so this file is invisible to anything collected from
outside this repo. See the README's "Implementing a Store" section
for the star-import pattern conformance consumers must use instead.
"""

from __future__ import annotations

import pytest

from amkb.conformance.fixtures import actor  # noqa: F401  (re-export for pytest)
from tests.impls.dict_store import DictStore


@pytest.fixture
def store() -> DictStore:
    """A fresh DictStore for each test."""

    return DictStore()
