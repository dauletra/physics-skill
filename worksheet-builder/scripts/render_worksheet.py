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
.subtask { margin: 3mm 0 3mm 6mm; }
.subtask-label { font-weight: bold; font-size: 12pt; flex: 0 0 auto; }
.task-with-visual { display: flex; gap: 6mm; align-items: flex-start; }
.task-with-visual .task-text { flex: 1 1 auto; min-width: 0; }
.task-with-visual .task-visual { flex: 0 0 36%; max-width: 36%; }
.task-with-visual .task-visual.visual-width-30 { flex-basis: 30%; max-width: 30%; }
.task-with-visual .task-visual.visual-width-36 { flex-basis: 36%; max-width: 36%; }
.task-with-visual .task-visual.visual-width-40 { flex-basis: 40%; max-width: 40%; }
.task-with-visual .task-visual.visual-width-50 { flex-basis: 50%; max-width: 50%; }
.task-with-visual .task-visual.visual-width-60 { flex-basis: 60%; max-width: 60%; }
.task-with-visual.visual-position-below { flex-direction: column; }
.task-with-visual.visual-position-below .task-visual { flex-basis: auto; max-width: 100%; }
.task-with-visual .task-visual svg.visual-svg { display: block; width: 100%; height: auto; }
.chart-wrap { margin-top: 2mm; }
.chart-legend { display: flex; gap: 4mm; font-size: 8pt; margin-top: 1mm; flex-wrap: wrap; }
.illustration-wrap { margin-top: 2mm; }
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
}
""".strip()

LETTERS = string.ascii_uppercase
LOWER_LETTERS = string.ascii_lowercase

# Fixed UI chrome strings, keyed by meta.json's "language" ("ru"/"kk"). Mirrors
# UI_STRINGS in LAYOUT_JS below — keep both in sync whenever a label changes
# or a language is added. Content (task prompt/answer/options/...) is NOT
# covered here: that's translated by hand into a separate workspace folder
# per references/translation.md, never auto-translated by this script.
#
# footer_text is only consumed by render_worksheet_docx.py (Word footer) —
# the HTML path has no footer, see the on-screen A4 page-view instead.
STRINGS = {
    "ru": {
        "school_class": "Школа/класс:",
        "date": "Дата:",
        "full_name": "Фамилия Имя:",
        "grade_suffix": "класс",
        "footer_text": "— стр. 1 —",
        "answer_label": "Ответ:",
        "true_label": "Верно",
        "false_label": "Неверно",
        "points_suffix": "б.",
        "teacher_variant": "Учитель (с ответами)",
        "student_variant": "Ученик",
        "default_title": "Рабочий лист",
    },
    "kk": {
        "school_class": "Мектеп/сынып:",
        "date": "Күні:",
        "full_name": "Аты-жөні:",
        "grade_suffix": "сынып",
        "footer_text": "— 1-бет —",
        "answer_label": "Жауабы:",
        "true_label": "Дұрыс",
        "false_label": "Дұрыс емес",
        "points_suffix": "ұ.",
        "teacher_variant": "Мұғалім (жауаптарымен)",
        "student_variant": "Оқушы",
        "default_title": "Жұмыс парағы",
    },
}


def t(lang, key):
    return STRINGS.get(lang, STRINGS["ru"]).get(key, STRINGS["ru"][key])


# Generic, declarative layout-toggle framework: Python only marks which
# control groups apply to a block (LAYOUT_CONTROLS_BY_TYPE + an empty
# data-controls div, see render_layout_toolbar); this script fills the
# toolbar with buttons and wires them up client-side, purely on-screen
# (@media print hides .layout-toolbar — see BASE_CSS). To add a new
# switchable option later: add a CONTROL_GROUPS entry here, list its key in
# LAYOUT_CONTROLS_BY_TYPE for the relevant task type(s), and make sure that
# type's rendered HTML has an element matching `target`.
LAYOUT_JS = """
// UI_STRINGS mirrors the Python STRINGS dict below — keep both in sync
// whenever a label changes or a language is added. WORKSHEET_LANG is
// injected as a preceding `const` by build_document() (see LANG_STRINGS_JS).
const UI_STRINGS = {
    ru: {
        visual_width_label: "Ширина рисунка",
        visual_position_label: "Расположение",
        visual_position_side: "Рядом с текстом",
        visual_position_below: "Опустить вниз",
        solution_toggle_label: "Место для решения",
        solution_show: "Показать",
        solution_hide: "Скрыть",
        variants_layout_label: "Варианты",
        variants_single: "1 колонка",
        variants_two: "2 колонки",
        variants_inline: "В строку",
    },
    kk: {
        visual_width_label: "Сурет ені",
        visual_position_label: "Орналасуы",
        visual_position_side: "Мәтін жанында",
        visual_position_below: "Төменге түсіру",
        solution_toggle_label: "Шешім орны",
        solution_show: "Көрсету",
        solution_hide: "Жасыру",
        variants_layout_label: "Нұсқалар",
        variants_single: "1 баған",
        variants_two: "2 баған",
        variants_inline: "Бір жолға",
    },
};
const UI = UI_STRINGS[typeof WORKSHEET_LANG !== "undefined" && UI_STRINGS[WORKSHEET_LANG] ? WORKSHEET_LANG : "ru"];

const CONTROL_GROUPS = {
    "visual-width": {
        label: UI.visual_width_label,
        target: ".task-visual",
        type: "radio",
        classPrefix: "visual-width-",
        options: [
            {value: "30", label: "30%"},
            {value: "36", label: "36%"},
            {value: "40", label: "40%"},
            {value: "50", label: "50%"},
            {value: "60", label: "60%"},
        ],
    },
    "visual-position": {
        label: UI.visual_position_label,
        target: ".task-with-visual",
        type: "radio",
        classPrefix: "visual-position-",
        options: [
            {value: "side", label: UI.visual_position_side},
            {value: "below", label: UI.visual_position_below},
        ],
    },
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

document.addEventListener("DOMContentLoaded", function () {
    buildGlobalToolbar();
    document.querySelectorAll(".layout-toolbar[data-controls]").forEach(function (toolbar) {
        // Guards against double-building: a browser "Save Page As" captures
        // the live DOM, i.e. a toolbar that's already been filled with
        // buttons by this same script on the previous load. Re-opening that
        // saved file re-runs this script against an already-built toolbar;
        // without this guard it would append a second set of buttons on top
        // (and a third on the next save/reopen cycle, and so on).
        if (toolbar.dataset.built) return;
        toolbar.dataset.built = "1";
        const block = toolbar.closest(".task, .subtask");
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

def render_text_with_solution(task, is_teacher, lang):
    lines = int(task.get("solution_lines", 4))
    show_solution = task.get("show_solution", True)
    style = ' style="display:none;"' if not show_solution else ""
    body = f'<div class="solution-area"{style}>' + "".join(
        '<div class="solution-line"></div>' for _ in range(lines)
    ) + "</div>"
    return body, task.get("answer")


def render_text_no_solution(task, is_teacher, lang):
    if task.get("answer_blank", True):
        body = f'<div>{t(lang, "answer_label")} <span class="answer-line"></span></div>'
    else:
        body = ""
    return body, task.get("answer")


def render_matching(task, is_teacher, lang):
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


def render_true_false(task, is_teacher, lang):
    statements = task.get("statements", [])
    rows = []
    for st in statements:
        text = esc(st.get("text", ""))
        correct = st.get("answer")
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


def render_multiple_choice(task, is_teacher, lang):
    options = task.get("options", [])
    correct = task.get("correct")
    layout = task.get("variants_layout", "single-column")
    items = []
    for i, opt in enumerate(options):
        is_correct = is_teacher and correct is not None and i == correct
        mark = "&#10003;" if is_correct else ""
        css = "mc-option mc-correct" if is_correct else "mc-option"
        items.append(
            f'<span class="{css}"><span class="mc-marker">{mark}</span> '
            f'{LOWER_LETTERS[i]}) {esc(opt)}</span>'
        )
    body = f'<div class="mc-options mc-layout-{esc(layout)}">' + "".join(items) + "</div>"
    return body, task.get("answer")


def render_fill_blank_text(task, is_teacher, lang):
    template = task.get("text_template", "")
    blanks = task.get("blanks", {})
    body = _fill_blank_render(template, blanks, is_teacher)
    return f"<p>{body}</p>", None


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


def render_fill_blank_table(task, is_teacher, lang):
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


def render_chart(task, is_teacher, lang):
    return build_chart_svg(task["chart_spec"]), task.get("answer")


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


def render_illustration(task, is_teacher, lang):
    if "svg_snippet" in task:
        name = task["svg_snippet"]["name"]
        params = task["svg_snippet"].get("params", {})
        if name not in SVG_SNIPPETS:
            raise ValueError(
                f"Unknown svg_snippet '{name}'. Available: {list(SVG_SNIPPETS)}. "
                "Use raw_svg instead, or add a generator to SVG_SNIPPETS."
            )
        svg = SVG_SNIPPETS[name](params)
    elif "raw_svg" in task:
        svg = task["raw_svg"]
    else:
        raise ValueError(f"Illustration task {task.get('id')} needs svg_snippet or raw_svg")
    return f'<div class="illustration-wrap">{svg}</div>', task.get("answer")


TASK_RENDERERS = {
    "text_with_solution": render_text_with_solution,
    "text_no_solution": render_text_no_solution,
    "matching": render_matching,
    "true_false": render_true_false,
    "fill_blank_text": render_fill_blank_text,
    "fill_blank_table": render_fill_blank_table,
    "chart": render_chart,
    "illustration": render_illustration,
    "multiple_choice": render_multiple_choice,
}


SIDE_VISUAL_TYPES = {"chart", "illustration"}

# Which on-screen layout-toolbar control groups (see LAYOUT_JS) apply to each
# task type. To make a new type's block interactively adjustable: add an
# entry here (comma-separated control-group keys) and a matching CONTROL_GROUPS
# entry in LAYOUT_JS whose `target` selector matches an element this type's
# renderer already emits.
LAYOUT_CONTROLS_BY_TYPE = {
    "chart": "visual-width,visual-position",
    "illustration": "visual-width,visual-position",
    "text_with_solution": "solution-toggle",
    "multiple_choice": "variants-layout",
}


def render_layout_toolbar(ttype):
    controls = LAYOUT_CONTROLS_BY_TYPE.get(ttype)
    return f'<div class="layout-toolbar" data-controls="{controls}"></div>' if controls else ""


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


def render_content_block(ttype, task_data, header_html, body_html, answer_html):
    toolbar_html = render_layout_toolbar(ttype)
    if ttype in SIDE_VISUAL_TYPES:
        # Chart/illustration sit beside the header+prompt (~36% width) instead
        # of stacked full-width below it, so the visual doesn't dominate the page.
        # visual_width/visual_position are optional JSON fields (defaults match
        # the previous fixed 36%-beside-text behavior); the layout-toolbar lets
        # the browser override them live without touching the JSON.
        width = esc(task_data.get("visual_width", "36"))
        position = esc(task_data.get("visual_position", "side"))
        return (
            f'<div class="task-with-visual visual-position-{position}">'
            f'<div class="task-text">{header_html}{answer_html}</div>'
            f'<div class="task-visual visual-width-{width}">{body_html}</div>'
            f"</div>{toolbar_html}"
        )
    return f"{header_html}{body_html}{answer_html}{toolbar_html}"


def render_compound_task(index, task, is_teacher, lang):
    points = task.get("points")
    prompt = task.get("prompt", "")
    header_html = render_header_line(f'<span class="task-num">{index}.</span>', prompt, points, lang)

    parts_html = []
    for i, part in enumerate(task.get("parts", [])):
        ptype = part.get("type")
        if ptype == "compound":
            raise ValueError(f"Nested 'compound' part not allowed in task {task.get('id')}")
        renderer = TASK_RENDERERS.get(ptype)
        if renderer is None:
            raise ValueError(f"Unknown part type '{ptype}' in task {task.get('id')} (part {i})")
        body_html, answer = renderer(part, is_teacher, lang)

        label = part.get("label") or LOWER_LETTERS[i]
        part_points = part.get("points")
        part_prompt = part.get("prompt", "")
        sub_header_html = render_header_line(f'<span class="subtask-label">{esc(label)})</span>', part_prompt, part_points, lang)

        answer_html = ""
        if is_teacher and answer:
            answer_html = f'<div class="answer-block"><strong>{t(lang, "answer_label")}</strong> {esc(answer)}</div>'

        content = render_content_block(ptype, part, sub_header_html, body_html, answer_html)
        parts_html.append(f'<div class="subtask">{content}</div>')

    return f'<div class="task">{header_html}{"".join(parts_html)}</div>'


def render_task(index, task, is_teacher, lang):
    ttype = task.get("type")
    if ttype == "compound":
        return render_compound_task(index, task, is_teacher, lang)
    renderer = TASK_RENDERERS.get(ttype)
    if renderer is None:
        raise ValueError(f"Unknown task type '{ttype}' in task {task.get('id')}")
    body_html, answer = renderer(task, is_teacher, lang)
    points = task.get("points")
    prompt = task.get("prompt", "")
    header_html = render_header_line(f'<span class="task-num">{index}.</span>', prompt, points, lang)
    answer_html = ""
    if is_teacher and answer:
        answer_html = f'<div class="answer-block"><strong>{t(lang, "answer_label")}</strong> {esc(answer)}</div>'

    content = render_content_block(ttype, task, header_html, body_html, answer_html)
    return f'<div class="task">{content}</div>'


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
    parser.add_argument(
        "--docx",
        action="store_true",
        help=(
            "Also write worksheet-student.docx/worksheet-teacher.docx "
            "(requires: pip install -r requirements-docx.txt)"
        ),
    )
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

    if args.docx:
        try:
            from render_worksheet_docx import build_docx_documents
        except ImportError as e:
            sys.exit(
                "Не найдены зависимости для --docx. Установите их один раз:\n"
                "  pip install -r worksheet-builder/scripts/requirements-docx.txt\n"
                f"(исходная ошибка: {e})"
            )
        student_doc, teacher_doc = build_docx_documents(meta, tasks)
        student_doc.save(output_dir / "worksheet-student.docx")
        teacher_doc.save(output_dir / "worksheet-teacher.docx")
        print(f"Wrote {output_dir / 'worksheet-student.docx'}")
        print(f"Wrote {output_dir / 'worksheet-teacher.docx'}")


if __name__ == "__main__":
    main()
