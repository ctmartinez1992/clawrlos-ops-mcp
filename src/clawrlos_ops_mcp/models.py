from datetime import datetime

from pydantic import BaseModel


class NewsItem(BaseModel):
    source: str
    external_id: str
    title: str
    url: str | None = None
    summary: str | None = None
    score: float | None = None
    author: str | None = None
    extra: dict = {}
    fetched_at: datetime | None = None
    created_at: datetime | None = None
