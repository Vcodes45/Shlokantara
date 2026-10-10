from typing import Literal

from pydantic import BaseModel, Field


AnswerLanguage = Literal[
    "en", "hi", "mr",
    "sd", "sd-Arab", "sd-Deva",
    "sa", "ta", "te", "kn", "ml", "bn", "gu", "pa", "or",
    "es", "fr", "de",
]


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)
    answer_language: AnswerLanguage = "en"
    source_language: str | None = Field(default=None, max_length=16)
    limit: int = Field(default=5, ge=1, le=8)
