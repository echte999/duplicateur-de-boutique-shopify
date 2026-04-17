## ADDED Requirements

### Requirement: Récupération paginée des collections source
Le système SHALL récupérer toutes les collections manuelles (`GET /admin/api/2024-01/custom_collections.json`) et automatiques (`GET /admin/api/2024-01/smart_collections.json`) de la boutique source, par pages de 250.

#### Scenario: Boutique avec collections manuelles uniquement
- **WHEN** la boutique source a 10 collections manuelles et 0 automatiques
- **THEN** le système retourne 10 collections de type `custom` et 0 de type `smart`

#### Scenario: Boutique avec les deux types
- **WHEN** la boutique source a 5 collections manuelles et 3 automatiques
- **THEN** le système retourne les 8 collections avec leur type respectif

#### Scenario: Pagination au-delà de 250 collections
- **WHEN** la boutique source contient 300 collections manuelles
- **THEN** le système effectue 2 requêtes successives et retourne les 300 collections

### Requirement: Création des collections manuelles sur la cible
Le système SHALL créer chaque collection manuelle sur la boutique cible via `POST /admin/api/2024-01/custom_collections.json` en copiant : `title`, `body_html` (après remapping de domaine), `sort_order`, `published`, `template_suffix`.

#### Scenario: Collection avec titre et description
- **WHEN** une collection source a `title: "Soldes"` et `body_html: "<p>Nos offres</p>"`
- **THEN** la collection cible est créée avec les mêmes valeurs

#### Scenario: Collection avec image
- **WHEN** une collection source a une image associée
- **THEN** l'image est téléchargée dans `tmp_images/collection_{id}/`, re-uploadée sur la cible et l'URL est mise à jour

#### Scenario: Remapping de domaine dans la description
- **WHEN** `body_html` contient `href="https://source.myshopify.com/products/exemple"`
- **THEN** la collection cible a `href="https://target.myshopify.com/products/exemple"`

### Requirement: Création des collections automatiques sur la cible
Le système SHALL créer chaque collection automatique via `POST /admin/api/2024-01/smart_collections.json` en copiant : `title`, `body_html` (après remapping), `rules`, `disjunctive`, `sort_order`, `published`, `template_suffix`.

#### Scenario: Collection avec règle sur les tags
- **WHEN** une smart collection a `rules: [{"column": "tag", "relation": "equals", "condition": "promo"}]`
- **THEN** la collection cible est créée avec la même règle et Shopify assigne automatiquement les produits tagués `promo`

#### Scenario: Collection avec plusieurs règles en OR
- **WHEN** une smart collection a `disjunctive: true` et deux règles de filtrage
- **THEN** la collection cible est créée avec `disjunctive: true` et les mêmes règles

### Requirement: Enregistrement des IDs collections dans la table de correspondance
Le système SHALL enregistrer dans `id_map["collection"]` la correspondance `{ id_source: id_cible }` immédiatement après chaque collection créée avec succès.

#### Scenario: Enregistrement après création réussie
- **WHEN** la collection source ID `200` est créée sur la cible avec ID `800`
- **THEN** `id_map["collection"]["200"]` vaut `"800"` et `id_map.json` est persisté sur disque

### Requirement: Assignation des produits aux collections manuelles
Le système SHALL récupérer tous les `Collect` de chaque collection manuelle source (`GET /admin/api/2024-01/collects.json?collection_id={id}`) et les recréer sur la cible avec les IDs remappés via `POST /admin/api/2024-01/collects.json`.

#### Scenario: Collection manuelle avec 3 produits
- **WHEN** une collection source contient les produits IDs `[1, 2, 3]`
- **THEN** 3 collects sont créés sur la cible avec les IDs cibles correspondants de `id_map["product"]`

#### Scenario: Produit absent de la table de correspondance
- **WHEN** un collect source référence un produit ID qui n'est pas dans `id_map["product"]`
- **THEN** le collect est ignoré, un warning est loggé avec l'ID source manquant, et le reste des collects est traité

#### Scenario: Préservation de l'ordre manuel
- **WHEN** un collect source a `position: 3`
- **THEN** le collect cible est créé avec `position: 3`
