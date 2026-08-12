"""The generated site — the part of it a browser can silently ignore.

The showcase promises that every sheet on it is the renderer's own output, so
the document stylesheet is scoped and pasted into a themed page. A selector
that comes out malformed costs nothing visible at build time: the browser
drops the rule and the preview quietly stops matching the printed sheet.
That is what these tests are for.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))

import build_site  # noqa: E402
import build_skill  # noqa: E402
from physics_svg.document.assets import BASE_CSS  # noqa: E402
from physics_svg.presentation import load_workspace as load_lesson  # noqa: E402
from physics_svg.presentation.slides import load_all as load_slides  # noqa: E402
from physics_svg.visuals import load_all as load_visuals  # noqa: E402

RULE = re.compile(r"([^{}]+)\{([^}]*)\}", re.S)


def rules() -> list[tuple[str, str]]:
    scoped = build_site._scoped_css()
    return [(m.group(1).strip(), m.group(2).strip()) for m in RULE.finditer(scoped)]


class TestGalleryCards:
    """A card that arranges its own pictures has to arrange all of them.

    Otherwise the page silently splits in two: a tour through cases, and a
    tail of unexplained examples that the author never noticed appearing.
    """

    def test_placed_specs_exist_and_cover_the_type(self) -> None:
        for entry in load_visuals().values():
            card = entry.doc("card.md").read_text(encoding="utf-8")
            placed = [match.group(1).strip() for match in build_site.SPEC_FENCE.finditer(card)]
            if not placed:
                continue  # a plain card: the page lists the specs itself
            assert sorted(placed) == sorted(path.stem for path in entry.specs), (
                f"{entry.tag}/card.md расставляет {sorted(placed)}, "
                f"а спеки — {sorted(path.stem for path in entry.specs)}"
            )


class TestSlidesPage:
    """The one page the site cannot render for itself.

    Everything else in the showcase is HTML, so the page shows it. A slide is
    a `.pptx`, and a page cannot show one — drawing a picture of a slide
    would mean a second renderer, which is the one thing the design forbids.
    So the page names every template and hands over the deck that holds them.
    """

    def test_every_template_is_named_and_shipped(self) -> None:
        page = build_site._slides_page()
        for entry in load_slides().values():
            name = f"slides-{entry.tag}.pptx"
            assert name in page, f"колода вида '{entry.tag}' не попала на страницу"
            deck = build_site.DOCS / "assets" / name
            assert deck.read_bytes().startswith(b"PK"), name
            for template in entry.templates:
                assert template.slug in page, f"'{entry.tag}/{template.slug}' не назван"

    def test_every_kind_reaches_the_page(self) -> None:
        page = build_site._slides_page()
        for entry in load_slides().values():
            heading = entry.card.read_text(encoding="utf-8").splitlines()[0].lstrip("# ")
            assert f"## {heading}" in page, f"карточка вида '{entry.tag}' не попала на страницу"

    def test_it_offers_a_presentation_that_builds(self) -> None:
        assert "assets/example-presentation.pptx" in build_site._slides_page()
        # The link is only worth anything if the lesson behind it still builds.
        from physics_svg.presentation.pptx.deck import build_deck

        lesson = load_lesson(build_site.EXAMPLE)
        deck, _ = build_deck(lesson.presentation, lesson.slides)
        assert deck.startswith(b"PK")


class TestHandwrittenPages:
    """A page may only offer a download the site actually produces.

    `--strict` checks links between pages and says nothing about what lives
    in `assets/`, so a stale download breaks silently: the front page went on
    offering `example-presentation.html` for a while after the presentation
    had become a `.pptx`, and the build stayed green.
    """

    def test_every_offered_asset_is_one_the_build_writes(self) -> None:
        builder = (REPO / "tools" / "build_site.py").read_text(encoding="utf-8")
        # The archive is the one asset named at run time, out of the bundle's
        # own name; everything else stands in the builder as a literal.
        by_name = f"{build_skill.BUNDLE_NAME}-skill.zip"
        pages = sorted(p for p in build_site.DOCS.glob("*.md") if p.name not in GENERATED_PAGES)
        for page in pages:
            for name in set(re.findall(r"assets/([A-Za-z0-9._-]+)", page.read_text("utf-8"))):
                assert name in builder or name == by_name, (
                    f"{page.name} предлагает assets/{name}, "
                    "а tools/build_site.py такого файла не пишет"
                )


#: Pages the builder generates itself — their links are its own business.
GENERATED_PAGES = {"questions.md", "slides.md"}


class TestScopedStylesheet:
    def test_no_comment_survives_into_a_selector(self) -> None:
        # A comment left in a selector list makes the whole list invalid.
        for selectors, _body in rules():
            assert "/*" not in selectors and "*/" not in selectors, selectors

    def test_every_selector_is_confined_to_the_wrapper(self) -> None:
        for selectors, _body in rules():
            for selector in selectors.split(","):
                assert selector.strip().startswith(f".{build_site.PREVIEW_CLASS}"), selector

    def test_nothing_is_lost_on_the_way(self) -> None:
        """Every rule of the stylesheet reaches the page.

        Counted rather than compared: the transformation is the point of the
        function, but a rule silently disappearing is the bug it had.
        """
        source = re.sub(r"/\*.*?\*/", "", BASE_CSS, flags=re.S)
        expected = [m for m in RULE.finditer(source) if m.group(2).strip()]
        # Plus the one rule the site appends to frame the sheet.
        assert len(rules()) == len(expected) + 1

    def test_the_page_level_rules_become_the_wrapper(self) -> None:
        """`body`/`html`/`:root` describe the sheet, not everything on it."""
        wrapper = f".{build_site.PREVIEW_CLASS}"
        for selectors, body in rules():
            if "--font-main" in body:  # the `:root` rule
                assert selectors == wrapper
