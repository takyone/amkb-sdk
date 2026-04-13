"""Default fixtures exposed by the conformance package.

Implementations MAY override these in their own ``conftest.py``.
"""

from __future__ import annotations

import pytest

from amkb.refs import ActorId
from amkb.types import ACTOR_HUMAN, Actor


@pytest.fixture
def actor() -> Actor:
    """A default human Actor used by every conformance test that needs one."""

    return Actor(id=ActorId("conformance-actor"), kind=ACTOR_HUMAN)
