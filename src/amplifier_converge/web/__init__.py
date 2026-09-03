"""The companion web page.

Importing `create_app` needs the optional `web` extra installed:

    uv run --extra web amplifier-converge web --repo . --port 8091
"""

from __future__ import annotations

__all__ = ["create_app"]


def __getattr__(name: str):
    if name == "create_app":
        from .app import create_app

        return create_app
    raise AttributeError(name)
