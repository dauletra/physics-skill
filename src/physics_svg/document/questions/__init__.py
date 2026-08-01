"""Question types: one module per pedagogical kind.

    questions/<tag>.py    spec + body renderer + answer renderer + register()
    questions/<tag>.md    reference fragment for the model, worked examples
    questions/<tag>.card.md   card for the teacher, shown on the site

See registry.py for the contract, and docs/schema-design-principles.md for
the rules a new kind has to satisfy — chiefly: the payload is the fields
natural to *that* kind, and the correct answer lives inline next to the
content it belongs to.
"""

from physics_svg.document.questions.registry import (
    QuestionType,
    is_question,
    load_all,
    question_models,
    register,
    render_answer,
    render_body,
)

__all__ = [
    "QuestionType",
    "is_question",
    "load_all",
    "question_models",
    "register",
    "render_answer",
    "render_body",
]
