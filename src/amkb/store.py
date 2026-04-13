"""Store and Transaction Protocols — the operation surface of AMKB.

Tracks spec/03-operations.md. The protocol surface is split into two
structural types:

- :class:`Transaction` — owns all mutations (``create``, ``rewrite``,
  ``retire``, ``merge``, ``link``, ``unlink``) plus ``commit`` and
  ``abort``. A ``Transaction`` is a context manager: leaving its body
  without an explicit ``commit`` MUST abort.
- :class:`Store` — owns session entry points (``begin``), read-only
  queries (``get``, ``find_by_attr``, ``neighbors``, ``retrieve``),
  history operations (``history``, ``diff``, ``revert``), and the
  event iterator (``events``).

Both are :class:`typing.Protocol` types, so implementations do **not**
inherit from them. Any class whose shape matches is structurally a
``Store``. This lets Spikuit (and other implementations) expose an
AMKB surface without restructuring their internal types.

This module defines the **synchronous** surface. An async variant
may be added later as ``AsyncStore`` / ``AsyncTransaction`` without
breaking the sync contract; §3.1.3 of the spec permits either.
"""

from __future__ import annotations

from collections.abc import Iterator
from types import TracebackType
from typing import Any, Literal, Protocol, runtime_checkable

import msgspec

from amkb.filters import Filter
from amkb.refs import (
    ActorId,
    ChangeSetRef,
    EdgeRef,
    NodeRef,
    Timestamp,
    TransactionRef,
)
from amkb.types import Actor, ChangeSet, Edge, Event, Node

Direction = Literal["out", "in", "both"]


class RetrievalHit(msgspec.Struct, frozen=True, kw_only=True):
    """A single result from :meth:`Store.retrieve`.

    Per spec §3.4.4, ``score`` is OPTIONAL. Implementations that do
    not produce a numeric relevance estimate (rank-only, LLM-judge,
    categorical) MUST set ``score`` to ``None`` and rely on list order
    to carry the ordering. When ``score`` is set, it MUST be a real
    number consistent with list order.
    """

    ref: NodeRef
    score: float | None = None


@runtime_checkable
class Transaction(Protocol):
    """The mutation surface of a single open transaction.

    Per §3.1.2, every mutation operation lives here rather than on
    the store. A transaction is acquired from :meth:`Store.begin`
    and used as a context manager. Leaving the body without calling
    :meth:`commit` MUST call :meth:`abort`.
    """

    ref: TransactionRef
    tag: str
    actor: ActorId

    # -- Node lifecycle ------------------------------------------------

    def create(
        self,
        *,
        kind: str,
        layer: str,
        content: str,
        attrs: dict[str, Any] | None = None,
    ) -> NodeRef:
        """Create a live Node. Emits ``node.created``. See §3.2.1."""

    def rewrite(
        self,
        ref: NodeRef,
        *,
        content: str,
        reason: str,
    ) -> NodeRef:
        """Replace a live Node's content. Emits ``node.rewritten``. See §3.2.2."""

    def retire(
        self,
        ref: NodeRef,
        *,
        reason: str,
    ) -> None:
        """Retire a Node and its incident Edges. Idempotent. See §3.2.3."""

    def merge(
        self,
        refs: list[NodeRef],
        *,
        content: str,
        attrs: dict[str, Any] | None = None,
        reason: str,
    ) -> NodeRef:
        """Merge multiple Nodes into one. L2 operation. See §3.2.4."""

    # -- Edge lifecycle ------------------------------------------------

    def link(
        self,
        src: NodeRef,
        dst: NodeRef,
        *,
        rel: str,
        attrs: dict[str, Any] | None = None,
    ) -> EdgeRef:
        """Create a directed edge. Emits ``edge.created``. See §3.3.1."""

    def unlink(
        self,
        ref: EdgeRef,
        *,
        reason: str,
    ) -> None:
        """Retire an Edge. Idempotent. See §3.3.2."""

    # -- In-transaction queries ----------------------------------------

    def get_node(self, ref: NodeRef) -> Node:
        """Return a Node (live or retired) visible within this transaction."""

    def get_edge(self, ref: EdgeRef) -> Edge:
        """Return an Edge (live or retired) visible within this transaction."""

    # -- Lifecycle -----------------------------------------------------

    def commit(self) -> ChangeSet:
        """Commit the transaction atomically and return its ChangeSet. See §3.5.2."""

    def abort(self) -> None:
        """Abort the transaction. No mutations take effect. See §3.5.3."""

    # -- Context manager -----------------------------------------------

    def __enter__(self) -> "Transaction": ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None: ...


@runtime_checkable
class Store(Protocol):
    """The read-side and session-entry surface of an AMKB store.

    All mutations flow through :meth:`begin` → :class:`Transaction`.
    Queries may be served here without opening a transaction (§3.4).
    """

    # -- Session entry -------------------------------------------------

    def begin(self, *, tag: str, actor: Actor) -> Transaction:
        """Open a new transaction. See §3.5.1."""

    # -- Read-only queries ---------------------------------------------

    def get_node(self, ref: NodeRef) -> Node:
        """Fetch a Node by ref. Retired Nodes MUST resolve. See §3.4.1."""

    def get_edge(self, ref: EdgeRef) -> Edge:
        """Fetch an Edge by ref. Retired Edges MUST resolve. See §3.4.1."""

    def find_by_attr(
        self,
        attributes: dict[str, Any],
        *,
        kind: str | None = None,
        layer: str | None = None,
        include_retired: bool = False,
        limit: int = 100,
    ) -> list[NodeRef]:
        """Equality lookup on attrs. L4a operation. See §3.4.2."""

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
        """Graph walk from ``ref``. L4a operation. See §3.4.3."""

    def retrieve(
        self,
        intent: str,
        *,
        k: int = 10,
        layer: str | list[str] | None = None,
        filters: Filter | None = None,
    ) -> list[RetrievalHit]:
        """Intent-driven retrieval. L4b operation. See §3.4.4."""

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
        """List committed ChangeSets matching the filters. See §3.6.1."""

    def get_changeset(self, ref: ChangeSetRef) -> ChangeSet:
        """Fetch a committed ChangeSet by ref."""

    def diff(self, from_ts: Timestamp, to_ts: Timestamp) -> list[Event]:
        """Events committed strictly within ``(from_ts, to_ts]``. L2. See §3.6.2."""

    def revert(
        self,
        target: ChangeSetRef | str,
        *,
        reason: str,
        actor: Actor,
    ) -> ChangeSet:
        """Emit the inverse of a past ChangeSet as a new ChangeSet. See §3.6.3."""

    # -- Events --------------------------------------------------------

    def events(
        self,
        *,
        since: Timestamp | None = None,
        follow: bool = False,
    ) -> Iterator[Event]:
        """Iterate events from ``since`` forward. See §3.7.1."""


__all__ = [
    "Direction",
    "RetrievalHit",
    "Store",
    "Transaction",
]
