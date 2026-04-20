"""
Test isolé de la phase blogs.
Usage : python test_blogs.py [--dry-run]

--dry-run : affiche les blogs et articles source sans rien écrire sur la cible.
Sans flag  : clone réellement les blogs et articles (remapping domaine + images + métafields).
"""
import asyncio
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


async def dry_run(client) -> None:
    from cloner.phases.blogs import fetch_all_blogs, fetch_articles

    blogs = await fetch_all_blogs(client)
    print(f"\n{'='*50}")
    print(f"Blogs trouvés sur la source : {len(blogs)}")
    print(f"{'='*50}")

    for blog in blogs:
        articles = await fetch_articles(client, blog["id"])
        print(f"\n  Blog [{blog['id']}] \"{blog.get('title')}\"  ({len(articles)} articles)")
        for article in articles:
            has_image = "🖼 " if article.get("image") else "   "
            status = "publié" if article.get("published") else "brouillon"
            print(f"    {has_image}[{article['id']}] \"{article.get('title')}\"  [{status}]")

    await client.close()


async def real_clone(client) -> None:
    from cloner.mapping import IDMapping
    from cloner.domain import DomainRemapper
    from cloner.image_cache import ImageCache
    from cloner.phases.blogs import clone_blogs
    from cloner.report import save_report

    mapping = IDMapping()
    remapper = DomainRemapper(
        source_myshopify=_require("SOURCE_SHOP"),
        target_domain=os.environ.get("TARGET_CUSTOM_DOMAIN") or _require("TARGET_SHOP"),
        source_custom=os.environ.get("SOURCE_CUSTOM_DOMAIN") or None,
    )
    cache = ImageCache()

    print("\nDémarrage du clonage blogs...")
    try:
        entries = await clone_blogs(client, mapping, remapper, cache)
        mapping.save()
    finally:
        await client.close()

    ok = sum(1 for e in entries if e["statut"] == "ok")
    skipped = sum(1 for e in entries if e["statut"] == "skipped")
    errors = [e for e in entries if e["statut"] not in ("ok", "skipped")]

    print(f"\n{'='*50}")
    print(f"Résultat : {ok} créés  |  {skipped} ignorés  |  {len(errors)} erreurs")
    if errors:
        print("\nErreurs :")
        for e in errors:
            print(f"  [{e['type']}] \"{e['title']}\" — {e['statut']}")
    print(f"{'='*50}")

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

    if "--dry-run" in sys.argv:
        await dry_run(client)
    else:
        await real_clone(client)


if __name__ == "__main__":
    asyncio.run(main())
