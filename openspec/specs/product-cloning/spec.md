## ADDED Requirements

### Requirement: Récupération paginée des produits source
Le système SHALL récupérer tous les produits de la boutique source via `GET /admin/api/2024-01/products.json` avec pagination basée sur curseur (`page_info`), par pages de 250.

#### Scenario: Boutique avec moins de 250 produits
- **WHEN** la boutique source contient 50 produits
- **THEN** le système effectue 1 requête et retourne les 50 produits

#### Scenario: Boutique avec plus de 250 produits
- **WHEN** la boutique source contient 600 produits
- **THEN** le système effectue 3 requêtes successives et retourne les 600 produits au total

### Requirement: Création du produit sur la boutique cible
Le système SHALL créer chaque produit sur la boutique cible via `POST /admin/api/2024-01/products.json` en copiant : `title`, `body_html`, `vendor`, `product_type`, `status`, `tags`, les variantes et leurs `price`, `sku`, `option1/2/3`, `inventory_policy`.

#### Scenario: Produit simple sans variantes multiples
- **WHEN** un produit source a une seule variante avec `price: "29.99"`
- **THEN** le produit cible est créé avec `price: "29.99"` sur sa variante par défaut

#### Scenario: Produit avec plusieurs variantes
- **WHEN** un produit source a 3 variantes avec des prix différents
- **THEN** le produit cible est créé avec les 3 variantes et leurs prix respectifs

#### Scenario: Produit avec statut archivé
- **WHEN** un produit source a `status: "archived"`
- **THEN** le produit cible est créé avec `status: "archived"`

### Requirement: Remapping d'IDs produits et variantes
Le système SHALL enregistrer dans la table de correspondance `{ id_source: id_cible }` l'ID du produit créé, ainsi que les IDs de chaque variante dans l'ordre de création.

#### Scenario: Enregistrement après création réussie
- **WHEN** le produit source ID `111` est créé sur la cible avec ID `999`
- **THEN** `id_map["product"]["111"]` vaut `999` et les variantes sont remappées dans `id_map["variant"]`

### Requirement: Clonage du métafield `caracteristiques` via GraphQL
Le système SHALL lire tous les métafields du produit source via GraphQL (`metafields(first: 100)`) et les écrire sur le produit cible via `metafieldsSet`, en ignorant les types dans `_SKIP_TYPES` (références croisées) et en appliquant le remapping de domaine sur les types dans `_REMAP_TYPES`.

#### Scenario: Produit avec métafield `caracteristiques` renseigné
- **WHEN** le produit source a `custom.caracteristiques` avec valeur `"Coton 100%"`
- **THEN** le produit cible reçoit le même métafield avec la même valeur

#### Scenario: Produit sans métafields
- **WHEN** le produit source n'a aucun métafield
- **THEN** aucune mutation GraphQL `metafieldsSet` n'est effectuée pour ce produit

#### Scenario: Produit avec plusieurs métafields personnalisés
- **WHEN** le produit source a 5 métafields de namespaces et clés variés
- **THEN** les 5 métafields sont écrits sur le produit cible en un seul appel `metafieldsSet`

#### Scenario: Produit avec métafield de type référence
- **WHEN** le produit source a un métafield de type `collection_reference`
- **THEN** ce métafield est ignoré (pas de copie sur la cible)

#### Scenario: Produit avec métafield HTML contenant un lien interne
- **WHEN** `body_html` ou un métafield de type `html` contient `href="https://source.myshopify.com/..."`
- **THEN** le lien est remappé vers le domaine cible avant écriture

### Requirement: Remapping de domaine dans `body_html`
Le système SHALL appliquer le remapping de domaine sur le champ `body_html` de chaque produit avant création sur la cible.

#### Scenario: Description contenant un lien interne
- **WHEN** `body_html` contient `href="https://source-boutique.myshopify.com/collections/soldes"`
- **THEN** le produit cible a `href="https://nouvelle-boutique.myshopify.com/collections/soldes"`
