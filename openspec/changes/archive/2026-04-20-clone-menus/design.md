## Context

L'API Shopify expose les menus via REST (`/admin/api/2023-10/menus.json`). Chaque menu contient une liste d'items hiérarchiques, chacun ayant un `type` (collection, product, page, article, http, frontpage, etc.) et un `subject_id` ou `url` pointant vers la ressource cible.

Les menus doivent être clonés **après** toutes les ressources contenu (produits, collections, pages, articles) pour que les IDs remappés soient disponibles. Le thème utilise les **handles** des menus (ex: `main-menu`, `footer`) dans `settings_data.json` — ces handles étant préservés lors du clonage, aucune injection supplémentaire dans le thème n'est nécessaire.

## Goals / Non-Goals

**Goals:**
- Cloner tous les menus (principale, footer, custom) avec leur structure hiérarchique complète
- Remapper les `subject_id` des items vers les IDs cibles via `id_map`
- Remapper les URLs internes dans les items de type `http` ou `url`
- Préserver les handles des menus pour compatibilité avec le thème

**Non-Goals:**
- Modifier `settings_data.json` du thème (les handles sont conservés, le thème ne change pas)
- Cloner les menus de l'interface admin Shopify (non exposés via API publique)
- Gérer des menus imbriqués à plus de 2 niveaux (limite Shopify)

## Decisions

### Remapping des `subject_id`

Chaque item de menu avec un `type` non-`http`/`frontpage` référence une ressource par `subject_id`. La table `id_map` contient les correspondances pour tous les types supportés.

**Stratégie** : pour chaque item, si `type` est `collection`, `product`, `page`, ou `article`, on cherche `id_map.get(subject_id)`. Si introuvable (ressource orpheline), on convertit l'item en `type: frontpage` pour éviter un menu cassé plutôt que de bloquer le clonage.

Alternative rejetée : ignorer l'item → perte de structure visible dans le menu.

### Gestion des items `http` avec URL interne

Les items `type: http` contiennent une URL libre. Si l'URL contient le domaine source, elle doit être remappée via `domain.remap()`.

### Ordre de création

Les items enfants (`items` imbriqués) sont inclus dans le payload de création du menu parent — l'API Shopify crée toute l'arborescence en une seule requête `POST /menus.json`.

## Risks / Trade-offs

- **Items orphelins** → Mitigation : fallback vers `frontpage`, loggé dans le rapport
- **Handle déjà existant sur la cible** : si la cible a déjà un menu avec le même handle (boutique partiellement peuplée), l'API retourne une erreur 422 → Mitigation : tenter un `PUT` si le `POST` échoue avec 422
- **Limite API non documentée sur le nombre d'items** : pour les grands menus, risque de timeout → Mitigation : le rate limiter existant gère les retries
