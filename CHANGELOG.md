# Changelog

All notable changes to `amkb` are documented in this file. The format
follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

Work preparing the `0.1.0` release — the first version intended for
real use. `0.1.0` has not shipped yet; this section will become the
`[0.1.0]` entry when it does. See the README's "Relationship to
Spikuit" section for the current release-gate status.

### Added

- `py.typed` marker (PEP 561) and a `Typing :: Typed` classifier —
  without these the typed Protocols/NewTypes were invisible
  downstream to type checkers.
- Top-level re-exports from `amkb`: `Node`, `Edge`, `Actor`, `Event`,
  `Store`, `Transaction` (the `amkb.store` Protocol), the Filter
  constructors (`Eq`, `In`, `Range`, `And`, `Or`, `Not`, `Filter`),
  `AmkbError`, and the `errors` submodule.
- `.github/workflows/ci.yml`: ruff check, ruff format --check, mypy
  (strict), and the full pytest baseline (unit tests + conformance
  suite) on Python 3.11/3.13/3.14.
- `supports_concurrency_detection` implemented on the in-tree
  `DictStore`, exercising an L3 capability-gated path that previously
  had no in-repo coverage.
- A "fixture contract" and a "conformant at level X" definition in
  the README and `amkb.conformance` docstring.
- A documented coverage-vs-matrix gap list for the four spec-matrix
  entries with no executable test yet (tracked for Phase B).
- Python 3.14 classifier and Issues/Changelog project URLs.

### Fixed

- The documented third-party conformance invocation
  (`pytest --pyargs amkb.conformance`) never actually worked: pytest
  only loads `conftest.py` files that are filesystem ancestors of the
  collected test files, so a consumer's `store` fixture was never
  seen. The README now documents the star-import wrapper pattern
  (already used by Spikuit's adapter test) that does work.
- `test_L4b_retrieve_02_score_ordering_monotone`: a `float | None`
  comparison that mypy strict correctly flagged (the list
  comprehension's `is not None` filter didn't narrow the type on
  later attribute access).
- Assorted false/future-tense claims in the README and internal
  docstrings — e.g. "gated on the full conformance suite passing",
  "Only L1 (Core) tests are shipped in this release" (L1-L4b all
  ship), "picked up regardless of where the installed package lives"
  (root `conftest.py`, wrong under pytest's conftest-discovery rules).
- 92 ruff findings and 5 unformatted files.

### Changed

- `pyproject.toml` description: dropped "reference implementation"
  — the SDK intentionally ships no storage backend.
- `pyproject.toml` license: PEP 639 SPDX expression (`"Apache-2.0"`)
  instead of the deprecated `license = { text = ... }` + classifier
  pair.

## [0.0.1] - 2026-04-13

Placeholder release reserving the `amkb` name on PyPI while the
protocol settles. No install story worth recommending; the public API
could change without notice.
