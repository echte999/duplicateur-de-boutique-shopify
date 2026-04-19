## ADDED Requirements

### Requirement: Clonage de tous les métafields des variantes
Le système SHALL lire les métafields de chaque variante du produit source via GraphQL (en étendant la requête produit existante) et les écrire sur les variantes correspondantes de la boutique cible, en utilisant les IDs remappés depuis la table de correspondance.

Les types dans `_SKIP_TYPES` (références croisées : `product_reference`, `collection_reference`, etc.) SHALL être ignorés. Les types dans `_REMAP_TYPES` (`html`, `url`, `json_string`) SHALL passer par le remapping de domaine avant écriture.

#### Scenario: Variante avec métafields personnalisés
- **WHEN** une variante source a 2 métafields (`custom.taille_guide` et `custom.matiere`)
- **THEN** les mêmes métafields sont écrits sur la variante cible avec les mêmes valeurs et types

#### Scenario: Variante sans métafields
- **WHEN** une variante source n'a aucun métafield
- **THEN** aucune mutation GraphQL `metafieldsSet` n'est effectuée pour cette variante

#### Scenario: Variante avec métafield de type référence
- **WHEN** une variante source a un métafield de type `product_reference`
- **THEN** ce métafield est ignoré (pas de copie sur la cible)

### Requirement: Clonage de tous les métafields des collections
Le système SHALL lire les métafields de chaque collection source via GraphQL après création sur la cible, et les écrire sur la collection cible via `metafieldsSet`.

Les types dans `_SKIP_TYPES` SHALL être ignorés. Les types dans `_REMAP_TYPES` SHALL passer par le remapping de domaine.

#### Scenario: Collection avec métafield SEO
- **WHEN** une collection source a un métafield `custom.seo_description` de type `single_line_text_field`
- **THEN** le même métafield est écrit sur la collection cible avec la même valeur

#### Scenario: Collection sans métafields
- **WHEN** une collection source n'a aucun métafield
- **THEN** aucune mutation GraphQL n'est effectuée pour cette collection

#### Scenario: Collection avec métafield HTML contenant un lien interne
- **WHEN** une collection source a un métafield de type `html` contenant `href="https://source.myshopify.com/..."`
- **THEN** le lien est remappé vers le domaine cible avant écriture

### Requirement: Clonage de tous les métafields des pages
Le système SHALL lire les métafields de chaque page source via GraphQL après création sur la cible, et les écrire sur la page cible via `metafieldsSet`.

Les types dans `_SKIP_TYPES` SHALL être ignorés. Les types dans `_REMAP_TYPES` SHALL passer par le remapping de domaine.

#### Scenario: Page avec métafield personnalisé
- **WHEN** une page source a un métafield `custom.auteur` de type `single_line_text_field`
- **THEN** le même métafield est écrit sur la page cible avec la même valeur

#### Scenario: Page sans métafields
- **WHEN** une page source n'a aucun métafield
- **THEN** aucune mutation GraphQL n'est effectuée pour cette page

### Requirement: Requête GraphQL des métafields par owner type
Le système SHALL utiliser la query GraphQL `metafields(first: 100)` sur le nœud de la ressource source (Product, ProductVariant, Collection, Page) pour récupérer tous ses métafields.

#### Scenario: Ressource avec moins de 100 métafields
- **WHEN** une ressource a 15 métafields
- **THEN** tous les 15 métafields sont récupérés en une seule requête

#### Scenario: Ressource avec plus de 100 métafields
- **WHEN** une ressource a 120 métafields
- **THEN** les 100 premiers sont récupérés (comportement acceptable pour le MVP — la pagination n'est pas requise)
