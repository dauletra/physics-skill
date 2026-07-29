"""Fixed interface strings and the letter series for subtasks.

Documents are Russian only, so the dictionary is flat — no language key.
Content (problem statements, options, answers) never comes from here: it is
written straight into the draft JSON.

Never hard-code any of these in markup; going through `t()` is what keeps a
label the same in the body of a task and in the answers section.
"""

from __future__ import annotations

STRINGS = {
    "school_class": "Школа/класс:",
    "date": "Дата:",
    "full_name": "Фамилия Имя:",
    "grade_suffix": "класс",
    "answer_label": "Ответ:",
    "answers_title": "Ответы",
    "explanation_label": "Пояснение:",
    "bank_label": "Слова/категории для выбора:",
    "choice_multiple_hint": "Отметьте все подходящие варианты.",
    "true_label": "Верно",
    "false_label": "Неверно",
    "points_suffix": "б.",
    "default_title": "Документ",
}

#: Enumeration letters for subtasks (`а)`, `б)`…), list markers and the
#: `match` summary — Cyrillic, as Russian textbooks number them, with the
#: standard omissions (no ё/й/ъ/ы/ь). One source for all three places: the
#: printed letter and the letter in an answer must be the same letter.
LETTERS = "абвгдежзиклмнопрстуфхцчшщэюя"


def t(key: str) -> str:
    return STRINGS[key]
