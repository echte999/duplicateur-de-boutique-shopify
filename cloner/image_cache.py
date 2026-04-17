from pathlib import Path
from urllib.parse import urlparse
import httpx


class ImageCache:
    def __init__(self, cache_dir: str = "tmp_images"):
        self._root = Path(cache_dir)

    def _local_path(self, url: str, product_id: int | str) -> Path:
        parsed = urlparse(url)
        filename = Path(parsed.path).name
        return self._root / str(product_id) / filename

    async def download(self, client: httpx.AsyncClient, url: str, product_id: int | str) -> Path:
        local = self._local_path(url, product_id)
        if local.exists():
            return local

        local.parent.mkdir(parents=True, exist_ok=True)
        response = await client.get(url)
        response.raise_for_status()
        local.write_bytes(response.content)
        return local
