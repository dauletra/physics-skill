"""Статические шаблонные блобы: сниппет KaTeX для <head>, базовый CSS и
клиентский JS раскладки/пагинации. Логики рендеринга здесь нет — только
строки, которые document.py вклеивает в сгенерированный HTML."""

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
    /* Экранное-only поле страницы, управляется тулбаром пресетов полей печати
       (applyMarginPreset() в LAYOUT_JS). Зеркалит margin у @page ниже — оба
       держатся в синхроне не только в момент генерации, но и в рантайме. */
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
    /* Полный лист A4 с настоящими полями (совпадает с @page выше), а не
       просто 177mm текстовая колонка — так экран показывает настоящее белое
       поле вокруг текста, как в Google Docs/Word, а не текст впритык к краю. */
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
/* Общая раскладка компонентов задания по строкам/колонкам (см. `layout` в
   task-schema.md), заменяет старую фиксированную пару "текст | один визуал".
   Ширина колонки задаётся инлайновым `style="flex:0 0 N%"` на каждом
   .task-col (проставляется в Python из `layout`), а не фиксированным набором
   CSS-классов, так что работает любое процентное разбиение, а не только
   горстка пресетов. */
.task-components { }
.task-row { display: flex; gap: 6mm; align-items: flex-start; margin-bottom: 2mm; position: relative; }
.task-row:last-child { margin-bottom: 0; }
.task-col { min-width: 0; }
.task-col svg.visual-svg { display: block; width: 100%; height: auto; }
.task-component-lettered { margin: 3mm 0 3mm 6mm; }
/* Per-row контролы колонок, показываются только на hover, целиком строятся
   на клиенте через initRowControls()/rebuildTaskRows() в LAYOUT_JS — см.
   design-system.md ("Интерактивные элементы вёрстки в браузере"). Подсветка
   + кнопки показываются только на :hover, и дополнительно принудительно
   скрыты при печати ниже для детерминизма (та же логика, что у
   .layout-toolbar/.global-toolbar). */
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
    /* Полный лист A4 (210mm x 297mm) с настоящими полями, совпадающими с
       @page выше — та же логика, что у правила body. Без fallback на
       max-width: более узкое окно просто скроллится горизонтально, а не
       переверстывается, так что пагинация всегда измеряется на той ширине,
       которую реально использует печать, независимо от текущего размера
       окна браузера. */
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

# Общий, декларативный фреймворк переключателей раскладки: Python только
# помечает, какие группы контролов применимы к блоку (render_layout_toolbar()
# + пустой div data-controls); этот скрипт наполняет тулбар кнопками и
# навешивает обработчики на клиенте, чисто на экране (@media print скрывает
# .layout-toolbar — см. BASE_CSS). Чтобы добавить новую переключаемую опцию
# позже: добавь запись в CONTROL_GROUPS здесь, соответствующее условие в
# render_layout_toolbar() для нужной формы компонента, и убедись, что
# отрендеренный HTML содержит элемент, совпадающий с `target`. Замечание:
# per-row контролы колонок (initRowControls()/rebuildTaskRows() ниже) — это
# отдельный, не-декларативный механизм — они перестраивают структуру DOM,
# а не переключают CSS-класс, поэтому не проходят через CONTROL_GROUPS.
LAYOUT_JS = """
// UI_STRINGS зеркалит Python-словарь STRINGS — держи оба в синхроне при
// изменении подписи или добавлении языка. WORKSHEET_LANG вставляется как
// предшествующий `const` через build_document() (см. LANG_STRINGS_JS).
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

// Пресеты полей печати, названы по образцу выпадающего списка полей в
// диалоге печати самого Chrome ("По умолчанию"/"Нет"/"Минимум"). "default"
// зеркалит правило @page из BASE_CSS (держи оба в синхроне). У "minimum" нет
// единственно верного значения — Chrome сам вычисляет своё "Минимум" из
// непечатаемой области выбранного принтера/драйвера, а это не постоянная
// величина, так что здесь наше собственное небольшое приближение, без
// гарантии совпадения с конкретным принтером.
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

// Применение пресета переписывает и экранный padding (через кастомное
// CSS-свойство --page-margin), и живое правило @page через CSSOM — так что
// печать с собственным выпадающим списком полей Chrome, оставленным на
// "По умолчанию", всегда совпадает с тем, какой пресет сейчас выбран здесь,
// какой бы это ни был.
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

// Экранный "вид по страницам A4": разбивает поток элементов
// .sheet-header/.task на визуально отдельные карточки размером со страницу,
// так что при открытии файла количество печатных страниц видно сразу, без
// номеров страниц. Чисто экранное удобство — вертикальный бюджет на
// страницу следует за активным пресетом полей печати выше, а не за
// постоянной константой.
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

// Тулбар уровня всего листа, отдельный от подзадачного .layout-toolbar
// выше: одна панель в самом верху документа (не привязана ни к одному
// конкретному заданию). Специально расширяемый — добавляй сюда новую запись
// для любого будущего инструмента уровня листа (в стиле radio, по форме
// CONTROL_GROUPS); сам рендеринг менять не придётся.
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
    // Тот же гвард на переоткрытие через "Сохранить страницу как", что и у
    // билдера подзадачного тулбара ниже.
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

// Per-row контролы колонок: кнопки "+"/"-", видимые только на hover, на
// каждой .task-row — позволяют учителю перегруппировать компоненты задания
// по строкам/колонкам прямо в браузере (см. "Интерактивные элементы вёрстки
// в браузере" в design-system.md). Иконки один раз скопированы из Lucide
// (plus.svg/minus.svg, лицензия MIT) как обычные строки — в этом репозитории
// нет npm/node_modules.
const ROW_ICONS = {
    plus: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14"/><path d="M12 5v14"/></svg>',
    minus: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14"/></svg>',
};

// Перестраивает .task-components задания с нуля: `widths[i]` — сколько
// последовательных элементов плоского упорядоченного списка `cols` (узлы
// .task-col задания — никогда не создаются заново, только переносятся к
// новому родителю) идёт в строку i. Это единственный источник истины о
// текущей раскладке; оба обработчика кнопок ниже только меняют `widths`,
// а затем вызывают эту функцию для перерисовки.
//
// Инвариант, на который это опирается и который нельзя незаметно сломать:
// когда у задания есть строка-шапка, её .task-col (помечен data-role="header"
// в Python) — это всегда cols[0] — строка 0 всегда заполняется с индекса 0
// вперёд, так что шапка всегда оказывается первой колонкой, помещаемой в
// строку 0. В неё можно только добавлять ("+" затягивает первый элемент
// следующей строки), но никогда не выселить через "-" (которая всегда
// убирает только *последнюю* колонку строки, а шапка никогда не последняя,
// пока ширина > 1). Если порядок заполнения этой функции когда-нибудь
// изменится — перепроверь, что этот инвариант всё ещё верен.
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
        // Затягиваем первый компонент следующей строки как новую колонку
        // этой строки; если следующая строка теперь пуста — убираем её целиком.
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
        // Выселяем последний компонент этой строки в свежую полноширинную
        // строку в самом конце. Каждая строка после этой сохраняет свою
        // ширину, так что её содержимое сдвигается на одну позицию — этот
        // каскад сам получается из учёта ширин, без явного цикла здесь.
        widths[rowIndex] -= 1;
        widths.push(1);
        rebuildTaskRows(container, widths, cols);
    });
    wrap.appendChild(removeBtn);

    return wrap;
}

function initRowControls() {
    document.querySelectorAll(".task-components").forEach(function (container) {
        // Тот же гвард на переоткрытие через "Сохранить страницу как", что и
        // у билдера тулбара ниже — без него повторный запуск на уже
        // перестроенном DOM заново оборачивал бы строки и задваивал
        // .row-controls на каждом цикле переоткрытия.
        if (container.dataset.rowControlsBuilt) return;
        container.dataset.rowControlsBuilt = "1";

        // Намеренно :scope > .task-row > .task-col, а не row.children —
        // у перестроенной строки есть ещё и соседний .row-controls, который
        // иначе ошибочно посчитался бы как лишняя колонка.
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
        // Защита от повторной постройки: браузерное "Сохранить страницу как"
        // захватывает живой DOM, т.е. тулбар, уже наполненный кнопками этим
        // же скриптом при предыдущей загрузке. Повторное открытие такого
        // сохранённого файла заново запускает этот скрипт на уже построенном
        // тулбаре; без этого гварда он дописал бы второй набор кнопок поверх
        // (а третий — при следующем цикле сохранения/открытия, и так далее).
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
