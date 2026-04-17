"""Script de réparation : corrige catégorie + swatches couleur sur tous les produits target clonés."""
import asyncio
import json
import os
from pathlib import Path

from cloner.client import ShopifyClient
from cloner.phases.products import (
    _fetch_product_extra,
    _clone_color_swatches,
    _MUTATION_PRODUCT_SET_CATEGORY,
)


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


async def repair_all(client: ShopifyClient, id_map: dict) -> None:
    product_map: dict[str, str] = id_map.get("product", {})
    print(f"{len(product_map)} produits à réparer...")
    metaobject_cache: dict[str, str] = {}
    ok = 0
    errors = 0

    for source_id_str, target_id_str in product_map.items():
        source_id = int(source_id_str)
        target_id = int(target_id_str)
        try:
            category_gid, _, source_options = await _fetch_product_extra(client, source_id)

            if category_gid:
                target_gid = f"gid://shopify/Product/{target_id}"
                cat_result = await client.graphql_target(
                    _MUTATION_PRODUCT_SET_CATEGORY,
                    {"id": target_gid, "categoryId": category_gid},
                )
                cat_errors = cat_result.get("data", {}).get("productUpdate", {}).get("userErrors", [])
                for err in cat_errors:
                    print(f"  [WARN] Catégorie ({target_id}): {err.get('message')}")

            if source_options:
                await _clone_color_swatches(client, source_options, target_id, metaobject_cache)

            ok += 1
            if ok % 10 == 0:
                print(f"  {ok}/{len(product_map)} réparés...")
        except Exception as exc:
            errors += 1
            print(f"  [ERROR] Produit {source_id} → {target_id}: {exc}")

    print(f"Réparation terminée : {ok} OK, {errors} erreurs.")
    print(f"Métaobjets couleur créés/mis à jour : {len(metaobject_cache)}")


async def main() -> None:
    load_env()
    client = ShopifyClient(
        source_shop=_require("SOURCE_SHOP"),
        source_token=_require("SOURCE_TOKEN"),
        target_shop=_require("TARGET_SHOP"),
        target_token=_require("TARGET_TOKEN"),
    )
    id_map = json.loads(Path("output/id_map.json").read_text(encoding="utf-8"))
    try:
        await repair_all(client, id_map)
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
