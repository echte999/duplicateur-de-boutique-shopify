import base64
import re

from cloner.client import ShopifyClient
from cloner.mapping import IDMapping
from cloner.domain import DomainRemapper
from cloner.image_cache import ImageCache

# Types de métafields qui référencent des ressources d'autres boutiques — on ne peut pas les copier
_SKIP_TYPES = {"metaobject_reference", "list.metaobject_reference",
               "file_reference", "list.file_reference",
               "product_reference", "list.product_reference",
               "variant_reference", "list.variant_reference",
               "page_reference", "list.page_reference",
               "collection_reference", "list.collection_reference"}

# Types où le remapping de domaine doit être appliqué
_REMAP_TYPES = {"html", "url", "json_string"}

_QUERY_PRODUCT_EXTRA = """
query GetProductExtra($id: ID!) {
  product(id: $id) {
    category { id }
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
    options {
      id name
      linkedMetafield { namespace key }
      optionValues { id name linkedMetafieldValue }
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

_QUERY_METAFIELD_DEFINITIONS = """
query GetMetafieldDefinitions($ownerType: MetafieldOwnerType!, $after: String) {
  metafieldDefinitions(ownerType: $ownerType, first: 100, after: $after) {
    edges {
      node {
        id
        namespace
        key
        name
        type { name }
        description
      }
    }
    pageInfo { hasNextPage endCursor }
  }
}
"""

_MUTATION_METAFIELD_DEFINITION_CREATE = """
mutation MetafieldDefinitionCreate($definition: MetafieldDefinitionInput!) {
  metafieldDefinitionCreate(definition: $definition) {
    createdDefinition { id }
    userErrors { field message }
  }
}
"""

_MUTATION_METAFIELD_DEFINITION_PIN = """
mutation MetafieldDefinitionPin($definitionId: ID!) {
  metafieldDefinitionPin(definitionId: $definitionId) {
    pinnedDefinition { id }
    userErrors { field message }
  }
}
"""

_MUTATION_PRODUCT_SET_CATEGORY = """
mutation ProductSetCategory($id: ID!, $categoryId: ID!) {
  productUpdate(input: { id: $id, category: $categoryId }) {
    product { id category { id } }
    userErrors { field message }
  }
}
"""

_QUERY_PRODUCT_OPTIONS = """
query GetProductOptions($id: ID!) {
  product(id: $id) {
    options {
      id name
      linkedMetafield { namespace key }
      optionValues { id name linkedMetafieldValue }
    }
  }
}
"""

_QUERY_METAOBJECT = """
query GetMetaobject($id: ID!) {
  metaobject(id: $id) {
    id handle type
    fields { key value type }
  }
}
"""

_MUTATION_METAOBJECT_CREATE = """
mutation MetaobjectCreate($metaobject: MetaobjectCreateInput!) {
  metaobjectCreate(metaobject: $metaobject) {
    metaobject { id handle type }
    userErrors { field message }
  }
}
"""

_MUTATION_METAOBJECT_UPSERT = """
mutation MetaobjectUpsert($handle: MetaobjectHandleInput!, $metaobject: MetaobjectUpsertInput!) {
  metaobjectUpsert(handle: $handle, metaobject: $metaobject) {
    metaobject { id handle type }
    userErrors { field message }
  }
}
"""

_MUTATION_PRODUCT_OPTION_UPDATE = """
mutation ProductOptionUpdate(
  $productId: ID!,
  $option: OptionUpdateInput!,
  $optionValuesToUpdate: [OptionValueUpdateInput!]
) {
  productOptionUpdate(
    productId: $productId,
    option: $option,
    optionValuesToUpdate: $optionValuesToUpdate
  ) {
    product {
      options { id name linkedMetafield { namespace key } optionValues { id name linkedMetafieldValue swatch { color } } }
    }
    userErrors { field message }
  }
}
"""

_LINK_RE = re.compile(r'<[^>]+[?&]page_info=([^&>]+)[^>]*>;\s*rel="next"')


async def _fetch_target_definition_ids(client: ShopifyClient) -> list[str]:
    """Retourne tous les IDs de définitions de métafields produit de la cible."""
    ids: list[str] = []
    cursor: str | None = None
    while True:
        variables: dict = {"ownerType": "PRODUCT"}
        if cursor:
            variables["after"] = cursor
        result = await client.graphql_target(_QUERY_METAFIELD_DEFINITIONS, variables)
        mf_defs = result.get("data", {}).get("metafieldDefinitions", {})
        ids.extend(edge["node"]["id"] for edge in mf_defs.get("edges", []))
        page_info = mf_defs.get("pageInfo", {})
        if page_info.get("hasNextPage"):
            cursor = page_info["endCursor"]
        else:
            break
    return ids


async def _sync_metafield_definitions(client: ShopifyClient) -> None:
    """Copie et épingle les définitions de métafields produit de la source vers la cible."""
    definitions: list[dict] = []
    cursor: str | None = None

    while True:
        variables: dict = {"ownerType": "PRODUCT"}
        if cursor:
            variables["after"] = cursor
        result = await client.graphql_source(_QUERY_METAFIELD_DEFINITIONS, variables)
        mf_defs = result.get("data", {}).get("metafieldDefinitions", {})
        definitions.extend(edge["node"] for edge in mf_defs.get("edges", []))
        page_info = mf_defs.get("pageInfo", {})
        if page_info.get("hasNextPage"):
            cursor = page_info["endCursor"]
        else:
            break

    print(f"  {len(definitions)} définitions de métafields produit trouvées sur la source.")

    for defn in definitions:
        mf_type = (defn.get("type") or {}).get("name", "")
        if mf_type in _SKIP_TYPES:
            continue
        result = await client.graphql_target(
            _MUTATION_METAFIELD_DEFINITION_CREATE,
            {"definition": {
                "namespace": defn["namespace"],
                "key": defn["key"],
                "name": defn["name"],
                "type": mf_type,
                "ownerType": "PRODUCT",
                "description": defn.get("description") or "",
            }},
        )
        errors = result.get("data", {}).get("metafieldDefinitionCreate", {}).get("userErrors", [])
        for err in errors:
            if "already" not in err.get("message", "").lower():
                print(f"  [WARN] Définition ({defn['namespace']}.{defn['key']}): {err.get('message')}")

    # Épingle toutes les définitions présentes sur la cible (nouvelles + pré-existantes)
    target_ids = await _fetch_target_definition_ids(client)
    for def_id in target_ids:
        await client.graphql_target(_MUTATION_METAFIELD_DEFINITION_PIN, {"definitionId": def_id})


async def fetch_all_products(client: ShopifyClient) -> list[dict]:
    all_products: list[dict] = []
    page_info: str | None = None

    while True:
        params: dict = {"limit": "250"}
        if page_info:
            params["page_info"] = page_info

        url = client._source_base + "products.json"
        async with client._semaphore:
            response = await client._http.get(url, headers=client._source_headers, params=params)
            response.raise_for_status()

        all_products.extend(response.json().get("products", []))
        print(f"  Fetched {len(all_products)} products so far...")

        match = _LINK_RE.search(response.headers.get("Link", ""))
        if match:
            page_info = match.group(1)
        else:
            break

    return all_products


async def _fetch_product_extra(
    client: ShopifyClient, source_id: int
) -> tuple[str | None, list[dict], list[dict]]:
    """Returns (category_gid, metafields_list, options_list)."""
    gid = f"gid://shopify/Product/{source_id}"
    result = await client.graphql_source(_QUERY_PRODUCT_EXTRA, {"id": gid})
    product_data = result.get("data", {}).get("product", {})

    category_id: str | None = (product_data.get("category") or {}).get("id")

    metafields = [
        edge["node"]
        for edge in product_data.get("metafields", {}).get("edges", [])
    ]
    options = product_data.get("options", [])
    return category_id, metafields, options


async def _ensure_color_metaobject(
    client: ShopifyClient,
    source_metaobject_gid: str,
    metaobject_cache: dict[str, str],
) -> str | None:
    """Assure que le métaobjet couleur existe sur la target. Retourne son GID cible."""
    if source_metaobject_gid in metaobject_cache:
        return metaobject_cache[source_metaobject_gid]

    result = await client.graphql_source(_QUERY_METAOBJECT, {"id": source_metaobject_gid})
    source_obj = result.get("data", {}).get("metaobject")
    if not source_obj:
        return None

    handle = source_obj.get("handle", "")
    obj_type = source_obj.get("type", "")

    fields_to_copy = []
    skip_field_types = {"file_reference", "list.file_reference"}
    for field in source_obj.get("fields", []):
        if field.get("type") in skip_field_types or field.get("value") is None:
            continue
        fields_to_copy.append({"key": field["key"], "value": field["value"]})

    upsert_result = await client.graphql_target(
        _MUTATION_METAOBJECT_UPSERT,
        {
            "handle": {"handle": handle, "type": obj_type},
            "metaobject": {"fields": fields_to_copy},
        },
    )
    errors = upsert_result.get("data", {}).get("metaobjectUpsert", {}).get("userErrors", [])
    for err in errors:
        print(f"  [WARN] Métaobjet ({handle}): {err.get('message')}")

    target_obj = upsert_result.get("data", {}).get("metaobjectUpsert", {}).get("metaobject")
    if not target_obj:
        return None

    target_gid = target_obj["id"]
    metaobject_cache[source_metaobject_gid] = target_gid
    return target_gid


async def _clone_color_swatches(
    client: ShopifyClient,
    source_options: list[dict],
    target_product_id: int,
    metaobject_cache: dict[str, str],
) -> None:
    """Clone les linked metafields (swatches couleur) sur les options du produit cible."""
    target_product_gid = f"gid://shopify/Product/{target_product_id}"

    # Récupère les options existantes sur la cible pour obtenir leurs IDs
    opts_result = await client.graphql_target(_QUERY_PRODUCT_OPTIONS, {"id": target_product_gid})
    target_options = opts_result.get("data", {}).get("product", {}).get("options", [])
    target_option_by_name = {opt["name"]: opt for opt in target_options}

    for src_opt in source_options:
        linked_mf = src_opt.get("linkedMetafield")
        if not linked_mf:
            continue

        opt_name = src_opt.get("name", "")
        target_opt = target_option_by_name.get(opt_name)
        if not target_opt:
            continue

        # Résout les métaobjets source → target pour chaque valeur
        values_to_update = []
        target_opt_values_by_name = {v["name"]: v for v in target_opt.get("optionValues", [])}

        for src_val in src_opt.get("optionValues", []):
            src_linked_gid = src_val.get("linkedMetafieldValue")
            if not src_linked_gid:
                continue

            val_name = src_val.get("name", "")
            target_val = target_opt_values_by_name.get(val_name)
            if not target_val:
                continue

            target_metaobject_gid = await _ensure_color_metaobject(
                client, src_linked_gid, metaobject_cache
            )
            if not target_metaobject_gid:
                continue

            values_to_update.append({
                "id": target_val["id"],
                "linkedMetafieldValue": target_metaobject_gid,
            })

        if not values_to_update:
            continue

        mut_result = await client.graphql_target(
            _MUTATION_PRODUCT_OPTION_UPDATE,
            {
                "productId": target_product_gid,
                "option": {
                    "id": target_opt["id"],
                    "linkedMetafield": {
                        "namespace": linked_mf["namespace"],
                        "key": linked_mf["key"],
                    },
                },
                "optionValuesToUpdate": values_to_update,
            },
        )
        errors = mut_result.get("data", {}).get("productOptionUpdate", {}).get("userErrors", [])
        for err in errors:
            print(f"  [WARN] Swatch option ({opt_name}): {err.get('message')}")


async def _write_metafields(
    client: ShopifyClient,
    target_product_id: int,
    metafields: list[dict],
    remapper: DomainRemapper,
) -> None:
    target_gid = f"gid://shopify/Product/{target_product_id}"

    inputs = []
    for mf in metafields:
        mf_type = mf.get("type", "")
        if mf_type in _SKIP_TYPES:
            continue
        value = mf["value"]
        if mf_type in _REMAP_TYPES:
            value = remapper.remap(value) or value
        inputs.append({
            "ownerId": target_gid,
            "namespace": mf["namespace"],
            "key": mf["key"],
            "value": value,
            "type": mf_type,
        })

    if not inputs:
        return

    result = await client.graphql_target(_MUTATION_METAFIELDS_SET, {"metafields": inputs})
    errors = result.get("data", {}).get("metafieldsSet", {}).get("userErrors", [])
    if errors:
        for err in errors:
            print(f"  [WARN] Metafield error ({err.get('field')}): {err.get('message')}")


async def clone_product_images(
    client: ShopifyClient,
    cache: ImageCache,
    source_product_id: int,
    target_product_id: int,
    images: list[dict],
) -> int | None:
    """Upload images and return the first target image ID (for variant assignment)."""
    first_target_image_id: int | None = None

    for image in sorted(images, key=lambda i: i.get("position", 999)):
        src = image.get("src", "")
        if not src:
            continue

        local_path = await cache.download(client._http, src, source_product_id)
        encoded = base64.b64encode(local_path.read_bytes()).decode("ascii")

        result = await client.post_target(
            f"products/{target_product_id}/images.json",
            {"image": {
                "attachment": encoded,
                "filename": local_path.name,
                "position": image.get("position", 1),
            }},
        )

        if first_target_image_id is None:
            first_target_image_id = result.get("image", {}).get("id")

    return first_target_image_id


async def _assign_variant_images(
    client: ShopifyClient,
    target_product_id: int,
    target_variants: list[dict],
    image_id: int,
) -> None:
    for variant in target_variants:
        await client.put_target(
            f"products/{target_product_id}/variants/{variant['id']}.json",
            {"variant": {"id": variant["id"], "image_id": image_id}},
        )


def _build_variant_payload(variant: dict) -> dict:
    fields = ["title", "price", "sku", "position", "inventory_policy",
              "compare_at_price", "fulfillment_service", "inventory_management",
              "option1", "option2", "option3", "taxable", "barcode", "weight", "weight_unit"]
    return {f: variant[f] for f in fields if f in variant}


async def clone_product(
    client: ShopifyClient,
    mapping: IDMapping,
    remapper: DomainRemapper,
    cache: ImageCache,
    product: dict,
    metaobject_cache: dict[str, str],
) -> None:
    source_id = product["id"]

    if mapping.has("product", source_id):
        print(f"  Skipping product {source_id} (already cloned)")
        return

    # Récupère catégorie + métafields + options (swatches) depuis la source
    category_gid, metafields, source_options = await _fetch_product_extra(client, source_id)

    payload: dict = {
        "title": product.get("title", ""),
        "body_html": remapper.remap(product.get("body_html", "")),
        "vendor": product.get("vendor", ""),
        "product_type": product.get("product_type", ""),
        "status": product.get("status", "active"),
        "tags": product.get("tags", ""),
        "options": product.get("options", []),
        "variants": [_build_variant_payload(v) for v in product.get("variants", [])],
    }

    # category_gid vient de GraphQL (plus fiable que le champ REST product_category)
    if category_gid:
        payload["product_category"] = {"product_taxonomy_node_id": category_gid}
    else:
        product_category = product.get("product_category") or {}
        taxonomy_node_id = product_category.get("product_taxonomy_node_id")
        if taxonomy_node_id:
            payload["product_category"] = {"product_taxonomy_node_id": taxonomy_node_id}

    result = await client.post_target("products.json", {"product": payload})
    target_product = result["product"]
    target_id = target_product["id"]

    mapping.set("product", source_id, target_id)
    for sv, tv in zip(product.get("variants", []), target_product.get("variants", [])):
        mapping.set("variant", sv["id"], tv["id"])

    # Shopify ignore product_category dans le POST — on le définit via GraphQL
    if category_gid:
        target_gid = f"gid://shopify/Product/{target_id}"
        cat_result = await client.graphql_target(
            _MUTATION_PRODUCT_SET_CATEGORY,
            {"id": target_gid, "categoryId": category_gid},
        )
        cat_errors = cat_result.get("data", {}).get("productUpdate", {}).get("userErrors", [])
        for err in cat_errors:
            print(f"  [WARN] Catégorie ({product.get('title')}): {err.get('message')}")

    # Upload des images + récupération du 1er ID pour les variantes
    images = product.get("images", [])
    first_image_id: int | None = None
    if images:
        first_image_id = await clone_product_images(client, cache, source_id, target_id, images)

    # Assigne la 1ère image à toutes les variantes
    if first_image_id and target_product.get("variants"):
        await _assign_variant_images(client, target_id, target_product["variants"], first_image_id)

    # Écrit tous les métafields (caracteristiques, couleur, SEO, etc.)
    if metafields:
        await _write_metafields(client, target_id, metafields, remapper)

    # Clone les swatches couleur (linked metafields sur les options)
    if source_options:
        await _clone_color_swatches(client, source_options, target_id, metaobject_cache)

    print(f"  Cloned product '{product.get('title')}' ({source_id} -> {target_id})")


async def clone_all_products(
    client: ShopifyClient,
    mapping: IDMapping,
    remapper: DomainRemapper,
) -> None:
    cache = ImageCache()
    metaobject_cache: dict[str, str] = {}
    print("Synchronisation des définitions de métafields...")
    await _sync_metafield_definitions(client)
    print("Fetching products from source store...")
    products = await fetch_all_products(client)
    print(f"Found {len(products)} products. Starting clone...")

    for product in products:
        await clone_product(client, mapping, remapper, cache, product, metaobject_cache)

    print(f"Products phase complete. {len(products)} products processed.")
