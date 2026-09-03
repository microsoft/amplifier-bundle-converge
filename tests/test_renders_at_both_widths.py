"""Surface.v1 clause 10 and the kit's "renders at 390 and 1280 with nothing cut off".

A browser is not needed to check this, and using one would only tell us about
one browser. What actually causes a page to overflow at 390 pixels is a small,
enumerable set of CSS mistakes — a fixed width wider than the viewport, a grid
child that cannot shrink, a code block or table that cannot scroll. Each of
those is asserted directly against the stylesheet and the markup.
"""

from __future__ import annotations

import re

import pytest

from amplifier_converge.web.styles import STYLESHEET

NARROW = 390
WIDE = 1280

PAGES = ("/", "/direction", "/direction/VISION", "/direction/gate.v1", "/operation")

FIXED_WIDTH = re.compile(r"(?<!max-)(?<!min-)\bwidth\s*:\s*(\d+(?:\.\d+)?)px")
MIN_WIDTH_QUERY = re.compile(r"@media\s*\(min-width\s*:\s*(\d+)px\)")


def _declarations() -> list[str]:
    return [line.strip() for line in STYLESHEET.splitlines()]


def test_the_viewport_is_declared_on_every_page(client):
    for page in PAGES:
        html = client.get(page).text
        assert 'name="viewport"' in html, f"{page} has no viewport declaration"
        assert "width=device-width" in html, f"{page} does not follow the device width"


def test_nothing_is_pinned_wider_than_the_narrow_screen():
    offenders = []
    for line in _declarations():
        for match in FIXED_WIDTH.finditer(line):
            if float(match.group(1)) > NARROW:
                offenders.append(line)
    assert not offenders, f"these would overflow a {NARROW}px screen: {offenders}"


def test_everything_measures_itself_border_box():
    assert "box-sizing:border-box" in STYLESHEET.replace(" ", "")


def test_long_words_wrap_rather_than_push_the_page_wide():
    assert "overflow-wrap:anywhere" in STYLESHEET.replace(" ", "")


def test_code_blocks_and_tables_scroll_inside_themselves():
    condensed = STYLESHEET.replace(" ", "").replace("\n", "")
    assert "max-width:100%;overflow-x:auto" in condensed, "code blocks can push the page wide"
    assert "table{width:100%;max-width:100%" in condensed, "tables can push the page wide"


def test_grid_children_are_allowed_to_shrink():
    """A grid track of `1fr` has a minimum size of `auto`, which is what
    actually causes overflow. Every track must be `minmax(0, …)`."""
    for match in re.finditer(r"grid-template-columns\s*:\s*([^;]+);", STYLESHEET):
        tracks = match.group(1)
        assert "minmax(0" in tracks, f"this track cannot shrink: {tracks}"


def test_the_two_column_shell_only_appears_when_there_is_room():
    """Base rules are the narrow layout — every grid there is a single column.

    Side-by-side columns are what actually cuts content off on a phone, so the
    rule is not "no grids before the media query" but "no grid with more than
    one track before it".
    """
    base, _, _ = STYLESHEET.partition("@media")
    for match in re.finditer(r"grid-template-columns\s*:\s*([^;}]+)", base):
        tracks = match.group(1)
        assert "repeat(" not in tracks and tracks.count("minmax(") <= 1, (
            f"a side-by-side layout is not behind a media query: {tracks}"
        )
    widths = [int(w) for w in MIN_WIDTH_QUERY.findall(STYLESHEET)]
    assert widths, "there is no wide breakpoint at all"
    for width in widths:
        assert NARROW < width <= WIDE, f"a breakpoint at {width}px serves neither width"


def test_answer_controls_are_large_enough_for_one_handed_use():
    condensed = STYLESHEET.replace(" ", "")
    assert "--tap:46px" in condensed
    assert "min-height:var(--tap)" in condensed


@pytest.mark.parametrize("page", PAGES)
def test_pages_are_server_rendered_with_no_script_at_all(client, page):
    html = client.get(page).text
    assert "<script" not in html.lower(), f"{page} carries script"
    assert "http://" not in html.replace("http://127.0.0.1", ""), f"{page} reaches off the machine"
    assert "https://" not in html, f"{page} loads something from a content network"
    assert html.lstrip().startswith("<!doctype html>")


def test_technical_words_never_reach_the_deciding_sentence(client):
    """Documents.v1 clause 11: technical detail is folded, never in the
    sentence a person decides on. This checks the app's own words — a work
    item's title is the project's own vocabulary, not the app's."""
    import re

    jargon = ("yaml", "json", "stdout", "subprocess", "worktree", "http", ".beads")
    for page in PAGES:
        html = client.get(page).text
        body = html.split('<main id="main">', 1)[1].split("</main>")[0]
        outside_folds = re.sub(r"<details>.*?</details>", "", body, flags=re.S)
        text = re.sub(r"<[^>]+>", " ", outside_folds).lower()
        for word in jargon:
            assert word not in text, f"{page} says “{word}” outside a Details fold"
