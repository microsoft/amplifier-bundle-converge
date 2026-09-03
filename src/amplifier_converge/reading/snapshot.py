"""One look at the project, gathered once per page.

Everything the page shows comes from here, and everything here is read from the
project. There is no store behind this object: build it, render it, drop it.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from . import Reading
from .constraints import Constraints, read_constraints
from .documents import Document, read_direction
from .gitfacts import GitFacts, read_git
from .kept import Standing, read_promises
from .lanes import Board, read_board
from .proposals import Proposal, read_proposals
from .queue import QueueSummary, WorkItem, read_items, read_summary


@dataclass
class Snapshot:
    repo: Path
    project: str
    documents: Reading[list[Document]]
    #: Where each promise stands against reality, by the file it lives in.
    promises: Reading[dict[str, Standing]]
    proposals: Reading[list[Proposal]]
    board: Reading[Board]
    items: Reading[list[WorkItem]]
    queue: Reading[QueueSummary]
    constraints: Reading[Constraints]
    git: Reading[GitFacts]

    @property
    def notes(self) -> list[tuple[str, str]]:
        """Sentences about sources we genuinely could not read.

        Only where `available` is False. A source that answered and had
        nothing to say is not a problem, and saying so at the top of the page
        would train the reader to ignore the one box that matters.

        `promises` is deliberately not among them. A project with no record of
        whether its promises are kept already says so in the one place a reader
        is looking — the word beside each promise reads *Can't check* — and a
        banner at the top of every page would say it a second time, louder,
        about something no page but Direction shows.
        """
        out: list[tuple[str, str]] = []
        for reading in (
            self.documents,
            self.proposals,
            self.board,
            self.items,
            self.queue,
            self.constraints,
            self.git,
        ):
            if reading.note and not reading.available:
                out.append((reading.note, reading.detail))
        return out

    @property
    def truly_ready(self) -> list[WorkItem]:
        return [item for item in self.items.value if item.truly_ready]

    @property
    def waiting_on_you(self) -> list[WorkItem]:
        return [item for item in self.items.value if item.waiting_on_you]

    @property
    def working(self) -> list[WorkItem]:
        return [item for item in self.items.value if item.status == "held"]


def take(
    repo: Path,
    project: str,
    batch_dir: Path | None = None,
    include_remote_proposals: bool = True,
) -> Snapshot:
    repo = Path(repo)
    return Snapshot(
        repo=repo,
        project=project,
        documents=read_direction(repo),
        promises=read_promises(repo),
        proposals=read_proposals(repo, include_remote=include_remote_proposals),
        board=read_board(repo, batch_dir),
        items=read_items(repo, project),
        queue=read_summary(repo, project),
        constraints=read_constraints(repo),
        git=read_git(repo),
    )
