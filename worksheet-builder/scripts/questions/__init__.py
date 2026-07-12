"""Реестр вопросов уровня 3 — см. references/task-schema.md."""

from questions.choice import ChoiceQuestion
from questions.classify import ClassifyQuestion
from questions.fill_blank import FillBlankTableQuestion, FillBlankTextQuestion
from questions.graph_question import GraphQuestion
from questions.matching import MatchingQuestion
from questions.open import OpenQuestion
from questions.ranking import RankingQuestion
from questions.true_false import TrueFalseQuestion

QUESTION_TYPES = {
    "open": OpenQuestion,
    "choice": ChoiceQuestion,
    "matching": MatchingQuestion,
    "fill_blank_text": FillBlankTextQuestion,
    "fill_blank_table": FillBlankTableQuestion,
    "graph_question": GraphQuestion,
    "true_false": TrueFalseQuestion,
    "ranking": RankingQuestion,
    "classify": ClassifyQuestion,
}


def question_from_dict(data: dict):
    question = QUESTION_TYPES[data["type"]].from_dict(data)
    question.validate()
    return question
