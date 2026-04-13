"""Executable AMKB conformance suite.

This package contains pytest test modules that mirror the human-readable
test matrix in `amkb-spec/conformance/`. Any implementation of the
:class:`amkb.store.Store` Protocol can exercise the suite by providing
a ``store`` fixture and running::

    pytest --pyargs amkb.conformance

Contract for implementers:

- Provide a pytest fixture named ``store`` that yields a **fresh,
  empty** ``amkb.store.Store``-compatible instance. The fixture SHOULD
  be function-scoped so every test gets an isolated store.
- The suite imports a default ``actor`` fixture from this package;
  implementations MAY override it in their own ``conftest.py`` if they
  need a specific Actor identity.

Example ``conftest.py`` for an implementation::

    import pytest
    from mystore import MyStore

    @pytest.fixture
    def store():
        return MyStore()

Then from the implementation repo root::

    pytest --pyargs amkb.conformance

Only L1 (Core) tests are shipped in this release. L2, L3, L4a, and
L4b suites will be added as the matrix in amkb-spec stabilises.
"""

from amkb.conformance.fixtures import actor

__all__ = ["actor"]
