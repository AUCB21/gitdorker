from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class Dork(BaseModel):
    query: str = Field(..., min_length=1)
    type: Literal["code", "repositories", "commits"] = "code"
    description: str = ""
    remediation: str = ""

    @model_validator(mode="after")
    def strip_query(self) -> "Dork":
        self.query = self.query.strip()
        return self


class DorksConfig(BaseModel):
    dorks: list[Dork]

    @classmethod
    def from_file(cls, path: Path) -> "DorksConfig":
        raw = json.loads(path.read_text(encoding="utf-8"))
        return cls.model_validate(raw)

    @classmethod
    def from_query(
        cls,
        query: str,
        search_type: Literal["code", "repositories", "commits"] = "code",
    ) -> "DorksConfig":
        return cls(dorks=[Dork(query=query, type=search_type)])
