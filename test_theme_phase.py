import unittest
from unittest.mock import AsyncMock, MagicMock, patch


class ThemePhaseTests(unittest.IsolatedAsyncioTestCase):
    async def test_clone_theme_clones_all_source_themes_and_publishes_only_main(self):
        from cloner.phases import theme

        client = object()
        mapping = MagicMock()
        remapper = MagicMock()
        source_themes = [
            {"id": 10, "name": "Summer", "role": "unpublished"},
            {"id": 20, "name": "Live", "role": "main"},
        ]
        cloned_theme_ids: list[int] = []

        async def fake_clone_single_theme(client_arg, mapping_arg, remapper_arg, source_theme, existing_names):
            self.assertIs(client_arg, client)
            self.assertIs(mapping_arg, mapping)
            self.assertIs(remapper_arg, remapper)
            cloned_theme_ids.append(source_theme["id"])
            summary_entry = {"type": "theme", "id_source": source_theme["id"], "published_final": False}
            return {
                "target_theme_id": source_theme["id"] + 1000,
                "summary_entry": summary_entry,
                "report_entries": [summary_entry],
            }

        with patch.object(theme, "fetch_active_theme", AsyncMock(side_effect=AssertionError("active-theme shortcut should not be used"))), \
             patch.object(theme, "fetch_source_themes", AsyncMock(return_value=source_themes), create=True), \
             patch.object(theme, "fetch_target_theme_names", AsyncMock(return_value=set())), \
             patch.object(theme, "clone_single_theme", AsyncMock(side_effect=fake_clone_single_theme), create=True), \
             patch.object(theme, "publish_theme", AsyncMock()) as publish_theme:
            entries = await theme.clone_theme(client, mapping, remapper)

        self.assertEqual(cloned_theme_ids, [10, 20])
        publish_theme.assert_awaited_once_with(client, 1020)
        self.assertEqual(
            entries,
            [
                {"type": "theme", "id_source": 10, "published_final": False},
                {"type": "theme", "id_source": 20, "published_final": True},
            ],
        )


class ThemeSelectionLabelTests(unittest.TestCase):
    def test_theme_phase_label_mentions_all_installed_themes(self):
        from cloner.phase_selector import PHASE_LABELS

        self.assertEqual(PHASE_LABELS["theme"], "Tous les themes installes")


class ThemeHelperTests(unittest.IsolatedAsyncioTestCase):
    def test_build_target_theme_name_uses_deterministic_suffix_on_collision(self):
        from cloner.phases.theme import build_target_theme_name

        name = build_target_theme_name(
            {"id": 42, "name": "Live"},
            {"Live", "Live (source 42)"},
        )

        self.assertEqual(name, "Live (source 42-2)")

    async def test_clone_single_theme_adds_theme_context_to_asset_entries(self):
        from cloner.phases import theme

        client = object()
        mapping = MagicMock()
        remapper = MagicMock()
        remapper.remap.return_value = None
        source_theme = {"id": 50, "name": "Live", "role": "main"}

        with patch.object(theme, "create_theme", AsyncMock(return_value=1500)), \
             patch.object(theme, "fetch_asset_list", AsyncMock(return_value=[{"key": "templates/index.json"}])), \
             patch.object(theme, "fetch_asset", AsyncMock(return_value={"value": "{}"})), \
             patch.object(theme, "upload_asset", AsyncMock()), \
             patch.object(theme, "migrate_shop_images", AsyncMock(return_value={})):
            result = await theme.clone_single_theme(client, mapping, remapper, source_theme, set())

        mapping.set.assert_called_once_with("theme", 50, 1500)
        self.assertEqual(result["summary_entry"]["target_title"], "Live")
        self.assertEqual(
            result["report_entries"][1],
            {
                "type": "theme_asset",
                "theme_source_id": 50,
                "theme_target_id": 1500,
                "theme_name": "Live",
                "theme_role_source": "main",
                "key": "templates/index.json",
                "statut": "success",
            },
        )


class ThemeMappingTests(unittest.TestCase):
    def test_id_mapping_initializes_theme_bucket(self):
        from cloner.mapping import IDMapping

        mapping = IDMapping()

        self.assertIn("theme", mapping._map)


if __name__ == "__main__":
    unittest.main()
