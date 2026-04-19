## Context

Le code `phases/products.py` clone déjà tous les métafields produit de manière générique via GraphQL (la spec `product-cloning` est donc en retard sur le code — elle décrit encore `caracteristiques` comme le seul champ). Les variantes, collections et pages n'ont aucun clonage de métafields. Un helper `_write_metafields()` existe déjà dans `products.py` mais est privé au module.

## Goals / Non-Goals

**Goals:**
- Cloner tous les métafields des variantes (via une requête GraphQL qui étend `_QUERY_PRODUCT_EXTRA`)
- Cloner tous les métafields des collections dans `phases/collections.py`
- Cloner tous les métafields des pages dans `phases/pages.py`
- Mettre à jour la spec `product-cloning` pour refléter le comportement réel (tous les métafields, pas seulement `caracteristiques`)

**Non-Goals:**
- Créer un module partagé pour `_write_metafields` — la duplication limitée entre 3 fichiers est acceptable pour rester simple
- Cloner les métafields des blogs/articles (hors périmètre MVP)
- Cloner les métafields de type référence (déjà exclus via `_SKIP_TYPES`)

## Decisions

### 1. Pas d'extraction du helper dans un module commun

**Décision** : Dupliquer la logique `_write_metafields` dans `collections.py` et `pages.py` plutôt que de créer un `cloner/metafields.py` partagé.

**Rationale** : Les 3 modules ont des besoins légèrement différents (owner type GID, owner type GraphQL). Une extraction prématurée crée du couplage sans réduire suffisamment la duplication (< 30 lignes par module).

### 2. Métafields variantes via extension de la requête produit existante

**Décision** : Étendre `_QUERY_PRODUCT_EXTRA` pour inclure les métafields de chaque variante en même temps que le fetch produit.

**Rationale** : Évite un appel GraphQL supplémentaire par produit. Les variantes sont déjà disponibles dans la réponse produit.

### 3. Owner type GID pour les mutations

**Décision** : Utiliser le GID Shopify (`gid://shopify/<Type>/<id>`) comme `ownerId` dans `metafieldsSet`.

**Rationale** : C'est le format requis par l'API GraphQL Shopify pour tous les types de ressources (Product, ProductVariant, Collection, Page).

## Risks / Trade-offs

- **Métafields de définitions manquantes sur la cible** → La mutation `metafieldsSet` crée les métafields même sans définition préalable ; pas de risque de blocage
- **Volume** : Une boutique avec 1000 produits × 50 variantes × métafields → requêtes GraphQL nombreuses → le rate limiting existant dans `client.py` absorbe ceci via backoff
- **Métafields `app--*` (namespaces d'apps)** → Ces métafields sont créés par des apps tierces qui n'existent pas sur la cible ; inclure le namespace complet dans la copie risque de créer des métafields orphelins. Mitigation : les copier quand même (la valeur est préservée même si l'app est absente)
