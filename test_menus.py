"""
Test isolé de la phase menus.
Usage : python test_menus.py [--dry-run] [--debug]

--dry-run : affiche les menus source et les menus cibles sans rien écrire.
--debug   : affiche le JSON brut de l'API pour diagnostiquer la structure des items.
Sans flag : clone réellement les menus (remapping IDs + domaine + fallback frontpage).
"""
import asyncio
import json
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


def _print_items(items: list[dict], indent: int = 4) -> None:
    prefix = " " * indent
    for item in items:
        link_type = item.get("type", "?")
        title = item.get("title", "(sans titre)")
        obj_id = item.get("object_id") or item.get("subject_id")
        url = item.get("url", "")
        detail = f"id={obj_id}" if obj_id else url
        print(f"{prefix}• [{link_type}] \"{title}\"  {detail}")
        if item.get("items"):
            _print_items(item["items"], indent + 4)


async def debug_run(client) -> None:
    from cloner.phases.menus import _fetch_all_menus
    from cloner.mapping import IDMapping

    mapping = IDMapping()

    source_menus = await _fetch_all_menus(client, source=True)
    target_menus = await _fetch_all_menus(client, source=False)
    target_handles = {m["handle"] for m in target_menus}

    print(f"\n{'='*60}")
    print(f"{'HANDLE SOURCE':<30} {'HANDLE CIBLE (match?)'}")
    print(f"{'='*60}")
    for m in source_menus:
        h = m.get("handle", "")
        match = "✓ UPDATE" if h in target_handles else "✗ CREATE (handle absent)"
        print(f"  {h:<30} {match}")

    print(f"\n{'='*60}")
    print("Handles présents sur la CIBLE uniquement (ne seront pas touchés) :")
    source_handles = {m["handle"] for m in source_menus}
    for h in sorted(target_handles - source_handles):
        print(f"  {h}")

    from cloner.phases.menus import _build_policy_map
    from cloner.client import ShopifyClient as _SC
    policy_map = await _build_policy_map(client)
    print(f"\n{len(policy_map)} politique(s) mappée(s) source→cible")

    print(f"\n{'='*60}")
    print("Détail des items SOURCE avec résolution id_map :")
    for menu in source_menus:
        print(f"\n  [{menu['handle']}] \"{menu.get('title')}\"")
        for item in menu.get("items", []):
            _debug_item(item, mapping, policy_map, indent=4)

    await client.close()


def _debug_item(item: dict, mapping, policy_map: dict, indent: int) -> None:
    from cloner.phases.menus import _GID_RE, _GID_TYPE_MAP, _PASSTHROUGH_GID_TYPES
    prefix = " " * indent
    link_type = item.get("type", "?")
    title = item.get("title", "")
    resource_id = item.get("resourceId", "")
    url = item.get("url", "")

    resolution = ""
    if resource_id:
        m = _GID_RE.match(resource_id)
        if m:
            gid_type, src_id = m.group(1), m.group(2)
            if gid_type in _PASSTHROUGH_GID_TYPES:
                resolution = f"→ passthrough (système)"
            elif gid_type == "ShopPolicy":
                if resource_id in policy_map:
                    resolution = f"✓ → ShopPolicy/{policy_map[resource_id].split('/')[-1]}"
                else:
                    resolution = f"✗ ShopPolicy id={src_id} absent de policy_map"
            else:
                map_key = _GID_TYPE_MAP.get(gid_type)
                if not map_key:
                    resolution = f"⚠ GID type '{gid_type}' non reconnu"
                elif mapping.has(map_key, src_id):
                    target_id = mapping.get(map_key, src_id)
                    resolution = f"✓ → {gid_type}/{target_id}"
                else:
                    resolution = f"✗ {map_key} id={src_id} absent de id_map"
        else:
            resolution = f"⚠ GID invalide: {resource_id}"
    elif url:
        resolution = f"url={url}"

    print(f"{prefix}[{link_type}] \"{title}\"  {resolution}")
    for child in item.get("items", []):
        _debug_item(child, mapping, policy_map, indent + 4)


async def dry_run(client) -> None:
    from cloner.phases.menus import _fetch_all_menus

    source_menus = await _fetch_all_menus(client)
    target_result = await client.get_target("menus.json")
    target_menus = target_result.get("menus", [])
    target_handles = {m["handle"] for m in target_menus}

    print(f"\n{'='*55}")
    print(f"Menus source : {len(source_menus)}")
    print(f"Menus cibles déjà présents : {len(target_menus)}")
    print(f"{'='*55}")

    for menu in source_menus:
        handle = menu.get("handle", "")
        exists = "→ UPDATE" if handle in target_handles else "→ CREATE"
        items = menu.get("items", [])
        print(f"\n  [{menu['id']}] \"{menu.get('title')}\"  handle={handle}  {exists}  ({len(items)} items)")
        _print_items(items)

    await client.close()


async def real_clone(client) -> None:
    from cloner.mapping import IDMapping
    from cloner.domain import DomainRemapper
    from cloner.phases.menus import clone_menus
    from cloner.report import save_report

    mapping = IDMapping()
    remapper = DomainRemapper(
        source_myshopify=_require("SOURCE_SHOP"),
        target_domain=os.environ.get("TARGET_CUSTOM_DOMAIN") or _require("TARGET_SHOP"),
        source_custom=os.environ.get("SOURCE_CUSTOM_DOMAIN") or None,
    )

    print("\nDémarrage du clonage menus...")
    try:
        entries = await clone_menus(client, mapping, remapper)
        mapping.save()
    finally:
        await client.close()

    ok = [e for e in entries if e["statut"] == "ok"]
    orphans = [e for e in entries if e["statut"] == "frontpage_fallback"]
    errors = [e for e in entries if e["statut"] not in ("ok", "frontpage_fallback")]

    print(f"\n{'='*55}")
    print(f"Résultat : {len(ok)} menus clonés  |  {len(orphans)} items orphelins  |  {len(errors)} erreurs")

    if orphans:
        print("\nItems orphelins convertis en frontpage :")
        for e in orphans:
            print(f"  {e['title']}")

    if errors:
        print("\nErreurs :")
        for e in errors:
            print(f"  [{e['type']}] \"{e['title']}\" — {e['statut']}")

    print(f"{'='*55}")

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

    if "--debug" in sys.argv:
        await debug_run(client)
    elif "--dry-run" in sys.argv:
        await dry_run(client)
    else:
        await real_clone(client)


if __name__ == "__main__":
    asyncio.run(main())
