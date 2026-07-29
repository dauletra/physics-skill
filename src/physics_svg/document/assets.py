"""Static blobs pasted into the generated HTML: the KaTeX snippet and the
stylesheet. No rendering logic — only strings.

The document is a plain on-screen page: one centred column of readable width,
white background, pixels. There is no print layout here and none is coming —
no `@page`, no `@media print`, no pagination. That is a decision, not an
omission.

KaTeX is the only client-side script, and it is loaded from a CDN: formulas
need the network. The `window.renderMathInElement` guard is not offline
support — it stops an unhandled exception when the script has not loaded.
"""

from __future__ import annotations

KATEX_VERSION = "0.16.11"

KATEX_HEAD = f"""
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@{KATEX_VERSION}/dist/katex.min.css">
<script defer src="https://cdn.jsdelivr.net/npm/katex@{KATEX_VERSION}/dist/katex.min.js"></script>
<script defer src="https://cdn.jsdelivr.net/npm/katex@{KATEX_VERSION}/dist/contrib/auto-render.min.js"></script>
<script>
document.addEventListener("DOMContentLoaded", function () {{
    if (window.renderMathInElement) {{
        renderMathInElement(document.body, {{
            delimiters: [
                {{left: "$$", right: "$$", display: true}},
                {{left: "$", right: "$", display: false}}
            ]
        }});
    }}
}});
</script>
""".strip()

BASE_CSS = """
:root { --font-main: "PT Sans", "Segoe UI", Verdana, Arial, sans-serif; }
* { box-sizing: border-box; }
html { background: #fff; }
body {
    font-family: var(--font-main);
    font-size: 12pt;
    line-height: 1.4;
    color: #000;
    background: #fff;
    max-width: 800px;
    margin: 0 auto;
    padding: 24px 32px;
}
.sheet-header { border-bottom: 1.5px solid #000; padding-bottom: 15px; margin-bottom: 23px; }
.meta-line { font-size: 11pt; margin-bottom: 11px; }
.meta-line .blank {
    display: inline-block; min-width: 105px; border-bottom: 1px solid #000; margin: 0 8px;
}
.sheet-title { font-size: 16pt; font-weight: bold; margin: 0 0 4px 0; }
.sheet-subtitle { font-size: 10.5pt; color: #333; margin: 0 0 11px 0; }
.sheet-instructions { font-style: italic; font-size: 11pt; margin: 8px 0 0 0; }
/* Section subheading (`heading`). Inside a task there are no headings — the
   hierarchy there is drawn by the task number and the subtask letters. */
.doc-heading { font-size: 13.5pt; font-weight: bold; margin: 20px 0 8px 0; }
.task { margin: 0 0 26px 0; }
.task-header { display: flex; align-items: baseline; gap: 8px; margin-bottom: 8px; }
.task-num { font-weight: bold; font-size: 12pt; flex: 0 0 auto; }
.subtask-label { font-weight: bold; font-size: 12pt; flex: 0 0 auto; }
.task-points { font-size: 9pt; color: #333; }
.answer-line {
    display: inline-block; min-width: 150px; border-bottom: 1px solid #000; margin-left: 8px;
}
.bank-list { margin-top: 8px; font-size: 11pt; }
/* Without this hint `single` and `multiple` are indistinguishable to a
   student: both render as the same list of options. */
.choice-hint { font-style: italic; font-size: 10.5pt; margin-top: 8px; }
/* The same equal-columns grid as .task-row — one CSS language for "beside". */
.match-columns {
    display: grid; grid-auto-flow: column; grid-auto-columns: 1fr;
    gap: 45px; align-items: start; margin-top: 8px;
}
/* One list markup for options, statements, ranked items and plain bullets. */
.list-component { margin-top: 8px; }
.list-row { display: flex; align-items: baseline; gap: 8px; padding: 5px 8px; }
.list-marker { font-weight: bold; flex: 0 0 auto; }
.list-content { flex: 1 1 auto; min-width: 0; }
.list-component.cols-single .list-row:nth-child(even) { background: #f2f2f2; }
.list-component.cols-two { display: block; column-count: 2; column-gap: 30px; }
.list-component.cols-two .list-row { display: block; margin-bottom: 6px; break-inside: avoid-column; }
.list-component.cols-inline { display: block; }
.list-component.cols-inline .list-row { display: inline-block; margin-right: 23px; }
/* "Statement on the left, control on the right" inside a list row — shared
   by true_false, rank and classify. */
.tf-line { display: flex; align-items: center; justify-content: space-between; width: 100%; gap: 15px; }
.tf-statement { flex: 1; }
.tf-box { display: inline-flex; align-items: center; gap: 6px; font-size: 10pt; white-space: nowrap; }
.tf-square, .rank-square {
    display: inline-block; width: 17px; height: 17px; border: 1.3px solid #000;
    text-align: center; line-height: 16px; font-weight: bold; font-size: 9pt;
}
.rank-square { flex: 0 0 auto; }
.table-component { border-collapse: collapse; width: 100%; margin-top: 8px; }
.table-component th, .table-component td {
    border: 1px solid #000; padding: 6px 9px; text-align: center; font-size: 11pt;
}
.table-component th { background: #eee; }
.fill-blank {
    display: inline-block; min-width: 68px; border-bottom: 1px solid #000;
    margin: 0 4px; text-align: center;
}
/* Answers section: separated by a rule, one line per question — the task
   number (and subtask letter) on the left, the compact answer on the right.
   flex-start rather than baseline: a plotted answer's first baseline is deep
   inside the picture, and the number would slide down with it. */
.answers-section { margin-top: 34px; border-top: 1.5px solid #000; padding-top: 15px; }
.answers-title { font-size: 13.5pt; font-weight: bold; margin-bottom: 8px; }
.answers-item { display: flex; align-items: flex-start; gap: 8px; margin-bottom: 5px; font-size: 11pt; }
.answers-num { font-weight: bold; flex: 0 0 auto; }
.answers-body { flex: 1 1 auto; min-width: 0; }
.answers-explanation { font-style: italic; color: #333; }
/* Blocks of a task stack down the column; the only way to put blocks side by
   side is the `row` container. */
.task-block { margin-bottom: 8px; }
.task-block:last-child { margin-bottom: 0; }
/* Illustrations carry their own width and height in pixels — the frame is
   known exactly — so the page only has to keep them inside a narrow column.
   A stretched ruling is the exception: it has no intrinsic ratio, and its
   height attribute is the author's data, so `height: auto` must not touch it. */
svg.visual-svg { display: block; max-width: 100%; }
svg.visual-svg:not(.visual-fluid) { height: auto; }
/* A subtask is indented from the task's shared statement. */
.task-part { margin: 11px 0 11px 23px; }
/* Layout container `row`: children share the line equally. An equal-columns
   grid accounts for the gap itself — no inline width arithmetic from Python. */
.task-row {
    display: grid; grid-auto-flow: column; grid-auto-columns: 1fr;
    gap: 23px; align-items: start; margin-bottom: 8px;
}
.task-row:last-child { margin-bottom: 0; }
.task-col { min-width: 0; }
.task-col .task-part { margin-left: 0; }
""".strip()
