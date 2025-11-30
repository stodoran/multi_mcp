from typing import Any, Dict, Tuple
from .service import ServiceError, process_item

async def create_item(request_body: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
    try:
        item = await process_item(request_body)
        response_body = {
            "id": item.id,
            "name": item.name,
            "score": item.score,
        }
        return 201, response_body
    except ServiceError as exc:
        return 500, {"error": str(exc)}
