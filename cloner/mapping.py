import json
from pathlib import Path

_MAP_PATH = Path("output/id_map.json")

_RESOURCE_TYPES = ["product", "variant", "collection", "page", "blog", "article", "menu"]


class IDMapping:
    def __init__(self):
        if _MAP_PATH.exists():
            raw = json.loads(_MAP_PATH.read_text(encoding="utf-8"))
            self._map: dict[str, dict[str, str]] = raw
        else:
            self._map = {t: {} for t in _RESOURCE_TYPES}

        for t in _RESOURCE_TYPES:
            self._map.setdefault(t, {})

    def set(self, resource_type: str, source_id: int | str, target_id: int | str) -> None:
        self._map.setdefault(resource_type, {})[str(source_id)] = str(target_id)
        _MAP_PATH.parent.mkdir(parents=True, exist_ok=True)
        _MAP_PATH.write_text(json.dumps(self._map, indent=2), encoding="utf-8")

    def get(self, resource_type: str, source_id: int | str) -> str:
        key = str(source_id)
        bucket = self._map.get(resource_type, {})
        if key not in bucket:
            raise KeyError(f"No mapping for {resource_type} id={source_id}")
        return bucket[key]

    def has(self, resource_type: str, source_id: int | str) -> bool:
        return str(source_id) in self._map.get(resource_type, {})

    def save(self) -> None:
        _MAP_PATH.parent.mkdir(parents=True, exist_ok=True)
        _MAP_PATH.write_text(json.dumps(self._map, indent=2), encoding="utf-8")
