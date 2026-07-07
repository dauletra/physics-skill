# Project: worksheet-builder skill

This repo *is* a single Claude skill (`worksheet-builder/`) plus a scratch
output folder (`preview-worksheet/`). There's no app to build or test suite to
run — "development" here means editing the skill's SKILL.md/references/script
and validating by rendering the example workspace.

## Core architectural rule

The skill never hand-writes the final worksheet HTML. Content lives in small
JSON files (`meta.json` + `tasks/task-NN.json`); `scripts/render_worksheet.py`
deterministically renders them into HTML. This split exists so that editing
one task doesn't require reading/rewriting the whole document. **Don't
reintroduce hand-authored HTML output** when touching this skill — if a
change needs new visual behavior, change the renderer/CSS, not per-task HTML.

Only Russian (`meta.json → "language": "ru"`) is supported. Fixed UI chrome
strings live in `STRINGS`/`UI_STRINGS` in the script. Don't add
per-language content fields (`prompt_ru`, etc.) to the task schema.

## Where things live

- `worksheet-builder/SKILL.md` — the workflow Claude follows when using the skill
- `worksheet-builder/references/task-schema.md` — JSON schema for meta.json + every task type
- `worksheet-builder/references/design-system.md` — CSS design tokens (fonts, margins, header, numbering, the side-by-side chart/illustration layout). Keep this in sync with `BASE_CSS` in the script whenever you change either.
- `worksheet-builder/references/charts-and-graphs.md` — `chart_spec` format and the B&W-safe visual code
- `worksheet-builder/references/symbols.md` — the text > `<sup>`/`<sub>` > LaTeX priority rule for any non-ASCII notation, plus a Greek-alphabet table and a list of Greek letters that are visually identical to Latin letters in the design-system font stack (verified by rendering, not guessed). This project's specific convention: velocity is `υ` (upsilon), not Latin `v` — `v` renders indistinguishable from `ν` (nu, frequency) in this font. Don't "simplify" example content back to Latin `v` for velocity without re-reading this file.
- `worksheet-builder/scripts/render_worksheet.py` — the only place that generates HTML. Illustration templates live here too, in the `SVG_SNIPPETS` dict (`_snippet_inclined_plane`, `_snippet_simple_circuit`) — there is deliberately no `assets/svg-snippets/` folder; don't recreate one without also wiring it into the loader. `esc()` deliberately passes through literal `<sup>`/`<sub>` tags (see `SUPSUB_TAGS`) instead of escaping everything — that's what lets task JSON use them per `symbols.md`; don't replace `esc()` calls with raw `html.escape()`. There's no printed page-number footer — instead `LAYOUT_JS`'s `paginate()` splits the on-screen flow into `.a4-page` cards (a JS-computed approximation of print pagination, not a hand-authored one) and a separate, extensible top toolbar (`GLOBAL_TOOLBAR_TOOLS`/`buildGlobalToolbar()`, distinct from the per-task `.layout-toolbar`/`CONTROL_GROUPS`) lets the teacher swap print-margin presets live; see `references/design-system.md`'s "Page-view" section for how these fit together, including why the CSS-only path (not a hidden HTML footer) was chosen and why the "Minimum" margin preset is a documented approximation rather than an exact Chrome value.
- `worksheet-builder/examples/kinematics-9th-grade/` — a worked draft covering every task type (12 task files — task-09 demonstrates the text/sup-sub/LaTeX symbol hierarchy, task-10 is a `compound` task, task-12 is `multiple_choice`), used for manual testing
- `preview-worksheet/` — a generated copy of the main (`ru`) example, kept at the project root purely so a human can open the rendered HTML. **Not part of the skill.** Safe to overwrite/regenerate; don't fold it back into `worksheet-builder/`.

## How to validate a change

No automated tests. After editing `render_worksheet.py` or the CSS:

```bash
python worksheet-builder/scripts/render_worksheet.py preview-worksheet
```

then open `preview-worksheet/output/worksheet-teacher.html` (has both the
questions and the answer blocks, so one file shows everything) in the Preview
tool and check it visually — especially after CSS changes, since a selector
that's too broad tends to leak into places it shouldn't (e.g. a past bug where
`svg { width: 100% }` scoped to the visual column also stretched the tiny
chart-legend icons — fixed by scoping to `svg.visual-svg` specifically).
After touching `LAYOUT_JS` specifically (pagination, either toolbar), the
static screenshot isn't enough — actually click through the top toolbar's
margin presets and a per-task toolbar control in the Preview tool and confirm
`.a4-page` count/padding update and the DOM doesn't get duplicated (this has
regressed silently before).

## Known trade-offs (don't "fix" these without asking)

- **The generated worksheet assumes the teacher is always online** when
  opening/printing it. Lean into online tools/CDNs fully instead of adding
  offline fallbacks, vendoring assets, or feature-detecting connectivity —
  that's deliberate scope-narrowing, not an oversight to patch.
- KaTeX loads from a CDN (jsdelivr), not bundled locally — keeps generated
  HTML small, but means viewing/printing needs internet. This is an instance
  of the online-only assumption above, not a one-off exception.
- Exception to the above: the teacher can genuinely be offline at the moment
  they open/print the file (e.g. printing at school with no/spotty wifi), so
  `KATEX_HEAD`'s `if (window.renderMathInElement)` guard in
  `render_worksheet.py` stays — it's not "offline support" (formulas still
  render as raw `$...$` if KaTeX didn't load, no fallback rendering is added),
  it just avoids an uncaught JS exception when the CDN script never arrived.
  Keep this guard; don't make the call unconditional.
- Chart/illustration SVG viewBox dimensions are tuned for the ~36%-width side
  column they render in (see comment in `build_chart_svg`), not for full page
  width — if you resize that column, the font-size/stroke-width constants in
  the SVG generators likely need retuning too, not just the CSS flex-basis.
