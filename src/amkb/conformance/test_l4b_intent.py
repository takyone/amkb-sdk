"""Executable L4b (Intent retrieval) conformance tests.

Mirrors ``amkb-spec/conformance/L4b-intent.md``. L4b covers the
`retrieve` operation: hit shape, score monotonicity, limit+filter
interaction, argument validation, empty-store behavior, and
determinism under an unchanged store.

Protocol note: the SDK's ``Store.retrieve`` signature uses ``k=`` for
the limit and ``filters=`` for the filter expression. The spec text
uses ``limit`` and ``filter`` in prose; these tests adhere to the
SDK signature.
"""

from __future__ import annotations

import math

import pytest

from amkb.errors import EInvalid
from amkb.filters import Eq
from amkb.store import Store
from amkb.types import KIND_CONCEPT, LAYER_CONCEPT, Actor


# ============================================================================
# retrieve
# ============================================================================


def test_L4b_retrieve_01_hit_carries_score(store: Store, actor: Actor) -> None:
    """L4b.retrieve.01 — Every hit's score is null or finite float."""
    with store.begin(tag="t", actor=actor) as tx:
        for i in range(3):
            tx.create(kind=KIND_CONCEPT, layer=LAYER_CONCEPT, content=f"widget {i}")
        tx.commit()
    hits = store.retrieve("widget", k=5)
    assert len(hits) >= 1
    for h in hits:
        assert h.score is None or (
            isinstance(h.score, float) and math.isfinite(h.score)
        )


def test_L4b_retrieve_02_score_ordering_monotone(store: Store, actor: Actor) -> None:
    """L4b.retrieve.02 — When scores are non-null, list is ordered descending."""
    with store.begin(tag="t", actor=actor) as tx:
        tx.create(kind=KIND_CONCEPT, layer=LAYER_CONCEPT, content="alpha")
        tx.create(kind=KIND_CONCEPT, layer=LAYER_CONCEPT, content="alpha alpha")
        tx.create(kind=KIND_CONCEPT, layer=LAYER_CONCEPT, content="alpha alpha alpha")
        tx.commit()
    hits = store.retrieve("alpha")
    scored = [h for h in hits if h.score is not None]
    if len(scored) < 2:
        pytest.skip("impl returned <2 scored hits; ordering is trivially true")
    for prev, cur in zip(scored, scored[1:]):
        assert prev.score >= cur.score


def test_L4b_retrieve_03_limit_and_filter(store: Store, actor: Actor) -> None:
    """L4b.retrieve.03 — limit k and filter are both honored."""
    with store.begin(tag="t", actor=actor) as tx:
        for i in range(5):
            tx.create(
                kind=KIND_CONCEPT,
                layer=LAYER_CONCEPT,
                content=f"widget {i}",
                attrs={"bucket": "keep"},
            )
        for i in range(3):
            tx.create(
                kind=KIND_CONCEPT,
                layer=LAYER_CONCEPT,
                content=f"widget drop {i}",
                attrs={"bucket": "drop"},
            )
        tx.commit()
    hits = store.retrieve("widget", k=2, filters=Eq(key="bucket", value="keep"))
    assert len(hits) <= 2
    for h in hits:
        node = store.get_node(h.ref)
        assert node.attrs.get("bucket") == "keep"


def test_L4b_retrieve_04_non_positive_limit_rejected(store: Store, actor: Actor) -> None:
    """L4b.retrieve.04 — k=0 or negative raises E_INVALID."""
    with pytest.raises(EInvalid):
        store.retrieve("anything", k=0)
    with pytest.raises(EInvalid):
        store.retrieve("anything", k=-1)


def test_L4b_retrieve_05_empty_store_returns_empty(store: Store, actor: Actor) -> None:
    """L4b.retrieve.05 — retrieve on an empty store returns []."""
    assert store.retrieve("anything") == []


def test_L4b_retrieve_06_unsupported_filter_operator(store: Store, actor: Actor) -> None:
    """L4b.retrieve.06 — Unknown filter AST node raises E_INVALID.

    The SDK ``Filter`` type is a closed algebra (Eq/In/Range/And/Or/Not).
    Passing an object that is not one of these variants MUST be
    rejected with E_INVALID (the Store is free to reject earlier at
    type-check time, but a runtime check is also valid).
    """
    with store.begin(tag="t", actor=actor) as tx:
        tx.create(kind=KIND_CONCEPT, layer=LAYER_CONCEPT, content="alpha")
        tx.commit()

    class BogusFilter:
        key = "x"
        value = 1

    with pytest.raises(EInvalid):
        store.retrieve("alpha", filters=BogusFilter())  # type: ignore[arg-type]


# ============================================================================
# determinism
# ============================================================================


def test_L4b_retrieve_07_repeated_call_stability(store: Store, actor: Actor) -> None:
    """L4b.retrieve.07 — Two identical retrieve calls return the same ordered list."""
    with store.begin(tag="t", actor=actor) as tx:
        for i in range(5):
            tx.create(
                kind=KIND_CONCEPT, layer=LAYER_CONCEPT, content=f"alpha beta {i}"
            )
        tx.commit()
    first = store.retrieve("alpha", k=3)
    second = store.retrieve("alpha", k=3)
    assert [h.ref for h in first] == [h.ref for h in second]
