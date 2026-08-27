"""Pydantic models mirroring the database tables (design doc §12).

Each model knows how to convert itself to/from a database row. Structured
fields (dicts/lists) live as JSON text columns in SQLite; the JSON_FIELDS
map declares which attribute serializes into which column.
"""

import json
from datetime import datetime, timezone
from typing import Any, ClassVar, Literal

from pydantic import BaseModel, Field

RunStatus = Literal["pending", "running", "completed", "failed"]
SourceType = Literal["homepage", "features", "pricing", "about", "comparison", "other"]
Section = Literal[
    "executive_summary", "competitive_landscape", "feature_comparison", "pricing_comparison"
]
# The trust model from design doc §7: verified = primary source,
# reported = secondary source, interpretation = labeled AI analysis.
ClaimType = Literal["verified", "reported", "interpretation"]


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class RowModel(BaseModel):
    """Base class handling row <-> model conversion, including JSON columns."""

    JSON_FIELDS: ClassVar[dict[str, str]] = {}  # attribute name -> db column name

    id: int | None = None

    def to_row(self) -> dict:
        data = self.model_dump()
        if data.get("id") is None:
            data.pop("id")  # let SQLite autoincrement assign it
        for attr, column in self.JSON_FIELDS.items():
            data[column] = json.dumps(data.pop(attr))
        return data

    @classmethod
    def from_row(cls, row) -> "RowModel":
        data = dict(row)
        for attr, column in cls.JSON_FIELDS.items():
            data[attr] = json.loads(data.pop(column))
        return cls(**data)


class Product(RowModel):
    JSON_FIELDS: ClassVar[dict[str, str]] = {"profile": "profile_json"}

    url: str
    domain: str
    name: str | None = None
    category: str | None = None
    profile: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=utcnow_iso)


class Run(RowModel):
    product_id: int
    status: RunStatus = "pending"
    started_at: str = Field(default_factory=utcnow_iso)
    finished_at: str | None = None
    cost_cents: int = 0
    token_count: int = 0
    tool_calls: int = 0
    error: str | None = None


class Competitor(RowModel):
    JSON_FIELDS: ClassVar[dict[str, str]] = {"discovery_methods": "discovery_methods_json"}

    run_id: int
    name: str
    domain: str
    relationship: str | None = None
    confidence: float | None = None
    discovery_methods: list[str] = Field(default_factory=list)
    verified: bool = False


class Source(RowModel):
    run_id: int
    competitor_id: int | None = None  # None = source about the original product
    url: str
    source_type: SourceType
    fetched_at: str = Field(default_factory=utcnow_iso)
    raw_text: str | None = None
    http_status: int | None = None
    content_hash: str | None = None


class Finding(RowModel):
    JSON_FIELDS: ClassVar[dict[str, str]] = {
        "value": "value_json",
        "source_ids": "source_ids_json",
    }

    run_id: int
    competitor_id: int | None = None
    dimension: str
    value: Any
    source_ids: list[int] = Field(default_factory=list)
    extracted_at: str = Field(default_factory=utcnow_iso)


class Claim(RowModel):
    JSON_FIELDS: ClassVar[dict[str, str]] = {"source_ids": "source_ids_json"}

    run_id: int
    section: Section
    text: str
    claim_type: ClaimType
    source_ids: list[int] = Field(default_factory=list)
    confidence: float | None = None


class EvalResult(RowModel):
    JSON_FIELDS: ClassVar[dict[str, str]] = {"details": "details_json"}

    run_id: int
    metric: str
    score: float
    details: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=utcnow_iso)
