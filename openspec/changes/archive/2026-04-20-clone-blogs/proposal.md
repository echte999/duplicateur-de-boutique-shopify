## Why

La V1 du clonage vise une boutique complète. Les articles de blog et les collections de blog (blogs) sont du contenu éditorial visible par les visiteurs — leur absence crée des pages manquantes et des menus cassés. C'est la 3e feature de la V1, après les pages statiques.

## What Changes

- Clonage des blogs (collections de blog) : titre, commentaires activés/désactivés, tags
- Clonage des articles : titre, contenu HTML, auteur, tags, image mise en avant, statut (publié/brouillon), date de publication
- Remapping de domaine dans le contenu HTML des articles
- Clonage des métafields sur les blogs et les articles (GraphQL)
- Mise en table de correspondance des IDs blogs et articles (`blog_id`, `article_id`)

## Capabilities

### New Capabilities
- `blog-cloning`: Clonage des blogs Shopify (collections de blog) et de leurs articles, avec remapping de domaine dans le contenu HTML, re-upload des images mise en avant, et clonage des métafields via GraphQL

### Modified Capabilities
- `metafield-cloning`: Ajout du support des types `blog` et `article` en plus des types déjà gérés (produit, variante, collection, page)

## Impact

- Nouveau fichier : `cloner/phases/blogs.py`
- `cloner/phases/metafields.py` (ou logique équivalente) : ajout des owner types `blog` et `article`
- `main.py` : ajout de la phase blogs dans l'orchestration (après les pages statiques, étape 4)
- `output/id_map.json` : nouvelles entrées pour les blogs et articles
- `output/clone_report.json` : nouvelles lignes de rapport pour blogs et articles
- Dépendance sur `cloner/domain.py` pour le remapping HTML
- Dépendance sur `cloner/client.py` pour les appels REST et GraphQL
