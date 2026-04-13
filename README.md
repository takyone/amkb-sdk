# amkb — Python SDK for the Agent-Managed Knowledge Base protocol

> **Status: Pre-alpha (v0.1.0).** This package tracks [amkb-spec](https://github.com/takyone/amkb-spec)
> v0.2.0 and is under active development. APIs may change without notice.

`amkb` provides:

1. **Core types** (`amkb.types`) — `Node`, `Edge`, `Actor`, `Transaction`,
   `ChangeSet`, `Event`, and the 22 canonical error codes.
2. **Store protocol** (`amkb.store.Store`) — a structural Python
   protocol matching the operation signatures in
   [spec/03-operations.md](https://github.com/takyone/amkb-spec/blob/main/spec/03-operations.md).
3. **Reference implementation** (`amkb.reference`) — a minimal
   SQLite-backed store that passes L1 conformance. Built for clarity,
   not performance.
4. **Executable conformance suite** (`amkb.conformance`) — pytest
   functions mirroring the human-readable test matrix in
   [amkb-spec/conformance/](https://github.com/takyone/amkb-spec/tree/main/conformance).
   Any implementation can run the suite against itself via
   `pytest --pyargs amkb.conformance`.

## Relationship to Spikuit

[Spikuit](https://github.com/takyone/spikuit) is a neural learning
graph that will use `amkb` as its knowledge-layer substrate. Spikuit
features such as FSRS scheduling, APPNP propagation, and pressure
dynamics live on top of the AMKB protocol, not inside it. A future
`spikuit.amkb_adapter` module will expose Spikuit's internal state as
an `amkb.Store` without changing Spikuit's own vocabulary.

## Install

```bash
pip install amkb             # core types + protocol
pip install amkb[reference]  # + reference SQLite impl
pip install amkb[test]       # + conformance suite deps
```

## Reading order

1. [amkb-spec](https://github.com/takyone/amkb-spec) — the normative
   protocol (authoritative)
2. `src/amkb/types.py` — data shapes
3. `src/amkb/store.py` — the Store protocol
4. `src/amkb/reference/sqlite_store.py` — a worked implementation

## License

Apache-2.0. See [LICENSE](LICENSE).
