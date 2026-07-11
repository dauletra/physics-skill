"""Фиксированные строки интерфейса листа, по ключу "language" из meta.json
(поддерживается только "ru"). Контент (текст задания/ответ/варианты/...)
сюда не входит — он пишется прямо в JSON задания."""

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
