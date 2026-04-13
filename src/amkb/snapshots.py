"""Pure snapshot builders for Event.before / Event.after payloads.

Events carry ``before`` and ``after`` as plain dicts so the log stays
serializable without leaking Store-internal types. Every Store
implementation produces the same shape; this module is the canonical
source of that shape. See spec 04-events §4.1.
"""

from __future__ import annotations

import copy
from typing import Any

from amkb.types import Edge, Node, compute_content_hash


def node_snapshot(node: Node) -> dict[str, Any]:
    """Return the Event payload shape for a Node at a point in time."""
    return {
        "ref": node.ref,
        "kind": node.kind,
        "layer": node.layer,
        "content": node.content,
        "content_hash": compute_content_hash(node.content),
        "attrs": copy.deepcopy(node.attrs),
        "state": node.state,
        "created_at": node.created_at,
        "updated_at": node.updated_at,
        "retired_at": node.retired_at,
    }


def edge_snapshot(edge: Edge) -> dict[str, Any]:
    """Return the Event payload shape for an Edge at a point in time."""
    return {
        "ref": edge.ref,
        "rel": edge.rel,
        "src": edge.src,
        "dst": edge.dst,
        "attrs": copy.deepcopy(edge.attrs),
        "state": edge.state,
        "created_at": edge.created_at,
        "retired_at": edge.retired_at,
    }


__all__ = ["node_snapshot", "edge_snapshot"]
