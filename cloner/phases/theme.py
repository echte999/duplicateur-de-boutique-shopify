import asyncio
import json
import re
import time
from typing import Any

from cloner.client import ShopifyClient
from cloner.domain import DomainRemapper
from cloner.mapping import IDMapping

_GID_RE = re.compile(r"gid://shopify/(Product|Collection)/(\d+)")

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
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "webp": "image/webp",
        "gif": "image/gif",
        "svg": "image/svg+xml",
    }.get(ext, "application/octet-stream")


def _is_group_file(key: str) -> bool:
    return key.endswith("group.json") and key.startswith("sections/")


async def fetch_active_theme(client: ShopifyClient) -> dict:
    themes = await fetch_source_themes(client)
    for theme in themes:
        if theme.get("role") == "main":
            return theme
    raise RuntimeError("No active theme (role=main) found on source shop.")


async def fetch_source_themes(client: ShopifyClient) -> list[dict]:
    result = await client.get_source("themes.json")
    themes = result.get("themes", [])
    main_count = sum(1 for theme in themes if theme.get("role") == "main")
    if main_count == 0:
        raise RuntimeError("No active theme (role=main) found on source shop.")
    if main_count > 1:
        raise RuntimeError("Multiple active themes (role=main) found on source shop.")
    return themes


async def fetch_target_theme_names(client: ShopifyClient) -> set[str]:
    result = await client.get_target("themes.json")
    return {theme.get("name", "") for theme in result.get("themes", []) if theme.get("name")}


def order_source_themes(themes: list[dict]) -> list[dict]:
    return sorted(themes, key=lambda theme: (theme.get("role") == "main", theme.get("id", 0)))


def build_target_theme_name(source_theme: dict, existing_names: set[str]) -> str:
    base_name = source_theme.get("name") or f"Theme {source_theme['id']}"
    if base_name not in existing_names:
        return base_name

    candidate = f"{base_name} (source {source_theme['id']})"
    if candidate not in existing_names:
        return candidate

    suffix = 2
    while True:
        candidate = f"{base_name} (source {source_theme['id']}-{suffix})"
        if candidate not in existing_names:
            return candidate
        suffix += 1


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
    result = await client.post_target("themes.json", {"theme": {"name": name, "role": "unpublished"}})
    return result["theme"]["id"]


async def publish_theme(client: ShopifyClient, theme_id: int) -> None:
    await client.put_target(f"themes/{theme_id}.json", {"theme": {"id": theme_id, "role": "main"}})


def _remap_value(value: Any, mapping: IDMapping) -> Any:
    if isinstance(value, dict):
        return {key: _remap_value(item, mapping) for key, item in value.items()}
    if isinstance(value, list):
        return [_remap_value(item, mapping) for item in value]
    if isinstance(value, str):
        def replace_gid(match: re.Match) -> str:
            resource_type = match.group(1).lower()
            source_id = match.group(2)
            if mapping.has(resource_type, source_id):
                return f"gid://shopify/{match.group(1)}/{mapping.get(resource_type, source_id)}"
            return match.group(0)

        remapped = _GID_RE.sub(replace_gid, value)
        if remapped != value:
            return remapped
        for resource_type in ("product", "collection"):
            if mapping.has(resource_type, value):
                return mapping.get(resource_type, value)
        return remapped
    return value


def remap_ids_in_json(content_str: str, mapping: IDMapping) -> str:
    try:
        data = json.loads(content_str)
    except (json.JSONDecodeError, ValueError):
        return content_str
    return json.dumps(_remap_value(data, mapping), ensure_ascii=False)


def _apply_shop_uri_map(content_str: str, shop_uri_map: dict[str, str]) -> str:
    if not shop_uri_map:
        return content_str
    try:
        data = json.loads(content_str)
    except (json.JSONDecodeError, ValueError):
        return content_str

    def remap(obj: Any) -> Any:
        if isinstance(obj, dict):
            return {key: remap(value) for key, value in obj.items()}
        if isinstance(obj, list):
            return [remap(value) for value in obj]
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
            for value in obj.values():
                walk(value)
        elif isinstance(obj, list):
            for value in obj:
                walk(value)
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
    stem = filename.rsplit(".", 1)[0]
    result = await client.graphql_target(_GQL_SEARCH_FILE, {"q": f"filename:{stem}"})
    nodes = result.get("data", {}).get("files", {}).get("nodes", [])
    for node in nodes:
        url = node.get("image", {}).get("originalSrc") or node.get("url", "")
        if not url:
            continue
        cdn_name = url.split("?")[0].split("/")[-1]
        if cdn_name.rsplit(".", 1)[0] == stem:
            return cdn_name
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
    mime = _mime(filename)
    print(f"    [{filename}] Requesting staged upload ({len(image_data)} bytes)...")

    stage_result = await client.graphql_target(
        _GQL_STAGED_UPLOAD,
        {"input": [{"filename": filename, "mimeType": mime, "resource": "IMAGE", "fileSize": str(len(image_data))}]},
    )
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

    create_result = await client.graphql_target(_GQL_FILE_CREATE, {"files": [{"originalSource": resource_url, "alt": filename}]})
    errors = create_result.get("data", {}).get("fileCreate", {}).get("userErrors", [])
    if errors:
        print(f"    [{filename}] fileCreate errors: {errors}")
        return None

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


async def migrate_shop_images(client: ShopifyClient, src_theme_id: int) -> dict[str, str]:
    print("  Scanning theme JSON for shopify://shop_images/ references...")
    asset_list = await fetch_asset_list(client, src_theme_id)
    json_keys = [asset["key"] for asset in asset_list if asset["key"].endswith(".json")]

    all_refs: set[str] = set()
    for key in json_keys:
        asset = await fetch_asset(client, src_theme_id, key)
        value = asset.get("value", "")
        if value:
            all_refs |= _collect_shop_image_refs(value)

    if not all_refs:
        print("  No shopify://shop_images/ references found.")
        return {}

    print(f"  Found {len(all_refs)} shop image ref(s): {sorted(all_refs)}")

    existing = await _target_shop_files_set(client)
    uri_map: dict[str, str] = {}

    for filename in sorted(all_refs):
        original_uri = f"shopify://shop_images/{filename}"

        if filename in existing:
            uri_map[original_uri] = original_uri
            print(f"  [{filename}] Already present on target (exact match).")
            continue

        actual = await _get_actual_name_on_target(client, filename)
        if actual and actual != filename:
            uri_map[original_uri] = f"shopify://shop_images/{actual}"
            print(f"  [{filename}] Found as '{actual}' on target (format converted).")
            continue

        src_url = await _get_source_shop_file_url(client, filename)
        if not src_url:
            print(f"  [{filename}] NOT FOUND in source shop files - skipped.")
            continue

        print(f"  [{filename}] Downloading from source CDN...")
        response = await client._http.get(src_url, follow_redirects=True, timeout=120)
        if response.status_code >= 400:
            print(f"  [{filename}] Download failed: HTTP {response.status_code}")
            continue

        actual = await _upload_shop_image_to_target(client, filename, response.content)
        if actual:
            uri_map[original_uri] = f"shopify://shop_images/{actual}"
        else:
            print(f"  [{filename}] Upload failed.")

    remapped = [(old, new) for old, new in uri_map.items() if old != new]
    if remapped:
        print(f"  URI remappings needed ({len(remapped)}):")
        for old, new in remapped:
            print(f"    {old} -> {new}")

    return uri_map


def _extract_section_types(group_content: str) -> list[str]:
    try:
        data = json.loads(group_content)
        sections = data.get("sections", {})
        return [section["type"] for section in sections.values() if isinstance(section, dict) and section.get("type")]
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
        present = {asset["key"] for asset in await fetch_asset_list_target(client, tgt_theme_id)}
        missing = [key for key in required_keys if key not in present]
        if not missing:
            return True
        if time.monotonic() >= deadline:
            print(f"  [WARN] Timed out waiting for sections: {missing}")
            return False
        print(f"  Waiting for sections to be indexed: {missing} - retrying in 10s...")
        await asyncio.sleep(10)


def _theme_entry(source_theme: dict, target_theme_id: int, target_theme_name: str) -> dict:
    return {
        "type": "theme",
        "id_source": source_theme["id"],
        "id_cible": target_theme_id,
        "title": source_theme.get("name", ""),
        "target_title": target_theme_name,
        "role_source": source_theme.get("role", ""),
        "published_final": False,
        "statut": "ok",
    }


def _theme_asset_entry(
    source_theme: dict,
    target_theme_id: int,
    target_theme_name: str,
    key: str,
    status: str,
) -> dict:
    return {
        "type": "theme_asset",
        "theme_source_id": source_theme["id"],
        "theme_target_id": target_theme_id,
        "theme_name": target_theme_name,
        "theme_role_source": source_theme.get("role", ""),
        "key": key,
        "statut": status,
    }


async def clone_single_theme(
    client: ShopifyClient,
    mapping: IDMapping,
    remapper: DomainRemapper,
    source_theme: dict,
    existing_names: set[str],
) -> dict:
    report_entries: list[dict] = []
    src_theme_id = source_theme["id"]
    target_theme_name = build_target_theme_name(source_theme, existing_names)
    existing_names.add(target_theme_name)

    print(f"  Creating target theme for '{source_theme['name']}'...")
    tgt_theme_id = await create_theme(client, target_theme_name)
    mapping.set("theme", src_theme_id, tgt_theme_id)
    print(f"  Target theme created: id={tgt_theme_id} name='{target_theme_name}'")

    summary_entry = _theme_entry(source_theme, tgt_theme_id, target_theme_name)
    report_entries.append(summary_entry)

    print("  Fetching asset list from source theme...")
    raw_list = await fetch_asset_list(client, src_theme_id)
    print(f"  Found {len(raw_list)} assets.")

    success_count = 0
    pending_group_files: list[tuple[str, str | None, str | None]] = []

    for asset_meta in raw_list:
        key = asset_meta["key"]
        try:
            asset = await fetch_asset(client, src_theme_id, key)

            if _is_group_file(key):
                value = process_asset_content(key, asset.get("value", ""), mapping, remapper) if "value" in asset else None
                attachment = asset.get("attachment") if "attachment" in asset else None
                pending_group_files.append((key, value, attachment))
                print(f"  [GROUP PENDING] {key}")
                continue

            if "value" in asset:
                processed = process_asset_content(key, asset["value"], mapping, remapper)
                await upload_asset(client, tgt_theme_id, key, value=processed)
            elif "attachment" in asset:
                await upload_asset(client, tgt_theme_id, key, attachment=asset["attachment"])
            else:
                print(f"  [WARN] Asset '{key}' has neither value nor attachment - skipped.")
                report_entries.append(_theme_asset_entry(source_theme, tgt_theme_id, target_theme_name, key, "skipped"))
                continue

            success_count += 1
            print(f"  Uploaded: {key}")
            report_entries.append(_theme_asset_entry(source_theme, tgt_theme_id, target_theme_name, key, "success"))

        except Exception as exc:
            print(f"  [ERROR] Asset '{key}': {exc}")
            report_entries.append(_theme_asset_entry(source_theme, tgt_theme_id, target_theme_name, key, f"error: {exc}"))

    if pending_group_files:
        print(f"\nUploading {len(pending_group_files)} section group file(s)...")
        for key, value, attachment in pending_group_files:
            if value:
                section_types = _extract_section_types(value)
                required_keys = [f"sections/{section_type}.liquid" for section_type in section_types]
                if required_keys:
                    print(f"  {key} requires sections: {section_types}")
                    await _wait_for_sections(client, tgt_theme_id, required_keys)
            try:
                await upload_asset(client, tgt_theme_id, key, value=value, attachment=attachment)
                success_count += 1
                print(f"  Uploaded: {key}")
                report_entries.append(_theme_asset_entry(source_theme, tgt_theme_id, target_theme_name, key, "success"))
            except Exception as exc:
                print(f"  [ERROR] {key}: {exc}")
                report_entries.append(_theme_asset_entry(source_theme, tgt_theme_id, target_theme_name, key, f"error: {exc}"))

    print("\nMigrating shop images (shopify://shop_images/ refs)...")
    shop_uri_map = await migrate_shop_images(client, src_theme_id)

    remapped_uris = {old: new for old, new in shop_uri_map.items() if old != new}
    if remapped_uris:
        print(f"\nRe-uploading JSON files with corrected shop image URIs ({len(remapped_uris)} remappings)...")
        asset_list = await fetch_asset_list(client, src_theme_id)
        json_keys = [asset["key"] for asset in asset_list if asset["key"].endswith(".json")]
        for key in json_keys:
            asset = await fetch_asset(client, src_theme_id, key)
            value = asset.get("value", "")
            if not value:
                continue
            try:
                data = json.loads(value)
                normalized = json.dumps(data)
                if not any(old in normalized for old in remapped_uris):
                    continue
            except (json.JSONDecodeError, ValueError):
                continue
            processed = process_asset_content(key, value, mapping, remapper, shop_uri_map)
            try:
                await upload_asset(client, tgt_theme_id, key, value=processed)
                print(f"  Re-uploaded with fixed URIs: {key}")
            except Exception as exc:
                print(f"  [ERROR] Re-uploading {key}: {exc}")

    print(f"  Theme clone complete. {success_count}/{len(raw_list)} assets uploaded.")
    return {
        "source_theme": source_theme,
        "target_theme_id": tgt_theme_id,
        "target_theme_name": target_theme_name,
        "summary_entry": summary_entry,
        "report_entries": report_entries,
    }


async def clone_theme(
    client: ShopifyClient,
    mapping: IDMapping,
    remapper: DomainRemapper,
) -> list[dict]:
    report_entries: list[dict] = []

    print("Fetching source theme inventory...")
    source_themes = await fetch_source_themes(client)
    ordered_themes = order_source_themes(source_themes)
    existing_names = await fetch_target_theme_names(client)
    main_target_theme_id: int | None = None

    for source_theme in ordered_themes:
        print(f"Cloning theme '{source_theme['name']}' (id={source_theme['id']}, role={source_theme.get('role', '')})...")
        cloned_theme = await clone_single_theme(client, mapping, remapper, source_theme, existing_names)
        report_entries.extend(cloned_theme["report_entries"])
        if source_theme.get("role") == "main":
            main_target_theme_id = cloned_theme["target_theme_id"]
            cloned_theme["summary_entry"]["published_final"] = True

    if main_target_theme_id is None:
        raise RuntimeError("No active theme (role=main) found on source shop.")

    print("Publishing main target theme...")
    await publish_theme(client, main_target_theme_id)
    print("  Main theme published.")

    print(f"Theme phase complete. {len(ordered_themes)} theme(s) cloned.")
    return report_entries
