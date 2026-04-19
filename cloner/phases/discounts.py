from cloner.client import ShopifyClient
from cloner.domain import DomainRemapper
from cloner.mapping import IDMapping

_POLICY_HANDLES = [
    "refund-policy",
    "privacy-policy",
    "terms-of-service",
    "shipping-policy",
    "contact-information",
    "subscription-policy",
    "legal-notice",
]


async def clone_policies(
    client: ShopifyClient,
    remapper: DomainRemapper,
) -> list[dict]:
    report_entries: list[dict] = []

    print("Fetching policies from source...")
    result = await client.get_source("policies.json")
    policies = result.get("policies", [])
    print(f"Found {len(policies)} policies.")

    for policy in policies:
        handle = policy.get("handle", "")
        title = policy.get("title", "")
        body = remapper.remap(policy.get("body", "")) or ""

        try:
            await client.post_target("policies.json", {"policy": {
                "handle": handle,
                "title": title,
                "body": body,
            }})
            print(f"  Cloned policy '{title}'")
            report_entries.append({
                "type": "policy", "id_source": handle, "id_cible": handle,
                "title": title, "statut": "ok",
            })
        except Exception as e:
            print(f"  [ERROR] Policy '{title}': {e}")
            report_entries.append({
                "type": "policy", "id_source": handle, "id_cible": None,
                "title": title, "statut": f"error: {e}",
            })

    return report_entries


async def clone_discounts(
    client: ShopifyClient,
    mapping: IDMapping,
    remapper: DomainRemapper,
) -> list[dict]:
    report_entries: list[dict] = []

    # Politiques du site
    policy_entries = await clone_policies(client, remapper)
    report_entries.extend(policy_entries)

    # Réductions (price rules + discount codes)
    print("Fetching price rules from source...")
    result = await client.get_source("price_rules.json?limit=250")
    price_rules = result.get("price_rules", [])
    print(f"Found {len(price_rules)} price rules.")

    for rule in price_rules:
        source_id = rule["id"]
        title = rule.get("title", "")

        try:
            payload = {k: v for k, v in rule.items() if k not in ("id", "admin_graphql_api_id", "created_at", "updated_at")}
            # Remapper les IDs de produits/collections ciblés
            entitled_product_ids = rule.get("entitled_product_ids", [])
            if entitled_product_ids:
                payload["entitled_product_ids"] = [
                    int(mapping.get("product", pid)) if mapping.has("product", pid) else pid
                    for pid in entitled_product_ids
                ]
            entitled_collection_ids = rule.get("entitled_collection_ids", [])
            if entitled_collection_ids:
                payload["entitled_collection_ids"] = [
                    int(mapping.get("collection", cid)) if mapping.has("collection", cid) else cid
                    for cid in entitled_collection_ids
                ]
            prerequisite_product_ids = rule.get("prerequisite_product_ids", [])
            if prerequisite_product_ids:
                payload["prerequisite_product_ids"] = [
                    int(mapping.get("product", pid)) if mapping.has("product", pid) else pid
                    for pid in prerequisite_product_ids
                ]

            result_post = await client.post_target("price_rules.json", {"price_rule": payload})
            target_id = result_post["price_rule"]["id"]
            mapping.set("price_rule", source_id, target_id)
            print(f"  Cloned price rule '{title}' ({source_id} -> {target_id})")

            # Copier les codes de réduction associés
            codes_result = await client.get_source(f"price_rules/{source_id}/discount_codes.json")
            codes = codes_result.get("discount_codes", [])
            for code in codes:
                try:
                    await client.post_target(f"price_rules/{target_id}/discount_codes.json", {
                        "discount_code": {"code": code["code"]}
                    })
                except Exception:
                    pass  # Code déjà existant ou conflit ignoré

            report_entries.append({
                "type": "price_rule", "id_source": source_id, "id_cible": target_id,
                "title": title, "statut": "ok",
            })
        except Exception as e:
            print(f"  [ERROR] Price rule '{title}' ({source_id}): {e}")
            report_entries.append({
                "type": "price_rule", "id_source": source_id, "id_cible": None,
                "title": title, "statut": f"error: {e}",
            })

    print(f"Discounts phase complete. {len(price_rules)} price rules processed.")
    return report_entries
