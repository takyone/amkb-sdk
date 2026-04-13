"""Executable L3 (Transactional) conformance tests.

Mirrors ``amkb-spec/conformance/L3-transactional.md``. L3 adds full
transactional guarantees: concurrency control, revertability, and
commit-time invariant enforcement. L3 inherits all L1 and L2
requirements.

Several L3 requirements demand capabilities (MVCC, resurrection,
commit-time constraint checking) that not every Store can offer.
Tests gate on capability flags exposed by the implementation:

* ``supports_concurrency_detection`` — the Store raises
  ``E_CONCURRENT_MODIFICATION`` when two tx commit conflicting
  mutations from the same snapshot.
* ``supports_merge_revert`` — ``revert`` of a merge restores the
  source Nodes to ``live``.
* ``supports_revert_conflict_detection`` — ``revert`` detects that
  the target has been diverged by a later transaction and raises
  ``E_CONFLICT``.
* ``supports_commit_time_constraints`` — the Store validates
  protocol invariants at commit and raises ``E_CONSTRAINT``.

An implementation that wants to advertise L3 conformance MUST set
these flags to ``True`` on its Store class.
"""

from __future__ import annotations

import pytest

from amkb.errors import (
    EChangesetNotFound,
    EConcurrentModification,
    EConflict,
    EConstraint,
)
from amkb.store import Store
from amkb.types import KIND_CONCEPT, LAYER_CONCEPT, Actor


def _cap(store: Store, name: str) -> bool:
    return bool(getattr(store, name, False))


# ============================================================================
# concurrency
# ============================================================================


def test_L3_concurrent_01_modification_detected(store: Store, actor: Actor) -> None:
    """L3.concurrent.01 — Conflicting concurrent commits: second raises E_CONCURRENT_MODIFICATION."""
    if not _cap(store, "supports_concurrency_detection"):
        pytest.skip("store does not advertise supports_concurrency_detection")
    with store.begin(tag="seed", actor=actor) as tx:
        a = tx.create(kind=KIND_CONCEPT, layer=LAYER_CONCEPT, content="seed")
        tx.commit()
    t1 = store.begin(tag="t1", actor=actor)
    t2 = store.begin(tag="t2", actor=actor)
    t1.rewrite(a, content="from-t1", reason="r")
    t2.rewrite(a, content="from-t2", reason="r")
    t1.commit()
    with pytest.raises(EConcurrentModification):
        t2.commit()


def test_L3_concurrent_02_disjoint_both_commit(store: Store, actor: Actor) -> None:
    """L3.concurrent.02 — Concurrent transactions on disjoint Nodes both commit."""
    with store.begin(tag="seed", actor=actor) as tx:
        a = tx.create(kind=KIND_CONCEPT, layer=LAYER_CONCEPT, content="a")
        b = tx.create(kind=KIND_CONCEPT, layer=LAYER_CONCEPT, content="b")
        tx.commit()
    t1 = store.begin(tag="t1", actor=actor)
    t2 = store.begin(tag="t2", actor=actor)
    t1.rewrite(a, content="a2", reason="r")
    t2.rewrite(b, content="b2", reason="r")
    cs1 = t1.commit()
    cs2 = t2.commit()
    assert cs1.ref != cs2.ref
    assert store.get_node(a).content == "a2"
    assert store.get_node(b).content == "b2"


# ============================================================================
# revert
# ============================================================================


def test_L3_revert_01_of_simple_creation(store: Store, actor: Actor) -> None:
    """L3.revert.01 — Reverting a creation-only tx retires the created Node."""
    with store.begin(tag="create-a", actor=actor) as tx:
        a = tx.create(kind=KIND_CONCEPT, layer=LAYER_CONCEPT, content="a")
        tx.commit()
    store.revert("create-a", reason="rollback", actor=actor)
    assert store.get_node(a).state == "retired"


def test_L3_revert_02_of_merge(store: Store, actor: Actor) -> None:
    """L3.revert.02 — Reverting a merge retires the merged Node and re-lives sources."""
    if not _cap(store, "supports_merge_revert"):
        pytest.skip("store does not advertise supports_merge_revert")
    with store.begin(tag="seed", actor=actor) as tx:
        a = tx.create(kind=KIND_CONCEPT, layer=LAYER_CONCEPT, content="a")
        b = tx.create(kind=KIND_CONCEPT, layer=LAYER_CONCEPT, content="b")
        tx.commit()
    with store.begin(tag="merge", actor=actor) as tx:
        m = tx.merge([a, b], content="ab", reason="dedup")
        tx.commit()
    store.revert("merge", reason="rollback", actor=actor)
    assert store.get_node(m).state == "retired"
    assert store.get_node(a).state == "live"
    assert store.get_node(b).state == "live"


def test_L3_revert_03_conflict_raises(store: Store, actor: Actor) -> None:
    """L3.revert.03 — Revert of a tx whose effects have been diverged raises E_CONFLICT."""
    if not _cap(store, "supports_revert_conflict_detection"):
        pytest.skip("store does not advertise supports_revert_conflict_detection")
    with store.begin(tag="T1", actor=actor) as tx:
        a = tx.create(kind=KIND_CONCEPT, layer=LAYER_CONCEPT, content="v1")
        tx.commit()
    with store.begin(tag="T2", actor=actor) as tx:
        tx.rewrite(a, content="v2", reason="later")
        tx.commit()
    with pytest.raises(EConflict):
        store.revert("T1", reason="rollback", actor=actor)


def test_L3_revert_04_unknown_tag(store: Store, actor: Actor) -> None:
    """L3.revert.04 — Reverting a non-existent tag raises E_CHANGESET_NOT_FOUND."""
    with pytest.raises(EChangesetNotFound):
        store.revert("does-not-exist", reason="oops", actor=actor)


# ============================================================================
# constraints
# ============================================================================


def test_L3_constraint_01_commit_time_invariant(store: Store, actor: Actor) -> None:
    """L3.constraint.01 — Commit that would violate a protocol invariant raises E_CONSTRAINT."""
    if not _cap(store, "supports_commit_time_constraints"):
        pytest.skip("store does not advertise supports_commit_time_constraints")
    # Implementations that opt-in MUST define how to set up a required
    # reserved-attribute dependency via their fixture layer. The generic
    # shape of the test is: create `a` and `b` such that `a` requires `b`;
    # retiring `b` inside a transaction and committing MUST raise
    # E_CONSTRAINT and leave `b` live.
    setup = getattr(store, "setup_required_attribute_pair", None)
    if setup is None:
        pytest.skip("store did not provide setup_required_attribute_pair helper")
    a, b = setup(actor=actor)
    with store.begin(tag="break", actor=actor) as tx:
        tx.retire(b, reason="break")
        with pytest.raises(EConstraint):
            tx.commit()
    assert store.get_node(b).state == "live"
