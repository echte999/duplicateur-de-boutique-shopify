import asyncio
import os
from pathlib import Path

from cloner.client import ShopifyClient
from cloner.mapping import IDMapping
from cloner.domain import DomainRemapper
from cloner.image_cache import ImageCache
from cloner.phases.products import clone_all_products
from cloner.phases.collections import clone_collections
from cloner.report import save_report


def load_env(path: str = ".env") -> None:
    env_path = Path(path)
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


def _require(key: str) -> str:
    value = os.environ.get(key)
    if not value:
        raise EnvironmentError(f"Missing required env var: {key}")
    return value


async def run_clone() -> None:
    client = ShopifyClient(
        source_shop=_require("SOURCE_SHOP"),
        source_token=_require("SOURCE_TOKEN"),
        target_shop=_require("TARGET_SHOP"),
        target_token=_require("TARGET_TOKEN"),
    )

    mapping = IDMapping()

    source_shop = _require("SOURCE_SHOP")
    remapper = DomainRemapper(
        source_myshopify=source_shop,
        target_domain=os.environ.get("TARGET_CUSTOM_DOMAIN") or _require("TARGET_SHOP"),
        source_custom=os.environ.get("SOURCE_CUSTOM_DOMAIN") or None,
    )

    cache = ImageCache()
    report: list[dict] = []

    try:
        await clone_all_products(client, mapping, remapper)
        collection_entries = await clone_collections(client, mapping, remapper, cache)
        report.extend(collection_entries)
        save_report(report)
        print("Clone complete.")
    finally:
        await client.close()


if __name__ == "__main__":
    load_env()
    asyncio.run(run_clone())
