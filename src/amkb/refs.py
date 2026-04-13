"""Opaque reference types for AMKB entities.

Per spec/02-types.md §2.1, references are opaque, stable identifiers.
Callers MUST NOT parse them or derive structure from them.
Implementations MAY use any internal format (integers, UUIDs, URIs,
content-addressed hashes) as long as stability and opacity hold.

The SDK represents them as ``NewType`` wrappers around ``str`` so that
static type checkers distinguish a ``NodeRef`` from a plain ``str``
without incurring runtime overhead.
"""

from __future__ import annotations

from typing import NewType

NodeRef = NewType("NodeRef", str)
EdgeRef = NewType("EdgeRef", str)
ActorId = NewType("ActorId", str)
TransactionRef = NewType("TransactionRef", str)
ChangeSetRef = NewType("ChangeSetRef", str)

Timestamp = NewType("Timestamp", int)
"""Monotonic timestamp within a single store. Unit is implementation-defined
but MUST be monotonic per spec/02-types.md §2.1."""

__all__ = [
    "ActorId",
    "ChangeSetRef",
    "EdgeRef",
    "NodeRef",
    "Timestamp",
    "TransactionRef",
]
