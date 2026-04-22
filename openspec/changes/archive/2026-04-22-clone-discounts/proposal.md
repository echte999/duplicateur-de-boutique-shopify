## Why

Le clonage des réductions est la dernière fonctionnalité manquante de la V1. Sans elle, la boutique cible n'a aucune promotion configurée, ce qui oblige l'opérateur à les recréer manuellement après chaque clone.

## What Changes

- Ajout de la phase `discounts` dans `cloner/phases/discounts.py` (déjà scaffoldée, à implémenter)
- Lecture de toutes les réductions actives depuis la boutique source via l'API GraphQL Shopify
- Création des réductions équivalentes sur la boutique cible avec les IDs produits/collections remappés
- Remise à zéro des compteurs d'utilisation (`usage_count` → 0) sur chaque réduction clonée
- Intégration de la phase dans l'ordre d'exécution global (étape 7, après les politiques)
- Ajout des entrées dans le rapport post-clonage (`clone_report.json`)

## Capabilities

### New Capabilities

- `discount-cloning` : Clonage des réductions Shopify (codes promo, réductions automatiques) avec remapping des cibles produits/collections et remise à zéro des compteurs d'utilisation

### Modified Capabilities

- `clone-report` : Ajout des entrées de type `discount` dans le rapport post-clonage

## Impact

- Fichier principal modifié : `cloner/phases/discounts.py`
- `main.py` : intégration de la phase discounts dans le pipeline
- `output/clone_report.json` : nouvelles entrées de type `discount`
- Dépend de la table `id_map` (produits et collections déjà remappés)
- API Shopify GraphQL utilisée (PriceRules, DiscountCodes, DiscountNodes)
