import re

from cloner.client import ShopifyClient
from cloner.domain import DomainRemapper
from cloner.mapping import IDMapping

_LINK_RE = re.compile(r'<[^>]+[?&]page_info=([^&>]+)[^>]*>;\s*rel="next"')

_SKIP_TYPES = {"metaobject_reference", "list.metaobject_reference",
               "file_reference", "list.file_reference",
               "product_reference", "list.product_reference",
               "variant_reference", "list.variant_reference",
               "page_reference", "list.page_reference",
               "collection_reference", "list.collection_reference"}

_REMAP_TYPES = {"html", "url", "json_string"}

_QUERY_PAGE_METAFIELDS = """
query GetPageMetafields($id: ID!) {
  page(id: $id) {
    metafields(first: 100) {
      edges {
        node {
          namespace
          key
          value
          type
        }
      }
    }
  }
}
"""

_MUTATION_METAFIELDS_SET = """
mutation MetafieldsSet($metafields: [MetafieldsSetInput!]!) {
  metafieldsSet(metafields: $metafields) {
    metafields { namespace key }
    userErrors { field message }
  }
}
"""


async def _fetch_page_metafields(client: ShopifyClient, source_id: int) -> list[dict]:
    gid = f"gid://shopify/OnlineStorePage/{source_id}"
    result = await client.graphql_source(_QUERY_PAGE_METAFIELDS, {"id": gid})
    edges = result.get("data", {}).get("page", {}).get("metafields", {}).get("edges", [])
    return [edge["node"] for edge in edges]


async def _write_page_metafields(
    client: ShopifyClient,
    target_id: int,
    metafields: list[dict],
    remapper: DomainRemapper,
) -> None:
    owner_gid = f"gid://shopify/OnlineStorePage/{target_id}"
    inputs = []
    for mf in metafields:
        mf_type = mf.get("type", "")
        if mf_type in _SKIP_TYPES:
            continue
        value = mf["value"]
        if mf_type in _REMAP_TYPES:
            value = remapper.remap(value) or value
        inputs.append({
            "ownerId": owner_gid,
            "namespace": mf["namespace"],
            "key": mf["key"],
            "value": value,
            "type": mf_type,
        })

    if not inputs:
        return

    result = await client.graphql_target(_MUTATION_METAFIELDS_SET, {"metafields": inputs})
    errors = result.get("data", {}).get("metafieldsSet", {}).get("userErrors", [])
    for err in errors:
        print(f"  [WARN] Page metafield ({err.get('field')}): {err.get('message')}")


async def fetch_all_pages(client: ShopifyClient) -> list[dict]:
    all_pages: list[dict] = []
    page_info: str | None = None

    while True:
        params: dict = {"limit": "250"}
        if page_info:
            params["page_info"] = page_info

        url = client._source_base + "pages.json"
        async with client._semaphore:
            response = await client._http.get(url, headers=client._source_headers, params=params)
            response.raise_for_status()

        all_pages.extend(response.json().get("pages", []))

        match = _LINK_RE.search(response.headers.get("Link", ""))
        if match:
            page_info = match.group(1)
        else:
            break

    return all_pages


async def clone_pages(
    client: ShopifyClient,
    mapping: IDMapping,
    remapper: DomainRemapper,
) -> list[dict]:
    report_entries: list[dict] = []

    print("Fetching pages from source...")
    pages = await fetch_all_pages(client)
    print(f"Found {len(pages)} pages.")

    for page in pages:
        source_id = page["id"]

        if mapping.has("page", source_id):
            print(f"  Skipping page '{page.get('title')}' (already cloned)")
            report_entries.append({
                "type": "page", "id_source": source_id,
                "id_cible": mapping.get("page", source_id),
                "title": page.get("title", ""), "statut": "skipped",
            })
            continue

        try:
            payload: dict = {
                "title": page.get("title", ""),
                "body_html": remapper.remap(page.get("body_html", "")) or "",
                "handle": page.get("handle", ""),
                "published": page.get("published_at") is not None,
            }
            if page.get("template_suffix"):
                payload["template_suffix"] = page["template_suffix"]

            result = await client.post_target("pages.json", {"page": payload})
            target_id = result["page"]["id"]
            mapping.set("page", source_id, target_id)

            metafields = await _fetch_page_metafields(client, source_id)
            if metafields:
                await _write_page_metafields(client, target_id, metafields, remapper)

            print(f"  Cloned page '{page.get('title')}' ({source_id} -> {target_id})")
            report_entries.append({
                "type": "page", "id_source": source_id, "id_cible": target_id,
                "title": page.get("title", ""), "statut": "ok",
            })
        except Exception as e:
            print(f"  [ERROR] Page '{page.get('title')}' ({source_id}): {e}")
            report_entries.append({
                "type": "page", "id_source": source_id, "id_cible": None,
                "title": page.get("title", ""), "statut": f"error: {e}",
            })

    print(f"Pages phase complete. {len(pages)} pages processed.")
    return report_entries
