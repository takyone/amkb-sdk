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
   L1 (Core), L2 (Lineage), L3 (Transactional), L4a (Structural), and
   L4b (Intent) all ship. See [Implementing a Store](#implementing-a-store)
   below for how a third-party implementation runs the suite —
   `pytest --pyargs amkb.conformance` does **not** work on its own;
   the star-import pattern documented there does.

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

### Running the conformance suite against your Store

`pytest --pyargs amkb.conformance` does **not** work by itself: pytest
only loads `conftest.py` files that are filesystem ancestors of the
files it collects, so when pytest collects test modules straight out
of the installed `amkb.conformance` package, a `conftest.py` sitting
at *your* repo root is never seen — your `store` fixture never
registers, and every test errors with "fixture 'store' not found."

The robust pattern — the same one used by
[Spikuit's adapter test](https://github.com/takyone/spikuit/blob/main/spikuit-agents/tests/test_amkb_conformance.py)
— is a star-import wrapper that pulls the test *functions* into a
module inside your own test tree, where your `conftest.py` **is** an
ancestor. Write exactly these two files:

```python
# tests/conftest.py
import pytest
from amkb.conformance.fixtures import actor  # noqa: F401  (re-export default actor fixture)
from my_package import MyStore

@pytest.fixture
def store():
    return MyStore()  # fresh, empty, function-scoped
```

```python
# tests/test_amkb_conformance.py
from amkb.conformance.test_l1_core import *          # noqa: F401,F403
from amkb.conformance.test_l2_lineage import *       # noqa: F401,F403
from amkb.conformance.test_l3_transactional import * # noqa: F401,F403
from amkb.conformance.test_l4a_structural import *   # noqa: F401,F403
from amkb.conformance.test_l4b_intent import *       # noqa: F401,F403
```

Then run `pytest` from your repo root as normal.

To opt out of a specific test (e.g. it encodes a decision your
implementation legitimately makes differently), redefine it below the
star imports:

```python
# tests/test_amkb_conformance.py (continued)
import pytest

@pytest.mark.skip(reason="documented deviation: <why>")
def test_L2_rewrite_01_updated_at_advances(store, actor):  # noqa: F811
    ...
```

### Fixture contract

- `store` — pytest fixture, function-scoped, yields a **fresh, empty**
  instance satisfying `amkb.store.Store` structurally.
- `actor` — pytest fixture providing an `amkb.types.Actor`. A default
  is exported from `amkb.conformance.fixtures`; override it in your
  own `conftest.py` if you need a specific identity.
- Capability flags — plain attributes on your `store` instance,
  default `False`/absent, each gating one or more L3 tests:
  - `supports_concurrency_detection`
  - `supports_merge_revert`
  - `supports_revert_conflict_detection`
  - `supports_commit_time_constraints`
- `setup_required_attribute_pair(actor)` — optional callable attribute
  on `store`, used only by the `supports_commit_time_constraints`
  test to construct a reserved-attribute dependency pair.
- Skip semantics: a skipped capability-gated test means "this
  implementation does not claim the capability," not a failure.

### Conformance claim

An implementation is **conformant at level X** when every test at
level X passes, with no skips other than capability-gated ones for
capabilities it does not claim.

## License

Apache-2.0. See [LICENSE](LICENSE).
