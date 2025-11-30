from typing import Any

from .config import get_settings
from .models import Item, parse_item
from .storage import save_item_dict, set_last_item


class ServiceError(RuntimeError):
    pass

async def process_item(payload: dict[str, Any]) -> Item | None:
    settings = get_settings()
    try:
        item = parse_item(payload)
        if not item.is_valid(settings.min_score):
            return None

        filename = payload.get("filename") or f"{item.id}.txt"
        item_dict = {"id": item.id, "name": item.name, "score": item.score}

        save_item_dict(item_dict, filename)
        if settings.enable_cache:
            set_last_item(item.id, item_dict)

        return item
    except Exception as exc:
        raise ServiceError(f"failed: {exc}") from exc
