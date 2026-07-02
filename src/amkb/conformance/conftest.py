"""Shared pytest plumbing for ``amkb.conformance``.

Re-exports the default ``actor`` fixture so test modules in this
package can request it without importing it explicitly. Does NOT
provide a ``store`` fixture — implementations MUST provide their own
via the star-import pattern documented in the README's "Implementing
a Store" section (a ``conftest.py`` at a consumer's own repo root is
not visible to modules collected from inside this installed package).
"""

from amkb.conformance.fixtures import actor  # noqa: F401
