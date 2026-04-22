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
from cloner.state import load_state, save_phase_completed, clear_state, cleanup_tmp_images, is_clone_complete
from cloner.phase_selector import select_phases


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


async def run_clone(selected_phases: list[str]) -> None:
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

    completed_phases, effective_selected = load_state(source_shop, selected_phases)

    def _skip(phase: str) -> bool:
        if phase not in effective_selected:
            print(f"[SÉLECTION] Phase '{phase}' non sélectionnée, ignorée.")
            return True
        if phase in completed_phases:
            print(f"[REPRISE] Phase '{phase}' déjà complétée, sautée.")
            return True
        return False

    success = False
    try:
        if not _skip("products"):
            product_entries = await clone_all_products(client, mapping, remapper)
            report.extend(product_entries)
            mapping.save()
            save_phase_completed("products")
            completed_phases.append("products")

        if not _skip("collections"):
            collection_entries = await clone_collections(client, mapping, remapper, cache)
            report.extend(collection_entries)
            mapping.save()
            save_phase_completed("collections")
            completed_phases.append("collections")

        if not _skip("pages"):
            page_entries = await clone_pages(client, mapping, remapper)
            report.extend(page_entries)
            mapping.save()
            save_phase_completed("pages")
            completed_phases.append("pages")

        if not _skip("blogs"):
            blog_entries = await clone_blogs(client, mapping, remapper)
            report.extend(blog_entries)
            mapping.save()
            save_phase_completed("blogs")
            completed_phases.append("blogs")

        if not _skip("menus"):
            menu_entries = await clone_menus(client, mapping, remapper)
            report.extend(menu_entries)
            mapping.save()
            save_phase_completed("menus")
            completed_phases.append("menus")

        if not _skip("policies"):
            policy_entries = await clone_policies(client, remapper)
            report.extend(policy_entries)
            save_phase_completed("policies")
            completed_phases.append("policies")

        if not _skip("discounts"):
            discount_entries = await clone_discounts(client, mapping, remapper)
            report.extend(discount_entries)
            mapping.save()
            save_phase_completed("discounts")
            completed_phases.append("discounts")

        if not _skip("theme"):
            theme_entries = await clone_theme(client, mapping, remapper)
            report.extend(theme_entries)
            mapping.save()
            save_phase_completed("theme")
            completed_phases.append("theme")

        success = True
        print("Clone complete.")
    finally:
        save_report(report)
        await client.close()
        if success and is_clone_complete(completed_phases):
            clear_state()
            cleanup_tmp_images()


if __name__ == "__main__":
    load_env()
    selected = select_phases()
    print(f"\n▶  Lancement du clonage — phases : {', '.join(selected)}\n")
    asyncio.run(run_clone(selected))
