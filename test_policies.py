"""
Test isolé de la phase politiques du site.
Usage : python test_policies.py [--dry-run]

--dry-run : affiche les politiques source avec le contenu remappé, sans rien écrire.
Sans flag : clone réellement les politiques sur la boutique cible.
"""
import asyncio
import os
import sys
from pathlib import Path


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


async def _build_remapper(client):
    from cloner.domain import DomainRemapper

    src_shop_data = await client.get_source("shop.json")
    dst_shop_data = await client.get_target("shop.json")
    source_shop_name = src_shop_data.get("shop", {}).get("name")
    target_shop_name = dst_shop_data.get("shop", {}).get("name")

    print(f"  Boutique source : {source_shop_name!r}")
    print(f"  Boutique cible  : {target_shop_name!r}")

    return DomainRemapper(
        source_myshopify=_require("SOURCE_SHOP"),
        target_domain=os.environ.get("TARGET_CUSTOM_DOMAIN") or _require("TARGET_SHOP"),
        source_custom=os.environ.get("SOURCE_CUSTOM_DOMAIN") or None,
        source_shop_name=source_shop_name,
        target_shop_name=target_shop_name,
    )


async def dry_run(client) -> None:
    remapper = await _build_remapper(client)

    result = await client.get_source("policies.json")
    policies = result.get("policies", [])

    print(f"\n{'='*60}")
    print(f"{len(policies)} politique(s) trouvée(s) sur la boutique source")
    print(f"{'='*60}")

    for policy in policies:
        handle = policy.get("handle", "")
        title = policy.get("title", "")
        body_original = policy.get("body", "") or ""
        body_remapped = remapper.remap(body_original) or ""

        changed = body_remapped != body_original
        flag = " [remappé]" if changed else ""
        print(f"\n  [{handle}] \"{title}\"{flag}")
        if changed:
            # Afficher un court extrait du changement
            for line in body_remapped.splitlines():
                if any(kw in line for kw in [_require("TARGET_SHOP").split(".")[0]]):
                    print(f"    → {line.strip()[:120]}")
                    break

    await client.close()


async def real_clone(client) -> None:
    from cloner.phases.policies import clone_policies
    from cloner.report import save_report

    remapper = await _build_remapper(client)

    print("\nDémarrage du clonage des politiques...")
    try:
        entries = await clone_policies(client, remapper)
    finally:
        await client.close()

    ok = [e for e in entries if e["statut"] == "ok"]
    skipped = [e for e in entries if e["statut"] == "skipped"]

    print(f"\n{'='*60}")
    print(f"Résultat : {len(ok)} clonée(s)  |  {len(skipped)} ignorée(s)")

    if skipped:
        print("\nPolitiques ignorées :")
        for e in skipped:
            print(f"  [{e['id_source']}] \"{e['title']}\" — {e.get('error', '')}")

    print(f"{'='*60}")

    save_report(entries)
    print("Rapport écrit dans output/clone_report.json")


async def main() -> None:
    load_env()

    from cloner.client import ShopifyClient
    client = ShopifyClient(
        source_shop=_require("SOURCE_SHOP"),
        source_token=_require("SOURCE_TOKEN"),
        target_shop=_require("TARGET_SHOP"),
        target_token=_require("TARGET_TOKEN"),
    )

    if "--dry-run" in sys.argv:
        await dry_run(client)
    else:
        await real_clone(client)


if __name__ == "__main__":
    asyncio.run(main())
