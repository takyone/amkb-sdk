"""A dict-backed in-memory Store implementation.

This implementation exists to exercise the :mod:`amkb.conformance`
suite on a minimal substrate that has **no** storage dependencies —
just Python dicts and lists. It is intentionally kept in the test
tree, not shipped with the package, to reinforce that the SDK itself
is backend-agnostic and that "any mapping is a valid AMKB backend"
is a literal statement.

Scope:

- L1 (Core): create / rewrite / retire / link / unlink / get /
  history / revert / events / begin / commit / abort
- L2 (Lineage): merge, diff, lineage via predecessor chain
- L4a (Structural): find_by_attr, neighbors with depth
- L4b (Intent): retrieve with a trivial substring-match ISF

This is not a production store. It is not concurrent-safe, not
durable across process restarts, and not optimized. It is the
smallest thing that passes the conformance suite.

Durability note: Level B durability in spec §4.4.2 requires events
to be recoverable after store restart. A dict impl cannot satisfy
Level B; the conformance suite's durability test is therefore
skipped for this implementation by marking the store as
``durability_level = "A"``.
"""

from __future__ import annotations

from collections.abc import Iterator
from types import TracebackType
from typing import Any, ClassVar, Literal
from uuid import uuid4

from amkb.errors import (
    EChangesetNotFound,
    EConstraint,
    EEdgeNotFound,
    EInvalid,
    ELineageCycle,
    ENodeAlreadyRetired,
    ENodeNotFound,
    ETransactionClosed,
)  # noqa: F401 — EConstraint used by _apply_inverse
from amkb.filters import Filter, evaluate as filter_evaluate
from amkb.lineage import would_cycle
from amkb.snapshots import edge_snapshot, node_snapshot
from amkb.refs import ActorId, ChangeSetRef, EdgeRef, NodeRef, Timestamp, TransactionRef
from amkb.store import Direction, RetrievalHit
from amkb.types import (
    KIND_CONCEPT,
    KIND_SOURCE,
    Actor,
    ChangeSet,
    Edge,
    Event,
    Node,
)
from amkb.validation import (
    validate_concept_content,
    validate_edge_rel,
    validate_kind_layer,
    validate_merge_uniform,
)


def _new_ref(prefix: str) -> str:
    return f"{prefix}:{uuid4().hex[:12]}"


class DictStore:
    """A dict-backed AMKB store. Satisfies the ``Store`` Protocol structurally."""

    durability_level: ClassVar[Literal["A", "B", "C", "C+"]] = "A"

    def __init__(self) -> None:
        self._clock: int = 0
        self._nodes: dict[NodeRef, Node] = {}
        self._edges: dict[EdgeRef, Edge] = {}
        self._node_predecessors: dict[NodeRef, tuple[NodeRef, ...]] = {}
        self._node_outgoing: dict[NodeRef, set[EdgeRef]] = {}
        self._node_incoming: dict[NodeRef, set[EdgeRef]] = {}
        self._changesets: dict[ChangeSetRef, ChangeSet] = {}
        self._changeset_order: list[ChangeSetRef] = []

    # -- Clock ---------------------------------------------------------

    def _tick(self) -> Timestamp:
        self._clock += 1
        return Timestamp(self._clock)

    # -- Session entry -------------------------------------------------

    def begin(self, *, tag: str, actor: Actor) -> "DictTransaction":
        if not tag:
            raise EInvalid("tag must be non-empty")
        return DictTransaction(self, tag=tag, actor=actor)

    # -- Read-only queries ---------------------------------------------

    def get_node(self, ref: NodeRef) -> Node:
        node = self._nodes.get(ref)
        if node is None:
            raise ENodeNotFound(f"node not found: {ref}", ref=ref)
        return node

    def get_edge(self, ref: EdgeRef) -> Edge:
        edge = self._edges.get(ref)
        if edge is None:
            raise EEdgeNotFound(f"edge not found: {ref}", ref=ref)
        return edge

    def find_by_attr(
        self,
        attributes: dict[str, Any],
        *,
        kind: str | None = None,
        layer: str | None = None,
        include_retired: bool = False,
        limit: int = 100,
    ) -> list[NodeRef]:
        if limit <= 0:
            raise EInvalid("limit must be positive")
        out: list[NodeRef] = []
        for ref, node in self._nodes.items():
            if not include_retired and node.state == "retired":
                continue
            if kind is not None and node.kind != kind:
                continue
            if layer is not None and node.layer != layer:
                continue
            if all(node.attrs.get(k) == v for k, v in attributes.items()):
                out.append(ref)
                if len(out) >= limit:
                    break
        return out

    def neighbors(
        self,
        ref: NodeRef,
        *,
        rel: str | list[str] | None = None,
        direction: Direction = "out",
        depth: int = 1,
        include_retired: bool = False,
        limit: int = 100,
    ) -> list[NodeRef]:
        if depth < 1:
            raise EInvalid("depth must be >= 1")
        if limit <= 0:
            raise EInvalid("limit must be positive")
        if ref not in self._nodes:
            raise ENodeNotFound(f"node not found: {ref}", ref=ref)
        rel_filter: set[str] | None
        if rel is None:
            rel_filter = None
        elif isinstance(rel, str):
            rel_filter = {rel}
        else:
            rel_filter = set(rel)

        seen: set[NodeRef] = {ref}
        frontier: list[NodeRef] = [ref]
        result: list[NodeRef] = []
        for _ in range(depth):
            next_frontier: list[NodeRef] = []
            for cur in frontier:
                edge_refs: set[EdgeRef] = set()
                if direction in ("out", "both"):
                    edge_refs |= self._node_outgoing.get(cur, set())
                if direction in ("in", "both"):
                    edge_refs |= self._node_incoming.get(cur, set())
                for eref in edge_refs:
                    edge = self._edges[eref]
                    if not include_retired and edge.state == "retired":
                        continue
                    if rel_filter is not None and edge.rel not in rel_filter:
                        continue
                    other = edge.dst if edge.src == cur else edge.src
                    if other in seen:
                        continue
                    other_node = self._nodes[other]
                    if not include_retired and other_node.state == "retired":
                        continue
                    if other_node.kind == KIND_SOURCE:
                        continue
                    seen.add(other)
                    result.append(other)
                    next_frontier.append(other)
                    if len(result) >= limit:
                        return result
            frontier = next_frontier
        return result

    def retrieve(
        self,
        intent: str,
        *,
        k: int = 10,
        layer: str | list[str] | None = None,
        filters: Filter | None = None,
    ) -> list[RetrievalHit]:
        if not intent:
            raise EInvalid("intent must be non-empty")
        if k <= 0:
            raise EInvalid("k must be positive")
        layer_set: set[str] | None
        if layer is None:
            layer_set = None
        elif isinstance(layer, str):
            layer_set = {layer}
        else:
            layer_set = set(layer)

        hits: list[RetrievalHit] = []
        needle = intent.lower()
        for ref, node in self._nodes.items():
            if node.state != "live":
                continue
            if node.kind == KIND_SOURCE:
                continue
            if layer_set is not None and node.layer not in layer_set:
                continue
            if filters is not None and not filter_evaluate(filters, node.attrs):
                continue
            # trivial substring ISF: score = occurrence count (monotone with list order)
            score = float(node.content.lower().count(needle))
            if score == 0 and needle not in node.content.lower():
                continue
            hits.append(RetrievalHit(ref=ref, score=score))
        hits.sort(key=lambda h: (-(h.score or 0), h.ref))
        return hits[:k]

    # -- History -------------------------------------------------------

    def history(
        self,
        *,
        since: Timestamp | None = None,
        until: Timestamp | None = None,
        actor: ActorId | None = None,
        tag: str | None = None,
        limit: int = 100,
    ) -> list[ChangeSetRef]:
        if limit <= 0:
            raise EInvalid("limit must be positive")
        if since is not None and until is not None and since > until:
            raise EInvalid("since > until")
        out: list[ChangeSetRef] = []
        for cs_ref in reversed(self._changeset_order):
            cs = self._changesets[cs_ref]
            if since is not None and cs.committed_at < since:
                continue
            if until is not None and cs.committed_at > until:
                continue
            if actor is not None and cs.actor != actor:
                continue
            if tag is not None and cs.tag != tag:
                continue
            out.append(cs_ref)
            if len(out) >= limit:
                break
        return out

    def get_changeset(self, ref: ChangeSetRef) -> ChangeSet:
        cs = self._changesets.get(ref)
        if cs is None:
            raise EChangesetNotFound(f"changeset not found: {ref}", ref=ref)
        return cs

    def diff(self, from_ts: Timestamp, to_ts: Timestamp) -> list[Event]:
        if from_ts > to_ts:
            raise EInvalid("from_ts > to_ts")
        out: list[Event] = []
        for cs_ref in self._changeset_order:
            cs = self._changesets[cs_ref]
            if cs.committed_at <= from_ts or cs.committed_at > to_ts:
                continue
            out.extend(cs.events)
        return out

    def revert(
        self,
        target: ChangeSetRef | str,
        *,
        reason: str,
        actor: Actor,
    ) -> ChangeSet:
        # Resolve target(s)
        targets: list[ChangeSetRef]
        if target in self._changesets:
            targets = [ChangeSetRef(target)]
        else:
            # Treat as tag
            matches = [
                r for r in self._changeset_order if self._changesets[r].tag == target
            ]
            if not matches:
                raise EChangesetNotFound(f"no changeset for target: {target}", target=target)
            targets = list(reversed(matches))

        with self.begin(tag=f"revert:{target}", actor=actor) as tx:
            for cs_ref in targets:
                cs = self._changesets[cs_ref]
                # Invert events in reverse order
                for ev in reversed(cs.events):
                    _apply_inverse(tx, ev)
            return tx.commit()

    # -- Events --------------------------------------------------------

    def events(
        self,
        *,
        since: Timestamp | None = None,
        follow: bool = False,
    ) -> Iterator[Event]:
        if follow:
            raise EInvalid("follow=True not supported by DictStore (Level A)")
        for cs_ref in self._changeset_order:
            cs = self._changesets[cs_ref]
            if since is not None and cs.committed_at <= since:
                continue
            yield from cs.events


class DictTransaction:
    """Transaction produced by :meth:`DictStore.begin`."""

    def __init__(self, store: DictStore, *, tag: str, actor: Actor) -> None:
        self._store = store
        self.ref: TransactionRef = TransactionRef(_new_ref("tx"))
        self.tag = tag
        self._actor_obj = actor
        self.actor: ActorId = actor.id
        self._state: Literal["open", "committed", "aborted"] = "open"
        self._started_at = store._tick()
        # Pending mutations and events
        self._pending_node_writes: dict[NodeRef, Node] = {}
        self._pending_edge_writes: dict[EdgeRef, Edge] = {}
        self._pending_pred_writes: dict[NodeRef, tuple[NodeRef, ...]] = {}
        self._pending_events: list[Event] = []

    # -- Context manager -----------------------------------------------

    def __enter__(self) -> "DictTransaction":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if self._state == "open":
            if exc is not None:
                self.abort()
            else:
                self.abort()

    # -- State guards --------------------------------------------------

    def _require_open(self) -> None:
        if self._state != "open":
            raise ETransactionClosed(f"transaction is {self._state}")

    # -- Staged view ---------------------------------------------------

    def _resolve_node(self, ref: NodeRef) -> Node:
        if ref in self._pending_node_writes:
            return self._pending_node_writes[ref]
        node = self._store._nodes.get(ref)
        if node is None:
            raise ENodeNotFound(f"node not found: {ref}", ref=ref)
        return node

    def _resolve_edge(self, ref: EdgeRef) -> Edge:
        if ref in self._pending_edge_writes:
            return self._pending_edge_writes[ref]
        edge = self._store._edges.get(ref)
        if edge is None:
            raise EEdgeNotFound(f"edge not found: {ref}", ref=ref)
        return edge

    def get_node(self, ref: NodeRef) -> Node:
        return self._resolve_node(ref)

    def get_edge(self, ref: EdgeRef) -> Edge:
        return self._resolve_edge(ref)

    # -- Node lifecycle ------------------------------------------------

    def create(
        self,
        *,
        kind: str,
        layer: str,
        content: str,
        attrs: dict[str, Any] | None = None,
    ) -> NodeRef:
        self._require_open()
        validate_kind_layer(kind, layer)
        validate_concept_content(kind, content)
        ref = NodeRef(_new_ref("n"))
        ts = self._store._tick()
        node = Node(
            ref=ref,
            kind=kind,
            layer=layer,
            content=content,
            attrs=dict(attrs or {}),
            state="live",
            created_at=ts,
            updated_at=ts,
        )
        self._pending_node_writes[ref] = node
        self._pending_events.append(
            Event(
                kind="node.created",
                target=ref,
                before=None,
                after=node_snapshot(node),
            )
        )
        return ref

    def rewrite(
        self,
        ref: NodeRef,
        *,
        content: str,
        reason: str,
    ) -> NodeRef:
        self._require_open()
        if not reason:
            raise EInvalid("reason must be non-empty")
        node = self._resolve_node(ref)
        if node.state == "retired":
            raise ENodeAlreadyRetired(f"node is retired: {ref}", ref=ref)
        validate_concept_content(node.kind, content)
        ts = self._store._tick()
        new_node = Node(
            ref=node.ref,
            kind=node.kind,
            layer=node.layer,
            content=content,
            attrs=dict(node.attrs),
            state=node.state,
            created_at=node.created_at,
            updated_at=ts,
            retired_at=node.retired_at,
        )
        self._pending_node_writes[ref] = new_node
        self._pending_events.append(
            Event(
                kind="node.rewritten",
                target=ref,
                before=node_snapshot(node),
                after=node_snapshot(new_node),
                meta={"reason": reason},
            )
        )
        return ref

    def retire(
        self,
        ref: NodeRef,
        *,
        reason: str,
    ) -> None:
        self._require_open()
        if not reason:
            raise EInvalid("reason must be non-empty")
        node = self._resolve_node(ref)
        if node.state == "retired":
            return  # idempotent no-op
        ts = self._store._tick()
        retired = Node(
            ref=node.ref,
            kind=node.kind,
            layer=node.layer,
            content=node.content,
            attrs=dict(node.attrs),
            state="retired",
            created_at=node.created_at,
            updated_at=ts,
            retired_at=ts,
        )
        self._pending_node_writes[ref] = retired
        self._pending_events.append(
            Event(
                kind="node.retired",
                target=ref,
                before=node_snapshot(node),
                after=node_snapshot(retired),
                meta={"reason": reason},
            )
        )
        # Retire incident edges
        incident = self._store._node_outgoing.get(ref, set()) | self._store._node_incoming.get(
            ref, set()
        )
        for eref in incident:
            edge = self._resolve_edge(eref)
            if edge.state == "retired":
                continue
            retired_edge = Edge(
                ref=edge.ref,
                rel=edge.rel,
                src=edge.src,
                dst=edge.dst,
                attrs=dict(edge.attrs),
                state="retired",
                created_at=edge.created_at,
                retired_at=ts,
            )
            self._pending_edge_writes[eref] = retired_edge
            self._pending_events.append(
                Event(
                    kind="edge.retired",
                    target=eref,
                    before=edge_snapshot(edge),
                    after=edge_snapshot(retired_edge),
                    meta={"reason": f"incident to retired node {ref}"},
                )
            )

    def merge(
        self,
        refs: list[NodeRef],
        *,
        content: str,
        attrs: dict[str, Any] | None = None,
        reason: str,
    ) -> NodeRef:
        self._require_open()
        if not reason:
            raise EInvalid("reason must be non-empty")
        unique = list(dict.fromkeys(refs))
        if len(unique) < 2:
            raise EInvalid("merge requires at least two distinct refs")
        resolved: list[Node] = [self._resolve_node(r) for r in unique]
        for n in resolved:
            if n.state == "retired":
                raise ENodeAlreadyRetired(f"node is retired: {n.ref}", ref=n.ref)
        validate_merge_uniform(resolved)
        # Cycle check: no target may be an ancestor of another
        offender = would_cycle(unique, self._predecessors_of)
        if offender is not None:
            raise ELineageCycle(
                f"merge would create a cycle: {offender} is an ancestor of a sibling"
            )
        validate_concept_content(resolved[0].kind, content)

        merged_ref = self.create(
            kind=resolved[0].kind,
            layer=resolved[0].layer,
            content=content,
            attrs=attrs,
        )
        # Retire sources and record lineage
        for r in unique:
            self.retire(r, reason=f"merged into {merged_ref}: {reason}")
        self._pending_pred_writes[merged_ref] = tuple(unique)
        # Replace the tail node.created event with a node.merged event
        # carrying the ancestors in meta
        for idx in range(len(self._pending_events) - 1, -1, -1):
            ev = self._pending_events[idx]
            if ev.kind == "node.created" and ev.target == merged_ref:
                self._pending_events[idx] = Event(
                    kind="node.merged",
                    target=merged_ref,
                    before=None,
                    after=ev.after,
                    meta={"ancestors": list(unique), "reason": reason},
                )
                break
        return merged_ref

    # -- Edge lifecycle ------------------------------------------------

    def link(
        self,
        src: NodeRef,
        dst: NodeRef,
        *,
        rel: str,
        attrs: dict[str, Any] | None = None,
    ) -> EdgeRef:
        self._require_open()
        src_node = self._resolve_node(src)
        dst_node = self._resolve_node(dst)
        if src_node.state == "retired":
            raise ENodeAlreadyRetired(f"src retired: {src}", ref=src)
        if dst_node.state == "retired":
            raise ENodeAlreadyRetired(f"dst retired: {dst}", ref=dst)
        validate_edge_rel(rel, src_node, dst_node)
        ref = EdgeRef(_new_ref("e"))
        ts = self._store._tick()
        edge = Edge(
            ref=ref,
            rel=rel,
            src=src,
            dst=dst,
            attrs=dict(attrs or {}),
            state="live",
            created_at=ts,
        )
        self._pending_edge_writes[ref] = edge
        self._pending_events.append(
            Event(kind="edge.created", target=ref, before=None, after=edge_snapshot(edge))
        )
        return ref

    def unlink(
        self,
        ref: EdgeRef,
        *,
        reason: str,
    ) -> None:
        self._require_open()
        if not reason:
            raise EInvalid("reason must be non-empty")
        edge = self._resolve_edge(ref)
        if edge.state == "retired":
            return
        ts = self._store._tick()
        retired = Edge(
            ref=edge.ref,
            rel=edge.rel,
            src=edge.src,
            dst=edge.dst,
            attrs=dict(edge.attrs),
            state="retired",
            created_at=edge.created_at,
            retired_at=ts,
        )
        self._pending_edge_writes[ref] = retired
        self._pending_events.append(
            Event(
                kind="edge.retired",
                target=ref,
                before=edge_snapshot(edge),
                after=edge_snapshot(retired),
                meta={"reason": reason},
            )
        )

    # -- Lifecycle -----------------------------------------------------

    def commit(self) -> ChangeSet:
        self._require_open()
        if not self._pending_events:
            # Empty transaction — still produce a ChangeSet for auditability?
            # Spec §4.2: one ChangeSet per committed transaction. We emit one
            # with zero events, which is consistent with "exactly one per
            # commit" and "one event per effective mutation" (zero here).
            pass
        store = self._store
        ts = store._tick()
        # Apply staged writes
        for ref, node in self._pending_node_writes.items():
            store._nodes[ref] = node
        for ref, edge in self._pending_edge_writes.items():
            store._edges[ref] = edge
            store._node_outgoing.setdefault(edge.src, set()).add(ref)
            store._node_incoming.setdefault(edge.dst, set()).add(ref)
        for ref, preds in self._pending_pred_writes.items():
            store._node_predecessors[ref] = preds
        # Emit ChangeSet
        cs_ref = ChangeSetRef(_new_ref("cs"))
        cs = ChangeSet(
            ref=cs_ref,
            tx_ref=self.ref,
            tag=self.tag,
            actor=self.actor,
            committed_at=ts,
            events=tuple(self._pending_events),
        )
        store._changesets[cs_ref] = cs
        store._changeset_order.append(cs_ref)
        self._state = "committed"
        return cs

    def abort(self) -> None:
        if self._state != "open":
            if self._state == "aborted":
                return
            raise ETransactionClosed(f"transaction is {self._state}")
        self._pending_node_writes.clear()
        self._pending_edge_writes.clear()
        self._pending_pred_writes.clear()
        self._pending_events.clear()
        self._state = "aborted"

    # -- Helpers -------------------------------------------------------

    def _predecessors_of(self, ref: NodeRef) -> tuple[NodeRef, ...]:
        """Merge committed and pending predecessor writes for ``ref``."""
        if ref in self._pending_pred_writes:
            return self._pending_pred_writes[ref]
        return self._store._node_predecessors.get(ref, ())


# -------- Module helpers --------


def _apply_inverse(tx: DictTransaction, ev: Event) -> None:
    """Best-effort inverse of an event inside a new transaction."""
    if ev.kind == "node.created" or ev.kind == "node.merged":
        target = ev.target
        try:
            node = tx._resolve_node(target)  # type: ignore[arg-type]
        except ENodeNotFound:
            return
        if node.state == "live":
            tx.retire(target, reason="revert")  # type: ignore[arg-type]
    elif ev.kind == "node.retired":
        # Cannot resurrect without protocol-level revive; raise constraint
        raise EConstraint("DictStore cannot resurrect retired nodes on revert")
    elif ev.kind == "node.rewritten":
        before = ev.before or {}
        prior = before.get("content")
        if prior is not None:
            tx.rewrite(ev.target, content=prior, reason="revert")  # type: ignore[arg-type]
    elif ev.kind == "edge.created":
        try:
            edge = tx._resolve_edge(ev.target)  # type: ignore[arg-type]
        except EEdgeNotFound:
            return
        if edge.state == "live":
            tx.unlink(ev.target, reason="revert")  # type: ignore[arg-type]
    elif ev.kind == "edge.retired":
        raise EConstraint("DictStore cannot resurrect retired edges on revert")


__all__ = ["DictStore", "DictTransaction"]
