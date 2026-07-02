"""amkb — Python SDK for the Agent-Managed Knowledge Base protocol.

Tracks amkb-spec v0.2.0. See README.md for reading order.

Note on ``Transaction``: this package re-exports ``amkb.store.Transaction``,
the ``typing.Protocol`` describing the mutation surface (``create``,
``rewrite``, ``retire``, ``merge``, ``link``, ``unlink``, ``commit``,
``abort``). A *different* ``Transaction`` — ``amkb.types.Transaction``,
a frozen ``msgspec.Struct`` record of a transaction's metadata
(``ref``, ``tag``, ``actor``, ``state``, timestamps) — lives in
``amkb.types`` and is not re-exported here to avoid shadowing the
Protocol. Both names are intentional and will not be renamed in
0.1.0; import the struct explicitly as ``from amkb.types import
Transaction`` if you need it.
"""

from amkb import errors
from amkb.errors import AmkbError
from amkb.filters import And, Eq, Filter, In, Not, Or, Range
from amkb.store import Store, Transaction
from amkb.types import Actor, Edge, Event, Node

__version__ = "0.0.1"
__spec_version__ = "0.2.0"

__all__ = [
    "Actor",
    "AmkbError",
    "And",
    "Edge",
    "Eq",
    "Event",
    "Filter",
    "In",
    "Node",
    "Not",
    "Or",
    "Range",
    "Store",
    "Transaction",
    "errors",
]
