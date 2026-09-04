"""Fixture stand-in for the candidate guard.

The fixtures exist to be RUN, not just read: rules 3b and 6b stand this
miniature repository up as a real session, and a bundle whose hook names a
module that is not there cannot be stood up at all. The guard's real behaviour
is not what rules 7a and 7b judge — they read the hook's *configuration* out of
`behaviors/sample.yaml` — so what this file must provide is a real, mountable
module, not a second implementation of the guard.

It registers one `tool:pre` handler that allows every call. Deliberately inert:
a fixture that actually denied writes would fail for a reason that has nothing
to do with the promise under test.
"""

from __future__ import annotations

from typing import Any

__all__ = ["mount"]


def mount(coordinator: Any, config: dict[str, Any] | None = None) -> Any:
    """Register the inert handler; return the unregister callable."""

    async def _allow(event: str, data: dict[str, Any]) -> None:
        return None

    coordinator.hooks.register("tool:pre", _allow, priority=5)

    def unmount() -> None:
        coordinator.hooks.unregister("tool:pre", _allow)

    return unmount
