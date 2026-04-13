"""Unit tests for the pure amkb.lineage helpers."""

from __future__ import annotations

from amkb.lineage import ancestors, would_cycle
from amkb.refs import NodeRef


def _preds(graph: dict[NodeRef, tuple[NodeRef, ...]]):
    return lambda ref: graph.get(ref, ())


def test_ancestors_empty() -> None:
    assert ancestors(NodeRef("x"), _preds({})) == set()


def test_ancestors_linear_chain() -> None:
    a, b, c = NodeRef("a"), NodeRef("b"), NodeRef("c")
    graph = {c: (b,), b: (a,)}
    assert ancestors(c, _preds(graph)) == {a, b}


def test_ancestors_diamond_dedups() -> None:
    a, b, c, d = NodeRef("a"), NodeRef("b"), NodeRef("c"), NodeRef("d")
    graph = {d: (b, c), b: (a,), c: (a,)}
    assert ancestors(d, _preds(graph)) == {a, b, c}


def test_ancestors_self_cycle_tolerated() -> None:
    a = NodeRef("a")
    graph = {a: (a,)}
    # Must not loop forever.
    assert ancestors(a, _preds(graph)) == {a}


def test_would_cycle_none_for_unrelated() -> None:
    a, b = NodeRef("a"), NodeRef("b")
    assert would_cycle([a, b], _preds({})) is None


def test_would_cycle_detects_ancestor_sibling() -> None:
    a, m = NodeRef("a"), NodeRef("m")
    graph = {m: (a,)}  # m already has a as ancestor
    offender = would_cycle([m, a], _preds(graph))
    assert offender == a


def test_would_cycle_transitive() -> None:
    a, b, m = NodeRef("a"), NodeRef("b"), NodeRef("m")
    graph = {m: (b,), b: (a,)}
    offender = would_cycle([m, a], _preds(graph))
    assert offender == a
