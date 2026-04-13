"""Pure validation helpers shared by AMKB Store implementations.

Every function is a pure check over already-parsed values: it either
returns ``None`` or raises a canonical error from :mod:`amkb.errors`.
No I/O, no state, no identity generation. Backends call these from
their transaction layer instead of reimplementing the rules.

The rules encoded here come straight from ``amkb-spec`` (02-types,
03-operations, 05-errors). If the spec text and the code disagree,
the spec wins — file an issue.
"""

from __future__ import annotations

from typing import Iterable

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
from amkb.types import (
    ATTESTATION_RELS,
    KIND_CONCEPT,
    KIND_SOURCE,
    RESERVED_KIND_LAYER,
    RESERVED_REL_LAYERS,
    Node,
)


def validate_kind_layer(kind: str, layer: str) -> None:
    """Check kind/layer pair against reserved pairings.

    Raises ``EInvalidKind`` / ``EInvalidLayer`` on empty values and
    ``ECrossLayerInvalid`` when ``kind`` is reserved but the layer
    does not match the reserved pairing.
    """
    if not kind:
        raise EInvalidKind("kind must be non-empty")
    if not layer:
        raise EInvalidLayer("layer must be non-empty")
    required = RESERVED_KIND_LAYER.get(kind)
    if required is not None and layer != required:
        raise ECrossLayerInvalid(
            f"kind={kind!r} requires layer={required!r}, got {layer!r}",
            kind=kind,
            layer=layer,
        )


def validate_concept_content(kind: str, content: str) -> None:
    """Concept Nodes MUST have non-empty content (spec §2.2)."""
    if kind == KIND_CONCEPT and not content:
        raise EEmptyContent("concept content must be non-empty")


def validate_edge_rel(rel: str, src: Node, dst: Node) -> None:
    """Check an Edge's rel / endpoint invariants before persisting.

    Enforces the reserved-rel layer pairing, the self-loop
    prohibition for reserved rels, and the concept→source
    attestation rule (spec §2.3, §3.1.5).
    """
    if not rel:
        raise EInvalidRel("rel must be non-empty")
    pairing = RESERVED_REL_LAYERS.get(rel)
    if pairing is not None:
        expected_src, expected_dst = pairing
        if src.layer != expected_src or dst.layer != expected_dst:
            raise ECrossLayerInvalid(
                f"rel={rel!r} requires {expected_src}->{expected_dst}",
                rel=rel,
            )
        if src.ref == dst.ref:
            raise ESelfLoop(f"self-loop forbidden for reserved rel {rel!r}")
    if src.kind == KIND_CONCEPT and dst.kind == KIND_SOURCE and rel not in ATTESTATION_RELS:
        raise EConceptToNonsourceAttest(
            f"concept→source edge must use an attestation rel, got {rel!r}",
        )


def validate_merge_uniform(nodes: Iterable[Node]) -> None:
    """Merge candidates MUST share kind and layer (spec §3.3)."""
    node_list = list(nodes)
    kinds = {n.kind for n in node_list}
    layers = {n.layer for n in node_list}
    if len(kinds) != 1 or len(layers) != 1:
        raise EMergeConflict(
            f"merge requires uniform kind and layer, got kinds={kinds}, layers={layers}"
        )


__all__ = [
    "validate_kind_layer",
    "validate_concept_content",
    "validate_edge_rel",
    "validate_merge_uniform",
]
