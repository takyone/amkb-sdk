"""Unit tests for amkb.snapshots pure builders."""

from __future__ import annotations

from amkb.refs import EdgeRef, NodeRef
from amkb.snapshots import edge_snapshot, node_snapshot
from amkb.types import (
    KIND_CONCEPT,
    LAYER_CONCEPT,
    REL_RELATES_TO,
    Edge,
    Node,
    compute_content_hash,
)


def _node(content: str = "hello") -> Node:
    return Node(
        ref=NodeRef("n:1"),
        kind=KIND_CONCEPT,
        layer=LAYER_CONCEPT,
        content=content,
        attrs={"foo": "bar"},
        state="live",
        created_at=10,
        updated_at=20,
    )


def _edge() -> Edge:
    return Edge(
        ref=EdgeRef("e:1"),
        rel=REL_RELATES_TO,
        src=NodeRef("a"),
        dst=NodeRef("b"),
        attrs={"w": 1},
        state="live",
        created_at=5,
    )


def test_node_snapshot_shape() -> None:
    snap = node_snapshot(_node("hello"))
    assert snap["ref"] == "n:1"
    assert snap["kind"] == KIND_CONCEPT
    assert snap["layer"] == LAYER_CONCEPT
    assert snap["content"] == "hello"
    assert snap["content_hash"] == compute_content_hash("hello")
    assert snap["attrs"] == {"foo": "bar"}
    assert snap["state"] == "live"
    assert snap["created_at"] == 10
    assert snap["updated_at"] == 20
    assert snap["retired_at"] is None


def test_node_snapshot_attrs_deepcopied() -> None:
    n = _node()
    snap = node_snapshot(n)
    snap["attrs"]["foo"] = "mutated"
    assert n.attrs["foo"] == "bar"


def test_edge_snapshot_shape() -> None:
    snap = edge_snapshot(_edge())
    assert snap["ref"] == "e:1"
    assert snap["rel"] == REL_RELATES_TO
    assert snap["src"] == "a"
    assert snap["dst"] == "b"
    assert snap["attrs"] == {"w": 1}
    assert snap["state"] == "live"
    assert snap["created_at"] == 5
    assert snap["retired_at"] is None
