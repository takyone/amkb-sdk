"""Pure lineage graph walks for Node predecessor chains.

AMKB tracks lineage as a per-Node tuple of predecessor refs
(populated by merge and single-node rewrite). Several correctness
checks traverse that chain: "is X an ancestor of Y?", "would adding
predecessors P to node X create a cycle?".

These helpers are storage-agnostic: callers pass a
``predecessors_of`` callable that maps a ``NodeRef`` to its
immediate predecessors. Backends with in-memory indexes, SQL tables,
or graph stores can all plug in.
"""

from __future__ import annotations

from typing import Callable, Iterable

from amkb.refs import NodeRef

PredecessorsOf = Callable[[NodeRef], Iterable[NodeRef]]
"""A function that returns the immediate predecessors of a Node."""


def ancestors(ref: NodeRef, predecessors_of: PredecessorsOf) -> set[NodeRef]:
    """Return the transitive closure of predecessors of ``ref``.

    ``ref`` itself is NOT included in the result. Cycles in the input
    graph are tolerated — each Node is visited at most once.
    """
    out: set[NodeRef] = set()
    stack: list[NodeRef] = list(predecessors_of(ref))
    while stack:
        cur = stack.pop()
        if cur in out:
            continue
        out.add(cur)
        stack.extend(predecessors_of(cur))
    return out


def would_cycle(
    refs: Iterable[NodeRef], predecessors_of: PredecessorsOf
) -> NodeRef | None:
    """Check whether any ref in ``refs`` is an ancestor of another.

    Used by merge to reject lineage cycles before persisting the new
    predecessor tuple. Returns the first offending ref found, or
    ``None`` if no cycle would be created. The caller is responsible
    for raising ``ELineageCycle`` with a descriptive message.
    """
    ref_list = list(refs)
    for i, ri in enumerate(ref_list):
        ri_ancestors = ancestors(ri, predecessors_of)
        for j, rj in enumerate(ref_list):
            if i == j:
                continue
            if rj in ri_ancestors:
                return rj
    return None


__all__ = ["PredecessorsOf", "ancestors", "would_cycle"]
