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

This module defines the AST and a pure reference evaluator
(:func:`evaluate`). Implementations MAY use it directly over an attrs
mapping, or implement filter translation into their native query
layer (SQL WHERE, Chroma where-clause, etc.) and fall back to this
evaluator only for post-filtering.
"""

from __future__ import annotations

from typing import Any, Mapping, Union

import msgspec

from amkb.errors import EInvalid


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


def evaluate(filt: Filter, attrs: Mapping[str, Any]) -> bool:
    """Evaluate a :data:`Filter` against an ``attrs`` mapping.

    Semantics match the spec closed algebra:

    - Missing keys → ``False`` for leaf predicates (``Eq``, ``In``,
      ``Range``). Implementations that want "present and equal" vs
      "absent" distinctions MUST encode that in their own layer;
      this evaluator treats absence as non-match.
    - ``Range`` short-circuits to ``False`` on non-numeric values.
    - Boolean combinators (``And``, ``Or``, ``Not``) recurse.
    - Any filter node that is not a recognized variant raises
      :class:`amkb.errors.EInvalid`.
    """
    if isinstance(filt, Eq):
        return filt.key in attrs and attrs[filt.key] == filt.value
    if isinstance(filt, In):
        return filt.key in attrs and attrs[filt.key] in filt.values
    if isinstance(filt, Range):
        if filt.key not in attrs:
            return False
        val = attrs[filt.key]
        if not isinstance(val, (int, float)):
            return False
        if filt.min is not None:
            if filt.inclusive:
                if val < filt.min:
                    return False
            elif val <= filt.min:
                return False
        if filt.max is not None:
            if filt.inclusive:
                if val > filt.max:
                    return False
            elif val >= filt.max:
                return False
        return True
    if isinstance(filt, And):
        return all(evaluate(f, attrs) for f in filt.filters)
    if isinstance(filt, Or):
        return any(evaluate(f, attrs) for f in filt.filters)
    if isinstance(filt, Not):
        return not evaluate(filt.filter, attrs)
    raise EInvalid(f"unknown filter node: {type(filt).__name__}")


__all__ = [
    "And",
    "Eq",
    "Filter",
    "In",
    "Not",
    "Or",
    "Range",
    "evaluate",
]
