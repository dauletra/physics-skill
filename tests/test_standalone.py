"""Standalone-SVG (`--visual`, worksheet_builder/standalone.py): из спеки
одного визуального блока собирается самодостаточный .svg. Golden фиксирует
общий вид; отдельно проверяются свойства, обязательные для файла вне CSS
листа (корневые width/height/font-family, белая подложка, отсутствие
CSS-классов), точное совпадение рисунка с SVG того же блока внутри листа и
эскейпинг авторского текста. Новый вид визуала покрывается автоматически,
как только его спека добавлена в MINIMAL_VISUALS (conftest)."""
import pytest

from conftest import MINIMAL_VISUALS
from test_escaping import ESCAPED, SENTINEL, STRUCTURAL_KEYS, poison
from worksheet_builder.components import render_component
from worksheet_builder.models import parse_visual
from worksheet_builder.standalone import _VISUAL_SVG_RE, build_standalone_svg


def build(name):
    return build_standalone_svg(parse_visual(MINIMAL_VISUALS[name]))


@pytest.mark.parametrize("name", sorted(MINIMAL_VISUALS))
def test_standalone_golden(name, golden):
    golden(f"visual-{name}", build(name), ext="svg")


@pytest.mark.parametrize("name", sorted(MINIMAL_VISUALS))
def test_standalone_is_self_contained(name):
    # Файл живёт вне HTML/CSS листа: размеры, шрифт и подложка — в нём самом.
    svg = build(name)
    assert svg.startswith("<svg ") and svg.endswith("</svg>")
    root_tag = svg[: svg.index(">")]
    for required in ('xmlns="http://www.w3.org/2000/svg"',
                     'width="', 'height="', 'font-family="'):
        assert required in root_tag, required
    assert 'fill="#fff"' in svg  # белая подложка (тёмный фон презентации)
    assert "class=" not in svg   # ничто не ждёт CSS листа


@pytest.mark.parametrize("name", sorted(MINIMAL_VISUALS))
def test_standalone_matches_worksheet_svg(name):
    # Один и тот же блок в листе и отдельным файлом — один и тот же рисунок.
    model = parse_visual(MINIMAL_VISUALS[name])
    worksheet_inner = _VISUAL_SVG_RE.search(render_component(model)).group(3)
    assert worksheet_inner in build_standalone_svg(model)


@pytest.mark.parametrize("name", sorted(MINIMAL_VISUALS))
def test_standalone_escapes_authored_text(name):
    # `label` в визуалах — свободный текст серии, а не буква part.
    spec = poison(MINIMAL_VISUALS[name], structural=STRUCTURAL_KEYS - {"label"})
    svg = build_standalone_svg(parse_visual(spec))
    assert SENTINEL not in svg, f"сырой HTML из данных просочился в SVG ({name})"
    assert ESCAPED in svg, f"сентинел вообще не попал в вывод ({name})"


def test_non_visual_block_is_rejected():
    with pytest.raises(ValueError, match="'text'"):
        parse_visual({"type": "text", "body": "просто текст"})


def test_spec_errors_name_the_field():
    with pytest.raises(ValueError, match="x_range"):
        parse_visual({"type": "graph", "x_label": "t", "y_label": "s",
                      "x_range": [5, 0], "y_range": [0, 1]})
