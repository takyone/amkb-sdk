"""Core AMKB types — Node, Edge, Actor, Transaction, ChangeSet, Event.

Tracks amkb-spec v0.2.0, chapter 02 (Types). All structs are frozen
``msgspec.Struct`` instances so instances are hashable and safe to
share across observers.

The protocol treats ``kind``, ``layer``, and ``rel`` as **open
enumerations**: reserved values carry fixed semantics, but
implementations MAY add their own values (prefixed ``ext:`` for kinds
and rels, ``L_ext_`` for layers). We therefore model these as ``str``
type aliases plus ``frozenset`` constants of the reserved values, and
validate reserved pairings in helper functions rather than via an
Enum.
"""

from __future__ import annotations

import hashlib
from typing import Any, Literal

import msgspec

from amkb.refs import ActorId, ChangeSetRef, EdgeRef, NodeRef, Timestamp, TransactionRef

# -------- Open enumerations --------

Kind = str
"""A Node kind. Reserved values: ``"concept"``, ``"source"``, ``"category"``.
Implementations MAY add kinds with an ``ext:`` prefix."""

Layer = str
"""A Node layer. Reserved values: ``"L_concept"``, ``"L_source"``,
``"L_category"``. Implementations MAY add layers with an ``L_ext_`` prefix."""

Rel = str
"""An Edge relation. See ``RESERVED_RELS`` for reserved values and their
semantics (spec/02-types.md §2.3.2)."""

KIND_CONCEPT: Kind = "concept"
KIND_SOURCE: Kind = "source"
KIND_CATEGORY: Kind = "category"
RESERVED_KINDS: frozenset[Kind] = frozenset({KIND_CONCEPT, KIND_SOURCE, KIND_CATEGORY})

LAYER_CONCEPT: Layer = "L_concept"
LAYER_SOURCE: Layer = "L_source"
LAYER_CATEGORY: Layer = "L_category"
RESERVED_LAYERS: frozenset[Layer] = frozenset({LAYER_CONCEPT, LAYER_SOURCE, LAYER_CATEGORY})

RESERVED_KIND_LAYER: dict[Kind, Layer] = {
    KIND_CONCEPT: LAYER_CONCEPT,
    KIND_SOURCE: LAYER_SOURCE,
    KIND_CATEGORY: LAYER_CATEGORY,
}
"""Per §2.2.4: when a reserved ``kind`` is used, the ``layer`` MUST match."""

# Reserved relations grouped by purpose (spec §2.3.2).
REL_DERIVED_FROM: Rel = "derived_from"
REL_ATTESTED_BY: Rel = "attested_by"
REL_CONTRADICTED_BY: Rel = "contradicted_by"
REL_SUPERSEDED_BY: Rel = "superseded_by"
REL_CONTAINS: Rel = "contains"
REL_BELONGS_TO: Rel = "belongs_to"
REL_GENERALIZES: Rel = "generalizes"
REL_REQUIRES: Rel = "requires"
REL_EXTENDS: Rel = "extends"
REL_CONTRASTS: Rel = "contrasts"
REL_RELATES_TO: Rel = "relates_to"

ATTESTATION_RELS: frozenset[Rel] = frozenset(
    {REL_DERIVED_FROM, REL_ATTESTED_BY, REL_CONTRADICTED_BY}
)
"""The only relations permitted from ``L_concept`` to ``L_source`` (§2.3.3)."""

RESERVED_RELS: frozenset[Rel] = frozenset(
    ATTESTATION_RELS
    | {
        REL_SUPERSEDED_BY,
        REL_CONTAINS,
        REL_BELONGS_TO,
        REL_GENERALIZES,
        REL_REQUIRES,
        REL_EXTENDS,
        REL_CONTRASTS,
        REL_RELATES_TO,
    }
)

RESERVED_REL_LAYERS: dict[Rel, tuple[Layer, Layer]] = {
    REL_DERIVED_FROM: (LAYER_CONCEPT, LAYER_SOURCE),
    REL_ATTESTED_BY: (LAYER_CONCEPT, LAYER_SOURCE),
    REL_CONTRADICTED_BY: (LAYER_CONCEPT, LAYER_SOURCE),
    REL_SUPERSEDED_BY: (LAYER_SOURCE, LAYER_SOURCE),
    REL_CONTAINS: (LAYER_CATEGORY, LAYER_CONCEPT),
    REL_BELONGS_TO: (LAYER_CONCEPT, LAYER_CATEGORY),
    REL_GENERALIZES: (LAYER_CATEGORY, LAYER_CATEGORY),
    REL_REQUIRES: (LAYER_CONCEPT, LAYER_CONCEPT),
    REL_EXTENDS: (LAYER_CONCEPT, LAYER_CONCEPT),
    REL_CONTRASTS: (LAYER_CONCEPT, LAYER_CONCEPT),
    REL_RELATES_TO: (LAYER_CONCEPT, LAYER_CONCEPT),
}
"""Required ``(src_layer, dst_layer)`` pairing for each reserved ``rel``."""

# -------- Actor kinds --------

ActorKind = str
ACTOR_LLM: ActorKind = "llm"
ACTOR_HUMAN: ActorKind = "human"
ACTOR_AUTOMATION: ActorKind = "automation"
ACTOR_COMPOSITE: ActorKind = "composite"
RESERVED_ACTOR_KINDS: frozenset[ActorKind] = frozenset(
    {ACTOR_LLM, ACTOR_HUMAN, ACTOR_AUTOMATION, ACTOR_COMPOSITE}
)

# -------- State enumerations --------

NodeState = Literal["live", "retired"]
EdgeState = Literal["live", "retired"]
TxState = Literal["open", "committed", "aborted"]

# -------- Event kinds --------

EventKind = Literal[
    "node.created",
    "node.rewritten",
    "node.retired",
    "node.merged",
    "edge.created",
    "edge.retired",
]
RESERVED_EVENT_KINDS: frozenset[str] = frozenset(
    {
        "node.created",
        "node.rewritten",
        "node.retired",
        "node.merged",
        "edge.created",
        "edge.retired",
    }
)

# -------- Core structs --------


class Node(msgspec.Struct, frozen=True, kw_only=True):
    """A Node — an atomic knowledge unit. See spec/02-types.md §2.2."""

    ref: NodeRef
    kind: Kind
    layer: Layer
    content: str
    attrs: dict[str, Any] = msgspec.field(default_factory=dict)
    state: NodeState = "live"
    created_at: Timestamp
    updated_at: Timestamp
    retired_at: Timestamp | None = None


class Edge(msgspec.Struct, frozen=True, kw_only=True):
    """An Edge — a typed, directed relation between Nodes. See §2.3."""

    ref: EdgeRef
    rel: Rel
    src: NodeRef
    dst: NodeRef
    attrs: dict[str, Any] = msgspec.field(default_factory=dict)
    state: EdgeState = "live"
    created_at: Timestamp
    retired_at: Timestamp | None = None


class Actor(msgspec.Struct, frozen=True, kw_only=True):
    """An Actor — the attributed author of a mutation. See §2.4."""

    id: ActorId
    kind: ActorKind
    profile: dict[str, Any] = msgspec.field(default_factory=dict)


class Transaction(msgspec.Struct, frozen=True, kw_only=True):
    """A Transaction — a batch of mutations committed atomically.

    Users do not construct ``Transaction`` directly; obtain one from
    ``Store.begin(...)``. See §2.5.
    """

    ref: TransactionRef
    tag: str
    actor: ActorId
    state: TxState = "open"
    started_at: Timestamp
    closed_at: Timestamp | None = None


class Event(msgspec.Struct, frozen=True, kw_only=True):
    """A single mutation event within a ChangeSet. See §2.6."""

    kind: EventKind
    target: NodeRef | EdgeRef
    before: dict[str, Any] | None = None
    after: dict[str, Any] | None = None
    meta: dict[str, Any] = msgspec.field(default_factory=dict)


class ChangeSet(msgspec.Struct, frozen=True, kw_only=True):
    """A ChangeSet — the committed record of one Transaction. See §2.6."""

    ref: ChangeSetRef
    tx_ref: TransactionRef
    tag: str
    actor: ActorId
    committed_at: Timestamp
    events: tuple[Event, ...]


# -------- Helpers --------


def compute_content_hash(content: str) -> str:
    """Return the canonical AMKB content hash for ``content``.

    The result is the algorithm-prefixed hex digest defined in
    spec/02-types.md §2.2.7 as the ``content_hash`` reserved attribute
    format (``sha256:<hex>``). Events that change ``Node.content`` MUST
    include this hash in their ``after`` (and, where possible,
    ``before``) payload per §2.6.5.
    """

    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


__all__ = [
    "ACTOR_AUTOMATION",
    "ACTOR_COMPOSITE",
    "ACTOR_HUMAN",
    "ACTOR_LLM",
    "ATTESTATION_RELS",
    "Actor",
    "ActorKind",
    "ChangeSet",
    "Edge",
    "EdgeState",
    "Event",
    "EventKind",
    "KIND_CATEGORY",
    "KIND_CONCEPT",
    "KIND_SOURCE",
    "Kind",
    "LAYER_CATEGORY",
    "LAYER_CONCEPT",
    "LAYER_SOURCE",
    "Layer",
    "Node",
    "NodeState",
    "REL_ATTESTED_BY",
    "REL_BELONGS_TO",
    "REL_CONTAINS",
    "REL_CONTRADICTED_BY",
    "REL_CONTRASTS",
    "REL_DERIVED_FROM",
    "REL_EXTENDS",
    "REL_GENERALIZES",
    "REL_RELATES_TO",
    "REL_REQUIRES",
    "REL_SUPERSEDED_BY",
    "RESERVED_ACTOR_KINDS",
    "RESERVED_EVENT_KINDS",
    "RESERVED_KINDS",
    "RESERVED_KIND_LAYER",
    "RESERVED_LAYERS",
    "RESERVED_RELS",
    "RESERVED_REL_LAYERS",
    "Rel",
    "Transaction",
    "TxState",
    "compute_content_hash",
]
