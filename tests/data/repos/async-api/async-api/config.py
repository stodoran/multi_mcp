from dataclasses import dataclass


@dataclass
class Settings:
    min_score: float = 0.3
    storage_dir_name: str = "data"
    enable_cache: bool = True

_cached_settings: Settings | None = None

def get_settings() -> Settings:
    global _cached_settings
    if _cached_settings is None:
        _cached_settings = Settings()
    return _cached_settings
