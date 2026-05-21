import json
from typing import Any

from pydantic import BaseModel, Field, field_validator


class RuleSetCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    rules_body: str = Field(min_length=1, alias="rules_json")
    version: int = 1

    model_config = {"populate_by_name": True}

    @field_validator("rules_body", mode="before")
    @classmethod
    def normalize_rules_body(cls, value: Any) -> str:
        if isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False)
        return str(value)


class RuleSetOut(BaseModel):
    id: str
    dataset_id: str
    name: str
    rules_body: str
    version: int
    created_at: object
