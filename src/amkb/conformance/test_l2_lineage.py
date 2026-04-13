"""Executable L2 (Lineage) conformance tests.

Mirrors ``amkb-spec/conformance/L2-lineage.md``. L2 adds rewrite
predecessor tracking, merge-with-lineage, lineage queries, cycle
prevention, and retention of merge events while successors remain
live. L2 inherits all L1 requirements.
"""

from __future__ import annotations

import pytest

from amkb.errors import EMergeConflict, ENodeAlreadyRetired
from amkb.store import Store
from amkb.types import (
    KIND_CATEGORY,
    KIND_CONCEPT,
    LAYER_CATEGORY,
    LAYER_CONCEPT,
    Actor,
)


# ============================================================================
# rewrite
# ============================================================================


def test_L2_rewrite_01_updated_at_advances(store: Store, actor: Actor) -> None:
    """L2.rewrite.01 — After rewrite, updated_at advances and content changes.

    The SDK's predecessor chain is exposed through merge meta; a
    single-node rewrite produces a node.rewritten event whose `before`
    and `after` snapshots carry the prior and new content. Testing the
    event is the implementation-independent way to verify predecessor
    visibility.
    """
    with store.begin(tag="t", actor=actor) as tx:
        a = tx.create(kind=KIND_CONCEPT, layer=LAYER_CONCEPT, content="v1")
        tx.commit()
    before = store.get_node(a)
    with store.begin(tag="t2", actor=actor) as tx:
        tx.rewrite(a, content="v2", reason="refinement")
        cs = tx.commit()
    after = store.get_node(a)
    assert after.content == "v2"
    assert after.updated_at >= before.updated_at
    rewrite_events = [e for e in cs.events if e.kind == "node.rewritten"]
    assert len(rewrite_events) == 1
    ev = rewrite_events[0]
    assert ev.before is not None and ev.before.get("content") == "v1"
    assert ev.after is not None and ev.after.get("content") == "v2"


def test_L2_rewrite_02_rewrite_retired_rejected(store: Store, actor: Actor) -> None:
    """L2.rewrite.02 — Rewriting a retired Node raises E_NODE_ALREADY_RETIRED."""
    with store.begin(tag="t", actor=actor) as tx:
        a = tx.create(kind=KIND_CONCEPT, layer=LAYER_CONCEPT, content="x")
        tx.commit()
    with store.begin(tag="t2", actor=actor) as tx:
        tx.retire(a, reason="drop")
        tx.commit()
    with store.begin(tag="t3", actor=actor) as tx:
        with pytest.raises(ENodeAlreadyRetired):
            tx.rewrite(a, content="y", reason="r")
        tx.abort()


# ============================================================================
# merge
# ============================================================================


def test_L2_merge_01_k_nodes_into_one(store: Store, actor: Actor) -> None:
    """L2.merge.01 — Merging k live Nodes yields one live + k retired."""
    with store.begin(tag="t", actor=actor) as tx:
        a = tx.create(kind=KIND_CONCEPT, layer=LAYER_CONCEPT, content="alpha")
        b = tx.create(kind=KIND_CONCEPT, layer=LAYER_CONCEPT, content="beta")
        c = tx.create(kind=KIND_CONCEPT, layer=LAYER_CONCEPT, content="gamma")
        tx.commit()
    with store.begin(tag="merge", actor=actor) as tx:
        m = tx.merge(
            [a, b, c],
            content="alpha+beta+gamma",
            reason="dedup",
        )
        tx.commit()
    merged = store.get_node(m)
    assert merged.state == "live"
    for ref in (a, b, c):
        assert store.get_node(ref).state == "retired"


def test_L2_merge_02_kind_mismatch_rejected(store: Store, actor: Actor) -> None:
    """L2.merge.02 — Merging Nodes of differing kind raises E_MERGE_CONFLICT."""
    with store.begin(tag="t", actor=actor) as tx:
        a = tx.create(kind=KIND_CONCEPT, layer=LAYER_CONCEPT, content="x")
        b = tx.create(kind=KIND_CATEGORY, layer=LAYER_CATEGORY, content="y")
        tx.commit()
    with store.begin(tag="merge", actor=actor) as tx:
        with pytest.raises(EMergeConflict):
            tx.merge([a, b], content="xy", reason="bad")
        tx.abort()


def test_L2_merge_03_event_shape(store: Store, actor: Actor) -> None:
    """L2.merge.03 — Merge emits k retire events + 1 merge event with ancestors meta."""
    with store.begin(tag="t", actor=actor) as tx:
        a = tx.create(kind=KIND_CONCEPT, layer=LAYER_CONCEPT, content="a")
        b = tx.create(kind=KIND_CONCEPT, layer=LAYER_CONCEPT, content="b")
        c = tx.create(kind=KIND_CONCEPT, layer=LAYER_CONCEPT, content="c")
        tx.commit()
    with store.begin(tag="merge", actor=actor) as tx:
        m = tx.merge([a, b, c], content="abc", reason="dedup")
        cs = tx.commit()
    retires = [
        e for e in cs.events if e.kind == "node.retired" and e.target in {a, b, c}
    ]
    merges = [e for e in cs.events if e.kind == "node.merged" and e.target == m]
    assert len(retires) == 3
    assert len(merges) == 1
    ancestors = merges[0].meta.get("ancestors")
    assert ancestors is not None
    assert set(ancestors) == {a, b, c}


# ============================================================================
# retention
# ============================================================================


def test_L2_retain_01_merge_events_visible_in_history(store: Store, actor: Actor) -> None:
    """L2.retain.01 — Merge events remain visible via history/events after commit."""
    with store.begin(tag="t", actor=actor) as tx:
        a = tx.create(kind=KIND_CONCEPT, layer=LAYER_CONCEPT, content="p")
        b = tx.create(kind=KIND_CONCEPT, layer=LAYER_CONCEPT, content="q")
        tx.commit()
    with store.begin(tag="merge", actor=actor) as tx:
        tx.merge([a, b], content="pq", reason="r")
        tx.commit()
    merge_cs_refs = store.history(tag="merge")
    assert len(merge_cs_refs) == 1
    cs = store.get_changeset(merge_cs_refs[0])
    merge_events = [e for e in cs.events if e.kind == "node.merged"]
    assert len(merge_events) == 1
