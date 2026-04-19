from cloner.client import ShopifyClient
from cloner.domain import DomainRemapper
from cloner.mapping import IDMapping

_REMAPPABLE_LINK_TYPES = {"collection", "product", "page", "blog", "article"}


def _remap_menu_item(item: dict, mapping: IDMapping, remapper: DomainRemapper) -> dict:
    item = dict(item)

    link_type = item.get("type", "")
    resource_id = item.get("object_id")

    if link_type in _REMAPPABLE_LINK_TYPES and resource_id:
        rtype = link_type  # matches our mapping keys
        if mapping.has(rtype, resource_id):
            item["object_id"] = int(mapping.get(rtype, resource_id))

    if item.get("url"):
        item["url"] = remapper.remap(item["url"]) or item["url"]

    if item.get("title"):
        item["title"] = remapper.remap(item["title"]) or item["title"]

    if item.get("items"):
        item["items"] = [_remap_menu_item(child, mapping, remapper) for child in item["items"]]

    return item


async def clone_menus(
    client: ShopifyClient,
    mapping: IDMapping,
    remapper: DomainRemapper,
) -> list[dict]:
    report_entries: list[dict] = []

    print("Fetching menus from source...")
    result = await client.get_source("menus.json")
    menus = result.get("menus", [])
    print(f"Found {len(menus)} menus.")

    for menu in menus:
        source_id = menu["id"]
        handle = menu.get("handle", "")
        title = menu.get("title", "")

        try:
            remapped_items = [
                _remap_menu_item(item, mapping, remapper)
                for item in menu.get("items", [])
            ]

            # Check if a menu with the same handle exists on target
            existing = await client.get_target("menus.json")
            existing_by_handle = {m["handle"]: m for m in existing.get("menus", [])}

            if handle in existing_by_handle:
                target_menu = existing_by_handle[handle]
                target_id = target_menu["id"]
                await client.put_target(f"menus/{target_id}.json", {"menu": {
                    "title": title,
                    "handle": handle,
                    "items": remapped_items,
                }})
                print(f"  Updated menu '{title}' ({source_id} -> {target_id})")
            else:
                result_post = await client.post_target("menus.json", {"menu": {
                    "title": title,
                    "handle": handle,
                    "items": remapped_items,
                }})
                target_id = result_post["menu"]["id"]
                print(f"  Cloned menu '{title}' ({source_id} -> {target_id})")

            mapping.set("menu", source_id, target_id)
            report_entries.append({
                "type": "menu", "id_source": source_id, "id_cible": target_id,
                "title": title, "statut": "ok",
            })
        except Exception as e:
            print(f"  [ERROR] Menu '{title}' ({source_id}): {e}")
            report_entries.append({
                "type": "menu", "id_source": source_id, "id_cible": None,
                "title": title, "statut": f"error: {e}",
            })

    print(f"Menus phase complete. {len(menus)} menus processed.")
    return report_entries
