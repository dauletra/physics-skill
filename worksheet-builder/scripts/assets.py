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

# Пресеты полей печати, названы по образцу выпадающего списка полей в диалоге
# печати Chrome ("По умолчанию"/"Нет"/"Минимум"). "default" зеркалит прежнее
# жёстко зашитое значение @page. У "minimum" нет единственно верного значения
# — Chrome сам вычисляет своё "Минимум" из непечатаемой области выбранного
# принтера/драйвера, а это не постоянная величина, так что здесь наше
# собственное небольшое приближение, без гарантии совпадения с конкретным
# принтером. Выбор пресета — поле `print_margins` в meta.json, разрешается в
# конкретные мм ровно один раз при сборке (build_base_css ниже), никакого
# рантайм-переключателя в браузере больше нет.
PRINT_MARGIN_PRESETS = {
    "default": {"top": 15, "right": 15, "bottom": 15, "left": 18},
    "none": {"top": 0, "right": 0, "bottom": 0, "left": 0},
    "minimum": {"top": 5, "right": 5, "bottom": 5, "left": 8},
}


def resolve_print_margin_mm(preset_key):
    preset = PRINT_MARGIN_PRESETS.get(preset_key, PRINT_MARGIN_PRESETS["default"])
    return f'{preset["top"]}mm {preset["right"]}mm {preset["bottom"]}mm {preset["left"]}mm'


_BASE_CSS_TEMPLATE = """
:root {
    --font-main: "PT Sans", "Segoe UI", Verdana, Arial, sans-serif;
    /* Поле страницы — фиксируется на сборке из `meta.json.print_margins`
       (см. build_base_css/resolve_print_margin_mm), никакого рантайм-
       переключателя в браузере больше нет. Зеркалит margin у @page ниже —
       оба всегда получают одно и то же значение при генерации. */
    --page-margin: __PAGE_MARGIN__;
}
@page { size: A4; margin: __PAGE_MARGIN__; }
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
.bank-list { margin-top: 2mm; font-size: 11pt; }
.matching-columns { display: flex; gap: 12mm; margin-top: 2mm; }
.matching-columns .list-component { flex: 1; }
/* Разметка ListComponent (уровень 2, components/list.py) — единый визуальный
   язык для choice/true_false/ranking/classify/matching и обычных списков, см.
   "Уровень 2: чистые компоненты" в task-schema.md. */
.list-component { margin-top: 2mm; }
.list-row { display: flex; align-items: baseline; gap: 2mm; padding: 1.2mm 2mm; }
.list-marker { font-weight: bold; flex: 0 0 auto; }
.list-content { flex: 1 1 auto; min-width: 0; }
/* Зебра — только для одиночной колонки (single); строится по всем видам
   list-контента одинаково, а не только для true_false/ranking, как раньше. */
.list-component.cols-single .list-row:nth-child(even) { background: #f2f2f2; }
.list-component.cols-two { display: block; column-count: 2; column-gap: 8mm; }
.list-component.cols-two .list-row { display: block; margin-bottom: 1.5mm; break-inside: avoid-column; }
.list-component.cols-inline { display: block; }
.list-component.cols-inline .list-row { display: inline-block; margin-right: 6mm; }
/* Внутренняя разбивка строки на "утверждение слева / отметка справа" —
   переиспользуется true_false.py/ranking.py/classify.py внутри их item-строк
   (ListComponent сам об этом не знает — это содержимое `list-content`). */
.tf-line { display: flex; align-items: center; justify-content: space-between; width: 100%; gap: 4mm; }
.tf-statement { flex: 1; }
.tf-box { display: inline-flex; align-items: center; gap: 1.5mm; font-size: 10pt; white-space: nowrap; }
.tf-square {
    display: inline-block; width: 4.5mm; height: 4.5mm; border: 1.3px solid #000;
    text-align: center; line-height: 4.2mm; font-weight: bold; font-size: 9pt;
}
.rank-square {
    display: inline-block; flex: 0 0 auto; width: 4.5mm; height: 4.5mm; border: 1.3px solid #000;
    text-align: center; line-height: 4.2mm; font-weight: bold; font-size: 9pt;
}
.mc-marker { display: inline-block; width: 4mm; text-align: center; font-weight: bold; }
.mc-correct { font-weight: bold; }
.table-component { border-collapse: collapse; width: 100%; margin-top: 2mm; }
.table-component th, .table-component td {
    border: 1px solid #000; padding: 1.5mm 2.5mm; text-align: center; font-size: 11pt;
}
.table-component th { background: #eee; }
.fill-blank { display: inline-block; min-width: 18mm; border-bottom: 1px solid #000; margin: 0 1mm; text-align: center; }
.fill-blank.answered { border-bottom: none; font-weight: bold; text-decoration: underline; }
.subtask-label { font-weight: bold; font-size: 12pt; flex: 0 0 auto; }
/* Общая раскладка компонентов задания по строкам/колонкам (см. `layout` в
   task-schema.md), заменяет старую фиксированную пару "текст | один визуал".
   Ширина колонки задаётся инлайновым `style="flex:0 0 N%"` на каждом
   .task-col (проставляется в Python из `layout`), а не фиксированным набором
   CSS-классов, так что работает любое процентное разбиение, а не только
   горстка пресетов. Раскладка целиком решается на сборке — в браузере её
   больше нельзя перегруппировать (никаких hover-контролов). */
.task-components { }
.task-row { display: flex; gap: 6mm; align-items: flex-start; margin-bottom: 2mm; }
.task-row:last-child { margin-bottom: 0; }
.task-col { min-width: 0; }
.task-col svg.visual-svg { display: block; width: 100%; height: auto; }
.task-component-lettered { margin: 3mm 0 3mm 6mm; }
.chart-wrap { margin-top: 2mm; }
.chart-legend { display: flex; gap: 4mm; font-size: 8pt; margin-top: 1mm; flex-wrap: wrap; }
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
@media print {
    body { padding: 0; width: auto; }
    body.page-view { background: #fff; padding: 0; }
    .a4-page {
        box-shadow: none; margin: 0; padding: 0; width: auto; min-height: 0;
        break-after: page;
    }
    .a4-page:last-child { break-after: auto; }
    .task { break-inside: avoid; }
}
""".strip()


def build_base_css(print_margins_preset):
    """Печёт фиксированные поля печати (`meta.json.print_margins`) в CSS один
    раз при сборке — см. `_BASE_CSS_TEMPLATE`/`PRINT_MARGIN_PRESETS` выше."""
    margin = resolve_print_margin_mm(print_margins_preset)
    return _BASE_CSS_TEMPLATE.replace("__PAGE_MARGIN__", margin)


# Клиентский JS ограничен исключительно пассивным экранным превью разбивки на
# страницы (paginate() — см. "Page-view" в design-system.md): показывает,
# сколько печатных страниц выйдет при полях, зафиксированных на сборке, но
# ничего не редактирует и не переключает. Любая настройка листа/компонента
# (поля печати, видимость места для решения, раскладка вариантов ответа,
# раскладка компонентов по строкам) — это поле в JSON, разрешается один раз
# в Python; рантайм-тулбаров и hover-контролов больше нет.
LAYOUT_JS = """
// Экранный "вид по страницам A4": разбивает поток элементов
// .sheet-header/.task на визуально отдельные карточки размером со страницу,
// так что при открытии файла количество печатных страниц видно сразу, без
// номеров страниц. Чисто экранное удобство, ничего не редактирует.
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

// Поля страницы фиксированы на сборке (--page-margin в BASE_CSS) — читаем
// их же значение из вычисленного стиля, а не держим отдельную JS-таблицу
// пресетов, чтобы бюджет высоты страницы не мог разойтись с тем, что реально
// напечатает браузер.
function getPageMarginMm() {
    const raw = getComputedStyle(document.documentElement).getPropertyValue("--page-margin");
    const parts = raw.trim().split(/\\s+/).map(function (v) { return parseFloat(v) || 0; });
    const [top, right, bottom, left] = parts.length === 4 ? parts : [0, 0, 0, 0];
    return {top: top, right: right, bottom: bottom, left: left};
}

function paginate() {
    const body = document.body;
    unwrapPages(body);

    const nodes = Array.from(body.querySelectorAll(":scope > .sheet-header, :scope > .task"));
    if (nodes.length === 0) return;

    const pxPerMm = measurePxPerMm(body);
    if (!pxPerMm) return;
    const margin = getPageMarginMm();
    const pageContentHeightMm = 297 - margin.top - margin.bottom;
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

document.addEventListener("DOMContentLoaded", function () {
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
