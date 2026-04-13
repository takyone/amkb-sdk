"""Shared pytest plumbing for ``amkb.conformance``.

Re-exports the default ``actor`` fixture so test modules in this
package can request it without importing it explicitly. Does NOT
provide a ``store`` fixture — implementations MUST provide their own
in the conftest of the repo that runs ``pytest --pyargs amkb.conformance``.
"""

from amkb.conformance.fixtures import actor  # noqa: F401
