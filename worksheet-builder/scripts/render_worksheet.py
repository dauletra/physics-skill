#!/usr/bin/env python3
"""Render a worksheet draft (meta.json + tasks/*.json) into printable HTML.

Usage:
    python render_worksheet.py <workspace_dir>
    python render_worksheet.py <workspace_dir> --task task-03

The first form writes <workspace_dir>/output/worksheet-student.html and
worksheet-teacher.html. The second form writes <workspace_dir>/task-03.preview.html
containing just that one task, for a cheap visual check without a full rebuild.
"""
import argparse
import html
import json
import re
import string
import sys
from pathlib import Path

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
:root {
    --font-main: "PT Sans", "Segoe UI", Verdana, Arial, sans-serif;
    /* Screen-only page margin, driven by the print-margin preset toolbar
       (applyMarginPreset() in LAYOUT_JS). Mirrors @page's margin below —
       the two are kept in sync at runtime, not just at generation time. */
    --page-margin: 15mm 15mm 15mm 18mm;
}
@page { size: A4; margin: 15mm 15mm 15mm 18mm; }
* { box-sizing: border-box; }
html { background: #fff; }
body {
    font-family: var(--font-main);
    font-size: 12pt;
    line-height: 1.4;
    color: #000;
    background: #fff;
    /* Full A4 sheet with real margins (matches @page above), not just the
       177mm text column — so screen shows a proper white margin around the
       text, like Google Docs/Word, instead of text flush against the edge. */
    width: 210mm;
    margin: 0 auto;
    padding: var(--page-margin);
}
.sheet-header { border-bottom: 1.5px solid #000; padding-bottom: 4mm; margin-bottom: 6mm; }
.meta-line { font-size: 11pt; margin-bottom: 3mm; }
.meta-line .blank { display: inline-block; min-width: 28mm; border-bottom: 1px solid #000; margin: 0 2mm; }
.sheet-title { font-size: 16pt; font-weight: bold; margin: 0 0 1mm 0; }
.sheet-subtitle { font-size: 10.5pt; color: #333; margin: 0 0 3mm 0; }
.sheet-instructions { font-style: italic; font-size: 11pt; margin: 2mm 0 0 0; }
.task { margin: 0 0 7mm 0; break-inside: avoid; page-break-inside: avoid; }
.task-header { display: flex; align-items: baseline; gap: 2mm; margin-bottom: 2mm; }
.task-num { font-weight: bold; font-size: 12pt; flex: 0 0 auto; }
.task-points { font-size: 9pt; color: #333; }
.task-prompt { flex: 1 1 auto; min-width: 0; margin: 0; }
.solution-area { margin-top: 2mm; }
.solution-line { border-bottom: 1px dotted #000; height: 7mm; }
.answer-line { display: inline-block; min-width: 40mm; border-bottom: 1px solid #000; margin-left: 2mm; }
.answer-block {
    margin-top: 2mm; padding: 2mm 3mm; border: 1px dashed #000; font-size: 11pt;
    background: repeating-linear-gradient(45deg, #fff, #fff 4px, #f2f2f2 4px, #f2f2f2 5px);
}
.matching-columns { display: flex; gap: 12mm; margin-top: 2mm; }
.matching-columns ol { margin: 0; padding-left: 6mm; }
.matching-columns li { margin-bottom: 1.5mm; }
.tf-row { display: flex; align-items: center; gap: 4mm; padding: 1.2mm 2mm; }
.tf-row:nth-child(even) { background: #f2f2f2; }
.tf-row .tf-statement { flex: 1; }
.tf-box { display: inline-flex; align-items: center; gap: 1.5mm; font-size: 10pt; }
.tf-square {
    display: inline-block; width: 4.5mm; height: 4.5mm; border: 1.3px solid #000;
    text-align: center; line-height: 4.2mm; font-weight: bold; font-size: 9pt;
}
.fill-table { border-collapse: collapse; width: 100%; margin-top: 2mm; }
.fill-table th, .fill-table td {
    border: 1px solid #000; padding: 1.5mm 2.5mm; text-align: center; font-size: 11pt;
}
.fill-table th { background: #eee; }
.fill-blank { display: inline-block; min-width: 18mm; border-bottom: 1px solid #000; margin: 0 1mm; text-align: center; }
.fill-blank.answered { border-bottom: none; font-weight: bold; text-decoration: underline; }
.subtask-label { font-weight: bold; font-size: 12pt; flex: 0 0 auto; }
/* Generic row/column layout for a task's components (see `layout` in
   task-schema.md), replacing the old fixed "text | one visual" pair. Column
   width comes from an inline `style="flex:0 0 N%"` per .task-col (set in
   Python from `layout`), not from a fixed set of CSS classes, so any
   percentage split works, not just a handful of presets. */
.task-components { }
.task-row { display: flex; gap: 6mm; align-items: flex-start; margin-bottom: 2mm; position: relative; }
.task-row:last-child { margin-bottom: 0; }
.task-col { min-width: 0; }
.task-col svg.visual-svg { display: block; width: 100%; height: auto; }
.task-component-lettered { margin: 3mm 0 3mm 6mm; }
/* Hover-only per-row column controls, built entirely client-side by
   initRowControls()/rebuildTaskRows() in LAYOUT_JS — see design-system.md
   ("Интерактивные элементы вёрстки в браузере"). Highlight + buttons only
   ever show on :hover, and are additionally forced hidden under print
   below for determinism (same reasoning as .layout-toolbar/.global-toolbar). */
.task-row:hover { background: #f6f6f6; outline: 1px dashed #bbb; outline-offset: 2px; }
.row-controls { position: absolute; top: 1mm; right: 1mm; display: none; gap: 1mm; z-index: 1; }
.task-row:hover .row-controls { display: flex; }
.row-controls button {
    width: 5mm; height: 5mm; padding: 0; border: 1px solid #999;
    background: #fff; border-radius: 2px; cursor: pointer;
    display: flex; align-items: center; justify-content: center;
}
.row-controls button:hover { background: #eee; }
.row-controls button:disabled { opacity: 0.35; cursor: default; }
.row-controls button:disabled:hover { background: #fff; }
.row-controls button svg { width: 3mm; height: 3mm; }
.task-component > ul, .task-component > ol { margin: 2mm 0 0 0; padding-left: 6mm; }
.chart-wrap { margin-top: 2mm; }
.chart-legend { display: flex; gap: 4mm; font-size: 8pt; margin-top: 1mm; flex-wrap: wrap; }
.illustration-wrap { margin-top: 2mm; }
.illustration-blank { min-height: 30mm; border: 1px dashed #999; margin-top: 2mm; }
.mc-options { margin-top: 2mm; display: flex; flex-direction: column; gap: 1.5mm; }
.mc-options.mc-layout-two-column { display: block; column-count: 2; column-gap: 8mm; }
.mc-options.mc-layout-two-column .mc-option { display: block; margin-bottom: 1.5mm; break-inside: avoid-column; }
.mc-options.mc-layout-inline { display: block; }
.mc-options.mc-layout-inline .mc-option { display: inline-block; margin-right: 6mm; }
.mc-marker { display: inline-block; width: 4mm; text-align: center; font-weight: bold; }
.mc-correct { font-weight: bold; }
.layout-toolbar {
    margin-top: 2mm; padding-top: 1.5mm; border-top: 1px dotted #ccc;
    display: flex; flex-wrap: wrap; gap: 3mm; font-size: 8.5pt; color: #555;
}
.layout-toolbar-group { display: flex; align-items: center; gap: 1mm; flex-wrap: wrap; }
.layout-toolbar-label { font-weight: bold; }
.layout-toolbar button {
    font-size: 8.5pt; padding: 0.5mm 2mm; border: 1px solid #999;
    background: #fafafa; border-radius: 2px; cursor: pointer;
}
.layout-toolbar button:hover { background: #eee; }
.layout-toolbar button.active { background: #ddd; font-weight: bold; }
body.page-view { background: #ddd; width: auto; padding: 10mm 0; }
.a4-page {
    /* Full A4 sheet (210mm x 297mm) with real margins matching @page above
       — same reasoning as body's rule. No max-width fallback: a narrower
       window scrolls horizontally rather than reflowing, so pagination is
       always measured at the width print actually uses, regardless of the
       browser window's current size. */
    background: #fff; width: 210mm; margin: 0 auto 10mm;
    padding: var(--page-margin); box-shadow: 0 0 8px rgba(0,0,0,.25);
    min-height: 297mm; box-sizing: border-box;
}
.global-toolbar {
    position: sticky; top: 0; z-index: 10;
    background: #fafafa; border-bottom: 1px solid #ccc;
    padding: 2mm 4mm; margin-bottom: 4mm;
    display: flex; flex-wrap: wrap; gap: 4mm; font-size: 9pt;
}
.global-toolbar-group { display: flex; align-items: center; gap: 1.5mm; flex-wrap: wrap; }
.global-toolbar-label { font-weight: bold; }
.global-toolbar button {
    font-size: 9pt; padding: 0.8mm 2.5mm; border: 1px solid #999;
    background: #fff; border-radius: 2px; cursor: pointer;
}
.global-toolbar button:hover { background: #eee; }
.global-toolbar button.active { background: #ddd; font-weight: bold; }
@media print {
    .global-toolbar { display: none !important; }
    body { padding: 0; width: auto; }
    body.page-view { background: #fff; padding: 0; }
    .a4-page {
        box-shadow: none; margin: 0; padding: 0; width: auto; min-height: 0;
        break-after: page;
    }
    .a4-page:last-child { break-after: auto; }
    .task { break-inside: avoid; }
    .layout-toolbar { display: none !important; }
    .row-controls { display: none !important; }
    .task-row:hover { background: none; outline: none; }
}
""".strip()

LETTERS = string.ascii_uppercase
LOWER_LETTERS = string.ascii_lowercase

# Fixed UI chrome strings, keyed by meta.json's "language" (only "ru" is
# supported). Mirrors UI_STRINGS in LAYOUT_JS below — keep both in sync
# whenever a label changes. Content (task prompt/answer/options/...) is NOT
# covered here: that's authored directly in the task JSON.
STRINGS = {
    "ru": {
        "school_class": "Школа/класс:",
        "date": "Дата:",
        "full_name": "Фамилия Имя:",
        "grade_suffix": "класс",
        "answer_label": "Ответ:",
        "true_label": "Верно",
        "false_label": "Неверно",
        "points_suffix": "б.",
        "teacher_variant": "Учитель (с ответами)",
        "student_variant": "Ученик",
        "default_title": "Рабочий лист",
    },
}


def t(lang, key):
    return STRINGS.get(lang, STRINGS["ru"]).get(key, STRINGS["ru"][key])


# Generic, declarative layout-toggle framework: Python only marks which
# control groups apply to a block (render_layout_toolbar() + an empty
# data-controls div); this script fills the toolbar with buttons and wires
# them up client-side, purely on-screen (@media print hides .layout-toolbar
# — see BASE_CSS). To add a new switchable option later: add a
# CONTROL_GROUPS entry here, a matching condition in render_layout_toolbar()
# for the relevant component shape, and make sure the rendered HTML has an
# element matching `target`. Note: the per-row
# column controls (initRowControls()/rebuildTaskRows() below) are a
# separate, non-declarative mechanism — they rebuild DOM structure rather
# than toggle a CSS class, so they don't go through CONTROL_GROUPS.
LAYOUT_JS = """
// UI_STRINGS mirrors the Python STRINGS dict below — keep both in sync
// whenever a label changes or a language is added. WORKSHEET_LANG is
// injected as a preceding `const` by build_document() (see LANG_STRINGS_JS).
const UI_STRINGS = {
    ru: {
        solution_toggle_label: "Место для решения",
        solution_show: "Показать",
        solution_hide: "Скрыть",
        variants_layout_label: "Варианты",
        variants_single: "1 колонка",
        variants_two: "2 колонки",
        variants_inline: "В строку",
        column_add_title: "Добавить колонку",
        column_remove_title: "Убрать колонку",
    },
};
const UI = UI_STRINGS[typeof WORKSHEET_LANG !== "undefined" && UI_STRINGS[WORKSHEET_LANG] ? WORKSHEET_LANG : "ru"];

const CONTROL_GROUPS = {
    "solution-toggle": {
        label: UI.solution_toggle_label,
        target: ".solution-area",
        type: "toggle-visibility",
        options: [
            {value: "show", label: UI.solution_show},
            {value: "hide", label: UI.solution_hide},
        ],
    },
    "variants-layout": {
        label: UI.variants_layout_label,
        target: ".mc-options",
        type: "radio",
        classPrefix: "mc-layout-",
        options: [
            {value: "single-column", label: UI.variants_single},
            {value: "two-column", label: UI.variants_two},
            {value: "inline", label: UI.variants_inline},
        ],
    },
};

function layoutApplyRadio(target, group, value, btn) {
    group.options.forEach(function (o) {
        target.classList.remove(group.classPrefix + o.value);
    });
    target.classList.add(group.classPrefix + value);
    btn.parentElement.querySelectorAll("button").forEach(function (b) {
        b.classList.toggle("active", b === btn);
    });
    schedulePaginate();
}

function layoutApplyToggleVisibility(target, value, btn) {
    target.style.display = value === "hide" ? "none" : "";
    btn.parentElement.querySelectorAll("button").forEach(function (b) {
        b.classList.toggle("active", b === btn);
    });
    schedulePaginate();
}

// Print-margin presets, named after Chrome's own print dialog margin
// dropdown ("По умолчанию"/"Нет"/"Минимум"). "default" mirrors BASE_CSS's
// @page rule (keep both in sync). "minimum" has no single correct value —
// Chrome derives its own "Minimum" from the selected printer/driver's
// unprintable area, which isn't a fixed constant, so this is our own small
// approximation, not a guaranteed match to any specific printer.
const PRINT_MARGIN_PRESETS = {
    default: {top: 15, right: 15, bottom: 15, left: 18, label: "По умолчанию"},
    none: {top: 0, right: 0, bottom: 0, left: 0, label: "Нет"},
    minimum: {top: 5, right: 5, bottom: 5, left: 8, label: "Минимум"},
};
let activeMarginPreset = "default";

function findPageRule() {
    for (const sheet of document.styleSheets) {
        let rules;
        try {
            rules = sheet.cssRules;
        } catch (e) {
            continue;
        }
        for (const rule of rules) {
            if (rule.type === CSSRule.PAGE_RULE) return rule;
        }
    }
    return null;
}

// Applying a preset rewrites both the on-screen padding (via the
// --page-margin custom property) and the live @page rule via CSSOM — so
// printing with Chrome's own margin dropdown left at "Default" always
// matches whichever preset is currently selected here, regardless of which
// one it is.
function applyMarginPreset(key) {
    const preset = PRINT_MARGIN_PRESETS[key];
    if (!preset) return;
    activeMarginPreset = key;
    const marginStr = preset.top + "mm " + preset.right + "mm " + preset.bottom + "mm " + preset.left + "mm";
    document.documentElement.style.setProperty("--page-margin", marginStr);
    const pageRule = findPageRule();
    if (pageRule) pageRule.style.margin = marginStr;
    schedulePaginate();
}

// On-screen "A4 page view": splits the flow of .sheet-header/.task elements
// into visually separate page-sized cards so opening the file makes the
// printed page count obvious at a glance, no page numbers needed. Purely a
// screen affordance — the vertical budget per page follows the active
// print-margin preset above, not a fixed constant.
let paginateScheduled = false;

function schedulePaginate() {
    if (paginateScheduled) return;
    paginateScheduled = true;
    requestAnimationFrame(function () {
        paginateScheduled = false;
        paginate();
    });
}

function unwrapPages(body) {
    body.querySelectorAll(":scope > .a4-page").forEach(function (page) {
        while (page.firstChild) {
            body.insertBefore(page.firstChild, page);
        }
        page.remove();
    });
}

function measurePxPerMm(body) {
    const probe = document.createElement("div");
    probe.style.cssText = "position:absolute; visibility:hidden; height:100mm; width:0; margin:0; padding:0; border:0;";
    body.appendChild(probe);
    const pxPerMm = probe.offsetHeight / 100;
    probe.remove();
    return pxPerMm;
}

function paginate() {
    const body = document.body;
    unwrapPages(body);

    const nodes = Array.from(body.querySelectorAll(":scope > .sheet-header, :scope > .task"));
    if (nodes.length === 0) return;

    const pxPerMm = measurePxPerMm(body);
    if (!pxPerMm) return;
    const activePreset = PRINT_MARGIN_PRESETS[activeMarginPreset];
    const pageContentHeightMm = 297 - activePreset.top - activePreset.bottom;
    const pageContentHeightPx = pageContentHeightMm * pxPerMm;

    const pages = [[]];
    let used = 0;
    nodes.forEach(function (node) {
        const rect = node.getBoundingClientRect();
        const cs = getComputedStyle(node);
        const extent = rect.height + parseFloat(cs.marginTop) + parseFloat(cs.marginBottom);
        const current = pages[pages.length - 1];
        if (current.length > 0 && used + extent > pageContentHeightPx) {
            pages.push([node]);
            used = extent;
        } else {
            current.push(node);
            used += extent;
        }
    });

    if (pages.length <= 1) {
        body.classList.remove("page-view");
        return;
    }

    body.classList.add("page-view");
    const scriptTag = body.querySelector("script");
    pages.forEach(function (pageNodes) {
        const pageEl = document.createElement("div");
        pageEl.className = "a4-page";
        body.insertBefore(pageEl, scriptTag);
        pageNodes.forEach(function (node) {
            pageEl.appendChild(node);
        });
    });
}

// Sheet-level toolbar, separate from the per-task .layout-toolbar above:
// a single bar at the very top of the document (not tied to any one task).
// Extensible on purpose — add a new entry here for any future sheet-level
// tool (radio-style, matching the shape used by CONTROL_GROUPS); rendering
// itself never needs to change.
const GLOBAL_TOOLBAR_TOOLS = [
    {
        id: "print-margins",
        label: "Поля печати",
        options: [
            {value: "default", label: PRINT_MARGIN_PRESETS.default.label},
            {value: "none", label: PRINT_MARGIN_PRESETS.none.label},
            {value: "minimum", label: PRINT_MARGIN_PRESETS.minimum.label},
        ],
        initial: "default",
        onSelect: applyMarginPreset,
    },
];

function buildGlobalToolbar() {
    // Same "Save Page As" re-open guard as the per-task toolbar builder below.
    if (document.querySelector(".global-toolbar")) return;
    const bar = document.createElement("div");
    bar.className = "global-toolbar";
    GLOBAL_TOOLBAR_TOOLS.forEach(function (tool) {
        const groupEl = document.createElement("div");
        groupEl.className = "global-toolbar-group";
        const labelEl = document.createElement("span");
        labelEl.className = "global-toolbar-label";
        labelEl.textContent = tool.label + ":";
        groupEl.appendChild(labelEl);
        tool.options.forEach(function (opt) {
            const btn = document.createElement("button");
            btn.type = "button";
            btn.textContent = opt.label;
            if (opt.value === tool.initial) btn.classList.add("active");
            btn.addEventListener("click", function () {
                groupEl.querySelectorAll("button").forEach(function (b) {
                    b.classList.remove("active");
                });
                btn.classList.add("active");
                tool.onSelect(opt.value);
            });
            groupEl.appendChild(btn);
        });
        bar.appendChild(groupEl);
    });
    document.body.insertBefore(bar, document.body.firstChild);
}

// Per-row column controls: hover-only "+"/"-" buttons on each .task-row
// that let the teacher regroup a task's components into rows/columns
// entirely in the browser (see "Интерактивные элементы вёрстки в браузере"
// in design-system.md). Icons copied once from Lucide (plus.svg/minus.svg,
// MIT-licensed) as plain strings — no npm/node_modules in this repo.
const ROW_ICONS = {
    plus: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14"/><path d="M12 5v14"/></svg>',
    minus: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14"/></svg>',
};

// Rebuilds a task's .task-components from scratch: `widths[i]` is how many
// consecutive items of the flat, ordered `cols` list (the task's .task-col
// nodes — never recreated, just re-parented) go into row i. This is the
// single source of truth for the current layout; both button handlers below
// only ever mutate `widths` and then call this to repaint.
function rebuildTaskRows(container, widths, cols) {
    container.innerHTML = "";
    let idx = 0;
    widths.forEach(function (width, rowIndex) {
        const rowEl = document.createElement("div");
        rowEl.className = "task-row";
        const pct = (100 / width).toFixed(2) + "%";
        for (let c = 0; c < width; c++) {
            const col = cols[idx++];
            col.style.flex = "0 0 " + pct;
            col.style.maxWidth = pct;
            rowEl.appendChild(col);
        }
        rowEl.appendChild(buildRowControlsEl(container, widths, cols, rowIndex));
        container.appendChild(rowEl);
    });
    schedulePaginate();
}

function buildRowControlsEl(container, widths, cols, rowIndex) {
    const wrap = document.createElement("div");
    wrap.className = "row-controls";

    const addBtn = document.createElement("button");
    addBtn.type = "button";
    addBtn.title = UI.column_add_title;
    addBtn.innerHTML = ROW_ICONS.plus;
    addBtn.disabled = rowIndex === widths.length - 1;
    addBtn.addEventListener("click", function () {
        // Pull the first component of the next row in as a new column of
        // this row; drop the next row entirely if it's now empty.
        widths[rowIndex] += 1;
        widths[rowIndex + 1] -= 1;
        if (widths[rowIndex + 1] === 0) widths.splice(rowIndex + 1, 1);
        rebuildTaskRows(container, widths, cols);
    });
    wrap.appendChild(addBtn);

    const removeBtn = document.createElement("button");
    removeBtn.type = "button";
    removeBtn.title = UI.column_remove_title;
    removeBtn.innerHTML = ROW_ICONS.minus;
    removeBtn.disabled = widths[rowIndex] === 1;
    removeBtn.addEventListener("click", function () {
        // Evict this row's last component into a fresh full-width row at
        // the very end. Every row after this one keeps its own width, so
        // its content shifts by one position — a cascade that falls out of
        // the width bookkeeping automatically, not an explicit loop here.
        widths[rowIndex] -= 1;
        widths.push(1);
        rebuildTaskRows(container, widths, cols);
    });
    wrap.appendChild(removeBtn);

    return wrap;
}

function initRowControls() {
    document.querySelectorAll(".task-components").forEach(function (container) {
        // Same "Save Page As" reopen guard as the toolbar builder below —
        // without it, re-running this against an already-rebuilt DOM would
        // re-wrap rows and double up .row-controls on every reopen cycle.
        if (container.dataset.rowControlsBuilt) return;
        container.dataset.rowControlsBuilt = "1";

        // Deliberately :scope > .task-row > .task-col, not row.children —
        // a rebuilt row also contains a .row-controls sibling, which would
        // otherwise get miscounted as an extra column.
        const cols = Array.from(container.querySelectorAll(":scope > .task-row > .task-col"));
        if (cols.length <= 1) return;
        const widths = Array.from(container.querySelectorAll(":scope > .task-row")).map(function (row) {
            return row.querySelectorAll(":scope > .task-col").length;
        });
        rebuildTaskRows(container, widths, cols);
    });
}

document.addEventListener("DOMContentLoaded", function () {
    buildGlobalToolbar();
    initRowControls();
    document.querySelectorAll(".layout-toolbar[data-controls]").forEach(function (toolbar) {
        // Guards against double-building: a browser "Save Page As" captures
        // the live DOM, i.e. a toolbar that's already been filled with
        // buttons by this same script on the previous load. Re-opening that
        // saved file re-runs this script against an already-built toolbar;
        // without this guard it would append a second set of buttons on top
        // (and a third on the next save/reopen cycle, and so on).
        if (toolbar.dataset.built) return;
        toolbar.dataset.built = "1";
        const block = toolbar.closest(".task, .task-component");
        if (!block) return;
        toolbar.dataset.controls.split(",").forEach(function (key) {
            const group = CONTROL_GROUPS[key];
            if (!group) return;
            const target = block.querySelector(group.target);
            if (!target) return;
            const groupEl = document.createElement("div");
            groupEl.className = "layout-toolbar-group";
            const labelEl = document.createElement("span");
            labelEl.className = "layout-toolbar-label";
            labelEl.textContent = group.label + ":";
            groupEl.appendChild(labelEl);
            group.options.forEach(function (opt) {
                const btn = document.createElement("button");
                btn.type = "button";
                btn.textContent = opt.label;
                const isInitial = group.type === "toggle-visibility"
                    ? (opt.value === "hide") === (target.style.display === "none")
                    : target.classList.contains(group.classPrefix + opt.value);
                if (isInitial) btn.classList.add("active");
                btn.addEventListener("click", function () {
                    if (group.type === "toggle-visibility") {
                        layoutApplyToggleVisibility(target, opt.value, btn);
                    } else {
                        layoutApplyRadio(target, group, opt.value, btn);
                    }
                });
                groupEl.appendChild(btn);
            });
            toolbar.appendChild(groupEl);
        });
    });

    paginate();
    if (document.fonts && document.fonts.ready) {
        document.fonts.ready.then(paginate);
    }
    let resizeTimer = null;
    window.addEventListener("resize", function () {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(paginate, 200);
    });
});
""".strip()


SUPSUB_TAGS = ("sup", "sub")


def esc(text):
    # Escapes everything except literal <sup>/<sub> (and their closing tags),
    # so task JSON can use them for indices/exponents with no Unicode symbol
    # (see references/symbols.md) without opening up arbitrary HTML.
    escaped = html.escape(str(text if text is not None else ""))
    for tag in SUPSUB_TAGS:
        escaped = escaped.replace(f"&lt;{tag}&gt;", f"<{tag}>")
        escaped = escaped.replace(f"&lt;/{tag}&gt;", f"</{tag}>")
    return escaped


def render_header(meta):
    lang = meta.get("language", "ru")
    school = esc(meta.get("school") or "")
    date = esc(meta.get("date") or "")
    subject = esc(meta.get("subject", ""))
    grade = esc(meta.get("grade", ""))
    title = esc(meta.get("title", ""))
    instructions = meta.get("instructions")
    parts = ['<div class="sheet-header">']
    parts.append(
        f'<div class="meta-line">{t(lang, "school_class")} <span class="blank">{school}</span>'
        f' {t(lang, "date")} <span class="blank">{date}</span>'
        f' {t(lang, "full_name")} <span class="blank" style="min-width:60mm;"></span></div>'
    )
    parts.append(f'<div class="sheet-title">{title}</div>')
    parts.append(f'<div class="sheet-subtitle">{subject} &middot; {grade} {t(lang, "grade_suffix")}</div>')
    if instructions:
        parts.append(f'<div class="sheet-instructions">{esc(instructions)}</div>')
    parts.append("</div>")
    return "".join(parts)


# ---------------------------------------------------------------------------
# Per-task-type renderers. Each returns (body_html, answer_html_or_None).
# ---------------------------------------------------------------------------

def render_text(task, is_teacher, lang):
    template = task.get("text_template")
    if template is None:
        # No inline blanks: the component's own prompt (rendered by the
        # caller as its header line) *is* the content — nothing else to
        # render in the body.
        return "", None
    blanks = task.get("blanks", {})
    return f"<p>{_fill_blank_render(template, blanks, is_teacher)}</p>", None


def _fill_blank_render(template, blanks, is_teacher):
    pieces = []
    last = 0
    for m in re.finditer(r"___(\w+)___", template):
        pieces.append(esc(template[last : m.start()]))
        key = m.group(1)
        if is_teacher and key in blanks:
            pieces.append(f'<span class="fill-blank answered">{esc(blanks[key])}</span>')
        else:
            pieces.append('<span class="fill-blank">&nbsp;</span>')
        last = m.end()
    pieces.append(esc(template[last:]))
    return "".join(pieces)


def render_list(task, is_teacher, lang):
    # Two-column mode (old `matching`): `left_items`/`right_items` replace
    # `items` entirely, mutually exclusive with the one-column modes below.
    if "left_items" in task or "right_items" in task:
        left_items = task.get("left_items", [])
        right_items = task.get("right_items", [])
        answer_map = task.get("answer_map", {})
        left_html = "".join(f"<li>{esc(item)}</li>" for item in left_items)
        letters = {item: LETTERS[i] for i, item in enumerate(right_items)}
        right_html = "".join(f"<li>{esc(item)}</li>" for item in right_items)
        body = (
            '<div class="matching-columns">'
            f'<ol type="1">{left_html}</ol>'
            f'<ol type="A" style="list-style-type: upper-latin;">{right_html}</ol>'
            "</div>"
        )
        answer = None
        if answer_map:
            pairs = []
            for i, item in enumerate(left_items, start=1):
                matched = answer_map.get(item)
                letter = letters.get(matched, "?")
                pairs.append(f"{i}-{letter}")
            answer = ", ".join(pairs)
        return body, answer

    items = task.get("items", [])
    style = task.get("item_style", "plain")

    if style == "statement_bool":
        rows = []
        for it in items:
            text = esc(it.get("text", ""))
            correct = it.get("correct")
            true_mark = "&#10005;" if is_teacher and correct is True else ""
            false_mark = "&#10005;" if is_teacher and correct is False else ""
            rows.append(
                '<div class="tf-row">'
                f'<span class="tf-statement">{text}</span>'
                '<span class="tf-box">'
                f'<span class="tf-square">{true_mark}</span> {t(lang, "true_label")}&nbsp;&nbsp;'
                f'<span class="tf-square">{false_mark}</span> {t(lang, "false_label")}'
                "</span>"
                "</div>"
            )
        return "".join(rows), None

    if style == "choice":
        layout = task.get("variants_layout", "single-column")
        parts = []
        for i, it in enumerate(items):
            is_correct = is_teacher and bool(it.get("correct"))
            mark = "&#10003;" if is_correct else ""
            css = "mc-option mc-correct" if is_correct else "mc-option"
            parts.append(
                f'<span class="{css}"><span class="mc-marker">{mark}</span> '
                f'{LOWER_LETTERS[i]}) {esc(it.get("text", ""))}</span>'
            )
        body = f'<div class="mc-options mc-layout-{esc(layout)}">' + "".join(parts) + "</div>"
        return body, task.get("answer")

    # "plain" — bare bullet/numbered list, no correctness marks (informational).
    tag = "ol" if task.get("ordered") else "ul"
    items_html = "".join(f"<li>{esc(item)}</li>" for item in items)
    return f"<{tag}>{items_html}</{tag}>", None


def render_table(task, is_teacher, lang):
    # Cell `null` = under-fill blank, revealed via `answers["r,c"]` for the
    # teacher version; a table with no `null` cells is just a plain
    # reference table (informational) — one code path covers both.
    headers = task.get("headers", [])
    rows = task.get("rows", [])
    answers = task.get("answers", {})
    thead = "".join(f"<th>{esc(h)}</th>" for h in headers)
    body_rows = []
    for r_i, row in enumerate(rows):
        cells = []
        for c_i, cell in enumerate(row):
            if cell is None:
                key = f"{r_i},{c_i}"
                value = answers.get(key, "") if is_teacher else ""
                cells.append(f'<td>{esc(value)}</td>' if value else "<td>&nbsp;</td>")
            else:
                cells.append(f"<td>{esc(cell)}</td>")
        body_rows.append(f"<tr>{''.join(cells)}</tr>")
    table = (
        '<table class="fill-table">'
        f"<thead><tr>{thead}</tr></thead>"
        f"<tbody>{''.join(body_rows)}</tbody>"
        "</table>"
    )
    return table, None


def render_prompt_response(task, is_teacher, lang):
    response = str(task.get("response", "none"))
    if response.startswith("lines:"):
        lines = int(response.split(":", 1)[1])
        show_response = task.get("show_response", True)
        style = ' style="display:none;"' if not show_response else ""
        body = f'<div class="solution-area"{style}>' + "".join(
            '<div class="solution-line"></div>' for _ in range(lines)
        ) + "</div>"
    elif response == "blank":
        body = f'<div>{t(lang, "answer_label")} <span class="answer-line"></span></div>'
    else:
        body = ""
    return body, task.get("answer")


DASH_PATTERNS = {"solid": None, "dashed": "8,4", "dotted": "1,3"}
MARKER_SHAPES = ["circle", "cross", "triangle"]


def _linspace(a, b, n):
    if n <= 1:
        return [a]
    step = (b - a) / (n - 1)
    return [a + step * i for i in range(n)]


def _fmt_num(n):
    if abs(n - round(n)) < 1e-9:
        return str(int(round(n)))
    return f"{n:.2f}".rstrip("0").rstrip(".")


def build_chart_svg(spec):
    # Sized for the ~36%-width side column (task-visual), not full page width —
    # viewBox units are chosen so font-size/stroke-width values below print at
    # a legible physical size once scaled down to that column's actual width.
    width, height = 220, 124
    margin = {"left": 36, "right": 10, "top": 10, "bottom": 22}
    plot_w = width - margin["left"] - margin["right"]
    plot_h = height - margin["top"] - margin["bottom"]
    x0, x1 = spec["x_range"]
    y0, y1 = spec["y_range"]

    def sx(x):
        return margin["left"] + (x - x0) / (x1 - x0) * plot_w

    def sy(y):
        return margin["top"] + plot_h - (y - y0) / (y1 - y0) * plot_h

    parts = [
        f'<svg class="visual-svg" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" '
        f'font-family="PT Sans, Segoe UI, Verdana, Arial, sans-serif">'
    ]

    # Gridlines + tick labels
    for gx in _linspace(x0, x1, 6):
        px = sx(gx)
        parts.append(
            f'<line x1="{px:.1f}" y1="{margin["top"]}" x2="{px:.1f}" '
            f'y2="{margin["top"] + plot_h}" stroke="#ccc" stroke-width="0.6"/>'
        )
        parts.append(
            f'<text x="{px:.1f}" y="{margin["top"] + plot_h + 12}" font-size="9" '
            f'text-anchor="middle">{_fmt_num(gx)}</text>'
        )
    for gy in _linspace(y0, y1, 6):
        py = sy(gy)
        parts.append(
            f'<line x1="{margin["left"]}" y1="{py:.1f}" '
            f'x2="{margin["left"] + plot_w}" y2="{py:.1f}" stroke="#ccc" stroke-width="0.6"/>'
        )
        parts.append(
            f'<text x="{margin["left"] - 6}" y="{py + 3:.1f}" font-size="9" '
            f'text-anchor="end">{_fmt_num(gy)}</text>'
        )

    # Axes
    parts.append(
        f'<line x1="{margin["left"]}" y1="{margin["top"] + plot_h}" '
        f'x2="{margin["left"] + plot_w}" y2="{margin["top"] + plot_h}" '
        'stroke="#000" stroke-width="1.5"/>'
    )
    parts.append(
        f'<line x1="{margin["left"]}" y1="{margin["top"]}" '
        f'x2="{margin["left"]}" y2="{margin["top"] + plot_h}" stroke="#000" stroke-width="1.5"/>'
    )
    parts.append(
        f'<text x="{margin["left"] + plot_w}" y="{margin["top"] + plot_h - 6}" '
        f'font-size="10" text-anchor="end">{esc(spec.get("x_label", ""))}</text>'
    )
    parts.append(
        f'<text x="{margin["left"] + 4}" y="{margin["top"] + 10}" '
        f'font-size="10" text-anchor="start">{esc(spec.get("y_label", ""))}</text>'
    )

    chart_type = spec.get("chart_type", "line")
    series = spec.get("series", [])
    legend_items = []
    for i, s in enumerate(series):
        points = s.get("points", [])
        style = s.get("style", "solid")
        dash = DASH_PATTERNS.get(style)
        dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
        if chart_type == "bar":
            bar_w = plot_w / max(len(points), 1) * 0.5
            for (x, y) in points:
                bx = sx(x) - bar_w / 2
                by = sy(y)
                bh = margin["top"] + plot_h - by
                parts.append(
                    f'<rect x="{bx:.1f}" y="{by:.1f}" width="{bar_w:.1f}" height="{bh:.1f}" '
                    f'fill="#fff" stroke="#000" stroke-width="1.3"{dash_attr}/>'
                )
        elif chart_type == "scatter":
            shape = MARKER_SHAPES[i % len(MARKER_SHAPES)]
            for (x, y) in points:
                px, py = sx(x), sy(y)
                if shape == "circle":
                    parts.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="3" fill="#000"/>')
                elif shape == "cross":
                    parts.append(
                        f'<line x1="{px-3:.1f}" y1="{py-3:.1f}" x2="{px+3:.1f}" y2="{py+3:.1f}" stroke="#000" stroke-width="1.3"/>'
                        f'<line x1="{px-3:.1f}" y1="{py+3:.1f}" x2="{px+3:.1f}" y2="{py-3:.1f}" stroke="#000" stroke-width="1.3"/>'
                    )
                else:
                    parts.append(
                        f'<polygon points="{px:.1f},{py-4:.1f} {px-4:.1f},{py+3:.1f} {px+4:.1f},{py+3:.1f}" fill="#000"/>'
                    )
        else:  # line
            path = " ".join(
                f'{"M" if idx == 0 else "L"}{sx(x):.1f},{sy(y):.1f}'
                for idx, (x, y) in enumerate(points)
            )
            parts.append(f'<path d="{path}" fill="none" stroke="#000" stroke-width="2"{dash_attr}/>')
        if s.get("label"):
            legend_items.append((s["label"], style, i))

    parts.append("</svg>")
    svg = "".join(parts)

    legend_html = ""
    if legend_items:
        chips = []
        for label, style, i in legend_items:
            dash = DASH_PATTERNS.get(style)
            sample = (
                f'<svg width="20" height="10"><line x1="0" y1="5" x2="20" y2="5" '
                f'stroke="#000" stroke-width="2"'
                + (f' stroke-dasharray="{dash}"' if dash else "")
                + "/></svg>"
            )
            chips.append(f'<span>{sample} {esc(label)}</span>')
        legend_html = f'<div class="chart-legend">{"".join(chips)}</div>'

    return f'<div class="chart-wrap">{svg}{legend_html}</div>'


# --- SVG snippet library for common illustrations -------------------------

def _snippet_inclined_plane(params):
    angle = params.get("angle", 30)
    mass_label = esc(params.get("mass_label", "m"))
    import math

    rad = math.radians(angle)
    base_len = 220
    height = base_len * math.tan(rad)
    height = min(height, 140)
    ax, ay = 20, 160
    bx, by = ax + base_len, ay
    cx, cy = ax, ay - height
    return (
        '<svg class="visual-svg" viewBox="0 0 260 190" xmlns="http://www.w3.org/2000/svg" '
        'font-family="PT Sans, Segoe UI, Verdana, Arial, sans-serif">'
        f'<polygon points="{ax},{ay} {bx},{by} {cx},{cy}" fill="none" stroke="#000" stroke-width="1.5"/>'
        f'<rect x="{(ax+bx)/2-14}" y="{(ay+cy)/2-40}" width="26" height="18" '
        f'fill="none" stroke="#000" stroke-width="1.5" '
        f'transform="rotate(-{angle} {(ax+bx)/2} {(ay+cy)/2-31})"/>'
        f'<text x="{(ax+bx)/2+16}" y="{(ay+cy)/2-30}" font-size="11">{mass_label}</text>'
        f'<text x="{ax+30}" y="{ay-8}" font-size="11">{angle}&#176;</text>'
        "</svg>"
    )


def _snippet_simple_circuit(params):
    r_label = esc(params.get("resistor_label", "R"))
    v_label = esc(params.get("source_label", "ε"))
    return (
        '<svg class="visual-svg" viewBox="0 0 220 140" xmlns="http://www.w3.org/2000/svg" '
        'font-family="PT Sans, Segoe UI, Verdana, Arial, sans-serif">'
        '<rect x="20" y="20" width="180" height="100" fill="none" stroke="#000" stroke-width="1.5"/>'
        '<rect x="85" y="10" width="50" height="20" fill="#fff" stroke="#000" stroke-width="1.5"/>'
        f'<text x="110" y="24" font-size="11" text-anchor="middle">{r_label}</text>'
        '<line x1="20" y1="60" x2="20" y2="80" stroke="#000" stroke-width="2.5"/>'
        '<line x1="14" y1="65" x2="26" y2="65" stroke="#000" stroke-width="1.5"/>'
        f'<text x="30" y="74" font-size="11">{v_label}</text>'
        "</svg>"
    )


SVG_SNIPPETS = {
    "inclined_plane": _snippet_inclined_plane,
    "simple_circuit": _snippet_simple_circuit,
}


def _resolve_svg(task, snippet_key, raw_key):
    if snippet_key in task:
        name = task[snippet_key]["name"]
        params = task[snippet_key].get("params", {})
        if name not in SVG_SNIPPETS:
            raise ValueError(
                f"Unknown {snippet_key} '{name}'. Available: {list(SVG_SNIPPETS)}. "
                "Use raw_svg instead, or add a generator to SVG_SNIPPETS."
            )
        return SVG_SNIPPETS[name](params)
    if raw_key in task:
        return task[raw_key]
    return None


def render_visual(task, is_teacher, lang):
    # Exactly one of chart_spec / svg_snippet / raw_svg is expected to supply
    # the base visual, and optionally one of answer_chart_spec /
    # answer_svg_snippet / answer_raw_svg supplies a second, teacher-only
    # visual (old chart/chart_fill and illustration/illustration_draw were
    # four types around this same "source + optional answer source" shape —
    # merged here into one dispatch, field names unchanged). No source at
    # all renders a blank box (e.g. freeform "draw the diagram yourself").
    if is_teacher and "answer_chart_spec" in task:
        return build_chart_svg(task["answer_chart_spec"]), task.get("answer")
    if "chart_spec" in task:
        return build_chart_svg(task["chart_spec"]), task.get("answer")

    if is_teacher:
        svg = _resolve_svg(task, "answer_svg_snippet", "answer_raw_svg") or _resolve_svg(task, "svg_snippet", "raw_svg")
    else:
        svg = _resolve_svg(task, "svg_snippet", "raw_svg")
    body = f'<div class="illustration-wrap">{svg}</div>' if svg else '<div class="illustration-blank"></div>'
    return body, task.get("answer")


# 5 structural formats replace the old 15 semantic types — grouped by what
# shape of data the renderer actually consumes, not by pedagogical intent.
# Whether a component carries a letter (a/b/в...) and an answer for the
# teacher version is decided purely by the component's own `answerable`
# flag (see render_task()), never by which format it uses.
COMPONENT_RENDERERS = {
    "text": render_text,
    "list": render_list,
    "table": render_table,
    "prompt_response": render_prompt_response,
    "visual": render_visual,
}

# Which on-screen layout-toolbar control groups (see LAYOUT_JS) apply to a
# component. Keyed off the full component (not just `type`) because one
# format now covers several old types that only some of which need a
# toolbar: to wire up a new one, add a condition here plus a matching
# CONTROL_GROUPS entry in LAYOUT_JS whose `target` selector matches an
# element this format's renderer already emits. (The per-row column
# controls are unrelated — they're built unconditionally per task by
# initRowControls() in LAYOUT_JS, not through this function.)
def render_layout_toolbar(comp):
    controls = []
    if comp.get("type") == "prompt_response" and str(comp.get("response", "")).startswith("lines:"):
        controls.append("solution-toggle")
    if comp.get("type") == "list" and comp.get("item_style") == "choice":
        controls.append("variants-layout")
    if not controls:
        return ""
    return f'<div class="layout-toolbar" data-controls="{",".join(controls)}"></div>'


def render_header_line(num_html, prompt, points, lang):
    # Number/letter and prompt text sit on the same line (num_html isn't
    # wrapped, so its wrapped continuation lines hang-indent under the text,
    # not under the number); points render inline at the end of the text,
    # not next to the number, per design-system.md numbering rules.
    points_html = f' <span class="task-points">({esc(points)} {t(lang, "points_suffix")})</span>' if points else ""
    if prompt:
        prompt_html = f'<span class="task-prompt">{esc(prompt)}{points_html}</span>'
    elif points_html:
        prompt_html = f'<span class="task-prompt">{points_html.strip()}</span>'
    else:
        prompt_html = ""
    return f'<div class="task-header">{num_html}{prompt_html}</div>'


def _partition_layout(components, layout):
    # Default: every component on its own full-width row (today's "all
    # stacked" look). Otherwise each entry is either an int N (N equal
    # columns) or a list of explicit percentages (one per column) — see
    # "Раскладка: layout" in task-schema.md. Validated by simple arithmetic:
    # the partition must account for exactly every component, no addressable
    # cells to get out of sync.
    if not layout:
        return [1] * len(components)
    total = sum(row if isinstance(row, int) else len(row) for row in layout)
    if total != len(components):
        raise ValueError(
            f"layout describes {total} component(s) but there are {len(components)}"
        )
    return layout


def render_task(index, task, is_teacher, lang):
    components = task.get("components", [])
    if not components:
        raise ValueError(f"Task {task.get('id')} has no components")

    answerable_positions = [i for i, c in enumerate(components) if c.get("answerable")]
    # Letters are only meaningful when there's more than one thing to answer —
    # a lone answerable component reads as a plain simple task, no letter.
    letter_for = {}
    if len(answerable_positions) > 1:
        for letter_i, pos in enumerate(answerable_positions):
            letter_for[pos] = LOWER_LETTERS[letter_i]

    task_prompt = task.get("prompt", "")
    task_points = task.get("points")
    # A single component with no task-level intro reads exactly like today's
    # plain flat task: its own prompt/points merge into the one task-number
    # header line, instead of two stacked header lines for one question.
    single_component = len(components) == 1 and not task_prompt

    rows = _partition_layout(components, task.get("layout"))
    row_htmls = []
    if not single_component:
        # The task-level intro (number + prompt) is itself a component for
        # layout purposes — it gets its own full-width row 0 by default, same
        # as any other component, so the hover +/- controls (initRowControls
        # in LAYOUT_JS) can merge it into a neighboring row too, not just
        # rearrange the "real" JSON components after it.
        header_html = render_header_line(f'<span class="task-num">{index}.</span>', task_prompt, task_points, lang)
        row_htmls.append(
            f'<div class="task-row"><div class="task-col" style="flex:0 0 100%;max-width:100%;">{header_html}</div></div>'
        )

    idx = 0
    for row in rows:
        width = row if isinstance(row, int) else len(row)
        pct_list = [100.0 / width] * width if isinstance(row, int) else row
        cell_htmls = []
        for cell_i in range(width):
            comp = components[idx]
            ctype = comp.get("type")
            renderer = COMPONENT_RENDERERS.get(ctype)
            if renderer is None:
                raise ValueError(
                    f"Unknown component type '{ctype}' in task {task.get('id')} (component {idx})"
                )
            body_html, answer = renderer(comp, is_teacher, lang)

            comp_prompt = comp.get("prompt", "")
            comp_points = comp.get("points")
            is_answerable = bool(comp.get("answerable"))
            show_letter = (not single_component) and is_answerable and len(answerable_positions) > 1
            label = (comp.get("label") or letter_for.get(idx)) if show_letter else None

            if single_component:
                num_html = f'<span class="task-num">{index}.</span>'
                merged_points = comp_points if comp_points is not None else task_points
                header_html = render_header_line(num_html, comp_prompt, merged_points, lang)
            elif label:
                header_html = render_header_line(
                    f'<span class="subtask-label">{esc(label)})</span>', comp_prompt, comp_points, lang
                )
            elif comp_prompt or comp_points:
                header_html = render_header_line("", comp_prompt, comp_points, lang)
            else:
                header_html = ""

            answer_html = ""
            if is_teacher and answer:
                answer_html = f'<div class="answer-block"><strong>{t(lang, "answer_label")}</strong> {esc(answer)}</div>'

            toolbar_html = render_layout_toolbar(comp)
            comp_class = "task-component task-component-lettered" if label else "task-component"
            pct = pct_list[cell_i]
            cell_htmls.append(
                f'<div class="task-col" style="flex:0 0 {pct:.2f}%;max-width:{pct:.2f}%;">'
                f'<div class="{comp_class}">{header_html}{body_html}{answer_html}{toolbar_html}</div>'
                "</div>"
            )
            idx += 1
        row_htmls.append(f'<div class="task-row">{"".join(cell_htmls)}</div>')

    components_html = f'<div class="task-components">{"".join(row_htmls)}</div>'

    return f'<div class="task">{components_html}</div>'


def build_document(meta, tasks, is_teacher):
    lang = meta.get("language", "ru")
    body = [render_header(meta)]
    for i, task in enumerate(tasks, start=1):
        body.append(render_task(i, task, is_teacher, lang))
    variant = t(lang, "teacher_variant") if is_teacher else t(lang, "student_variant")
    js_lang = lang if lang in STRINGS else "ru"
    return f"""<!DOCTYPE html>
<html lang="{js_lang}">
<head>
<meta charset="UTF-8">
<title>{esc(meta.get('title') or t(lang, "default_title"))} — {variant}</title>
{KATEX_HEAD}
<style>{BASE_CSS}</style>
</head>
<body>
{''.join(body)}
<script>const WORKSHEET_LANG = "{js_lang}";
{LAYOUT_JS}</script>
</body>
</html>"""


def load_workspace(workspace):
    workspace = Path(workspace)
    meta_path = workspace / "meta.json"
    if not meta_path.exists():
        sys.exit(f"meta.json not found in {workspace}")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    tasks_dir = workspace / "tasks"
    order = meta.get("order") or sorted(p.stem for p in tasks_dir.glob("*.json"))
    tasks = []
    for task_id in order:
        task_path = tasks_dir / f"{task_id}.json"
        if not task_path.exists():
            sys.exit(f"Task file not found: {task_path}")
        tasks.append(json.loads(task_path.read_text(encoding="utf-8")))
    return meta, tasks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workspace", help="Path to the worksheet draft folder (contains meta.json, tasks/)")
    parser.add_argument("--task", help="Render only this single task id as a preview HTML")
    args = parser.parse_args()

    workspace = Path(args.workspace)
    meta, tasks = load_workspace(workspace)

    if args.task:
        match = next((t for t in tasks if t.get("id") == args.task), None)
        if match is None:
            sys.exit(f"Task id '{args.task}' not found in meta.json order")
        html_doc = build_document(meta, [match], is_teacher=True)
        out_path = workspace / f"{args.task}.preview.html"
        out_path.write_text(html_doc, encoding="utf-8")
        print(f"Wrote {out_path}")
        return

    output_dir = workspace / "output"
    output_dir.mkdir(exist_ok=True)
    student_html = build_document(meta, tasks, is_teacher=False)
    teacher_html = build_document(meta, tasks, is_teacher=True)
    (output_dir / "worksheet-student.html").write_text(student_html, encoding="utf-8")
    (output_dir / "worksheet-teacher.html").write_text(teacher_html, encoding="utf-8")
    print(f"Wrote {output_dir / 'worksheet-student.html'}")
    print(f"Wrote {output_dir / 'worksheet-teacher.html'}")


if __name__ == "__main__":
    main()
