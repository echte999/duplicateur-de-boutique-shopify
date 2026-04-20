"""
Commande standalone pour tester uniquement la phase pages.
Usage : python clone_pages_only.py [--force]
  --force  Efface les correspondances pages du mapping et re-clone tout
"""
import asyncio
import os
import sys
from pathlib import Path

from cloner.client import ShopifyClient
from cloner.mapping import IDMapping
from cloner.domain import DomainRemapper
from cloner.phases.pages import clone_pages
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
        raise EnvironmentError(f"Variable manquante : {key}")
    return value


async def run() -> None:
    load_env()

    client = ShopifyClient(
        source_shop=_require("SOURCE_SHOP"),
        source_token=_require("SOURCE_TOKEN"),
        target_shop=_require("TARGET_SHOP"),
        target_token=_require("TARGET_TOKEN"),
    )

    mapping = IDMapping()

    if "--force" in sys.argv:
        mapping._map["page"] = {}
        mapping.save()
        print("Mapping pages effacé — re-clonage forcé.")

    source_shop = _require("SOURCE_SHOP")
    remapper = DomainRemapper(
        source_myshopify=source_shop,
        target_domain=os.environ.get("TARGET_CUSTOM_DOMAIN") or _require("TARGET_SHOP"),
        source_custom=os.environ.get("SOURCE_CUSTOM_DOMAIN") or None,
    )

    print("=== Clone pages uniquement ===")
    entries = await clone_pages(client, mapping, remapper)
    mapping.save()
    save_report(entries)

    ok = sum(1 for e in entries if e["statut"] == "ok")
    skipped = sum(1 for e in entries if e["statut"] == "skipped")
    errors = sum(1 for e in entries if str(e["statut"]).startswith("error"))
    print(f"\nRésultat : {ok} clonées, {skipped} ignorées, {errors} erreurs")


if __name__ == "__main__":
    asyncio.run(run())
