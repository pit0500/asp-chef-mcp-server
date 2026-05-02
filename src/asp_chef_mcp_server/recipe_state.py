from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass
class RecipeState:
    ingredients: list[dict[str, Any]] = field(default_factory=list)
    connector_index: int = -1
    connector_id: str = ""
    input_text: str = ""
    global_options: dict[str, Any] = field(default_factory=dict)
    docs: dict[str, str] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    raw_state: dict[str, Any] = field(default_factory=dict)

    def update(self, body: dict) -> None:
        self.raw_state = body
        self.ingredients = body.get("recipe", [])
        self.connector_index = body.get("connector_index", -1)
        self.connector_id = body.get("connector_id", "")
        self.input_text = body.get("input", "")
        self.global_options = body.get("global_options", {})
        self.errors = body.get("errors", [])

    def set_doc(self, docs: dict[str, str]) -> None:
        self.docs = docs

    def get_operation_doc(self, operation: str) -> str:
        return self.docs.get(
            operation, f"Documentation for operation '{operation}' not found."
        )

    def ingredient_at(self, index: int) -> dict | None:
        if 0 <= index < len(self.ingredients):
            return self.ingredients[index]
        return None
