# Быстрый старт

У скилла два контракта запуска с общим ядром: обычный пользователь работает
через sandbox Claude, разработчик — из репозитория.

## Пользователю: установить скилл

1. Собрать бандл — `python build_bundle.py` в корне репозитория. Итог:
   `dist/worksheet-builder-skill.zip`.
2. Загрузить zip в Claude: **Settings → Capabilities → Skills**.
3. Попросить в диалоге: «сделай рабочий лист по теме …».

Ставить что-либо вручную не нужно: при первом рендере в сессии
`scripts/render.py` сам доустанавливает pydantic (нужна сеть, несколько
секунд, один раз на жизнь контейнера). Дальше рендеры мгновенные.

```
python <путь-к-skill>/scripts/render.py <папка-черновика>
```

## Разработчику: запуск из репозитория

```bash
uv run render-worksheet worksheet-builder/examples/kinematics-9th-grade
```

Или без uv:

```bash
pip install -e ".[dev]"
python -m worksheet_builder worksheet-builder/examples/kinematics-9th-grade
```

## Команды рендерера

| Команда | Что делает |
|---|---|
| `<workspace>` | `output/document.html` — весь документ, секция «Ответы» и встроенный черновик |
| `<workspace> --no-answers` | `output/document-no-answers.html` — раздаточный вариант |
| `<workspace> --block task-03` | `task-03.preview.html` — один блок под его настоящим номером |
| `--visual spec.json [-o out.svg] [--scale 2]` | Один визуальный блок самодостаточным SVG |
| `--emit-schema docs/document.schema.json` | JSON Schema для автокомплита в редакторе |

Полный `document.html` несёт внутри копию черновика
(`<script type="application/json" id="document-source">`) — одного этого
файла достаточно, чтобы вернуться к правкам в новой сессии. Раздаточный
вариант и превью черновик не несут: он раскрыл бы ответы через исходный код
страницы.

## Схема черновика

Машиночитаемая схема — [`document.schema.json`](document.schema.json)
(генерируется из моделей, CI сверяет). Человеческий справочник —
[схема документа](reference/document-schema.md); почему схема устроена
именно так — [принципы схемы](schema-design-principles.md).
