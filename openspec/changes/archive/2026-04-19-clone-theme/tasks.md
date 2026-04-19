## 1. Récupération du thème source

- [x] 1.1 Implémenter `fetch_active_theme(client, shop)` — appel `GET /themes.json`, filtrer `role == "main"`, lever une erreur si absent
- [x] 1.2 Implémenter `fetch_asset_list(client, shop, theme_id)` — appel `GET /themes/{id}/assets.json`, retourner la liste des keys
- [x] 1.3 Implémenter `fetch_asset(client, shop, theme_id, key)` — appel `GET /themes/{id}/assets.json?asset[key]=<key>`, retourner `value` ou `attachment`

## 2. Création du thème cible

- [x] 2.1 Implémenter `create_theme(client, shop, name)` — appel `POST /themes.json` avec `role: "unpublished"`, retourner l'ID du nouveau thème
- [x] 2.2 Implémenter `publish_theme(client, shop, theme_id)` — appel `PUT /themes/{id}.json` avec `role: "main"`, appelé en fin de phase

## 3. Remapping des contenus

- [x] 3.1 Implémenter `remap_ids_in_json(content_str, id_map)` — parcourir récursivement le JSON désérialisé, remplacer les GIDs (`gid://shopify/(Product|Collection)/\d+`) et les IDs numériques bruts (string) via `id_map`
- [x] 3.2 Implémenter `process_asset_content(key, value, id_map, domain_remapper)` — appliquer `domain_remapper` sur tous les assets textuels ; appliquer `remap_ids_in_json` uniquement sur les fichiers `.json` (templates et `settings_data.json`)

## 4. Upload des assets vers la cible

- [x] 4.1 Implémenter `upload_asset(client, shop, theme_id, key, value=None, attachment=None)` — appel `PUT /themes/{id}/assets.json`, gérer les deux formes (textuel / base64)
- [x] 4.2 Implémenter la boucle principale `clone_theme_assets(client, source_shop, target_shop, source_theme_id, target_theme_id, id_map, domain_remapper)` — itérer sur la liste des assets, fetch → process → upload, logger chaque asset

## 5. Rapport et intégration

- [x] 5.1 Ajouter les entrées de rapport pour chaque asset (`type: "theme_asset"`, `key`, `statut: success/skipped/error`) dans `report.py`
- [x] 5.2 Ajouter l'entrée de rapport pour le thème global (`type: "theme"`, `id_source`, `id_cible`, `statut`)
- [x] 5.3 Intégrer `clone_theme` dans `main.py` comme phase 8, après les collections — passer `id_map` et `domain_remapper` existants

## 6. Fiabilisation section groups et shop images

- [x] 6.1 Gestion des `.group.json` par polling déterministe — `fetch_asset_list_target`, `_extract_section_types`, `_wait_for_sections` — jamais uploadés dans le premier pass, attendus jusqu'à confirmation des sections sur la cible
- [x] 6.2 Migration `shopify://shop_images/` avec vérification post-upload — `_file_exists_on_target` (poll 5s/60s), query GraphQL avec variables (`$q: String!`), logs détaillés par étape
