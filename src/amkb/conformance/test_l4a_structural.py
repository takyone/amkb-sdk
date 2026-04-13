"""Executable L4a (Structural retrieval) conformance tests.

Mirrors ``amkb-spec/conformance/L4a-structural.md``. L4a adds
structural graph retrieval: depth-bounded neighbor traversal,
direction/relation filters, retired-edge exclusion, and the
invariant that Nodes with ``kind="source"`` MUST NOT appear in walk
results.
"""

from __future__ import annotations

import pytest

from amkb.errors import EInvalid
from amkb.store import Store
from amkb.types import (
    KIND_CONCEPT,
    KIND_SOURCE,
    LAYER_CONCEPT,
    LAYER_SOURCE,
    REL_ATTESTED_BY,
    REL_DERIVED_FROM,
    REL_RELATES_TO,
    Actor,
)


# ============================================================================
# neighbors
# ============================================================================


def test_L4a_neighbors_01_depth_one(store: Store, actor: Actor) -> None:
    """L4a.neighbors.01 — depth=1 returns all direct neighbors."""
    with store.begin(tag="t", actor=actor) as tx:
        n = tx.create(kind=KIND_CONCEPT, layer=LAYER_CONCEPT, content="n")
        a = tx.create(kind=KIND_CONCEPT, layer=LAYER_CONCEPT, content="a")
        b = tx.create(kind=KIND_CONCEPT, layer=LAYER_CONCEPT, content="b")
        c = tx.create(kind=KIND_CONCEPT, layer=LAYER_CONCEPT, content="c")
        tx.link(n, a, rel=REL_RELATES_TO)
        tx.link(n, b, rel=REL_RELATES_TO)
        tx.link(n, c, rel=REL_RELATES_TO)
        tx.commit()
    result = set(store.neighbors(n, depth=1))
    assert result == {a, b, c}


def test_L4a_neighbors_02_depth_bound(store: Store, actor: Actor) -> None:
    """L4a.neighbors.02 — depth=k excludes Nodes farther than k hops."""
    with store.begin(tag="t", actor=actor) as tx:
        n = tx.create(kind=KIND_CONCEPT, layer=LAYER_CONCEPT, content="n")
        a = tx.create(kind=KIND_CONCEPT, layer=LAYER_CONCEPT, content="a")
        b = tx.create(kind=KIND_CONCEPT, layer=LAYER_CONCEPT, content="b")
        c = tx.create(kind=KIND_CONCEPT, layer=LAYER_CONCEPT, content="c")
        tx.link(n, a, rel=REL_RELATES_TO)
        tx.link(a, b, rel=REL_RELATES_TO)
        tx.link(b, c, rel=REL_RELATES_TO)
        tx.commit()
    result = set(store.neighbors(n, depth=2))
    assert a in result and b in result
    assert c not in result


def test_L4a_neighbors_03_invalid_depth_rejected(store: Store, actor: Actor) -> None:
    """L4a.neighbors.03 — depth=0 or negative raises E_INVALID."""
    with store.begin(tag="t", actor=actor) as tx:
        n = tx.create(kind=KIND_CONCEPT, layer=LAYER_CONCEPT, content="n")
        tx.commit()
    with pytest.raises(EInvalid):
        store.neighbors(n, depth=0)
    with pytest.raises(EInvalid):
        store.neighbors(n, depth=-1)


def test_L4a_neighbors_04_relation_filter(store: Store, actor: Actor) -> None:
    """L4a.neighbors.04 — rel filter returns only matching edges."""
    with store.begin(tag="t", actor=actor) as tx:
        n = tx.create(kind=KIND_CONCEPT, layer=LAYER_CONCEPT, content="n")
        a = tx.create(kind=KIND_CONCEPT, layer=LAYER_CONCEPT, content="a")
        s = tx.create(kind=KIND_SOURCE, layer=LAYER_SOURCE, content="s")
        tx.link(n, a, rel=REL_RELATES_TO)
        tx.link(n, s, rel=REL_DERIVED_FROM)
        tx.commit()
    result = set(store.neighbors(n, rel=REL_RELATES_TO, depth=1))
    assert result == {a}


def test_L4a_neighbors_05_retired_edges_excluded(store: Store, actor: Actor) -> None:
    """L4a.neighbors.05 — Retired edges do not contribute to neighbor results."""
    with store.begin(tag="t", actor=actor) as tx:
        n = tx.create(kind=KIND_CONCEPT, layer=LAYER_CONCEPT, content="n")
        a = tx.create(kind=KIND_CONCEPT, layer=LAYER_CONCEPT, content="a")
        b = tx.create(kind=KIND_CONCEPT, layer=LAYER_CONCEPT, content="b")
        e_live = tx.link(n, a, rel=REL_RELATES_TO)
        e_dead = tx.link(n, b, rel=REL_RELATES_TO)
        tx.commit()
    with store.begin(tag="t2", actor=actor) as tx:
        tx.unlink(e_dead, reason="drop")
        tx.commit()
    assert e_live  # silence unused
    result = set(store.neighbors(n, depth=1))
    assert result == {a}


# ============================================================================
# traversal correctness
# ============================================================================


def test_L4a_walk_01_no_duplicate_nodes(store: Store, actor: Actor) -> None:
    """L4a.walk.01 — Diamond walk returns each Node once."""
    with store.begin(tag="t", actor=actor) as tx:
        n = tx.create(kind=KIND_CONCEPT, layer=LAYER_CONCEPT, content="n")
        a = tx.create(kind=KIND_CONCEPT, layer=LAYER_CONCEPT, content="a")
        b = tx.create(kind=KIND_CONCEPT, layer=LAYER_CONCEPT, content="b")
        c = tx.create(kind=KIND_CONCEPT, layer=LAYER_CONCEPT, content="c")
        tx.link(n, a, rel=REL_RELATES_TO)
        tx.link(n, b, rel=REL_RELATES_TO)
        tx.link(a, c, rel=REL_RELATES_TO)
        tx.link(b, c, rel=REL_RELATES_TO)
        tx.commit()
    result = store.neighbors(n, depth=2)
    assert result.count(c) == 1


def test_L4a_walk_02_source_nodes_excluded(store: Store, actor: Actor) -> None:
    """L4a.walk.02 — Traversal MUST NOT return Nodes with kind=source."""
    with store.begin(tag="t", actor=actor) as tx:
        n = tx.create(kind=KIND_CONCEPT, layer=LAYER_CONCEPT, content="n")
        s = tx.create(kind=KIND_SOURCE, layer=LAYER_SOURCE, content="s")
        tx.link(n, s, rel=REL_ATTESTED_BY)
        tx.commit()
    result = store.neighbors(n, depth=1)
    assert s not in result
