import re

from cloner.client import ShopifyClient
from cloner.domain import DomainRemapper
from cloner.mapping import IDMapping

_GID_RE = re.compile(r"gid://shopify/(\w+)/(\d+)")

# GID type → clé dans id_map
_GID_TYPE_MAP = {
    "Collection": "collection",
    "Product": "product",
    "Page": "page",
    "OnlineStorePage": "page",
    "Blog": "blog",
    "Article": "article",
}

# GID types passés tels quels (pages système identiques sur toutes les boutiques)
_PASSTHROUGH_GID_TYPES = {"CustomerAccountPage"}

_QUERY_MENUS = """
query GetMenus($cursor: String) {
  menus(first: 50, after: $cursor) {
    pageInfo { hasNextPage endCursor }
    edges {
      node {
        id
        handle
        title
        items {
          id
          title
          type
          url
          resourceId
          items {
            id
            title
            type
            url
            resourceId
          }
        }
      }
    }
  }
}
"""

_QUERY_MENUS_HANDLES = """
query GetMenuHandles($cursor: String) {
  menus(first: 50, after: $cursor) {
    pageInfo { hasNextPage endCursor }
    edges {
      node { id handle title }
    }
  }
}
"""

# Retourne les GIDs des 5 politiques standard Shopify, par champ
_QUERY_SHOP_POLICIES = """
query ShopPolicies {
  shop {
    refundPolicy { id }
    privacyPolicy { id }
    termsOfService { id }
    shippingPolicy { id }
    legalNotice { id }
  }
}
"""

_MUTATION_MENU_CREATE = """
mutation MenuCreate($title: String!, $handle: String!, $items: [MenuItemCreateInput!]!) {
  menuCreate(title: $title, handle: $handle, items: $items) {
    menu { id handle }
    userErrors { field message }
  }
}
"""

_MUTATION_MENU_UPDATE = """
mutation MenuUpdate($id: ID!, $title: String!, $items: [MenuItemUpdateInput!]!) {
  menuUpdate(id: $id, title: $title, items: $items) {
    menu { id handle }
    userErrors { field message }
  }
}
"""

_MUTATION_MENU_DELETE = """
mutation MenuDelete($id: ID!) {
  menuDelete(id: $id) {
    deletedMenuId
    userErrors { field message }
  }
}
"""


async def _build_policy_map(client: ShopifyClient) -> dict[str, str]:
    """Retourne toujours un dict vide — les ShopPolicy sont gérées via URL fallback."""
    return {}


def _remap_resource_id(
    resource_id: str,
    mapping: IDMapping,
    policy_map: dict[str, str],
    orphans: list[dict],
) -> tuple[str | None, bool]:
    m = _GID_RE.match(resource_id)
    if not m:
        return resource_id, False

    gid_type, source_id = m.group(1), m.group(2)

    if gid_type in _PASSTHROUGH_GID_TYPES:
        return resource_id, False

    if gid_type == "ShopPolicy":
        target_gid = policy_map.get(resource_id)
        if target_gid:
            return target_gid, False
        orphans.append({"gid_type": gid_type, "source_id": source_id})
        return None, True

    map_key = _GID_TYPE_MAP.get(gid_type)
    if not map_key:
        orphans.append({"gid_type": gid_type, "source_id": source_id})
        return None, True

    if mapping.has(map_key, source_id):
        target_id = mapping.get(map_key, source_id)
        return f"gid://shopify/{gid_type}/{target_id}", False

    orphans.append({"gid_type": gid_type, "source_id": source_id})
    return None, True


def _remap_item(
    item: dict,
    mapping: IDMapping,
    remapper: DomainRemapper,
    policy_map: dict[str, str],
    orphans: list[dict],
) -> dict:
    item_type = item.get("type", "FRONTPAGE")
    title = remapper.remap(item.get("title", "")) or item.get("title", "")
    url = item.get("url", "")
    resource_id = item.get("resourceId")

    result: dict = {"title": title, "type": item_type}

    if resource_id:
        new_rid, is_orphan = _remap_resource_id(resource_id, mapping, policy_map, orphans)
        if is_orphan:
            remapped_url = remapper.remap(url) or url if url else None
            if remapped_url:
                result["type"] = "HTTP"
                result["url"] = remapped_url
            else:
                result["type"] = "FRONTPAGE"
        else:
            result["resourceId"] = new_rid
            if url:
                result["url"] = remapper.remap(url) or url
    elif url:
        result["url"] = remapper.remap(url) or url

    if item.get("items"):
        result["items"] = [
            _remap_item(child, mapping, remapper, policy_map, orphans)
            for child in item["items"]
        ]

    return result


async def _fetch_all_menus(client: ShopifyClient, source: bool = True) -> list[dict]:
    menus: list[dict] = []
    cursor = None
    query = _QUERY_MENUS if source else _QUERY_MENUS_HANDLES

    while True:
        variables = {"cursor": cursor} if cursor else {}
        if source:
            result = await client.graphql_source(query, variables)
        else:
            result = await client.graphql_target(query, variables)

        data = result.get("data", {}).get("menus", {})
        for edge in data.get("edges", []):
            menus.append(edge["node"])

        page_info = data.get("pageInfo", {})
        if page_info.get("hasNextPage"):
            cursor = page_info["endCursor"]
        else:
            break

    return menus


async def clone_menus(
    client: ShopifyClient,
    mapping: IDMapping,
    remapper: DomainRemapper,
) -> list[dict]:
    report_entries: list[dict] = []

    print("Fetching menus from source...")
    source_menus = await _fetch_all_menus(client, source=True)
    print(f"Found {len(source_menus)} menus.")

    target_menus = await _fetch_all_menus(client, source=False)
    existing_by_handle = {m["handle"]: m for m in target_menus}

    policy_map = await _build_policy_map(client)

    for menu in source_menus:
        source_gid = menu["id"]
        source_id = source_gid.split("/")[-1]
        handle = menu.get("handle", "")
        title = menu.get("title", "")
        orphans: list[dict] = []

        try:
            remapped_items = [
                _remap_item(item, mapping, remapper, policy_map, orphans)
                for item in menu.get("items", [])
            ]

            for orphan in orphans:
                print(f"  [WARN] Menu '{title}': {orphan['gid_type']} id={orphan['source_id']} non remappé → frontpage")
                report_entries.append({
                    "type": "menu_item_orphan",
                    "id_source": orphan["source_id"],
                    "id_cible": None,
                    "title": f"{title} > {orphan['gid_type']}:{orphan['source_id']}",
                    "statut": "frontpage_fallback",
                })

            if handle in existing_by_handle:
                target_gid = existing_by_handle[handle]["id"]
                target_id = target_gid.split("/")[-1]

                gql_result = await client.graphql_target(_MUTATION_MENU_UPDATE, {
                    "id": target_gid,
                    "title": title,
                    "items": remapped_items,
                })
                top_errors = gql_result.get("errors", [])
                user_errors = gql_result.get("data", {}).get("menuUpdate", {}).get("userErrors", [])
                updated_menu = gql_result.get("data", {}).get("menuUpdate", {}).get("menu")

                if top_errors or user_errors or not updated_menu:
                    print(f"  [WARN] menuUpdate échoué, tentative delete+recreate...")
                    del_result = await client.graphql_target(_MUTATION_MENU_DELETE, {"id": target_gid})
                    del_errors = del_result.get("data", {}).get("menuDelete", {}).get("userErrors", [])
                    if del_errors:
                        messages = [e.get("message", "") for e in del_errors]
                        if any("Default menu cannot be deleted" in msg for msg in messages):
                            print(f"  [SKIP] Menu '{title}' est un menu par défaut non supprimable et non mis à jour.")
                            continue
                        raise Exception(f"menuDelete userErrors: {del_errors}")

                    gql_result = await client.graphql_target(_MUTATION_MENU_CREATE, {
                        "title": title,
                        "handle": handle,
                        "items": remapped_items,
                    })
                    create_errors = gql_result.get("data", {}).get("menuCreate", {}).get("userErrors", [])
                    if create_errors:
                        raise Exception(f"menuCreate userErrors (après delete): {create_errors}")
                    target_gid = gql_result.get("data", {}).get("menuCreate", {}).get("menu", {}).get("id", "")
                    target_id = target_gid.split("/")[-1]
                    print(f"  Replaced menu '{title}' ({source_id} → {target_id})")
                else:
                    print(f"  Updated menu '{title}' ({source_id} → {target_id})")
            else:
                gql_result = await client.graphql_target(_MUTATION_MENU_CREATE, {
                    "title": title,
                    "handle": handle,
                    "items": remapped_items,
                })
                errors = gql_result.get("data", {}).get("menuCreate", {}).get("userErrors", [])
                if errors:
                    raise Exception(f"GraphQL userErrors: {errors}")
                target_gid = gql_result.get("data", {}).get("menuCreate", {}).get("menu", {}).get("id", "")
                target_id = target_gid.split("/")[-1]
                print(f"  Created menu '{title}' ({source_id} → {target_id})")

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

    print(f"Menus phase complete. {len(source_menus)} menus processed.")
    return report_entries
