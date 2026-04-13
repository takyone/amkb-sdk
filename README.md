# amkb — Python SDK for the Agent-Managed Knowledge Base protocol

> **Status: Pre-alpha (v0.1.0).** This package tracks [amkb-spec](https://github.com/takyone/amkb-spec)
> v0.2.0 and is under active development. APIs may change without notice.

`amkb` is a **backend-agnostic** Python SDK for the AMKB protocol. It
provides the types, error catalog, filter algebra, Store protocol,
and a reusable conformance suite. It intentionally ships **no storage
backend**: SQLite, Chroma, Postgres, an in-memory dict, or a custom
engine are all equally valid implementations of the protocol.

The package consists of:

1. **Core types** (`amkb.types`) — `Node`, `Edge`, `Actor`, `Transaction`,
   `ChangeSet`, `Event`, plus reserved kind / layer / rel constants.
2. **Canonical errors** (`amkb.errors`) — 22 error codes in 5
   categories, as a typed exception hierarchy.
3. **Filter algebra** (`amkb.filters`) — `Eq` / `In` / `Range` /
   `And` / `Or` / `Not`, JSON-serializable via msgspec tags.
4. **Store protocol** (`amkb.store`) — `Store` and `Transaction` as
   `typing.Protocol` types. Implementations satisfy them structurally,
   without inheritance.
5. **Conformance suite** (`amkb.conformance`) — pytest functions
   mirroring the test matrix at
   [amkb-spec/conformance/](https://github.com/takyone/amkb-spec/tree/main/conformance).
   Any implementation can exercise the suite by providing a ``store``
   fixture and running `pytest --pyargs amkb.conformance`.

## Relationship to Spikuit

[Spikuit](https://github.com/takyone/spikuit) is a neural learning
graph and will be the first real consumer of `amkb`. Spikuit features
such as FSRS scheduling, APPNP propagation, and pressure dynamics live
on top of the AMKB protocol, not inside it. A future
`spikuit.amkb_adapter` module will expose Spikuit's internal state as
an `amkb.Store` without changing Spikuit's own vocabulary.

## Install

```bash
pip install amkb             # types, errors, filters, protocol
pip install amkb[test]       # + conformance suite deps (pytest)
```

`amkb` has one runtime dependency: [msgspec](https://jcristharif.com/msgspec/).

## Reading order

1. [amkb-spec](https://github.com/takyone/amkb-spec) — the normative
   protocol (authoritative).
2. `src/amkb/types.py` — data shapes.
3. `src/amkb/errors.py` — the 22 canonical codes.
4. `src/amkb/filters.py` — the filter algebra.
5. `src/amkb/store.py` — the `Store` and `Transaction` protocols.
6. `src/amkb/conformance/` — the executable test matrix.

## Implementing a Store

Any class whose shape matches the `Store` protocol is a valid AMKB
store. A minimal dict-backed implementation used as an executable
reference for the conformance suite lives in `tests/impls/dict_store.py`
— it is intentionally kept in tests rather than shipped as part of
the package, to reinforce that the SDK itself is backend-agnostic.

## License

Apache-2.0. See [LICENSE](LICENSE).
