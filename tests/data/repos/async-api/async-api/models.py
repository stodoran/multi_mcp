from dataclasses import dataclass
from typing import Any


@dataclass
class Item:
    id: str
    name: str
    score: float

    def is_valid(self, min_score: float) -> bool:
        return self.score >= min_score

def parse_item(payload: dict[str, Any], default_min_score: float = 0.5) -> Item:
    return Item(
        id=str(payload.get("id", "")),
        name=str(payload.get("name", "")),
        score=float(payload.get("score", 0.0)),
    )
