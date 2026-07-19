"""Статические шаблонные блобы: сниппет KaTeX для <head> и базовый CSS.
Логики рендеринга здесь нет — только строки, которые document.py вклеивает в
сгенерированный HTML. Клиентского JS, кроме KaTeX, в листе нет вообще."""

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

# Оболочка листа: сплошной поток заданий в центрированной колонке читаемой
# ширины (см. "Оболочка листа" в references/design-system.md). Никакой
# вёрстки под печать/A4 здесь нет — ни @page, ни @media print, ни экранной
# пагинации: лист — обычный документ для чтения с экрана.
BASE_CSS = """
:root {
    --font-main: "PT Sans", "Segoe UI", Verdana, Arial, sans-serif;
}
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
.meta-line .blank { display: inline-block; min-width: 105px; border-bottom: 1px solid #000; margin: 0 8px; }
.sheet-title { font-size: 16pt; font-weight: bold; margin: 0 0 4px 0; }
.sheet-subtitle { font-size: 10.5pt; color: #333; margin: 0 0 11px 0; }
.sheet-instructions { font-style: italic; font-size: 11pt; margin: 8px 0 0 0; }
/* Подзаголовок раздела документа (--document, блок `heading`); в заданиях
   листа заголовков нет — иерархию там рисуют номер и буквы подзаданий. */
.doc-heading { font-size: 13.5pt; font-weight: bold; margin: 20px 0 8px 0; }
.task { margin: 0 0 26px 0; }
.task-header { display: flex; align-items: baseline; gap: 8px; margin-bottom: 8px; }
.task-num { font-weight: bold; font-size: 12pt; flex: 0 0 auto; }
.task-points { font-size: 9pt; color: #333; }
.solution-area { margin-top: 8px; }
.solution-line { border-bottom: 1px dotted #000; height: 26px; }
.answer-line { display: inline-block; min-width: 150px; border-bottom: 1px solid #000; margin-left: 8px; }
.answer-block {
    margin-top: 8px; padding: 8px 11px; border: 1px dashed #000; font-size: 11pt;
    background: repeating-linear-gradient(45deg, #fff, #fff 4px, #f2f2f2 4px, #f2f2f2 5px);
}
.bank-list { margin-top: 8px; font-size: 11pt; }
/* Подсказка "Отметьте все подходящие варианты." над списком choice при
   select: multiple — без неё single и multiple неотличимы для ученика. */
.choice-hint { font-style: italic; font-size: 10.5pt; margin-top: 8px; }
/* Тот же грид-механизм равных колонок, что у .task-row — один CSS-язык
   для любого "рядом". */
.match-columns { display: grid; grid-auto-flow: column; grid-auto-columns: 1fr; gap: 45px; align-items: start; margin-top: 8px; }
/* Разметка списка (list_html, components.py) — единый визуальный язык для
   choice/true_false/rank/classify/match и обычных списков, см. "Компоненты"
   в task-schema.md. */
.list-component { margin-top: 8px; }
.list-row { display: flex; align-items: baseline; gap: 8px; padding: 5px 8px; }
.list-marker { font-weight: bold; flex: 0 0 auto; }
.list-content { flex: 1 1 auto; min-width: 0; }
/* Зебра — только для одиночной колонки (single); строится по всем видам
   list-контента одинаково. */
.list-component.cols-single .list-row:nth-child(even) { background: #f2f2f2; }
.list-component.cols-two { display: block; column-count: 2; column-gap: 30px; }
.list-component.cols-two .list-row { display: block; margin-bottom: 6px; break-inside: avoid-column; }
.list-component.cols-inline { display: block; }
.list-component.cols-inline .list-row { display: inline-block; margin-right: 23px; }
/* Внутренняя разбивка строки на "утверждение слева / отметка справа" —
   переиспользуется рендером true_false/rank/classify (questions.py) внутри
   их item-строк (list_html об этом не знает — это содержимое `list-content`). */
.tf-line { display: flex; align-items: center; justify-content: space-between; width: 100%; gap: 15px; }
.tf-statement { flex: 1; }
.tf-box { display: inline-flex; align-items: center; gap: 6px; font-size: 10pt; white-space: nowrap; }
.tf-square {
    display: inline-block; width: 17px; height: 17px; border: 1.3px solid #000;
    text-align: center; line-height: 16px; font-weight: bold; font-size: 9pt;
}
.rank-square {
    display: inline-block; flex: 0 0 auto; width: 17px; height: 17px; border: 1.3px solid #000;
    text-align: center; line-height: 16px; font-weight: bold; font-size: 9pt;
}
.mc-marker { display: inline-block; width: 15px; text-align: center; font-weight: bold; }
.mc-correct { font-weight: bold; }
.table-component { border-collapse: collapse; width: 100%; margin-top: 8px; }
.table-component th, .table-component td {
    border: 1px solid #000; padding: 6px 9px; text-align: center; font-size: 11pt;
}
.table-component th { background: #eee; }
.fill-blank { display: inline-block; min-width: 68px; border-bottom: 1px solid #000; margin: 0 4px; text-align: center; }
.fill-blank.answered { border-bottom: none; font-weight: bold; text-decoration: underline; }
.subtask-label { font-weight: bold; font-size: 12pt; flex: 0 0 auto; }
/* Блоки задания идут друг под другом на всю ширину колонки; единственный
   способ поставить блоки рядом — layout-контейнер `row` (см. task-schema.md).
   График при этом не растягивается на всю колонку: у svg.visual-svg
   фиксированный max-width — его viewBox/шрифты откалиброваны под эту ширину
   (см. комментарий в build_chart_svg, worksheet_builder/visuals.py).
   Селектор намеренно узкий (svg.visual-svg, не голый svg) — чтобы не
   задевать маленькие svg-иконки легенды графика. */
.task-block { margin-bottom: 8px; }
.task-block:last-child { margin-bottom: 0; }
.task-block svg.visual-svg { display: block; width: 100%; max-width: 330px; height: auto; }
/* Подзадание (`part`) — с небольшим отступом от общего условия задания. */
.task-part { margin: 11px 0 11px 23px; }
/* Layout-контейнер `row` — дети стоят в одну строку и делят её поровну
   (см. task-schema.md). Грид с равными колонками сам учитывает gap —
   никаких инлайновых ширин из Python. */
.task-row { display: grid; grid-auto-flow: column; grid-auto-columns: 1fr; gap: 23px; align-items: start; margin-bottom: 8px; }
.task-row:last-child { margin-bottom: 0; }
.task-col { min-width: 0; }
.task-col .task-part { margin-left: 0; }
.chart-wrap { margin-top: 8px; }
.chart-legend { display: flex; gap: 15px; font-size: 8pt; margin-top: 4px; flex-wrap: wrap; }
/* Приборы (компонент `instrument`): ширина висит на обёртке семейства, SVG
   заполняет её (правило svg.visual-svg выше). Масштаб всех семейств ~1.5px
   на единицу viewBox — как у графиков (220 -> 330px), чтобы шрифты всех SVG
   листа были одного экранного размера; при смене ширины перепроверь
   калибровку рендером (см. instruments.py). */
.instrument-wrap { margin-top: 8px; }
.instrument-wrap.instrument-strip { max-width: 330px; }
.instrument-wrap.instrument-column { max-width: 105px; }
.instrument-wrap.instrument-dial { max-width: 240px; }
.instrument-wrap.instrument-clock { max-width: 180px; }
.instrument-wrap.instrument-vernier { max-width: 330px; }
.instrument-wrap.instrument-digital { max-width: 225px; }
.instrument-caption { font-size: 9pt; text-align: center; margin-top: 3px; }
""".strip()
