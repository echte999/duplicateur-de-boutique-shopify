## Context

Le clonage des blogs suit le même patron que les pages statiques (déjà implémenté). Dans Shopify, un "blog" est une collection de blog (ex : "Actualités", "Conseils"), et chaque blog contient des articles. L'API REST expose `/blogs.json` et `/blogs/{id}/articles.json`. Les métafields sont gérés via GraphQL, exactement comme pour les pages.

## Goals / Non-Goals

**Goals:**
- Cloner tous les blogs (collections de blog) et leurs articles de la boutique source vers la cible
- Remapper le domaine dans le contenu HTML des articles
- Re-uploader les images mises en avant des articles via le cache local
- Cloner les métafields sur les blogs et les articles (owner types `Blog` et `Article` en GraphQL)
- Alimenter la table `id_map.json` avec les correspondances blogs et articles

**Non-Goals:**
- Clonage des commentaires d'articles
- Pagination au-delà de 250 blogs ou articles (limite API Shopify — suffisant pour l'usage prévu)
- Gestion des redirections d'URL d'articles

## Decisions

### 1. Ordre de clonage : blogs avant menus
Les menus peuvent pointer vers des blogs et des articles. Le clonage des blogs doit donc précéder le clonage des menus. L'ordre existant (étape 4 dans l'orchestration) est conservé.

### 2. Réutilisation du patron pages.py
Le module `blogs.py` suit exactement la même structure que `pages.py` : fetch REST → create REST → métafields GraphQL. Cela évite une nouvelle abstraction — trois fichiers similaires valent mieux qu'un générateur complexe.

### 3. Images des articles : même flux que les produits
Les images mise en avant d'articles (`image.src`) passent par le même flux `tmp_images/` que les images produits : téléchargement → cache local → re-upload REST. L'ID de l'article source sert de clé de répertoire.

### 4. Métafields : extension de la logique existante
Plutôt que de dupliquer la logique de métafields, `blogs.py` appellera directement la fonction utilitaire de clonage de métafields (déjà utilisée dans `pages.py` et `collections.py`) en passant les owner types GraphQL `Blog` et `Article`.

## Risks / Trade-offs

- **Articles sans image mise en avant** → le champ `image` peut être `null`, à vérifier avant tentative de download
- **Contenu HTML riche dans les articles** → le remapping de domaine doit couvrir tous les attributs `href`/`src`, comme pour les pages
- **Limite 250 articles par blog** → acceptable pour l'usage prévu, à documenter
