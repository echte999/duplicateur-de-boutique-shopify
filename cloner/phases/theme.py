import asyncio
import json
import re
import time
from typing import Any

from cloner.client import ShopifyClient, ShopifyAPIError
from cloner.domain import DomainRemapper
from cloner.mapping import IDMapping

_GID_RE = re.compile(r'gid://shopify/(Product|Collection)/(\d+)')

_GQL_STAGED_UPLOAD = """
mutation stagedUploadsCreate($input: [StagedUploadInput!]!) {
  stagedUploadsCreate(input: $input) {
    stagedTargets { url resourceUrl parameters { name value } }
    userErrors { field message }
  }
}
"""

_GQL_FILE_CREATE = """
mutation fileCreate($files: [FileCreateInput!]!) {
  fileCreate(files: $files) {
    files {
      ... on MediaImage { id image { url } }
      ... on GenericFile { id url }
    }
    userErrors { field message }
  }
}
"""

_GQL_LIST_FILES = """
{
  files(first: 250) {
    nodes {
      ... on MediaImage { image { originalSrc } }
      ... on GenericFile { url }
    }
  }
}
"""

_GQL_SEARCH_FILE = """
query($q: String!) {
  files(first: 10, query: $q) {
    nodes {
      ... on MediaImage { image { originalSrc } }
      ... on GenericFile { url }
    }
  }
}
"""


def _mime(filename: str) -> str:
    ext = filename.lower().rsplit(".", 1)[-1]
    return {
        "jpg": "image/jpeg", "jpeg": "image/jpeg",
        "png": "image/png", "webp": "image/webp",
        "gif": "image/gif", "svg": "image/svg+xml",
    }.get(ext, "application/octet-stream")


def _is_group_file(key: str) -> bool:
    """Match both 'header-group.json' (dash) and 'header.group.json' (dot) formats."""
    return key.endswith("group.json") and key.startswith("sections/")


async def fetch_active_theme(client: ShopifyClient) -> dict:
    result = await client.get_source("themes.json")
    for theme in result.get("themes", []):
        if theme.get("role") == "main":
            return theme
    raise RuntimeError("No active theme (role=main) found on source shop.")


async def fetch_asset_list(client: ShopifyClient, theme_id: int) -> list[dict]:
    result = await client.get_source(f"themes/{theme_id}/assets.json")
    return result.get("assets", [])


async def fetch_asset_list_target(client: ShopifyClient, theme_id: int) -> list[dict]:
    result = await client.get_target(f"themes/{theme_id}/assets.json")
    return result.get("assets", [])


async def fetch_asset(client: ShopifyClient, theme_id: int, key: str) -> dict:
    result = await client.get_source(
        f"themes/{theme_id}/assets.json",
        params={"asset[key]": key},
    )
    return result.get("asset", {})


async def create_theme(client: ShopifyClient, name: str) -> int:
    result = await client.post_target("themes.json", {
        "theme": {"name": name, "role": "unpublished"},
    })
    return result["theme"]["id"]


async def publish_theme(client: ShopifyClient, theme_id: int) -> None:
    await client.put_target(f"themes/{theme_id}.json", {
        "theme": {"id": theme_id, "role": "main"},
    })


def _remap_value(value: Any, mapping: IDMapping) -> Any:
    if isinstance(value, dict):
        return {k: _remap_value(v, mapping) for k, v in value.items()}
    if isinstance(value, list):
        return [_remap_value(v, mapping) for v in value]
    if isinstance(value, str):
        def replace_gid(m: re.Match) -> str:
            rtype = m.group(1).lower()
            src_id = m.group(2)
            if mapping.has(rtype, src_id):
                return f"gid://shopify/{m.group(1)}/{mapping.get(rtype, src_id)}"
            return m.group(0)

        remapped = _GID_RE.sub(replace_gid, value)
        if remapped != value:
            return remapped
        for rtype in ("product", "collection"):
            if mapping.has(rtype, value):
                return mapping.get(rtype, value)
        return remapped
    return value


def remap_ids_in_json(content_str: str, mapping: IDMapping) -> str:
    try:
        data = json.loads(content_str)
    except (json.JSONDecodeError, ValueError):
        return content_str
    return json.dumps(_remap_value(data, mapping), ensure_ascii=False)


def _apply_shop_uri_map(content_str: str, shop_uri_map: dict[str, str]) -> str:
    """Replace shopify://shop_images/ URIs in a JSON string using the provided map."""
    if not shop_uri_map:
        return content_str
    try:
        data = json.loads(content_str)
    except (json.JSONDecodeError, ValueError):
        return content_str

    def remap(obj: Any) -> Any:
        if isinstance(obj, dict):
            return {k: remap(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [remap(v) for v in obj]
        if isinstance(obj, str) and obj in shop_uri_map:
            return shop_uri_map[obj]
        return obj

    return json.dumps(remap(data), ensure_ascii=False)


def process_asset_content(
    key: str,
    value: str,
    mapping: IDMapping,
    remapper: DomainRemapper,
    shop_uri_map: dict[str, str] | None = None,
) -> str:
    content = remapper.remap(value) or value
    if key.endswith(".json"):
        content = remap_ids_in_json(content, mapping)
        if shop_uri_map:
            content = _apply_shop_uri_map(content, shop_uri_map)
    return content


async def upload_asset(
    client: ShopifyClient,
    theme_id: int,
    key: str,
    value: str | None = None,
    attachment: str | None = None,
) -> None:
    asset_payload: dict = {"key": key}
    if value is not None:
        asset_payload["value"] = value
    elif attachment is not None:
        asset_payload["attachment"] = attachment
    await client.put_target(f"themes/{theme_id}/assets.json", {"asset": asset_payload})


def _collect_shop_image_refs(content_str: str) -> set[str]:
    try:
        data = json.loads(content_str)
    except (json.JSONDecodeError, ValueError):
        return set()

    refs: set[str] = set()

    def walk(obj: Any) -> None:
        if isinstance(obj, dict):
            for v in obj.values():
                walk(v)
        elif isinstance(obj, list):
            for v in obj:
                walk(v)
        elif isinstance(obj, str) and obj.startswith("shopify://shop_images/"):
            refs.add(obj[len("shopify://shop_images/"):])

    walk(data)
    return refs


async def _get_source_shop_file_url(client: ShopifyClient, filename: str) -> str | None:
    result = await client.graphql_source(_GQL_SEARCH_FILE, {"q": f"filename:{filename.rsplit('.', 1)[0]}"})
    nodes = result.get("data", {}).get("files", {}).get("nodes", [])
    for node in nodes:
        url = node.get("image", {}).get("originalSrc") or node.get("url", "")
        if url:
            return url
    return None


async def _get_actual_name_on_target(client: ShopifyClient, filename: str) -> str | None:
    """Search target files by stem; return actual stored filename (may differ if format-converted)."""
    stem = filename.rsplit(".", 1)[0]
    result = await client.graphql_target(_GQL_SEARCH_FILE, {"q": f"filename:{stem}"})
    nodes = result.get("data", {}).get("files", {}).get("nodes", [])
    # Prefer exact stem match without UUID suffix
    for node in nodes:
        url = node.get("image", {}).get("originalSrc") or node.get("url", "")
        if not url:
            continue
        cdn_name = url.split("?")[0].split("/")[-1]
        if cdn_name.rsplit(".", 1)[0] == stem:
            return cdn_name
    # Fallback: first result
    for node in nodes:
        url = node.get("image", {}).get("originalSrc") or node.get("url", "")
        if url:
            return url.split("?")[0].split("/")[-1]
    return None


async def _upload_shop_image_to_target(
    client: ShopifyClient,
    filename: str,
    image_data: bytes,
) -> str | None:
    """Upload image to target shop files. Returns actual stored filename (may differ from input)."""
    mime = _mime(filename)
    print(f"    [{filename}] Requesting staged upload ({len(image_data)} bytes)...")

    stage_result = await client.graphql_target(_GQL_STAGED_UPLOAD, {
        "input": [{"filename": filename, "mimeType": mime, "resource": "IMAGE", "fileSize": str(len(image_data))}]
    })
    targets = stage_result.get("data", {}).get("stagedUploadsCreate", {}).get("stagedTargets", [])
    if not targets:
        errors = stage_result.get("data", {}).get("stagedUploadsCreate", {}).get("userErrors", [])
        print(f"    [{filename}] Staged upload error: {errors}")
        return None

    target = targets[0]
    upload_url = target["url"]
    resource_url = target["resourceUrl"]

    response = await client._http.put(upload_url, content=image_data, headers={"Content-Type": mime}, timeout=120)
    if response.status_code not in (200, 201, 204):
        print(f"    [{filename}] GCS PUT failed: HTTP {response.status_code}")
        return None

    create_result = await client.graphql_target(_GQL_FILE_CREATE, {
        "files": [{"originalSource": resource_url, "alt": filename}]
    })
    errors = create_result.get("data", {}).get("fileCreate", {}).get("userErrors", [])
    if errors:
        print(f"    [{filename}] fileCreate errors: {errors}")
        return None

    # Poll until file is accessible and get actual stored filename
    print(f"    [{filename}] Waiting for Shopify to process...")
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        actual = await _get_actual_name_on_target(client, filename)
        if actual:
            if actual != filename:
                print(f"    [{filename}] Stored as: {actual} (format converted by Shopify)")
            else:
                print(f"    [{filename}] Upload confirmed.")
            return actual
        await asyncio.sleep(5)

    print(f"    [{filename}] Timed out. File may still be processing.")
    return None


async def _target_shop_files_set(client: ShopifyClient) -> set[str]:
    result = await client.graphql_target(_GQL_LIST_FILES)
    nodes = result.get("data", {}).get("files", {}).get("nodes", [])
    names: set[str] = set()
    for node in nodes:
        url = node.get("image", {}).get("originalSrc") or node.get("url", "")
        if url:
            names.add(url.split("?")[0].split("/")[-1])
    return names


async def migrate_shop_images(
    client: ShopifyClient,
    src_theme_id: int,
) -> dict[str, str]:
    """
    Scan source theme JSON assets for shopify://shop_images/ refs.
    Upload missing images to target.
    Return URI map: {original_shopify_uri -> actual_shopify_uri_on_target}
    (URIs may differ when Shopify converts file formats, e.g. .webp -> .jpg)
    """
    print("  Scanning theme JSON for shopify://shop_images/ references...")
    asset_list = await fetch_asset_list(client, src_theme_id)
    json_keys = [a["key"] for a in asset_list if a["key"].endswith(".json")]

    all_refs: set[str] = set()
    for key in json_keys:
        asset = await fetch_asset(client, src_theme_id, key)
        val = asset.get("value", "")
        if val:
            all_refs |= _collect_shop_image_refs(val)

    if not all_refs:
        print("  No shopify://shop_images/ references found.")
        return {}

    print(f"  Found {len(all_refs)} shop image ref(s): {sorted(all_refs)}")

    existing = await _target_shop_files_set(client)
    uri_map: dict[str, str] = {}

    for filename in sorted(all_refs):
        original_uri = f"shopify://shop_images/{filename}"

        # Check if exact filename already on target
        if filename in existing:
            uri_map[original_uri] = original_uri  # no change
            print(f"  [{filename}] Already present on target (exact match).")
            continue

        # Check if a format-converted version exists (e.g., .webp -> .jpg)
        actual = await _get_actual_name_on_target(client, filename)
        if actual and actual != filename:
            actual_uri = f"shopify://shop_images/{actual}"
            uri_map[original_uri] = actual_uri
            print(f"  [{filename}] Found as '{actual}' on target (format converted).")
            continue

        # Need to upload from source
        src_url = await _get_source_shop_file_url(client, filename)
        if not src_url:
            print(f"  [{filename}] NOT FOUND in source shop files — skipped.")
            continue

        print(f"  [{filename}] Downloading from source CDN...")
        resp = await client._http.get(src_url, follow_redirects=True, timeout=120)
        if resp.status_code >= 400:
            print(f"  [{filename}] Download failed: HTTP {resp.status_code}")
            continue

        actual = await _upload_shop_image_to_target(client, filename, resp.content)
        if actual:
            actual_uri = f"shopify://shop_images/{actual}"
            uri_map[original_uri] = actual_uri
        else:
            print(f"  [{filename}] Upload failed.")

    # Report changes
    remapped = [(k, v) for k, v in uri_map.items() if k != v]
    if remapped:
        print(f"  URI remappings needed ({len(remapped)}):")
        for old, new in remapped:
            print(f"    {old} -> {new}")

    return uri_map


def _extract_section_types(group_content: str) -> list[str]:
    try:
        data = json.loads(group_content)
        sections = data.get("sections", {})
        return [v["type"] for v in sections.values() if isinstance(v, dict) and v.get("type")]
    except (json.JSONDecodeError, ValueError, KeyError):
        return []


async def _wait_for_sections(
    client: ShopifyClient,
    tgt_theme_id: int,
    required_keys: list[str],
    timeout: int = 300,
) -> bool:
    if not required_keys:
        return True
    deadline = time.monotonic() + timeout
    while True:
        present = {a["key"] for a in await fetch_asset_list_target(client, tgt_theme_id)}
        missing = [k for k in required_keys if k not in present]
        if not missing:
            return True
        if time.monotonic() >= deadline:
            print(f"  [WARN] Timed out waiting for sections: {missing}")
            return False
        print(f"  Waiting for sections to be indexed: {missing} — retrying in 10s...")
        await asyncio.sleep(10)


async def clone_theme(
    client: ShopifyClient,
    mapping: IDMapping,
    remapper: DomainRemapper,
) -> list[dict]:
    report_entries: list[dict] = []

    print("Fetching active theme from source...")
    src_theme = await fetch_active_theme(client)
    src_theme_id = src_theme["id"]
    print(f"  Source theme: '{src_theme['name']}' (id={src_theme_id})")

    print("Creating new theme on target...")
    tgt_theme_id = await create_theme(client, src_theme["name"])
    mapping.set("theme", src_theme_id, tgt_theme_id)
    print(f"  Target theme created: id={tgt_theme_id}")

    report_entries.append({
        "type": "theme",
        "id_source": src_theme_id,
        "id_cible": tgt_theme_id,
        "title": src_theme.get("name", ""),
        "statut": "ok",
    })

    print("Fetching asset list from source theme...")
    raw_list = await fetch_asset_list(client, src_theme_id)
    print(f"  Found {len(raw_list)} assets.")

    success_count = 0
    # Collect section group files upfront — always defer, never upload in first pass
    pending_group_files: list[tuple[str, str | None, str | None]] = []

    for asset_meta in raw_list:
        key = asset_meta["key"]
        try:
            asset = await fetch_asset(client, src_theme_id, key)

            if _is_group_file(key):
                val = process_asset_content(key, asset.get("value", ""), mapping, remapper) if "value" in asset else None
                att = asset.get("attachment") if "attachment" in asset else None
                pending_group_files.append((key, val, att))
                print(f"  [GROUP PENDING] {key}")
                continue

            if "value" in asset:
                processed = process_asset_content(key, asset["value"], mapping, remapper)
                await upload_asset(client, tgt_theme_id, key, value=processed)
            elif "attachment" in asset:
                await upload_asset(client, tgt_theme_id, key, attachment=asset["attachment"])
            else:
                print(f"  [WARN] Asset '{key}' has neither value nor attachment — skipped.")
                report_entries.append({"type": "theme_asset", "key": key, "statut": "skipped"})
                continue

            success_count += 1
            print(f"  Uploaded: {key}")
            report_entries.append({"type": "theme_asset", "key": key, "statut": "success"})

        except Exception as e:
            print(f"  [ERROR] Asset '{key}': {e}")
            report_entries.append({"type": "theme_asset", "key": key, "statut": f"error: {e}"})

    # Upload section group files after polling for section dependencies
    if pending_group_files:
        print(f"\nUploading {len(pending_group_files)} section group file(s)...")
        for key, val, att in pending_group_files:
            if val:
                section_types = _extract_section_types(val)
                required_keys = [f"sections/{t}.liquid" for t in section_types]
                if required_keys:
                    print(f"  {key} requires sections: {section_types}")
                    await _wait_for_sections(client, tgt_theme_id, required_keys)
            try:
                await upload_asset(client, tgt_theme_id, key, value=val, attachment=att)
                success_count += 1
                print(f"  Uploaded: {key}")
                report_entries.append({"type": "theme_asset", "key": key, "statut": "success"})
            except Exception as e:
                print(f"  [ERROR] {key}: {e}")
                report_entries.append({"type": "theme_asset", "key": key, "statut": f"error: {e}"})

    # Migrate shop images and build URI remap map
    print("\nMigrating shop images (shopify://shop_images/ refs)...")
    shop_uri_map = await migrate_shop_images(client, src_theme_id)

    # Re-upload any JSON files that had shop image refs with corrected URIs
    remapped_uris = {k: v for k, v in shop_uri_map.items() if k != v}
    if remapped_uris:
        print(f"\nRe-uploading JSON files with corrected shop image URIs ({len(remapped_uris)} remappings)...")
        asset_list = await fetch_asset_list(client, src_theme_id)
        json_keys = [a["key"] for a in asset_list if a["key"].endswith(".json")]
        for key in json_keys:
            asset = await fetch_asset(client, src_theme_id, key)
            val = asset.get("value", "")
            if not val:
                continue
            # Check if this file has any of the remapped URIs
            try:
                data = json.loads(val)
                val_parsed = json.dumps(data)  # normalized
                if not any(old in val_parsed for old in remapped_uris):
                    continue
            except (json.JSONDecodeError, ValueError):
                continue
            # Re-process with full URI map
            processed = process_asset_content(key, val, mapping, remapper, shop_uri_map)
            try:
                await upload_asset(client, tgt_theme_id, key, value=processed)
                print(f"  Re-uploaded with fixed URIs: {key}")
            except Exception as e:
                print(f"  [ERROR] Re-uploading {key}: {e}")

    print("Publishing theme on target...")
    await publish_theme(client, tgt_theme_id)
    print("  Theme published.")

    print(f"Theme phase complete. {success_count}/{len(raw_list)} assets uploaded.")
    return report_entries
