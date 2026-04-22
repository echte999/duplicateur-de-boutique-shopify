import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch


class ThemeMainOnlyScriptTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        os.environ["SOURCE_SHOP"] = "source-shop.myshopify.com"
        os.environ["SOURCE_TOKEN"] = "src-token"
        os.environ["TARGET_SHOP"] = "target-shop.myshopify.com"
        os.environ["TARGET_TOKEN"] = "dst-token"

    def tearDown(self):
        for key in ("SOURCE_SHOP", "SOURCE_TOKEN", "TARGET_SHOP", "TARGET_TOKEN", "TARGET_CUSTOM_DOMAIN", "SOURCE_CUSTOM_DOMAIN"):
            os.environ.pop(key, None)

    async def test_run_clones_and_publishes_only_active_theme(self):
        import test_theme_main_only as script

        fake_client = AsyncMock()
        fake_client.close = AsyncMock()
        active_theme = {"id": 20, "name": "Live", "role": "main"}
        clone_result = {
            "target_theme_id": 1200,
            "summary_entry": {"type": "theme", "id_source": 20, "published_final": False},
            "report_entries": [{"type": "theme", "id_source": 20, "published_final": False}],
        }

        with patch.object(script, "ShopifyClient", return_value=fake_client), \
             patch.object(script, "IDMapping", return_value=MagicMock()), \
             patch.object(script, "DomainRemapper", return_value=MagicMock()), \
             patch.object(script, "fetch_active_theme", AsyncMock(return_value=active_theme)), \
             patch.object(script, "fetch_target_theme_names", AsyncMock(return_value=set())), \
             patch.object(script, "clone_single_theme", AsyncMock(return_value=clone_result)), \
             patch.object(script, "publish_theme", AsyncMock()) as publish_theme, \
             patch.object(script, "save_report") as save_report:
            await script.run()

        publish_theme.assert_awaited_once_with(fake_client, 1200)
        save_report.assert_called_once_with([{"type": "theme", "id_source": 20, "published_final": True}])
        fake_client.close.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
