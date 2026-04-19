## 1. Métafields des variantes (products.py)

- [x] 1.1 Étendre `_QUERY_PRODUCT_EXTRA` pour inclure les métafields de chaque variante (`variants { edges { node { id metafields(first: 100) { edges { node { ... } } } } } }`)
- [x] 1.2 Mettre à jour `_fetch_product_extra` pour retourner un dict `{ source_variant_id: [metafields] }` en plus des données existantes
- [x] 1.3 Dans `clone_product`, après le remapping des variantes, appeler `_write_metafields` pour chaque variante ayant des métafields (en utilisant le GID cible depuis `id_map["variant"]`)

## 2. Métafields des collections (collections.py)

- [x] 2.1 Ajouter une query GraphQL `_QUERY_COLLECTION_METAFIELDS` pour récupérer les métafields d'une collection source par GID
- [x] 2.2 Ajouter une mutation `_MUTATION_METAFIELDS_SET` (identique à celle de products.py)
- [x] 2.3 Ajouter une fonction `_fetch_collection_metafields(client, source_id)` → liste de métafields
- [x] 2.4 Ajouter une fonction `_write_collection_metafields(client, target_id, metafields, remapper)` qui filtre `_SKIP_TYPES` et remappe `_REMAP_TYPES`
- [x] 2.5 Appeler ces fonctions dans `clone_custom_collection` et dans le flux de clonage des smart collections, après création sur la cible

## 3. Métafields des pages (pages.py)

- [x] 3.1 Ajouter une query GraphQL `_QUERY_PAGE_METAFIELDS` pour récupérer les métafields d'une page source par GID
- [x] 3.2 Ajouter une mutation `_MUTATION_METAFIELDS_SET`
- [x] 3.3 Ajouter une fonction `_fetch_page_metafields(client, source_id)` → liste de métafields
- [x] 3.4 Ajouter une fonction `_write_page_metafields(client, target_id, metafields, remapper)` qui filtre et remappe
- [x] 3.5 Appeler ces fonctions dans la fonction de clonage de page, après création sur la cible

## 4. Mise à jour de la spec product-cloning

- [x] 4.1 Vérifier que la spec archivée `product-cloning` reflète le comportement réel (tous les métafields, pas seulement `caracteristiques`) — déjà couvert par le delta spec dans ce change
