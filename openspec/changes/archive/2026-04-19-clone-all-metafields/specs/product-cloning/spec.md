## MODIFIED Requirements

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
