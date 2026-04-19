import re

from cloner.client import ShopifyClient
from cloner.domain import DomainRemapper
from cloner.mapping import IDMapping

_LINK_RE = re.compile(r'<[^>]+[?&]page_info=([^&>]+)[^>]*>;\s*rel="next"')


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


async def clone_blogs(
    client: ShopifyClient,
    mapping: IDMapping,
    remapper: DomainRemapper,
) -> list[dict]:
    report_entries: list[dict] = []

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

                result = await client.post_target(
                    f"blogs/{target_blog_id}/articles.json",
                    {"article": payload},
                )
                target_article_id = result["article"]["id"]
                mapping.set("article", source_article_id, target_article_id)

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
