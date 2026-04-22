import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cloner.phases.blogs import fetch_all_blogs, fetch_articles
from cloner.phases.collections import fetch_custom_collections, fetch_smart_collections
from cloner.phases.menus import _GID_TYPE_MAP, _PASSTHROUGH_GID_TYPES, _fetch_all_menus
from cloner.phases.pages import fetch_all_pages
from cloner.phases.products import fetch_all_products
from cloner.phases.theme import fetch_active_theme, fetch_asset, fetch_asset_list

AUDIT_PATH = Path("output/source_health_audit.json")
_THEME_GID_RE = re.compile(r"gid://shopify/(Product|Collection)/(\d+)")
_THEME_HINT_KEYS = {
    "product": "product",
    "product_id": "product",
    "featured_product": "product",
    "collection": "collection",
    "collection_id": "collection",
    "featured_collection": "collection",
}


@dataclass
class AuditResult:
    summary: dict[str, Any]
    issues: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {"summary": self.summary, "issues": self.issues}


def save_audit_result(result: AuditResult) -> None:
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    AUDIT_PATH.write_text(json.dumps(result.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")


async def build_source_index(client: Any, selected_phases: list[str]) -> dict[str, set[str]]:
    required_types: set[str] = set()

    if "menus" in selected_phases:
        required_types.update({"product", "collection", "page", "blog", "article"})
    if "discounts" in selected_phases or "theme" in selected_phases:
        required_types.update({"product", "collection"})

    index: dict[str, set[str]] = {
        "product": set(),
        "collection": set(),
        "page": set(),
        "blog": set(),
        "article": set(),
    }

    if "product" in required_types:
        products = await fetch_all_products(client)
        index["product"] = {str(product["id"]) for product in products}

    if "collection" in required_types:
        custom = await fetch_custom_collections(client)
        smart = await fetch_smart_collections(client)
        index["collection"] = {str(collection["id"]) for collection in [*custom, *smart]}

    if "page" in required_types:
        pages = await fetch_all_pages(client)
        index["page"] = {str(page["id"]) for page in pages}

    if "blog" in required_types or "article" in required_types:
        blogs = await fetch_all_blogs(client)
        index["blog"] = {str(blog["id"]) for blog in blogs}
        if "article" in required_types:
            article_ids: set[str] = set()
            for blog in blogs:
                articles = await fetch_articles(client, int(blog["id"]))
                article_ids.update(str(article["id"]) for article in articles)
            index["article"] = article_ids

    return index


def _make_issue(
    detector: str,
    code: str,
    resource_type: str,
    resource_id: str | int,
    resource_title: str,
    reference_path: str,
    referenced_type: str,
    referenced_id: str | int,
    message: str,
    severity: str = "warning",
) -> dict[str, Any]:
    return {
        "detector": detector,
        "code": code,
        "severity": severity,
        "resource_type": resource_type,
        "resource_id": str(resource_id),
        "resource_title": resource_title,
        "reference_path": reference_path,
        "referenced_type": referenced_type,
        "referenced_id": str(referenced_id),
        "message": message,
    }


def _iter_theme_references(payload: Any, path: str = ""):
    if isinstance(payload, dict):
        for key, value in payload.items():
            child_path = f"{path}.{key}" if path else key
            yield from _iter_theme_references(value, child_path)
            if isinstance(value, str) and value.isdigit():
                referenced_type = _THEME_HINT_KEYS.get(key)
                if referenced_type:
                    yield child_path, referenced_type, value
            elif isinstance(value, int):
                referenced_type = _THEME_HINT_KEYS.get(key)
                if referenced_type:
                    yield child_path, referenced_type, str(value)
    elif isinstance(payload, list):
        for idx, item in enumerate(payload):
            child_path = f"{path}[{idx}]"
            yield from _iter_theme_references(item, child_path)
    elif isinstance(payload, str):
        for match in _THEME_GID_RE.finditer(payload):
            yield path or "$", match.group(1).lower(), match.group(2)


async def detect_menu_issues(client: Any, source_index: dict[str, set[str]]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    menus = await _fetch_all_menus(client, source=True)

    def walk(items: list[dict], menu_title: str, menu_id: str, path_prefix: str) -> None:
        for idx, item in enumerate(items):
            resource_id = item.get("resourceId")
            item_path = f"{path_prefix}[{idx}]"
            if resource_id:
                match = re.match(r"gid://shopify/(\w+)/(\d+)", resource_id)
                if match:
                    gid_type, source_id = match.group(1), match.group(2)
                    if gid_type not in _PASSTHROUGH_GID_TYPES:
                        map_key = _GID_TYPE_MAP.get(gid_type)
                        if map_key is None:
                            issues.append(_make_issue(
                                detector="menus",
                                code="unsupported-menu-resource",
                                resource_type="menu",
                                resource_id=menu_id,
                                resource_title=menu_title,
                                reference_path=f"{item_path}.resourceId",
                                referenced_type=gid_type,
                                referenced_id=source_id,
                                message=f"Menu item points to unsupported resource type '{gid_type}'.",
                            ))
                        elif source_id not in source_index.get(map_key, set()):
                            issues.append(_make_issue(
                                detector="menus",
                                code="missing-menu-resource",
                                resource_type="menu",
                                resource_id=menu_id,
                                resource_title=menu_title,
                                reference_path=f"{item_path}.resourceId",
                                referenced_type=map_key,
                                referenced_id=source_id,
                                message=f"Menu item references missing {map_key} #{source_id}.",
                            ))
            children = item.get("items") or []
            if children:
                walk(children, menu_title, menu_id, f"{item_path}.items")

    for menu in menus:
        walk(menu.get("items", []), menu.get("title", ""), menu["id"].split("/")[-1], "items")

    return issues


async def detect_discount_issues(client: Any, source_index: dict[str, set[str]]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    result = await client.get_source("price_rules.json?limit=250")
    price_rules = result.get("price_rules", [])
    field_map = {
        "entitled_product_ids": "product",
        "entitled_collection_ids": "collection",
        "prerequisite_product_ids": "product",
    }

    for rule in price_rules:
        for field_name, referenced_type in field_map.items():
            for idx, referenced_id in enumerate(rule.get(field_name, []) or []):
                ref_id = str(referenced_id)
                if ref_id in source_index.get(referenced_type, set()):
                    continue
                issues.append(_make_issue(
                    detector="discounts",
                    code="missing-discount-resource",
                    resource_type="price_rule",
                    resource_id=rule["id"],
                    resource_title=rule.get("title", ""),
                    reference_path=f"{field_name}[{idx}]",
                    referenced_type=referenced_type,
                    referenced_id=ref_id,
                    message=f"Discount rule references missing {referenced_type} #{ref_id}.",
                ))

    return issues


async def detect_theme_issues(client: Any, source_index: dict[str, set[str]]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    theme = await fetch_active_theme(client)
    assets = await fetch_asset_list(client, int(theme["id"]))

    for asset_meta in assets:
        key = asset_meta.get("key", "")
        if not key.endswith(".json"):
            continue
        asset = await fetch_asset(client, int(theme["id"]), key)
        raw_value = asset.get("value", "")
        if not raw_value:
            continue
        try:
            payload = json.loads(raw_value)
        except (json.JSONDecodeError, TypeError, ValueError):
            continue

        for reference_path, referenced_type, referenced_id in _iter_theme_references(payload):
            if referenced_id in source_index.get(referenced_type, set()):
                continue
            dedupe_key = (key, referenced_type, referenced_id)
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            issues.append(_make_issue(
                detector="theme",
                code="missing-theme-resource",
                resource_type="theme_asset",
                resource_id=key,
                resource_title=key,
                reference_path=reference_path,
                referenced_type=referenced_type,
                referenced_id=referenced_id,
                message=f"Theme asset references missing {referenced_type} #{referenced_id}.",
            ))

    return issues


def _build_summary(selected_phases: list[str], issues: list[dict[str, Any]]) -> dict[str, Any]:
    selected_detectors = [phase for phase in ("menus", "discounts", "theme") if phase in selected_phases]
    issues_by_detector = {detector: 0 for detector in selected_detectors}
    for issue in issues:
        issues_by_detector[issue["detector"]] = issues_by_detector.get(issue["detector"], 0) + 1

    return {
        "selected_phases": selected_phases,
        "audited_detectors": selected_detectors,
        "total_issues": len(issues),
        "issues_by_detector": issues_by_detector,
    }


async def run_source_health_audit(client: Any, selected_phases: list[str]) -> AuditResult:
    source_index = await build_source_index(client, selected_phases)
    issues: list[dict[str, Any]] = []

    if "menus" in selected_phases:
        issues.extend(await detect_menu_issues(client, source_index))
    if "discounts" in selected_phases:
        issues.extend(await detect_discount_issues(client, source_index))
    if "theme" in selected_phases:
        issues.extend(await detect_theme_issues(client, source_index))

    result = AuditResult(summary=_build_summary(selected_phases, issues), issues=issues)
    save_audit_result(result)
    return result
