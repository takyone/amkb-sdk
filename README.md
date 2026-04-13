# amkb — Python SDK for the Agent-Managed Knowledge Base protocol

> 🚧 **Not yet usable.** This `0.0.x` release exists only to reserve
> the name on PyPI while the protocol settles. The first usable
> release will be `0.1.0`, gated on a real reference implementation
> (Spikuit adapter) passing the full conformance suite. Until then,
> the public API may change without notice and there is no install
> story worth recommending. Track progress at
> [amkb-spec](https://github.com/takyone/amkb-spec) and
> [amkb-sdk](https://github.com/takyone/amkb-sdk).

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
graph and is the first real consumer of `amkb`. Spikuit features
such as FSRS scheduling, APPNP propagation, and pressure dynamics live
on top of the AMKB protocol, not inside it.

**Status (2026-04):** Spikuit **v0.7.0** ships the `spikuit-core`
plumbing needed to back an adapter — soft-retire as the sole delete
path, a `changeset` / `event` log, an `async with circuit.transaction()`
wrapper, `neuron_predecessor` lineage, and a physical-purge escape
hatch via `spkt history prune`. The hot read/write paths stayed
byte-identical: 408 pre-existing tests pass unchanged, and the
spaced-repetition `fire()` path was deliberately kept off the event
log (+0.18% overhead in benchmark). The adapter module
(`spikuit_agents.amkb`) that surfaces these as an `amkb.Store` is
targeted at Spikuit v0.7.1 and will be gated on the full conformance
suite passing. At that point, `amkb==0.1.0` can ship with Spikuit as
its reference implementation.

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
