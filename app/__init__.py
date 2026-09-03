"""The Converge companion app — the page beside your project.

Three seams live here, one per lane: this package's backend (config, auth,
data, writes, serve), the frontend's templates and static files, and the
tmux viewer's router. Nothing here invents data: every field a screen shows
is read from a real file, a real git history, or a real tmux socket, and a
thing that is not there says so rather than showing a placeholder.
"""

__all__ = ["__version__"]

__version__ = "0.1.0"
