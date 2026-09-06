"""Converge — the readers and writers behind the app beside your project.

Reading: the project's documents, its code record, its work queue, its lanes.
Writing: the five writes the app is allowed to make. This package keeps nothing
of its own — every word it hands back is read from the project.

The page this package used to serve was retired on 2026-09-06, and
`contracts/surface.v1.md` was superseded on 2026-09-03. The app you open beside
a project is `app/`, started with `scripts/run-app.sh`; the promises it keeps
are in `contracts/experience.v1.md` and the experience family beneath it.
"""

__all__ = ["__version__"]

__version__ = "0.1.0"
