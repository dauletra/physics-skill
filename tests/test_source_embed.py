"""Встроенный черновик в тичер-HTML (document.render_source_script):
round-trip (встроенное == исходному), защита от `</script>` в авторском
тексте и сквозная проверка CLI — у учителя черновик есть, у ученика нет."""
import json
import re
import sys

from worksheet_builder.cli import main
from worksheet_builder.document import build_document, render_source_script
from worksheet_builder.models import parse_meta, parse_task

SOURCE_RE = re.compile(
    r'<script type="application/json" id="worksheet-source">(.*?)</script>',
    re.S,
)


def extract_source(html: str) -> dict:
    matches = SOURCE_RE.findall(html)
    assert len(matches) == 1, "Ожидался ровно один worksheet-source"
    return json.loads(matches[0])


def make_source(body: str) -> dict:
    return {
        "meta": {"title": "Лист"},
        "tasks": [{
            "id": "task-01",
            "blocks": [
                {"type": "text", "body": body},
                {"type": "open", "answer": "υ = 5 м/с"},
            ],
        }],
    }


def build_teacher(source: dict) -> str:
    meta = parse_meta(source["meta"])
    tasks = [parse_task(raw) for raw in source["tasks"]]
    return build_document(meta, tasks, is_teacher=True, source=source)


def test_source_round_trips():
    source = make_source("Тело движется со скоростью υ₀ > 0.")
    assert extract_source(build_teacher(source)) == source


def test_script_closer_in_content_cannot_break_out():
    # Авторский текст с </script> не должен закрыть тег черновика досрочно:
    # весь payload живёт без единого сырого "<".
    source = make_source('Коварный текст </script><img src=x> и "кавычки".')
    html = build_teacher(source)
    payload = SOURCE_RE.findall(html)[0]
    assert "<" not in payload
    assert extract_source(html) == source


def test_render_source_script_escapes_all_angle_brackets():
    script = render_source_script({"x": "a<b</script>"})
    inner = script.removeprefix(
        '<script type="application/json" id="worksheet-source">'
    ).removesuffix("</script>")
    assert "<" not in inner


def test_no_source_when_not_passed():
    source = make_source("Обычный текст.")
    meta = parse_meta(source["meta"])
    tasks = [parse_task(raw) for raw in source["tasks"]]
    assert "worksheet-source" not in build_document(meta, tasks, is_teacher=True)


def test_cli_embeds_source_only_into_teacher(tmp_path, monkeypatch):
    source = make_source("Сквозной прогон CLI.")
    (tmp_path / "tasks").mkdir()
    (tmp_path / "meta.json").write_text(
        json.dumps(source["meta"], ensure_ascii=False), encoding="utf-8"
    )
    (tmp_path / "tasks" / "task-01.json").write_text(
        json.dumps(source["tasks"][0], ensure_ascii=False), encoding="utf-8"
    )
    monkeypatch.setattr(sys, "argv", ["render-worksheet", str(tmp_path)])
    main()

    teacher = (tmp_path / "output" / "worksheet-teacher.html").read_text(encoding="utf-8")
    student = (tmp_path / "output" / "worksheet-student.html").read_text(encoding="utf-8")
    assert extract_source(teacher) == source
    assert "worksheet-source" not in student


def test_cli_task_preview_has_no_source(tmp_path, monkeypatch):
    # Превью одного задания — черновой артефакт, черновик в него не едет.
    source = make_source("Превью без черновика.")
    (tmp_path / "tasks").mkdir()
    (tmp_path / "meta.json").write_text(
        json.dumps(source["meta"], ensure_ascii=False), encoding="utf-8"
    )
    (tmp_path / "tasks" / "task-01.json").write_text(
        json.dumps(source["tasks"][0], ensure_ascii=False), encoding="utf-8"
    )
    monkeypatch.setattr(sys, "argv", ["render-worksheet", str(tmp_path), "--task", "task-01"])
    main()
    preview = (tmp_path / "task-01.preview.html").read_text(encoding="utf-8")
    assert "worksheet-source" not in preview
