"""
Test isolé de la phase de clonage des réductions.
Usage : python test_discounts.py
"""
import asyncio
import json
import os
from pathlib import Path

from cloner.client import ShopifyClient
from cloner.domain import DomainRemapper
from cloner.mapping import IDMapping
from cloner.phases.discounts import clone_discounts


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


async def main() -> None:
    load_env()

    client = ShopifyClient(
        source_shop=_require("SOURCE_SHOP"),
        source_token=_require("SOURCE_TOKEN"),
        target_shop=_require("TARGET_SHOP"),
        target_token=_require("TARGET_TOKEN"),
    )

    mapping = IDMapping()

    src_shop_data = await client.get_source("shop.json")
    dst_shop_data = await client.get_target("shop.json")
    source_shop_name = src_shop_data.get("shop", {}).get("name")
    target_shop_name = dst_shop_data.get("shop", {}).get("name")

    remapper = DomainRemapper(
        source_myshopify=_require("SOURCE_SHOP"),
        target_domain=os.environ.get("TARGET_CUSTOM_DOMAIN") or _require("TARGET_SHOP"),
        source_custom=os.environ.get("SOURCE_CUSTOM_DOMAIN") or None,
        source_shop_name=source_shop_name,
        target_shop_name=target_shop_name,
    )

    try:
        entries = await clone_discounts(client, mapping, remapper)
    finally:
        await client.close()

    print("\n--- Résultats ---")
    for e in entries:
        status = e.get("statut", "?")
        print(f"  [{status}] {e.get('title')} : {e.get('id_source')} -> {e.get('id_cible')}")

    ok = sum(1 for e in entries if e.get("statut") == "ok")
    errors = len(entries) - ok
    print(f"\n{ok} réduction(s) clonée(s), {errors} erreur(s).")

    Path("output").mkdir(exist_ok=True)
    Path("output/test_discounts_report.json").write_text(
        json.dumps(entries, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print("Rapport écrit dans output/test_discounts_report.json")


if __name__ == "__main__":
    asyncio.run(main())
