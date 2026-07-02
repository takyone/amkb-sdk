# amkb — Python SDK for the Agent-Managed Knowledge Base protocol

> 🚧 **Not yet released as `0.1.0`.** This `0.0.x` version exists to
> reserve the name on PyPI while the protocol settles. The reference
> implementation (Spikuit's `amkb.Store` adapter) already passes
> L1/L2/L4a/L4b with the skips documented in "Relationship to
> Spikuit" below — the release gate for `0.1.0` is met; what remains
> is this repo's own packaging/CI process. Until `0.1.0` ships, the
> public API may change without notice. Track progress at
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

**Status:** Spikuit **v0.9.0** ships an `amkb.Store` adapter
(`spikuit_agents/src/spikuit_agents/amkb/`) backed by its
`spikuit-core` Circuit/Brain plumbing. Running the star-import
conformance wrapper (`spikuit-agents/tests/test_amkb_conformance.py`)
against it passes **31 tests with 12 documented skips and zero
failures**:

- **L1 (Core), L4a (Structural), L4b (Intent)** pass in full except
  for the gaps below.
- **L2 (Lineage)** passes except `test_L2_merge_02_kind_mismatch_rejected`
  (`KIND_CATEGORY` is not yet a Spikuit kind).
- **L3 (Transactional)** is entirely skipped: Spikuit's Circuit
  forbids nested/concurrent transactions and has no `revert()` yet;
  MVCC and revert are on the adapter's roadmap.
- Two L4a tests (`neighbors_04`, `walk_02`) skip because
  `REL_DERIVED_FROM` / `REL_ATTESTED_BY` have no `SynapseType`
  counterpart in Spikuit.
- One L4b test (`retrieve_03`) skips because Spikuit only exposes
  `type`/`domain`/`source` as queryable attrs, not free-form filters;
  another (`retrieve_02`) skips because the fixture happens to
  produce fewer than two scored hits against Spikuit's ISF — the
  shared conformance test itself treats that as trivially true rather
  than a capability gap.

This is the release gate for `amkb` 0.1.0: it ships once the
reference implementation passes L1/L2/L4a/L4b with only documented
skips, which is already the current state above. There is no
additional gate — the remaining work to ship 0.1.0 lives in this
repo (packaging, CI, docs), not in the reference implementation.

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

## Development

This repo's own baseline — unit tests plus the conformance suite run
against the in-tree `DictStore` — requires an **editable install**:
a non-editable install collides with the `src/` layout
(`ImportPathMismatchError`). A bare `pytest` invocation only collects
`tests/` (`testpaths = ["tests"]` in `pyproject.toml`) — 36 unit
tests, not the full baseline. Run both paths explicitly:

```sh
uv run --no-project --with pytest --with pytest-cov --with msgspec --with-editable . \
  python -m pytest tests src/amkb/conformance -q
```

Lint and type-check:

```sh
uv run --no-project --with ruff ruff check .
uv run --no-project --with ruff ruff format --check .
uv run --no-project --with mypy --with msgspec --with pytest --with-editable . mypy
```

The `mypy` invocation needs `--with pytest` alongside `--with-editable .`:
`packages = ["amkb"]` in `[tool.mypy]` checks the installed package,
and `amkb.conformance`'s submodules import pytest, so mypy needs it
resolvable in the same environment even though nothing in `amkb`
itself depends on it at runtime.

## License

Apache-2.0. See [LICENSE](LICENSE).
