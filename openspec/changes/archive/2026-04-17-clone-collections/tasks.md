## 1. Récupération des collections source

- [x] 1.1 Implémenter `fetch_custom_collections(client)` — pagination par 250, retourne la liste complète des collections manuelles
- [x] 1.2 Implémenter `fetch_smart_collections(client)` — pagination par 250, retourne la liste complète des collections automatiques
- [x] 1.3 Implémenter `fetch_collects(client, collection_id)` — récupère tous les collects d'une collection manuelle (pagination par 250)

## 2. Création des collections sur la cible

- [x] 2.1 Implémenter `clone_custom_collection(src_client, tgt_client, collection, domain_remapper, id_mapping, image_cache)` — crée la collection manuelle avec `title`, `body_html` remappé, `sort_order`, `published`, `template_suffix`
- [x] 2.2 Implémenter `clone_collection_image(src_collection, tgt_collection_id, tgt_client, image_cache)` — télécharge l'image dans `tmp_images/collection_{id}/`, re-upload via `POST /custom_collections/{id}/image.json`
- [x] 2.3 Implémenter `clone_smart_collection(tgt_client, collection, domain_remapper)` — crée la collection automatique avec `title`, `body_html` remappé, `rules`, `disjunctive`, `sort_order`, `published`, `template_suffix`
- [x] 2.4 Enregistrer la correspondance `id_map["collection"][src_id] = tgt_id` après chaque création réussie et persister `id_map.json`

## 3. Assignation des produits aux collections manuelles

- [x] 3.1 Implémenter `clone_collects(src_client, tgt_client, src_collection_id, tgt_collection_id, id_mapping)` — itère sur les collects source, résout les IDs via `id_mapping`, crée les collects cibles avec `position`
- [x] 3.2 Loguer un warning et ignorer silencieusement les collects dont l'ID produit source est absent de `id_map["product"]` (pas de crash)

## 4. Orchestration de la phase collections

- [x] 4.1 Créer `cloner/phases/collections.py` avec la fonction principale `clone_collections(src_client, tgt_client, id_mapping, domain_remapper, image_cache, progress_callback)` qui exécute dans l'ordre : fetch → création custom → création smart → assignation collects
- [x] 4.2 Brancher `clone_collections` dans `main.py` après la phase produits, en passant les mêmes dépendances (`id_mapping`, `domain_remapper`, `image_cache`)

## 5. Rapport post-clonage

- [x] 5.1 Mettre à jour `cloner/report.py` pour inclure les collections dans `clone_report.json` avec les champs `{ type: "collection", id_source, id_cible, title, statut }`
