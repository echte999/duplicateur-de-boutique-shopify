import asyncio
import json
import os
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch


class _DummyResponse:
    def raise_for_status(self) -> None:
        return None


class _DummySemaphore:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _FakeHTTP:
    async def get(self, url, headers=None, params=None):
        raise AssertionError(f"Unexpected raw HTTP GET: {url}")


class _FakeClient:
    def __init__(self):
        self._source_base = "https://source-shop/admin/api/2024-01/"
        self._source_headers = {}
        self._semaphore = _DummySemaphore()
        self._http = _FakeHTTP()
        self.closed = False

    async def get_source(self, path: str, params=None):
        if path == "blogs.json":
            return {"blogs": [{"id": 20, "title": "News"}]}
        if path == "price_rules.json?limit=250":
            return {
                "price_rules": [
                    {
                        "id": 30,
                        "title": "Missing collection",
                        "entitled_collection_ids": [999],
                        "entitled_product_ids": [],
                        "prerequisite_product_ids": [],
                    }
                ]
            }
        if path == "themes.json":
            return {"themes": [{"id": 40, "name": "Main", "role": "main"}]}
        if path == "themes/40/assets.json":
            return {"assets": [{"key": "templates/index.json"}]}
        return {}

    async def graphql_source(self, query: str, variables=None):
        if "menus(first: 50" in query:
            return {
                "data": {
                    "menus": {
                        "edges": [
                            {
                                "node": {
                                    "id": "gid://shopify/Menu/1",
                                    "handle": "main-menu",
                                    "title": "Main menu",
                                    "items": [
                                        {
                                            "id": "gid://shopify/MenuItem/1",
                                            "title": "Ghost product",
                                            "type": "PRODUCT",
                                            "url": None,
                                            "resourceId": "gid://shopify/Product/404",
                                            "items": [],
                                        }
                                    ],
                                }
                            }
                        ],
                        "pageInfo": {"hasNextPage": False, "endCursor": None},
                    }
                }
            }
        raise AssertionError(f"Unexpected GraphQL query: {query[:80]}")

    async def close(self):
        self.closed = True


class HealthAuditTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.report_path = Path("output/source_health_audit.json")
        if self.report_path.exists():
            self.report_path.unlink()

    def tearDown(self):
        if self.report_path.exists():
            self.report_path.unlink()

    async def test_run_source_health_audit_detects_menu_discount_and_theme_orphans(self):
        from cloner.health_audit import run_source_health_audit

        client = _FakeClient()

        with patch("cloner.health_audit.fetch_all_products", AsyncMock(return_value=[{"id": 101}])), \
             patch("cloner.health_audit.fetch_custom_collections", AsyncMock(return_value=[{"id": 201, "title": "Summer"}])), \
             patch("cloner.health_audit.fetch_smart_collections", AsyncMock(return_value=[])), \
             patch("cloner.health_audit.fetch_all_pages", AsyncMock(return_value=[{"id": 301, "title": "About"}])), \
             patch("cloner.health_audit.fetch_all_blogs", AsyncMock(return_value=[{"id": 20, "title": "News"}])), \
             patch("cloner.health_audit.fetch_articles", AsyncMock(return_value=[{"id": 21, "title": "Launch"}])), \
             patch("cloner.health_audit.fetch_asset", AsyncMock(return_value={"value": json.dumps({"featured_product": "404", "blocks": [{"product": "gid://shopify/Product/404"}]})})):
            result = await run_source_health_audit(client, ["menus", "discounts", "theme"])

        self.assertEqual(result.summary["total_issues"], 3)
        self.assertEqual(result.summary["issues_by_detector"]["menus"], 1)
        self.assertEqual(result.summary["issues_by_detector"]["discounts"], 1)
        self.assertEqual(result.summary["issues_by_detector"]["theme"], 1)

        codes = {issue["code"] for issue in result.issues}
        self.assertEqual(codes, {"missing-menu-resource", "missing-discount-resource", "missing-theme-resource"})

        report_path = Path("output/source_health_audit.json")
        self.assertTrue(report_path.exists())
        payload = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertEqual(payload["summary"]["total_issues"], 3)
        self.assertEqual(len(payload["issues"]), 3)

    async def test_run_source_health_audit_skips_unselected_detectors(self):
        from cloner.health_audit import run_source_health_audit

        client = _FakeClient()

        with patch("cloner.health_audit.fetch_all_products", AsyncMock(return_value=[])), \
             patch("cloner.health_audit.fetch_custom_collections", AsyncMock(return_value=[])), \
             patch("cloner.health_audit.fetch_smart_collections", AsyncMock(return_value=[])), \
             patch("cloner.health_audit.fetch_all_pages", AsyncMock(return_value=[])), \
             patch("cloner.health_audit.fetch_all_blogs", AsyncMock(return_value=[])), \
             patch("cloner.health_audit.fetch_articles", AsyncMock(return_value=[])), \
             patch("cloner.health_audit.detect_menu_issues", AsyncMock(side_effect=AssertionError("menus should be skipped"))), \
             patch("cloner.health_audit.detect_discount_issues", AsyncMock(side_effect=AssertionError("discounts should be skipped"))), \
             patch("cloner.health_audit.detect_theme_issues", AsyncMock(return_value=[])) as theme_detector:
            result = await run_source_health_audit(client, ["theme"])

        self.assertEqual(result.summary["total_issues"], 0)
        self.assertEqual(theme_detector.await_count, 1)


class MainAuditGateTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        os.environ["SOURCE_SHOP"] = "source-shop.myshopify.com"
        os.environ["SOURCE_TOKEN"] = "src-token"
        os.environ["TARGET_SHOP"] = "target-shop.myshopify.com"
        os.environ["TARGET_TOKEN"] = "dst-token"
        self.report_path = Path("output/source_health_audit.json")
        self.state_path = Path("output/clone_state.json")
        self.map_path = Path("output/id_map.json")
        if self.report_path.exists():
            self.report_path.unlink()
        if self.state_path.exists():
            self.state_path.unlink()
        if self.map_path.exists():
            self.map_path.unlink()

    def tearDown(self):
        for key in ("SOURCE_SHOP", "SOURCE_TOKEN", "TARGET_SHOP", "TARGET_TOKEN", "TARGET_CUSTOM_DOMAIN", "SOURCE_CUSTOM_DOMAIN"):
            os.environ.pop(key, None)
        if self.report_path.exists():
            self.report_path.unlink()
        if self.state_path.exists():
            self.state_path.unlink()
        if self.map_path.exists():
            self.map_path.unlink()

    async def test_run_clone_stops_before_phases_when_audit_is_rejected(self):
        import main

        fake_client = AsyncMock()
        fake_client.get_source.return_value = {"shop": {"name": "Source"}}
        fake_client.get_target.return_value = {"shop": {"name": "Target"}}
        fake_client.close = AsyncMock()

        audit_result = type("AuditResult", (), {"summary": {"total_issues": 1}, "issues": [{"code": "missing-menu-resource"}]})()

        with patch.object(main, "ShopifyClient", return_value=fake_client), \
             patch.object(main, "run_source_health_audit", AsyncMock(return_value=audit_result)), \
             patch.object(main, "confirm_audit_continue", return_value=False), \
             patch.object(main, "load_state", return_value=([], ["products"])), \
             patch.object(main, "clone_all_products", AsyncMock(side_effect=AssertionError("products phase should not run"))), \
             patch.object(main, "save_report") as save_report:
            await main.run_clone(["products"])

        save_report.assert_not_called()
        fake_client.close.assert_awaited_once()

    async def test_run_clone_starts_selected_phase_when_audit_is_clean(self):
        import main

        fake_client = AsyncMock()
        fake_client.get_source.return_value = {"shop": {"name": "Source"}}
        fake_client.get_target.return_value = {"shop": {"name": "Target"}}
        fake_client.close = AsyncMock()

        audit_result = type("AuditResult", (), {"summary": {"total_issues": 0, "issues_by_detector": {}}, "issues": []})()

        with patch.object(main, "ShopifyClient", return_value=fake_client), \
             patch.object(main, "run_source_health_audit", AsyncMock(return_value=audit_result)), \
             patch.object(main, "load_state", return_value=([], ["products"])), \
             patch.object(main, "save_phase_completed"), \
             patch.object(main, "clone_all_products", AsyncMock(return_value=[])) as clone_products, \
             patch.object(main, "cleanup_tmp_images"), \
             patch.object(main, "clear_state"), \
             patch.object(main, "is_clone_complete", return_value=True), \
             patch.object(main, "save_report") as save_report:
            await main.run_clone(["products"])

        clone_products.assert_awaited_once()
        save_report.assert_called_once()
        fake_client.close.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
