## Why

Les pages statiques (Contact, À propos, CGV, pages custom) sont absentes de la boutique cible après le clone MVP. Sans elles, la boutique cible est incomplète et non utilisable en production. C'est la prochaine étape V1 définie dans le PRD.

## What Changes

- Ajout d'une nouvelle phase `cloner/phases/pages.py` qui lit toutes les pages statiques de la boutique source et les recrée sur la cible
- Remapping de domaine appliqué sur le contenu HTML de chaque page (`body_html`)
- Clonage des métafields sur les pages via GraphQL (même pattern que produits/collections)
- La table `id_map` est mise à jour avec les correspondances `page_id_source → page_id_cible`
- La phase est intégrée dans l'orchestrateur principal (`main.py`) en position 3 (après collections, avant blogs)
- Le rapport post-clonage inclut les pages dans son inventaire

## Capabilities

### New Capabilities
- `page-cloning`: Lecture, création et remapping des pages statiques Shopify avec leur contenu HTML, métafields, et application du remapping de domaine

### Modified Capabilities
- `domain-remapping`: Le remapping s'applique désormais également au contenu des pages statiques (`body_html`)
- `metafield-cloning`: Extension du clonage de métafields aux objets de type `page`

## Impact

- Nouveau fichier : `cloner/phases/pages.py`
- `main.py` : ajout de l'appel à la phase pages dans l'orchestrateur
- `cloner/report.py` : inclusion des pages dans le rapport final
- Aucune nouvelle dépendance externe
