## Context

Les produits et leurs variantes sont déjà clonés (phase 1). La table `id_map["product"]` contient toutes les correspondances `id_source → id_cible`. L'étape suivante est de créer les collections sur la boutique cible et d'y assigner les produits clonés.

Shopify distingue deux types de collections :
- **Collections manuelles** (`custom_collections`) : la liste des produits est définie explicitement via l'objet `Collect` (relation produit ↔ collection)
- **Collections automatiques** (`smart_collections`) : les produits y apparaissent selon des règles (conditions basées sur titre, tag, prix, etc.) — Shopify gère l'assignation automatiquement

## Goals / Non-Goals

**Goals:**
- Cloner toutes les collections manuelles avec leur description, image et ordre de tri
- Cloner toutes les collections automatiques avec leurs règles de filtrage
- Assigner les produits remappés aux collections manuelles via `POST /collects`
- Appliquer le remapping de domaine dans les descriptions de collections
- Enregistrer les correspondances d'IDs collection dans `id_map["collection"]`

**Non-Goals:**
- Clonage des métafields de collections (prévu en V1, pas MVP)
- Gestion des collections imbriquées (Shopify ne les supporte pas nativement)
- Forcer la mise à jour de l'assignation des produits dans les smart collections (Shopify le fait automatiquement via ses règles)

## Decisions

### 1. Deux passes : création puis assignation

**Décision** : créer d'abord toutes les collections (custom + smart), puis assigner les produits aux collections manuelles dans une deuxième passe.

**Pourquoi** : les collects (assignations) nécessitent les IDs des collections cibles, qui ne sont connus qu'après création. Une passe unique obligerait à mélanger création et assignation, complexifiant la gestion d'erreurs.

**Alternative écartée** : créer collection + assigns en une seule boucle. Problème : si une collection échoue à la création, les assigns orphelins créeraient des erreurs confuses.

### 2. Smart collections : ne pas recréer les collects

**Décision** : pour les smart collections, copier uniquement les règles (`rules`, `disjunctive`) et laisser Shopify gérer l'assignation des produits automatiquement.

**Pourquoi** : les smart collections sont définies par leurs règles, pas par une liste fixe de produits. Forcer les assigns manuellement serait redondant et potentiellement incohérent avec les règles.

### 3. Images de collection : même flux que les images produits

**Décision** : télécharger l'image de collection source dans `tmp_images/collection_{id}/`, re-uploader via `POST /custom_collections/{id}/image.json`.

**Pourquoi** : cohérence avec le flux images existant du module `products.py`. Réutilise le cache local.

### 4. Ordre de tri des products dans les collections manuelles

**Décision** : copier le champ `sort_order` de la collection source. Pour l'ordre manuel (`sort_order: "manual"`), copier également la position de chaque `Collect` via le champ `position`.

**Pourquoi** : préserver l'ordre d'affichage de la boutique source, qui peut avoir été configuré manuellement par le marchand.

## Risks / Trade-offs

- **[Risque] Rate limiting sur les collects** : une boutique avec 500 collections × 100 produits = 50 000 appels POST /collects. → Mitigation : le semaphore et le backoff du `ShopifyClient` gèrent cela, mais le clonage peut être long.
- **[Risque] Produit non remappé** : si un produit de la collection source n'a pas été cloné (erreur phase 1), son ID n'est pas dans `id_map`. → Mitigation : logger un warning et sauter le collect plutôt que de planter.
- **[Trade-off] Smart collections et délai d'indexation** : après création des règles, Shopify peut mettre quelques secondes à indexer les produits correspondants. Le rapport peut temporairement afficher 0 produits dans une smart collection. Acceptable pour un outil de clonage one-shot.
