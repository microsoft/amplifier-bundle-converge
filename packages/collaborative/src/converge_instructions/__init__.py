"""Portable text resources; composing them does not start or configure a runtime."""

from importlib.resources import files


def instruction(role: str) -> str:
    """Return the shared collaboration guidance and one role's instructions.

    Direct resource readers remain supported, but need to include
    ``instructions/collaboration.md`` themselves. This helper performs no
    recursive mention resolution and reads only the two named package files.
    """
    if role not in {"manager", "supervisor"}:
        raise ValueError("role must be 'manager' or 'supervisor'")
    resources = files(__package__).joinpath("instructions")
    return "\n\n".join(
        resources.joinpath(name).read_text(encoding="utf-8").rstrip()
        for name in ("collaboration.md", f"{role}.md")
    ) + "\n"
