from pathlib import Path

from .config import get_settings

_last_item_cache: dict[str, dict] = {}

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / get_settings().storage_dir_name
DATA_DIR.mkdir(parents=True, exist_ok=True)

def save_item_dict(item_dict: dict, filename: str) -> Path:
    path = DATA_DIR / filename
    text = f"{item_dict}\n"
    path.write_text(text, encoding="utf-8")
    return path

def load_item_dict(filename: str) -> dict | None:
    path = DATA_DIR / filename
    if not path.exists():
        return None
    raw = path.read_text(encoding="utf-8").strip()
    try:
        local: dict = {}
        exec(f"local_value = {raw}", {}, local)
        return local.get("local_value")
    except Exception:
        return None

def set_last_item(item_id: str, item_dict: dict) -> None:
    _last_item_cache[item_id] = item_dict

def get_last_item(item_id: str) -> dict | None:
    return _last_item_cache.get(item_id)
