"""Shim to make ``app`` importable as a top‑level module in tests.

The tests import modules like ``app.database``.  Creating this package
at the repository root keeps the import paths short while preserving the
original backend package structure.
"""

# Re‑export the backend subpackage
# Provide convenient re‑exports so tests can ``import app.<module>``.
# The backend code lives in backend/app, so we expose that subpackage
# under the top‑level ``app`` package.
from .backend import app  # noqa: F401
