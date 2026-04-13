"""AMKB canonical errors — 22 codes grouped into 5 categories.

Tracks spec/05-errors.md. Every error raised by a conformant
implementation MUST carry one of the canonical codes below. The SDK
models each code as a distinct subclass of :class:`AmkbError` so that
callers can either:

- catch a specific code (``except ENodeNotFound``)
- catch a category (``except NotFoundError``)
- catch everything (``except AmkbError``)

The three required fields from §5.1 (``code``, ``message``,
``category``) are exposed as attributes; the string form of the
exception is ``"<code>: <message>"``.

Categories (§5.3):

====================   =====================================
``validation``         Input violates a precondition
``not_found``          Referenced entity does not exist
``state``              Store state incompatible with operation
``invariant``          Protocol invariant violated
``internal``           Implementation-side failure
====================   =====================================
"""

from __future__ import annotations

from typing import Any, ClassVar, Literal

ErrorCategory = Literal["validation", "not_found", "state", "invariant", "internal"]


class AmkbError(Exception):
    """Base class for every AMKB canonical error.

    Subclasses set ``code`` and ``category`` as class-level attributes.
    Instances additionally carry a human-readable ``message`` and an
    optional ``details`` mapping for diagnostic fields (offending ref,
    hint, etc.). Per §5.1 callers MUST NOT parse ``message``.
    """

    code: ClassVar[str] = "E_AMKB"
    category: ClassVar[ErrorCategory] = "internal"

    def __init__(self, message: str = "", **details: Any) -> None:
        super().__init__(message)
        self.message = message
        self.details: dict[str, Any] = details

    def __str__(self) -> str:
        return f"{self.code}: {self.message}" if self.message else self.code


# -------- Category bases --------


class ValidationError(AmkbError):
    """Input violates a precondition. Caller SHOULD fix input before retry."""

    category: ClassVar[ErrorCategory] = "validation"


class NotFoundError(AmkbError):
    """Referenced entity does not exist."""

    category: ClassVar[ErrorCategory] = "not_found"


class StateError(AmkbError):
    """Store state is incompatible with the operation."""

    category: ClassVar[ErrorCategory] = "state"


class InvariantError(AmkbError):
    """A protocol invariant was violated. Callers MUST NOT retry."""

    category: ClassVar[ErrorCategory] = "invariant"


class InternalError(AmkbError):
    """Implementation-side failure. Callers MAY retry."""

    category: ClassVar[ErrorCategory] = "internal"


# -------- Validation codes --------


class EInvalid(ValidationError):
    """Catch-all for malformed arguments with no more specific code."""

    code = "E_INVALID"


class EInvalidKind(ValidationError):
    """``kind`` field is empty, malformed, or syntactically invalid."""

    code = "E_INVALID_KIND"


class EInvalidLayer(ValidationError):
    """``layer`` field is empty, malformed, or unsupported."""

    code = "E_INVALID_LAYER"


class EInvalidRel(ValidationError):
    """``rel`` field is empty, malformed, or unsupported."""

    code = "E_INVALID_REL"


class EEmptyContent(ValidationError):
    """Concept Node created or rewritten with empty ``content`` (§2.2.5)."""

    code = "E_EMPTY_CONTENT"


class ECrossLayerInvalid(ValidationError):
    """Reserved ``kind``/``layer`` pairing was violated (§2.4)."""

    code = "E_CROSS_LAYER_INVALID"


class EMissingRequiredAttr(ValidationError):
    """A reserved attribute required for the operation is missing."""

    code = "E_MISSING_REQUIRED_ATTR"


class EReservedRelMisuse(ValidationError):
    """Reserved relation used with semantics that violate its contract."""

    code = "E_RESERVED_REL_MISUSE"


class EConceptToNonsourceAttest(ValidationError):
    """An attestation edge has a destination that is not a source Node."""

    code = "E_CONCEPT_TO_NONSOURCE_ATTEST"


class ESelfLoop(ValidationError):
    """Edge has ``src == dst``. Self-loops are forbidden on reserved rels."""

    code = "E_SELF_LOOP"


# -------- Not-found codes --------


class ENodeNotFound(NotFoundError):
    """A ``NodeRef`` does not resolve to any Node in the store."""

    code = "E_NODE_NOT_FOUND"


class EEdgeNotFound(NotFoundError):
    """An ``EdgeRef`` does not resolve to any Edge in the store."""

    code = "E_EDGE_NOT_FOUND"


class EChangesetNotFound(NotFoundError):
    """A transaction tag or changeset identifier is unknown."""

    code = "E_CHANGESET_NOT_FOUND"


# -------- State codes --------


class ENodeAlreadyRetired(StateError):
    """Operation requires a live Node but the target is retired."""

    code = "E_NODE_ALREADY_RETIRED"


class EMergeConflict(StateError):
    """``merge`` was called on Nodes with mismatched ``kind``/``layer``."""

    code = "E_MERGE_CONFLICT"


class ELineageCycle(StateError):
    """Operation would introduce a cycle in lineage."""

    code = "E_LINEAGE_CYCLE"


class ETransactionClosed(StateError):
    """Operation was issued on a committed, aborted, or terminated tx."""

    code = "E_TRANSACTION_CLOSED"


class EConcurrentModification(StateError):
    """``commit`` saw divergent state since ``begin``. Retry from begin."""

    code = "E_CONCURRENT_MODIFICATION"


class EConstraint(StateError):
    """A protocol invariant would be violated at commit. Tx is aborted."""

    code = "E_CONSTRAINT"


class EConflict(StateError):
    """``revert`` target has diverged and cannot be cleanly undone."""

    code = "E_CONFLICT"


# -------- Invariant codes --------


class ESourceInRetrieval(InvariantError):
    """A source Node was about to be returned by ``retrieve``. MUST NOT occur."""

    code = "E_SOURCE_IN_RETRIEVAL"


# -------- Internal codes --------


class EInternal(InternalError):
    """Implementation-side failure not covered by any other code."""

    code = "E_INTERNAL"


# -------- Registries --------

CANONICAL_ERRORS: tuple[type[AmkbError], ...] = (
    EInvalid,
    EInvalidKind,
    EInvalidLayer,
    EInvalidRel,
    EEmptyContent,
    ECrossLayerInvalid,
    EMissingRequiredAttr,
    EReservedRelMisuse,
    EConceptToNonsourceAttest,
    ESelfLoop,
    ENodeNotFound,
    EEdgeNotFound,
    EChangesetNotFound,
    ENodeAlreadyRetired,
    EMergeConflict,
    ELineageCycle,
    ETransactionClosed,
    EConcurrentModification,
    EConstraint,
    EConflict,
    ESourceInRetrieval,
    EInternal,
)
"""All 22 canonical error classes, in the order listed in spec §5.4."""

ERROR_BY_CODE: dict[str, type[AmkbError]] = {cls.code: cls for cls in CANONICAL_ERRORS}
"""Lookup from canonical code string to exception class."""


__all__ = [
    "AmkbError",
    "CANONICAL_ERRORS",
    "EChangesetNotFound",
    "EConceptToNonsourceAttest",
    "EConcurrentModification",
    "EConflict",
    "EConstraint",
    "ECrossLayerInvalid",
    "EEdgeNotFound",
    "EEmptyContent",
    "EInternal",
    "EInvalid",
    "EInvalidKind",
    "EInvalidLayer",
    "EInvalidRel",
    "ELineageCycle",
    "EMergeConflict",
    "EMissingRequiredAttr",
    "ENodeAlreadyRetired",
    "ENodeNotFound",
    "EReservedRelMisuse",
    "ESelfLoop",
    "ESourceInRetrieval",
    "ETransactionClosed",
    "ERROR_BY_CODE",
    "ErrorCategory",
    "InternalError",
    "InvariantError",
    "NotFoundError",
    "StateError",
    "ValidationError",
]
