"""Реестр вопросов — см. references/task-schema.md."""

from questions.choice import ChoiceQuestion
from questions.classify import ClassifyQuestion
from questions.fill_table import FillTableQuestion
from questions.fill_text import FillTextQuestion
from questions.match import MatchQuestion
from questions.open import OpenQuestion
from questions.plot import PlotQuestion
from questions.rank import RankQuestion
from questions.true_false import TrueFalseQuestion

QUESTION_TYPES = {
    "open": OpenQuestion,
    "choice": ChoiceQuestion,
    "match": MatchQuestion,
    "fill_text": FillTextQuestion,
    "fill_table": FillTableQuestion,
    "plot": PlotQuestion,
    "true_false": TrueFalseQuestion,
    "rank": RankQuestion,
    "classify": ClassifyQuestion,
}


def question_from_dict(data: dict):
    question = QUESTION_TYPES[data["type"]].from_dict(data)
    question.validate()
    return question
