## 1. Implémentation de cloner/phases/menus.py

- [x] 1.1 Créer `cloner/phases/menus.py` avec la fonction `clone_menus(src, tgt, mapping, remapper, logger)`
- [x] 1.2 Implémenter `_fetch_all_menus(client)` : GET `/admin/api/2023-10/menus.json` avec pagination si nécessaire
- [x] 1.3 Implémenter `_remap_items(items, mapping, remapper)` : remapping récursif des `subject_id` et des URLs pour les items de type `http`
- [x] 1.4 Implémenter la logique de fallback : item avec `subject_id` introuvable dans `id_map` → conversion en `type: frontpage` + log
- [x] 1.5 Implémenter la création du menu via `POST /menus.json`, avec fallback `PUT` si réponse 422 (handle existant)
- [x] 1.6 Enregistrer le mapping `menu_id` source→cible dans la table de correspondance

## 2. Intégration dans l'orchestrateur

- [x] 2.1 Importer et appeler `clone_menus` dans `main.py` comme phase 5 (après blogs, avant politiques)
- [x] 2.2 Vérifier que la phase menus apparaît dans la barre de progression de l'interface web

## 3. Rapport post-clonage

- [x] 3.1 S'assurer que chaque menu cloné (succès et échec) est enregistré dans `clone_report.json` avec `{ id_source, id_cible, type: "menu", statut }`
- [x] 3.2 Logger les items orphelins convertis en `frontpage` avec leur `subject_id` source dans le rapport
