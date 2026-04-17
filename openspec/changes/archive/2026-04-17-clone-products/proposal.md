## Why

Le MVP du copieur de boutique Shopify doit cloner les produits en premier, car toutes les autres ressources (collections, menus, thème) en dépendent pour le remapping d'IDs. Sans cette phase, aucun clonage complet n'est possible.

## What Changes

- Nouveau module `cloner/phases/products.py` qui récupère tous les produits de la boutique source via l'API REST Shopify et les recrée sur la boutique cible
- Clonage des variantes et de leurs prix, SKU et options dans le même appel
- Téléchargement des images produits vers `tmp_images/{product_id}/` et re-upload vers la boutique cible
- Récupération et écriture du métafield `caracteristiques` via l'API GraphQL
- Remapping de domaine appliqué aux descriptions HTML des produits
- Enregistrement des correspondances `id_source → id_cible` dans `mapping.py` après chaque produit créé
- Nouveau module `cloner/client.py` avec rate limiting REST (bucket 40 appels, backoff exponentiel sur 429)
- Nouveau module `cloner/mapping.py` pour persister la table de correspondance dans `output/id_map.json`
- Nouveau module `cloner/domain.py` pour le remplacement chirurgical des domaines dans les contenus HTML/JSON

## Capabilities

### New Capabilities

- `product-cloning`: Clonage complet d'un produit Shopify (titre, description, images, prix, variantes, statut, métafield `caracteristiques`) depuis une boutique source vers une boutique cible
- `image-cache`: Téléchargement et stockage local des images dans `tmp_images/`, avec réutilisation du cache si le fichier existe déjà
- `id-mapping`: Table de correspondance `{ id_source: id_cible }` construite en temps réel et persistée dans `output/id_map.json`
- `domain-remapping`: Remplacement chirurgical du domaine source par le domaine cible dans tous les contenus textuels
- `shopify-client`: Client HTTP async avec rate limiting REST et retry backoff exponentiel

### Modified Capabilities

## Impact

- Crée les fichiers : `cloner/__init__.py`, `cloner/client.py`, `cloner/mapping.py`, `cloner/domain.py`, `cloner/phases/__init__.py`, `cloner/phases/products.py`
- Dépendances Python : `httpx` (client HTTP async), aucune nouvelle dépendance au-delà du stack défini
- Expose l'API Shopify REST `GET /products.json` (source) et `POST /products.json` (cible), ainsi que GraphQL pour les métafields
- Crée les répertoires `tmp_images/` et `output/` s'ils n'existent pas
