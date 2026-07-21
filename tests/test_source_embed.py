"""Встроенный черновик в итоговом HTML (document.render_source_script):
round-trip (встроенное == исходному), защита от `</script>` в авторском
тексте и сквозная проверка CLI — у полного варианта черновик есть, у
раздаточного (--no-answers) и у превью блока — нет."""
import json
import re
import sys

from worksheet_builder.cli import main
from worksheet_builder.document import build_document, render_source_script
from worksheet_builder.models import parse_block, parse_document

SOURCE_RE = re.compile(
    r'<script type="application/json" id="document-source">(.*?)</script>',
    re.S,
)


def extract_source(html: str) -> dict:
    matches = SOURCE_RE.findall(html)
    assert len(matches) == 1, "Ожидался ровно один document-source"
    return json.loads(matches[0])


def make_source(body: str) -> dict:
    return {
        "document": {"title": "Документ"},
        "blocks": [{
            "type": "task",
            "id": "task-01",
            "blocks": [
                {"type": "text", "body": body},
                {"type": "open", "answer": "υ = 5 м/с"},
            ],
        }],
    }


def build_full(source: dict) -> str:
    doc = parse_document(source["document"])
    blocks = [parse_block(raw) for raw in source["blocks"]]
    return build_document(doc, blocks, with_answers=True, source=source)


def write_workspace(tmp_path, source: dict) -> None:
    (tmp_path / "blocks").mkdir()
    (tmp_path / "document.json").write_text(
        json.dumps(source["document"], ensure_ascii=False), encoding="utf-8"
    )
    for raw in source["blocks"]:
        (tmp_path / "blocks" / f"{raw['id']}.json").write_text(
            json.dumps(raw, ensure_ascii=False), encoding="utf-8"
        )


def test_source_round_trips():
    source = make_source("Тело движется со скоростью υ₀ > 0.")
    assert extract_source(build_full(source)) == source


def test_script_closer_in_content_cannot_break_out():
    # Авторский текст с </script> не должен закрыть тег черновика досрочно:
    # весь payload живёт без единого сырого "<".
    source = make_source('Коварный текст </script><img src=x> и "кавычки".')
    html = build_full(source)
    payload = SOURCE_RE.findall(html)[0]
    assert "<" not in payload
    assert extract_source(html) == source


def test_render_source_script_escapes_all_angle_brackets():
    script = render_source_script({"x": "a<b</script>"})
    inner = script.removeprefix(
        '<script type="application/json" id="document-source">'
    ).removesuffix("</script>")
    assert "<" not in inner


def test_no_source_when_not_passed():
    source = make_source("Обычный текст.")
    doc = parse_document(source["document"])
    blocks = [parse_block(raw) for raw in source["blocks"]]
    assert "document-source" not in build_document(doc, blocks, with_answers=True)


def test_cli_embeds_source_only_into_full_variant(tmp_path, monkeypatch):
    source = make_source("Сквозной прогон CLI.")
    write_workspace(tmp_path, source)

    monkeypatch.setattr(sys, "argv", ["render-worksheet", str(tmp_path)])
    main()
    full = (tmp_path / "output" / "document.html").read_text(encoding="utf-8")
    assert extract_source(full) == source

    # Раздаточный вариант: ни ответов, ни черновика (он бы их раскрыл).
    monkeypatch.setattr(sys, "argv", ["render-worksheet", str(tmp_path), "--no-answers"])
    main()
    handout = (tmp_path / "output" / "document-no-answers.html").read_text(encoding="utf-8")
    assert "document-source" not in handout
    assert 'class="answers-section"' not in handout


def test_cli_block_preview_has_no_source(tmp_path, monkeypatch):
    # Превью одного блока — черновой артефакт, черновик в него не едет.
    source = make_source("Превью без черновика.")
    write_workspace(tmp_path, source)
    monkeypatch.setattr(sys, "argv", ["render-worksheet", str(tmp_path), "--block", "task-01"])
    main()
    preview = (tmp_path / "task-01.preview.html").read_text(encoding="utf-8")
    assert "document-source" not in preview
    # Ответ в превью есть: оно всегда с ответами.
    assert 'class="answers-section"' in preview
