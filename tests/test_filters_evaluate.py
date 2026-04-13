"""Unit tests for amkb.filters.evaluate pure evaluator."""

from __future__ import annotations

import pytest

from amkb.errors import EInvalid
from amkb.filters import And, Eq, In, Not, Or, Range, evaluate


def test_eq_match() -> None:
    assert evaluate(Eq(key="k", value=1), {"k": 1})


def test_eq_missing_key() -> None:
    assert not evaluate(Eq(key="k", value=1), {})


def test_in_match() -> None:
    assert evaluate(In(key="k", values=(1, 2, 3)), {"k": 2})


def test_in_missing() -> None:
    assert not evaluate(In(key="k", values=(1, 2)), {"k": 99})


def test_range_inclusive() -> None:
    f = Range(key="score", min=0.0, max=1.0, inclusive=True)
    assert evaluate(f, {"score": 0.0})
    assert evaluate(f, {"score": 1.0})
    assert not evaluate(f, {"score": 1.1})


def test_range_exclusive() -> None:
    f = Range(key="score", min=0.0, max=1.0, inclusive=False)
    assert not evaluate(f, {"score": 0.0})
    assert evaluate(f, {"score": 0.5})
    assert not evaluate(f, {"score": 1.0})


def test_range_non_numeric_false() -> None:
    f = Range(key="k", min=0, max=10)
    assert not evaluate(f, {"k": "not a number"})


def test_range_open_ended() -> None:
    f = Range(key="k", min=5)
    assert evaluate(f, {"k": 10})
    assert not evaluate(f, {"k": 4})


def test_and() -> None:
    f = And(filters=(Eq(key="a", value=1), Eq(key="b", value=2)))
    assert evaluate(f, {"a": 1, "b": 2})
    assert not evaluate(f, {"a": 1, "b": 3})


def test_or() -> None:
    f = Or(filters=(Eq(key="a", value=1), Eq(key="b", value=2)))
    assert evaluate(f, {"a": 1})
    assert evaluate(f, {"b": 2})
    assert not evaluate(f, {"a": 0, "b": 0})


def test_not() -> None:
    f = Not(filter=Eq(key="a", value=1))
    assert evaluate(f, {"a": 2})
    assert not evaluate(f, {"a": 1})


def test_unknown_filter_raises() -> None:
    class Bogus:
        pass

    with pytest.raises(EInvalid):
        evaluate(Bogus(), {})  # type: ignore[arg-type]
