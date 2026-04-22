import asyncio
import os
from pathlib import Path

from cloner.client import ShopifyClient
from cloner.mapping import IDMapping
from cloner.domain import DomainRemapper
from cloner.image_cache import ImageCache
from cloner.phases.products import clone_all_products
from cloner.phases.collections import clone_collections
from cloner.phases.pages import clone_pages
from cloner.phases.blogs import clone_blogs
from cloner.phases.menus import clone_menus
from cloner.phases.policies import clone_policies
from cloner.phases.discounts import clone_discounts
from cloner.phases.theme import clone_theme
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

    src_shop_data = await client.get_source("shop.json")
    dst_shop_data = await client.get_target("shop.json")
    source_shop_name = src_shop_data.get("shop", {}).get("name")
    target_shop_name = dst_shop_data.get("shop", {}).get("name")

    remapper = DomainRemapper(
        source_myshopify=source_shop,
        target_domain=os.environ.get("TARGET_CUSTOM_DOMAIN") or _require("TARGET_SHOP"),
        source_custom=os.environ.get("SOURCE_CUSTOM_DOMAIN") or None,
        source_shop_name=source_shop_name,
        target_shop_name=target_shop_name,
    )

    cache = ImageCache()
    report: list[dict] = []

    try:
        # 1. Produits + variantes
        product_entries = await clone_all_products(client, mapping, remapper)
        report.extend(product_entries)
        mapping.save()

        # 2. Collections
        collection_entries = await clone_collections(client, mapping, remapper, cache)
        report.extend(collection_entries)
        mapping.save()

        # 3. Pages statiques
        page_entries = await clone_pages(client, mapping, remapper)
        report.extend(page_entries)
        mapping.save()

        # 4. Blogs + articles
        blog_entries = await clone_blogs(client, mapping, remapper)
        report.extend(blog_entries)
        mapping.save()

        # 5. Menus
        menu_entries = await clone_menus(client, mapping, remapper)
        report.extend(menu_entries)
        mapping.save()

        # 6. Politiques du site
        policy_entries = await clone_policies(client, remapper)
        report.extend(policy_entries)

        # 7. Réductions
        discount_entries = await clone_discounts(client, mapping, remapper)
        report.extend(discount_entries)
        mapping.save()

        # 8. Thème actif
        theme_entries = await clone_theme(client, mapping, remapper)
        report.extend(theme_entries)
        mapping.save()

        print("Clone complete.")
    finally:
        save_report(report)
        await client.close()


if __name__ == "__main__":
    load_env()
    asyncio.run(run_clone())
