"""
Test isolé de l'audit de santé source.
Usage : python test_health_audit_run.py [phases...]

Sans argument, audite : menus, discounts, theme
Exemple : python test_health_audit_run.py theme
"""
import asyncio
import json
import sys

import main
from cloner.client import ShopifyClient
from cloner.health_audit import run_source_health_audit


DEFAULT_PHASES = ["menus", "discounts", "theme"]


async def _main() -> None:
    main.load_env()
    phases = sys.argv[1:] or DEFAULT_PHASES

    client = ShopifyClient(
        source_shop=main._require("SOURCE_SHOP"),
        source_token=main._require("SOURCE_TOKEN"),
        target_shop=main._require("TARGET_SHOP"),
        target_token=main._require("TARGET_TOKEN"),
    )

    try:
        result = await run_source_health_audit(client, phases)
    finally:
        await client.close()

    print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
    print("\nRapport écrit dans output/source_health_audit.json")


if __name__ == "__main__":
    asyncio.run(_main())
