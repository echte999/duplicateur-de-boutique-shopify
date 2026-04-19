## Why

Le clonage actuel des métafields est limité au seul champ `custom.caracteristiques` des produits. Toutes les autres ressources (variantes, collections, pages) et tous les autres métafields personnalisés sont ignorés, ce qui rend la copie de boutique incomplète pour tout marchand utilisant des métafields au-delà de ce champ unique.

## What Changes

- Supprimer la logique spécifique à `caracteristiques` dans `phases/products.py`
- Ajouter une fonction générique de clonage de tous les métafields via GraphQL pour : produits, variantes, collections, pages
- Mettre à jour la spec `product-cloning` pour refléter le nouveau comportement (clonage exhaustif au lieu de champ unique)

## Capabilities

### New Capabilities

- `metafield-cloning` : Clonage exhaustif de tous les métafields GraphQL pour les ressources produits, variantes, collections et pages — avec préservation du namespace, de la clé, du type et de la valeur

### Modified Capabilities

- `product-cloning` : Le clonage des métafields passe d'un champ hardcodé (`custom.caracteristiques`) à une découverte dynamique de tous les métafields du produit et de ses variantes

## Impact

- `cloner/phases/products.py` — remplacer la logique `caracteristiques` par appel générique
- `cloner/phases/collections.py` — ajouter le clonage des métafields après création
- `cloner/phases/pages.py` — ajouter le clonage des métafields après création
- Nouveau helper GraphQL réutilisable (dans `cloner/phases/` ou `cloner/`) pour fetch + write métafields
