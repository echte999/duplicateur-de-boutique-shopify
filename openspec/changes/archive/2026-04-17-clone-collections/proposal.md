## Why

Le clonage des collections est la deuxième phase du MVP : sans elles, la boutique cible n'a pas de navigation ni de catalogue structuré. Les produits clonés lors de la phase 1 doivent être assignés aux collections de la boutique cible avec les IDs remappés.

## What Changes

- Nouveau module `cloner/phases/collections.py` : récupération, création et assignation des collections manuelles et automatiques
- Intégration avec la table de correspondance IDs existante (`mapping.py`) pour résoudre les IDs produits source → cible
- Support des règles de collections automatiques (conditions basées sur les tags, prix, titre, etc.)
- Remapping de domaine dans les descriptions de collections via `domain.py`
- Rapport post-clonage enrichi avec les collections et leurs assignations

## Capabilities

### New Capabilities

- `collection-cloning` : Clonage des collections manuelles et automatiques avec assignation des produits remappés, respect des règles de tri et remapping de domaine dans les descriptions

### Modified Capabilities

- `id-mapping` : Ajout de l'enregistrement des correspondances d'IDs pour les collections (type `collection`)

## Impact

- Nouveau fichier : `cloner/phases/collections.py`
- Fichier modifié : `main.py` — ajout de la phase collections dans l'orchestrateur
- Fichier modifié : `cloner/report.py` — ajout des collections dans le rapport final
- Dépend de : `cloner/phases/products.py` (les produits doivent exister avant l'assignation)
- Utilise : `cloner/client.py`, `cloner/mapping.py`, `cloner/domain.py`
- API Shopify REST : `GET /collections`, `POST /custom_collections`, `POST /smart_collections`, `POST /collects`
