"""Executable AMKB conformance suite.

This package contains pytest test modules that mirror the human-readable
test matrix in `amkb-spec/conformance/`. L1 (Core), L2 (Lineage), L3
(Transactional), L4a (Structural), and L4b (Intent) all ship in this
release.

``pytest --pyargs amkb.conformance`` does **not** work standalone:
pytest only loads ``conftest.py`` files that are filesystem ancestors
of the files it collects, so a consumer's ``conftest.py`` at their own
repo root is never seen when collecting straight out of this
installed package — their ``store`` fixture never registers. The
supported pattern is a star-import wrapper in the consumer's own test
tree; see the "Implementing a Store" section of the README for the
exact two files to write and worked examples.

Fixture contract for implementers:

- ``store`` — pytest fixture, MUST be function-scoped, MUST yield a
  fresh, empty instance satisfying :class:`amkb.store.Store`
  structurally. Provided by the implementer, not this package.
- ``actor`` — pytest fixture providing an :class:`amkb.types.Actor`.
  A default is exported from :mod:`amkb.conformance.fixtures`;
  implementations MAY override it in their own ``conftest.py``.
- Capability flags (plain attributes on the ``store`` instance,
  default ``False``/absent): ``supports_concurrency_detection``,
  ``supports_merge_revert``, ``supports_revert_conflict_detection``,
  ``supports_commit_time_constraints``. Set a flag ``True`` to opt in
  to the corresponding L3 test(s); leave it unset/``False`` to skip
  them.
- ``setup_required_attribute_pair`` — optional callable attribute on
  ``store``, ``(actor: Actor) -> tuple[NodeRef, NodeRef]``, used only
  by the ``supports_commit_time_constraints``-gated test to construct
  a reserved-attribute dependency pair.
- Skip semantics: a skipped capability-gated test means "this
  implementation does not claim the capability," not a failure. It is
  not evidence of non-conformance at the level that test belongs to.

Conformance claim: an implementation is "conformant at level X" when
every test at level X passes, with no skips other than
capability-gated ones for capabilities it does not claim.

Example ``conftest.py`` for an implementation::

    import pytest
    from amkb.conformance.fixtures import actor  # noqa: F401
    from mystore import MyStore

    @pytest.fixture
    def store():
        return MyStore()

Then, in a ``tests/test_amkb_conformance.py`` in the same tree::

    from amkb.conformance.test_l1_core import *          # noqa: F401,F403
    from amkb.conformance.test_l2_lineage import *       # noqa: F401,F403
    from amkb.conformance.test_l3_transactional import * # noqa: F401,F403
    from amkb.conformance.test_l4a_structural import *   # noqa: F401,F403
    from amkb.conformance.test_l4b_intent import *       # noqa: F401,F403
"""

try:
    from amkb.conformance.fixtures import actor
except ModuleNotFoundError as exc:
    if exc.name == "pytest":
        raise ModuleNotFoundError(
            "amkb.conformance requires pytest. Install with `pip install amkb[test]`."
        ) from exc
    raise

__all__ = ["actor"]
