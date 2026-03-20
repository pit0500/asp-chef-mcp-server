"""Shared mutable state: the current ASP Chef recipe snapshot."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass
class RecipeState:
    ingredients: list[dict[str, Any]] = field(default_factory=list)
    connector_index: int = -1
    docs: dict[str, str] = field(default_factory=dict)

    def set_doc(self, docs: dict[str, str]) -> None:
        self.docs = docs

    def get_operation_doc(self, operation: str) -> str:
        return self.docs.get(operation, f"Documentation for operation '{operation}' not found.")

    def update(self, ingredients: list[dict], connector_index: int) -> None:
        self.ingredients = ingredients
        self.connector_index = connector_index

    def ingredient_at(self, index: int) -> dict | None:
        if 0 <= index < len(self.ingredients):
            return self.ingredients[index]
        return None
