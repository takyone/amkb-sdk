"""Unit tests for amkb.validation pure helpers."""

from __future__ import annotations

import pytest

from amkb.errors import (
    EConceptToNonsourceAttest,
    ECrossLayerInvalid,
    EEmptyContent,
    EInvalidKind,
    EInvalidLayer,
    EInvalidRel,
    EMergeConflict,
    ESelfLoop,
)
from amkb.refs import NodeRef
from amkb.types import (
    KIND_CATEGORY,
    KIND_CONCEPT,
    KIND_SOURCE,
    LAYER_CATEGORY,
    LAYER_CONCEPT,
    LAYER_SOURCE,
    Node,
    REL_ATTESTED_BY,
    REL_DERIVED_FROM,
    REL_RELATES_TO,
)
from amkb.validation import (
    validate_concept_content,
    validate_edge_rel,
    validate_kind_layer,
    validate_merge_uniform,
)


def _node(ref: str, kind: str, layer: str) -> Node:
    return Node(
        ref=NodeRef(ref),
        kind=kind,
        layer=layer,
        content="x",
        attrs={},
        state="live",
        created_at=0,
        updated_at=0,
    )


def test_validate_kind_layer_ok() -> None:
    validate_kind_layer(KIND_CONCEPT, LAYER_CONCEPT)


def test_validate_kind_layer_empty_kind() -> None:
    with pytest.raises(EInvalidKind):
        validate_kind_layer("", LAYER_CONCEPT)


def test_validate_kind_layer_empty_layer() -> None:
    with pytest.raises(EInvalidLayer):
        validate_kind_layer(KIND_CONCEPT, "")


def test_validate_kind_layer_reserved_mismatch() -> None:
    with pytest.raises(ECrossLayerInvalid):
        validate_kind_layer(KIND_SOURCE, LAYER_CONCEPT)


def test_validate_concept_content_ok() -> None:
    validate_concept_content(KIND_CONCEPT, "hello")


def test_validate_concept_content_empty_raises() -> None:
    with pytest.raises(EEmptyContent):
        validate_concept_content(KIND_CONCEPT, "")


def test_validate_concept_content_non_concept_ignored() -> None:
    # Source nodes MAY have empty content (spec allows it)
    validate_concept_content(KIND_SOURCE, "")


def test_validate_edge_rel_ok_reserved() -> None:
    src = _node("a", KIND_CONCEPT, LAYER_CONCEPT)
    dst = _node("s", KIND_SOURCE, LAYER_SOURCE)
    validate_edge_rel(REL_DERIVED_FROM, src, dst)


def test_validate_edge_rel_empty() -> None:
    src = _node("a", KIND_CONCEPT, LAYER_CONCEPT)
    dst = _node("b", KIND_CONCEPT, LAYER_CONCEPT)
    with pytest.raises(EInvalidRel):
        validate_edge_rel("", src, dst)


def test_validate_edge_rel_layer_mismatch() -> None:
    src = _node("a", KIND_CONCEPT, LAYER_CONCEPT)
    dst = _node("b", KIND_CONCEPT, LAYER_CONCEPT)
    with pytest.raises(ECrossLayerInvalid):
        validate_edge_rel(REL_DERIVED_FROM, src, dst)


def test_validate_edge_rel_self_loop_reserved() -> None:
    n = _node("a", KIND_CONCEPT, LAYER_CONCEPT)
    with pytest.raises(ESelfLoop):
        validate_edge_rel(REL_RELATES_TO, n, n)


def test_validate_edge_rel_concept_to_source_non_attestation() -> None:
    src = _node("a", KIND_CONCEPT, LAYER_CONCEPT)
    dst = _node("s", KIND_SOURCE, LAYER_SOURCE)
    with pytest.raises(EConceptToNonsourceAttest):
        validate_edge_rel("ext:custom", src, dst)


def test_validate_merge_uniform_ok() -> None:
    a = _node("a", KIND_CONCEPT, LAYER_CONCEPT)
    b = _node("b", KIND_CONCEPT, LAYER_CONCEPT)
    validate_merge_uniform([a, b])


def test_validate_merge_uniform_kind_mismatch() -> None:
    a = _node("a", KIND_CONCEPT, LAYER_CONCEPT)
    b = _node("b", KIND_CATEGORY, LAYER_CATEGORY)
    with pytest.raises(EMergeConflict):
        validate_merge_uniform([a, b])
