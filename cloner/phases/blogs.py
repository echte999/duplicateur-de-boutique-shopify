import base64
import re

from cloner.client import ShopifyClient
from cloner.domain import DomainRemapper
from cloner.image_cache import ImageCache
from cloner.mapping import IDMapping

_LINK_RE = re.compile(r'<[^>]+[?&]page_info=([^&>]+)[^>]*>;\s*rel="next"')

_SKIP_TYPES = {"metaobject_reference", "list.metaobject_reference",
               "file_reference", "list.file_reference",
               "product_reference", "list.product_reference",
               "variant_reference", "list.variant_reference",
               "page_reference", "list.page_reference",
               "collection_reference", "list.collection_reference"}

_REMAP_TYPES = {"html", "url", "json_string"}

_QUERY_BLOG_METAFIELDS = """
query GetBlogMetafields($id: ID!) {
  blog(id: $id) {
    metafields(first: 100) {
      edges {
        node { namespace key value type }
      }
    }
  }
}
"""

_QUERY_ARTICLE_METAFIELDS = """
query GetArticleMetafields($id: ID!) {
  article(id: $id) {
    metafields(first: 100) {
      edges {
        node { namespace key value type }
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


async def _fetch_metafields(client: ShopifyClient, query: str, gid: str, resource_key: str) -> list[dict]:
    result = await client.graphql_source(query, {"id": gid})
    edges = result.get("data", {}).get(resource_key, {}).get("metafields", {}).get("edges", [])
    return [edge["node"] for edge in edges]


async def _write_metafields(
    client: ShopifyClient,
    owner_gid: str,
    metafields: list[dict],
    remapper: DomainRemapper,
) -> None:
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
        print(f"  [WARN] Metafield ({err.get('field')}): {err.get('message')}")


async def fetch_all_blogs(client: ShopifyClient) -> list[dict]:
    result = await client.get_source("blogs.json")
    return result.get("blogs", [])


async def fetch_articles(client: ShopifyClient, blog_id: int) -> list[dict]:
    all_articles: list[dict] = []
    page_info: str | None = None

    while True:
        params: dict = {"limit": "250"}
        if page_info:
            params["page_info"] = page_info

        url = client._source_base + f"blogs/{blog_id}/articles.json"
        async with client._semaphore:
            response = await client._http.get(url, headers=client._source_headers, params=params)
            response.raise_for_status()

        all_articles.extend(response.json().get("articles", []))

        match = _LINK_RE.search(response.headers.get("Link", ""))
        if match:
            page_info = match.group(1)
        else:
            break

    return all_articles


async def _upload_article_image(
    client: ShopifyClient,
    cache: ImageCache,
    article_id: int,
    image: dict,
) -> dict | None:
    src = image.get("src", "")
    if not src:
        return None

    local_path = await cache.download(client._http, src, f"article_{article_id}")
    encoded = base64.b64encode(local_path.read_bytes()).decode("ascii")
    return {
        "attachment": encoded,
        "filename": local_path.name,
        "alt": image.get("alt", ""),
    }


async def clone_blogs(
    client: ShopifyClient,
    mapping: IDMapping,
    remapper: DomainRemapper,
    cache: ImageCache | None = None,
) -> list[dict]:
    report_entries: list[dict] = []
    if cache is None:
        cache = ImageCache()

    print("Fetching blogs from source...")
    blogs = await fetch_all_blogs(client)
    print(f"Found {len(blogs)} blogs.")

    for blog in blogs:
        source_blog_id = blog["id"]

        if mapping.has("blog", source_blog_id):
            target_blog_id = int(mapping.get("blog", source_blog_id))
            print(f"  Blog '{blog.get('title')}' already cloned, checking articles...")
        else:
            try:
                result = await client.post_target("blogs.json", {"blog": {
                    "title": blog.get("title", ""),
                    "handle": blog.get("handle", ""),
                    "commentable": blog.get("commentable", "no"),
                }})
                target_blog_id = result["blog"]["id"]
                mapping.set("blog", source_blog_id, target_blog_id)

                # Métafields du blog
                blog_gid = f"gid://shopify/Blog/{source_blog_id}"
                metafields = await _fetch_metafields(client, _QUERY_BLOG_METAFIELDS, blog_gid, "blog")
                if metafields:
                    target_gid = f"gid://shopify/Blog/{target_blog_id}"
                    await _write_metafields(client, target_gid, metafields, remapper)

                print(f"  Cloned blog '{blog.get('title')}' ({source_blog_id} -> {target_blog_id})")
                report_entries.append({
                    "type": "blog", "id_source": source_blog_id, "id_cible": target_blog_id,
                    "title": blog.get("title", ""), "statut": "ok",
                })
            except Exception as e:
                print(f"  [ERROR] Blog '{blog.get('title')}' ({source_blog_id}): {e}")
                report_entries.append({
                    "type": "blog", "id_source": source_blog_id, "id_cible": None,
                    "title": blog.get("title", ""), "statut": f"error: {e}",
                })
                continue

        articles = await fetch_articles(client, source_blog_id)
        print(f"  Found {len(articles)} articles in '{blog.get('title')}'.")

        for article in articles:
            source_article_id = article["id"]

            if mapping.has("article", source_article_id):
                report_entries.append({
                    "type": "article", "id_source": source_article_id,
                    "id_cible": mapping.get("article", source_article_id),
                    "title": article.get("title", ""), "statut": "skipped",
                })
                continue

            try:
                payload: dict = {
                    "title": article.get("title", ""),
                    "body_html": remapper.remap(article.get("body_html", "")) or "",
                    "author": article.get("author", ""),
                    "tags": article.get("tags", ""),
                    "published": article.get("published", True),
                    "summary_html": remapper.remap(article.get("summary_html", "")) or "",
                }
                if article.get("handle"):
                    payload["handle"] = article["handle"]

                # Image mise en avant
                if article.get("image"):
                    uploaded = await _upload_article_image(client, cache, source_article_id, article["image"])
                    if uploaded:
                        payload["image"] = uploaded

                result = await client.post_target(
                    f"blogs/{target_blog_id}/articles.json",
                    {"article": payload},
                )
                target_article_id = result["article"]["id"]
                mapping.set("article", source_article_id, target_article_id)

                # Métafields de l'article
                article_gid = f"gid://shopify/Article/{source_article_id}"
                metafields = await _fetch_metafields(client, _QUERY_ARTICLE_METAFIELDS, article_gid, "article")
                if metafields:
                    target_gid = f"gid://shopify/Article/{target_article_id}"
                    await _write_metafields(client, target_gid, metafields, remapper)

                print(f"    Cloned article '{article.get('title')}' ({source_article_id} -> {target_article_id})")
                report_entries.append({
                    "type": "article", "id_source": source_article_id, "id_cible": target_article_id,
                    "title": article.get("title", ""), "statut": "ok",
                })
            except Exception as e:
                print(f"    [ERROR] Article '{article.get('title')}' ({source_article_id}): {e}")
                report_entries.append({
                    "type": "article", "id_source": source_article_id, "id_cible": None,
                    "title": article.get("title", ""), "statut": f"error: {e}",
                })

    print(f"Blogs phase complete. {len(blogs)} blogs processed.")
    return report_entries
