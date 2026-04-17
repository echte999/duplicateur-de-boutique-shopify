import base64
import re

from cloner.client import ShopifyClient, ShopifyAPIError
from cloner.mapping import IDMapping
from cloner.domain import DomainRemapper
from cloner.image_cache import ImageCache

_LINK_RE = re.compile(r'<[^>]+[?&]page_info=([^&>]+)[^>]*>;\s*rel="next"')


async def fetch_custom_collections(client: ShopifyClient) -> list[dict]:
    all_collections: list[dict] = []
    page_info: str | None = None

    while True:
        params: dict = {"limit": "250"}
        if page_info:
            params["page_info"] = page_info

        url = client._source_base + "custom_collections.json"
        async with client._semaphore:
            response = await client._http.get(url, headers=client._source_headers, params=params)
            response.raise_for_status()

        all_collections.extend(response.json().get("custom_collections", []))
        print(f"  Fetched {len(all_collections)} custom collections so far...")

        match = _LINK_RE.search(response.headers.get("Link", ""))
        if match:
            page_info = match.group(1)
        else:
            break

    return all_collections


async def fetch_smart_collections(client: ShopifyClient) -> list[dict]:
    all_collections: list[dict] = []
    page_info: str | None = None

    while True:
        params: dict = {"limit": "250"}
        if page_info:
            params["page_info"] = page_info

        url = client._source_base + "smart_collections.json"
        async with client._semaphore:
            response = await client._http.get(url, headers=client._source_headers, params=params)
            response.raise_for_status()

        all_collections.extend(response.json().get("smart_collections", []))
        print(f"  Fetched {len(all_collections)} smart collections so far...")

        match = _LINK_RE.search(response.headers.get("Link", ""))
        if match:
            page_info = match.group(1)
        else:
            break

    return all_collections


async def fetch_collects(client: ShopifyClient, collection_id: int) -> list[dict]:
    all_collects: list[dict] = []
    page_info: str | None = None

    while True:
        params: dict = {"limit": "250", "collection_id": str(collection_id)}
        if page_info:
            params["page_info"] = page_info

        url = client._source_base + "collects.json"
        async with client._semaphore:
            response = await client._http.get(url, headers=client._source_headers, params=params)
            response.raise_for_status()

        all_collects.extend(response.json().get("collects", []))

        match = _LINK_RE.search(response.headers.get("Link", ""))
        if match:
            page_info = match.group(1)
        else:
            break

    return all_collects


async def clone_custom_collection(
    client: ShopifyClient,
    src_collection: dict,
    remapper: DomainRemapper,
    mapping: IDMapping,
    cache: ImageCache,
) -> int:
    payload: dict = {
        "title": src_collection.get("title", ""),
        "body_html": remapper.remap(src_collection.get("body_html", "")) or "",
        "sort_order": src_collection.get("sort_order", ""),
        "published": src_collection.get("published", True),
    }
    if src_collection.get("template_suffix"):
        payload["template_suffix"] = src_collection["template_suffix"]

    image = src_collection.get("image")
    if image and image.get("src"):
        folder_key = f"collection_{src_collection['id']}"
        local_path = await cache.download(client._http, image["src"], folder_key)
        encoded = base64.b64encode(local_path.read_bytes()).decode("ascii")
        payload["image"] = {
            "attachment": encoded,
            "filename": local_path.name,
            "alt": image.get("alt", ""),
        }

    result = await client.post_target("custom_collections.json", {"custom_collection": payload})
    tgt_id = result["custom_collection"]["id"]
    mapping.set("collection", src_collection["id"], tgt_id)
    print(f"  Cloned custom collection '{src_collection.get('title')}' ({src_collection['id']} -> {tgt_id})")
    return tgt_id


async def clone_smart_collection(
    client: ShopifyClient,
    src_collection: dict,
    remapper: DomainRemapper,
    mapping: IDMapping,
) -> int:
    payload: dict = {
        "title": src_collection.get("title", ""),
        "body_html": remapper.remap(src_collection.get("body_html", "")) or "",
        "sort_order": src_collection.get("sort_order", ""),
        "published": src_collection.get("published", True),
        "rules": src_collection.get("rules", []),
        "disjunctive": src_collection.get("disjunctive", False),
    }
    if src_collection.get("template_suffix"):
        payload["template_suffix"] = src_collection["template_suffix"]

    result = await client.post_target("smart_collections.json", {"smart_collection": payload})
    tgt_id = result["smart_collection"]["id"]
    mapping.set("collection", src_collection["id"], tgt_id)
    print(f"  Cloned smart collection '{src_collection.get('title')}' ({src_collection['id']} -> {tgt_id})")
    return tgt_id


async def clone_collects(
    client: ShopifyClient,
    src_collection_id: int,
    tgt_collection_id: int,
    mapping: IDMapping,
) -> int:
    collects = await fetch_collects(client, src_collection_id)
    cloned = 0

    for collect in collects:
        src_product_id = collect["product_id"]
        if not mapping.has("product", src_product_id):
            print(f"  [WARN] Collect: produit source {src_product_id} absent de la table de correspondance, ignoré.")
            continue

        tgt_product_id = int(mapping.get("product", src_product_id))
        try:
            await client.post_target("collects.json", {"collect": {
                "product_id": tgt_product_id,
                "collection_id": tgt_collection_id,
                "position": collect.get("position"),
            }})
        except ShopifyAPIError as e:
            if e.status_code == 422 and "already exists" in str(e):
                pass  # produit déjà assigné à cette collection
            else:
                raise
        cloned += 1

    return cloned


async def clone_collections(
    client: ShopifyClient,
    mapping: IDMapping,
    remapper: DomainRemapper,
    cache: ImageCache,
) -> list[dict]:
    report_entries: list[dict] = []

    print("Fetching custom collections from source...")
    custom_collections = await fetch_custom_collections(client)
    print(f"Found {len(custom_collections)} custom collections.")

    print("Fetching smart collections from source...")
    smart_collections = await fetch_smart_collections(client)
    print(f"Found {len(smart_collections)} smart collections.")

    for col in custom_collections:
        if mapping.has("collection", col["id"]):
            print(f"  Skipping custom collection {col['id']} (already cloned)")
            report_entries.append({
                "type": "collection", "id_source": col["id"],
                "id_cible": mapping.get("collection", col["id"]),
                "title": col.get("title", ""), "statut": "skipped",
            })
            continue
        try:
            tgt_id = await clone_custom_collection(client, col, remapper, mapping, cache)
            report_entries.append({
                "type": "collection", "id_source": col["id"], "id_cible": tgt_id,
                "title": col.get("title", ""), "statut": "ok",
            })
        except Exception as e:
            print(f"  [ERROR] Custom collection '{col.get('title')}' ({col['id']}): {e}")
            report_entries.append({
                "type": "collection", "id_source": col["id"], "id_cible": None,
                "title": col.get("title", ""), "statut": f"error: {e}",
            })

    for col in smart_collections:
        if mapping.has("collection", col["id"]):
            print(f"  Skipping smart collection {col['id']} (already cloned)")
            report_entries.append({
                "type": "collection", "id_source": col["id"],
                "id_cible": mapping.get("collection", col["id"]),
                "title": col.get("title", ""), "statut": "skipped",
            })
            continue
        try:
            tgt_id = await clone_smart_collection(client, col, remapper, mapping)
            report_entries.append({
                "type": "collection", "id_source": col["id"], "id_cible": tgt_id,
                "title": col.get("title", ""), "statut": "ok",
            })
        except Exception as e:
            print(f"  [ERROR] Smart collection '{col.get('title')}' ({col['id']}): {e}")
            report_entries.append({
                "type": "collection", "id_source": col["id"], "id_cible": None,
                "title": col.get("title", ""), "statut": f"error: {e}",
            })

    print("Assigning products to manual collections...")
    for col in custom_collections:
        if not mapping.has("collection", col["id"]):
            continue
        tgt_collection_id = int(mapping.get("collection", col["id"]))
        n = await clone_collects(client, col["id"], tgt_collection_id, mapping)
        print(f"  Assigned {n} products to collection '{col.get('title')}'")

    print(f"Collections phase complete. {len(custom_collections)} custom + {len(smart_collections)} smart.")
    return report_entries
