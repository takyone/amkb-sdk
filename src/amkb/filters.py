"""Filter algebra for intent retrieval.

Implements the minimal filter algebra defined in spec/03-operations.md
§3.4.5. Filters narrow the candidate set **before** the
implementation's relevance estimator ranks survivors.

The five leaf constructors (``Eq``, ``In``, ``Range``, ``And``, ``Or``,
``Not``) are modeled as frozen ``msgspec.Struct`` classes, and
``Filter`` is their discriminated union. All are JSON-serializable via
``msgspec.json.encode`` / ``decode`` for cross-implementation transport.

Spec obligations:

- L4b MUST support ``Eq``, ``In``, ``And``, ``Or``.
- L4b SHOULD support ``Range`` and ``Not``.
- Extension filters MUST be prefixed ``ext:``; recipients unfamiliar
  with an extension MUST reject the filter with ``E_INVALID``.

This module defines only the AST. Evaluation of a filter against a
concrete ``Node`` lives in each store implementation; a reference
evaluator is provided for convenience in ``amkb.reference``.
"""

from __future__ import annotations

from typing import Any, Union

import msgspec


class Eq(msgspec.Struct, frozen=True, tag="eq"):
    """``attrs[key] == value`` (JSON equality)."""

    key: str
    value: Any


class In(msgspec.Struct, frozen=True, tag="in"):
    """``attrs[key] ∈ values`` (JSON equality on each element)."""

    key: str
    values: tuple[Any, ...]


class Range(msgspec.Struct, frozen=True, tag="range"):
    """``min <= attrs[key] <= max`` for numeric or timestamp values.

    Either ``min`` or ``max`` MAY be ``None`` for open-ended ranges.
    When ``inclusive`` is ``False``, endpoint inclusion is dropped.
    """

    key: str
    min: float | int | None = None
    max: float | int | None = None
    inclusive: bool = True


class And(msgspec.Struct, frozen=True, tag="and"):
    """Conjunction: every sub-filter MUST match."""

    filters: tuple["Filter", ...]


class Or(msgspec.Struct, frozen=True, tag="or"):
    """Disjunction: at least one sub-filter MUST match."""

    filters: tuple["Filter", ...]


class Not(msgspec.Struct, frozen=True, tag="not"):
    """Negation: the sub-filter MUST NOT match."""

    filter: "Filter"


Filter = Union[Eq, In, Range, And, Or, Not]
"""Discriminated union of filter AST nodes. Serialized with a ``type``
tag per ``msgspec.Struct(tag=...)``."""


__all__ = [
    "And",
    "Eq",
    "Filter",
    "In",
    "Not",
    "Or",
    "Range",
]
