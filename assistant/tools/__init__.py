"""Importing this package registers all built-in tools."""
from .base import registry, tool  # noqa: F401
from . import builtin  # noqa: F401  (side effect: registers tools)
