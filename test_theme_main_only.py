import asyncio
import os
from pathlib import Path

from cloner.client import ShopifyClient
from cloner.domain import DomainRemapper
from cloner.mapping import IDMapping
from cloner.phases.theme import (
    clone_single_theme,
    fetch_active_theme,
    fetch_target_theme_names,
    publish_theme,
)
from cloner.report import save_report


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
        raise EnvironmentError(f"Missing required env var: {key}")
    return value


async def run() -> None:
    client = ShopifyClient(
        source_shop=_require("SOURCE_SHOP"),
        source_token=_require("SOURCE_TOKEN"),
        target_shop=_require("TARGET_SHOP"),
        target_token=_require("TARGET_TOKEN"),
    )

    mapping = IDMapping()
    remapper = DomainRemapper(
        source_myshopify=_require("SOURCE_SHOP"),
        target_domain=os.environ.get("TARGET_CUSTOM_DOMAIN") or _require("TARGET_SHOP"),
        source_custom=os.environ.get("SOURCE_CUSTOM_DOMAIN") or None,
    )

    try:
        active_theme = await fetch_active_theme(client)
        existing_names = await fetch_target_theme_names(client)
        cloned_theme = await clone_single_theme(client, mapping, remapper, active_theme, existing_names)
        cloned_theme["summary_entry"]["published_final"] = True
        for entry in cloned_theme["report_entries"]:
            if entry.get("type") == "theme" and entry.get("id_source") == active_theme["id"]:
                entry["published_final"] = True
        await publish_theme(client, cloned_theme["target_theme_id"])
        save_report(cloned_theme["report_entries"])
        print("Main theme clone complete.")
    finally:
        await client.close()


if __name__ == "__main__":
    load_env()
    asyncio.run(run())
