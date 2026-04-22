from cloner.client import ShopifyClient
from cloner.domain import DomainRemapper

_HANDLE_TO_GQL_TYPE = {
    "refund-policy": "REFUND_POLICY",
    "privacy-policy": "PRIVACY_POLICY",
    "terms-of-service": "TERMS_OF_SERVICE",
    "terms-of-sale": "TERMS_OF_SALE",
    "shipping-policy": "SHIPPING_POLICY",
    "contact-information": "CONTACT_INFORMATION",
    "subscription-policy": "SUBSCRIPTION_POLICY",
    "legal-notice": "LEGAL_NOTICE",
}

_MUTATION = """
mutation shopPolicyUpdate($shopPolicy: ShopPolicyInput!) {
  shopPolicyUpdate(shopPolicy: $shopPolicy) {
    shopPolicy { type body }
    userErrors { field message }
  }
}
"""


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
        gql_type = _HANDLE_TO_GQL_TYPE.get(handle)

        if not gql_type:
            print(f"  [SKIP] Unknown policy handle '{handle}' — no GraphQL type mapping")
            report_entries.append({
                "type": "policy", "id_source": handle, "id_cible": None,
                "title": title, "statut": "skipped", "error": "unknown handle",
            })
            continue

        if not body.strip():
            print(f"  [SKIP] Policy '{title}': body vide (politique automatisée Shopify — désactiver dans l'admin source)")
            report_entries.append({
                "type": "policy", "id_source": handle, "id_cible": None,
                "title": title, "statut": "skipped", "error": "body vide (politique automatisée)",
            })
            continue

        try:
            gql_result = await client.graphql_target(
                _MUTATION,
                variables={"shopPolicy": {"type": gql_type, "body": body}},
            )
            user_errors = (gql_result.get("data") or {}).get("shopPolicyUpdate", {}).get("userErrors", [])
            if user_errors:
                error_msg = "; ".join(e.get("message", "") for e in user_errors)
                print(f"  [SKIP] Policy '{title}': {error_msg}")
                report_entries.append({
                    "type": "policy", "id_source": handle, "id_cible": None,
                    "title": title, "statut": "skipped", "error": error_msg,
                })
            else:
                print(f"  Cloned policy '{title}'")
                report_entries.append({
                    "type": "policy", "id_source": handle, "id_cible": handle,
                    "title": title, "statut": "ok",
                })
        except Exception as e:
            print(f"  [ERROR] Policy '{title}': {e}")
            report_entries.append({
                "type": "policy", "id_source": handle, "id_cible": None,
                "title": title, "statut": "skipped", "error": str(e),
            })

    print(f"Policies phase complete. {len(policies)} policies processed.")
    return report_entries
