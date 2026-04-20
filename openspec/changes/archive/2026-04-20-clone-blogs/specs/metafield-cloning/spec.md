## ADDED Requirements

### Requirement: Clonage de tous les métafields des blogs
Le système SHALL lire les métafields de chaque blog source via GraphQL après création sur la cible, et les écrire sur le blog cible via `metafieldsSet`.

Les types dans `_SKIP_TYPES` SHALL être ignorés. Les types dans `_REMAP_TYPES` SHALL passer par le remapping de domaine.

#### Scenario: Blog avec métafield personnalisé
- **WHEN** un blog source a un métafield `custom.description_seo` de type `single_line_text_field`
- **THEN** le même métafield est écrit sur le blog cible avec la même valeur

#### Scenario: Blog sans métafields
- **WHEN** un blog source n'a aucun métafield
- **THEN** aucune mutation GraphQL `metafieldsSet` n'est effectuée pour ce blog

### Requirement: Clonage de tous les métafields des articles
Le système SHALL lire les métafields de chaque article source via GraphQL après création sur la cible, et les écrire sur l'article cible via `metafieldsSet`.

Les types dans `_SKIP_TYPES` SHALL être ignorés. Les types dans `_REMAP_TYPES` SHALL passer par le remapping de domaine.

#### Scenario: Article avec métafield HTML
- **WHEN** un article source a un métafield de type `html` contenant un lien interne
- **THEN** le lien est remappé vers le domaine cible avant écriture sur l'article cible

#### Scenario: Article sans métafields
- **WHEN** un article source n'a aucun métafield
- **THEN** aucune mutation GraphQL n'est effectuée pour cet article

## MODIFIED Requirements

### Requirement: Requête GraphQL des métafields par owner type
Le système SHALL utiliser la query GraphQL `metafields(first: 100)` sur le nœud de la ressource source (Product, ProductVariant, Collection, Page, Blog, Article) pour récupérer tous ses métafields.

#### Scenario: Ressource avec moins de 100 métafields
- **WHEN** une ressource a 15 métafields
- **THEN** tous les 15 métafields sont récupérés en une seule requête

#### Scenario: Ressource avec plus de 100 métafields
- **WHEN** une ressource a 120 métafields
- **THEN** les 100 premiers sont récupérés (comportement acceptable pour le MVP — la pagination n'est pas requise)
