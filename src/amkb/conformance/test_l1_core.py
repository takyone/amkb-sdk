"""Executable L1 (Core) conformance tests.

Mirrors ``amkb-spec/conformance/L1-core.md``. Each test function is
named after the matrix ID (``L1.area.seq``) so failures trace back to
the spec row one-to-one.

The tests request a ``store`` fixture (provided by the implementation
under test) and an ``actor`` fixture (provided by
``amkb.conformance.fixtures`` with a default implementation).
"""

from __future__ import annotations

import pytest

from amkb.errors import (
    ECrossLayerInvalid,
    EEmptyContent,
    ESelfLoop,
    ETransactionClosed,
)
from amkb.store import Store
from amkb.types import (
    KIND_CONCEPT,
    KIND_SOURCE,
    LAYER_CONCEPT,
    LAYER_SOURCE,
    Actor,
)


# ============================================================================
# create
# ============================================================================


def test_L1_create_01_concept_with_content(store: Store, actor: Actor) -> None:
    """L1.create.01 — Concept Node with non-empty content is created and visible."""
    with store.begin(tag="t", actor=actor) as tx:
        ref = tx.create(kind=KIND_CONCEPT, layer=LAYER_CONCEPT, content="hello")
        tx.commit()
    node = store.get_node(ref)
    assert node.content == "hello"
    assert node.kind == KIND_CONCEPT
    assert node.layer == LAYER_CONCEPT
    assert node.state == "live"


def test_L1_create_02_empty_content_rejected(store: Store, actor: Actor) -> None:
    """L1.create.02 — Creating a concept Node with empty content raises E_EMPTY_CONTENT."""
    with store.begin(tag="t", actor=actor) as tx:
        with pytest.raises(EEmptyContent):
            tx.create(kind=KIND_CONCEPT, layer=LAYER_CONCEPT, content="")
        tx.abort()


def test_L1_create_03_cross_layer_violation_rejected(store: Store, actor: Actor) -> None:
    """L1.create.03 — Reserved kind with wrong layer raises E_CROSS_LAYER_INVALID."""
    with store.begin(tag="t", actor=actor) as tx:
        with pytest.raises(ECrossLayerInvalid):
            tx.create(kind=KIND_SOURCE, layer=LAYER_CONCEPT, content="x")
        tx.abort()


def test_L1_create_04_edge_between_live_nodes(store: Store, actor: Actor) -> None:
    """L1.create.04 — An Edge between two live Nodes is created and visible."""
    with store.begin(tag="t", actor=actor) as tx:
        a = tx.create(kind=KIND_CONCEPT, layer=LAYER_CONCEPT, content="A")
        b = tx.create(kind=KIND_CONCEPT, layer=LAYER_CONCEPT, content="B")
        e = tx.link(a, b, rel="relates_to")
        tx.commit()
    edge = store.get_edge(e)
    assert edge.src == a
    assert edge.dst == b
    assert edge.rel == "relates_to"
    assert edge.state == "live"


def test_L1_create_05_self_loop_rejected(store: Store, actor: Actor) -> None:
    """L1.create.05 — An Edge with src == dst raises E_SELF_LOOP."""
    with store.begin(tag="t", actor=actor) as tx:
        a = tx.create(kind=KIND_CONCEPT, layer=LAYER_CONCEPT, content="A")
        with pytest.raises(ESelfLoop):
            tx.link(a, a, rel="relates_to")
        tx.abort()


# ============================================================================
# retire
# ============================================================================


def test_L1_retire_01_retire_live_node(store: Store, actor: Actor) -> None:
    """L1.retire.01 — Retiring a live Node tombstones it and excludes it from retrieve."""
    with store.begin(tag="t", actor=actor) as tx:
        a = tx.create(kind=KIND_CONCEPT, layer=LAYER_CONCEPT, content="retire me")
        tx.commit()
    with store.begin(tag="t2", actor=actor) as tx:
        tx.retire(a, reason="test")
        tx.commit()
    node = store.get_node(a)
    assert node.state == "retired"
    assert node.retired_at is not None
    # default retrieve MUST NOT return retired nodes
    hits = store.retrieve("retire me")
    assert all(h.ref != a for h in hits)


def test_L1_retire_02_retire_already_retired_is_noop(store: Store, actor: Actor) -> None:
    """L1.retire.02 — Retiring an already-retired Node is a no-op and emits no event."""
    with store.begin(tag="t", actor=actor) as tx:
        a = tx.create(kind=KIND_CONCEPT, layer=LAYER_CONCEPT, content="A")
        tx.commit()
    with store.begin(tag="t2", actor=actor) as tx:
        tx.retire(a, reason="first")
        tx.commit()
    # Second retire must succeed and produce a ChangeSet with no
    # node.retired events targeting `a`.
    with store.begin(tag="t3", actor=actor) as tx:
        tx.retire(a, reason="again")
        cs = tx.commit()
    retire_events = [
        e for e in cs.events if e.kind == "node.retired" and e.target == a
    ]
    assert retire_events == []


# ============================================================================
# retrieve
# ============================================================================


def test_L1_retrieve_01_sources_excluded(store: Store, actor: Actor) -> None:
    """L1.retrieve.01 — retrieve MUST NOT return any Node with kind=source."""
    with store.begin(tag="t", actor=actor) as tx:
        tx.create(kind=KIND_CONCEPT, layer=LAYER_CONCEPT, content="alpha topic")
        tx.create(
            kind=KIND_SOURCE,
            layer=LAYER_SOURCE,
            content="alpha topic attestation",
        )
        tx.commit()
    hits = store.retrieve("alpha")
    for h in hits:
        node = store.get_node(h.ref)
        assert node.kind != KIND_SOURCE


def test_L1_retrieve_02_limit_respected(store: Store, actor: Actor) -> None:
    """L1.retrieve.02 — retrieve(k=n) returns at most n hits."""
    with store.begin(tag="t", actor=actor) as tx:
        for i in range(5):
            tx.create(
                kind=KIND_CONCEPT,
                layer=LAYER_CONCEPT,
                content=f"concept item {i} widget",
            )
        tx.commit()
    hits = store.retrieve("widget", k=3)
    assert len(hits) <= 3


def test_L1_retrieve_03_retired_excluded(store: Store, actor: Actor) -> None:
    """L1.retrieve.03 — Retired Nodes MUST NOT appear in default retrieve output."""
    with store.begin(tag="t", actor=actor) as tx:
        a = tx.create(kind=KIND_CONCEPT, layer=LAYER_CONCEPT, content="widget apple")
        tx.create(kind=KIND_CONCEPT, layer=LAYER_CONCEPT, content="widget banana")
        tx.commit()
    with store.begin(tag="t2", actor=actor) as tx:
        tx.retire(a, reason="drop")
        tx.commit()
    hits = store.retrieve("widget")
    assert all(h.ref != a for h in hits)


# ============================================================================
# events
# ============================================================================


def test_L1_events_01_changeset_per_commit(store: Store, actor: Actor) -> None:
    """L1.events.01 — Each committed transaction produces exactly one ChangeSet."""
    before = len(store.history())
    with store.begin(tag="t", actor=actor) as tx:
        tx.create(kind=KIND_CONCEPT, layer=LAYER_CONCEPT, content="a")
        tx.create(kind=KIND_CONCEPT, layer=LAYER_CONCEPT, content="b")
        cs = tx.commit()
    after = len(store.history())
    assert after == before + 1
    assert len(cs.events) == 2


def test_L1_events_02_aborted_tx_emits_nothing(store: Store, actor: Actor) -> None:
    """L1.events.02 — An aborted transaction MUST NOT produce any event."""
    before_events = list(store.events())
    before_cs = len(store.history())
    with store.begin(tag="t", actor=actor) as tx:
        tx.create(kind=KIND_CONCEPT, layer=LAYER_CONCEPT, content="discarded")
        tx.abort()
    after_events = list(store.events())
    after_cs = len(store.history())
    assert len(after_events) == len(before_events)
    assert after_cs == before_cs


def test_L1_events_04_causal_order_across_changesets(store: Store, actor: Actor) -> None:
    """L1.events.04 — Events from tx A precede all events from tx B if A < B."""
    with store.begin(tag="A", actor=actor) as tx:
        tx.create(kind=KIND_CONCEPT, layer=LAYER_CONCEPT, content="A1")
        tx.create(kind=KIND_CONCEPT, layer=LAYER_CONCEPT, content="A2")
        cs_a = tx.commit()
    with store.begin(tag="B", actor=actor) as tx:
        tx.create(kind=KIND_CONCEPT, layer=LAYER_CONCEPT, content="B1")
        cs_b = tx.commit()
    all_events = list(store.events())
    a_indices = [i for i, e in enumerate(all_events) if e in cs_a.events]
    b_indices = [i for i, e in enumerate(all_events) if e in cs_b.events]
    assert max(a_indices) < min(b_indices)


def test_L1_events_05_within_changeset_order_preserved(
    store: Store, actor: Actor
) -> None:
    """L1.events.05 — Events within a ChangeSet follow the issue order."""
    with store.begin(tag="t", actor=actor) as tx:
        n1 = tx.create(kind=KIND_CONCEPT, layer=LAYER_CONCEPT, content="first")
        n2 = tx.create(kind=KIND_CONCEPT, layer=LAYER_CONCEPT, content="second")
        n3 = tx.create(kind=KIND_CONCEPT, layer=LAYER_CONCEPT, content="third")
        cs = tx.commit()
    targets = [e.target for e in cs.events]
    assert targets == [n1, n2, n3]


# ============================================================================
# transactions
# ============================================================================


def test_L1_tx_01_op_on_closed_tx_rejected(store: Store, actor: Actor) -> None:
    """L1.tx.01 — Issuing an operation on a committed tx raises E_TRANSACTION_CLOSED."""
    tx = store.begin(tag="t", actor=actor)
    tx.create(kind=KIND_CONCEPT, layer=LAYER_CONCEPT, content="x")
    tx.commit()
    with pytest.raises(ETransactionClosed):
        tx.create(kind=KIND_CONCEPT, layer=LAYER_CONCEPT, content="y")


# ============================================================================
# history
# ============================================================================


def test_L1_history_01_changeset_by_tag(store: Store, actor: Actor) -> None:
    """L1.history.01 — A committed ChangeSet is retrievable by its transaction tag."""
    with store.begin(tag="ingest/batch-1", actor=actor) as tx:
        tx.create(kind=KIND_CONCEPT, layer=LAYER_CONCEPT, content="in batch")
        tx.commit()
    refs = store.history(tag="ingest/batch-1")
    assert len(refs) == 1
    cs = store.get_changeset(refs[0])
    assert cs.tag == "ingest/batch-1"
    assert len(cs.events) == 1
