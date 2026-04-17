## ADDED Requirements

### Requirement: Téléchargement des images vers le cache local
Le système SHALL télécharger chaque image d'un produit source depuis son URL CDN Shopify vers `tmp_images/{product_id_source}/{filename}` où `filename` est le dernier segment de l'URL avant les paramètres de query.

#### Scenario: Téléchargement d'une nouvelle image
- **WHEN** l'image `https://cdn.shopify.com/s/files/.../image.jpg?v=123` n'existe pas localement
- **THEN** le fichier est téléchargé et sauvegardé dans `tmp_images/{product_id}/image.jpg`

#### Scenario: Image déjà en cache
- **WHEN** `tmp_images/{product_id}/image.jpg` existe déjà sur disque
- **THEN** le téléchargement est ignoré et le fichier local est utilisé directement

### Requirement: Re-upload des images vers la boutique cible
Le système SHALL uploader chaque image depuis le cache local vers la boutique cible via `POST /admin/api/2024-01/products/{id_cible}/images.json` avec le contenu binaire de l'image encodé en base64.

#### Scenario: Upload réussi
- **WHEN** une image est uploadée vers la boutique cible
- **THEN** l'URL CDN retournée par l'API cible est stockée et la position de l'image est préservée

#### Scenario: Image principale préservée
- **WHEN** un produit source a une image marquée comme principale (position 1)
- **THEN** le produit cible a la même image en position 1

### Requirement: Création du répertoire cache
Le système SHALL créer le répertoire `tmp_images/{product_id}/` s'il n'existe pas avant tout téléchargement.

#### Scenario: Premier téléchargement d'un produit
- **WHEN** aucun répertoire `tmp_images/{product_id}/` n'existe
- **THEN** le répertoire est créé automatiquement avant le téléchargement
