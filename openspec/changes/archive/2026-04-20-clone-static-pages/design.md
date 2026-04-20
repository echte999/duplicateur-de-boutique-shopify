## Context

Le MVP a implémenté produits, collections et thème. Les pages statiques (Contact, À propos, CGV, pages custom) sont la prochaine étape V1. L'API Shopify REST expose `/admin/api/2024-01/pages.json` pour la lecture et la création. Les métafields sur les pages utilisent le même pattern GraphQL déjà utilisé pour produits et collections.

La phase `pages.py` s'insère en position 3 dans l'ordre de clonage, après collections et avant blogs — ses dépendances (ID mapping, client HTTP, domain remapper) existent déjà.

## Goals / Non-Goals

**Goals:**
- Cloner toutes les pages statiques avec leur contenu HTML (`body_html`), titre, handle, statut publié
- Appliquer le remapping de domaine sur `body_html`
- Cloner les métafields de chaque page via GraphQL
- Alimenter la table `id_map` avec les correspondances page
- Inclure les pages dans le rapport post-clonage

**Non-Goals:**
- Gestion des redirects liés aux handles de pages
- Préservation des dates de publication exactes
- Pages protégées par mot de passe (non exposées via l'API Admin REST)

## Decisions

### Décision 1 : Pagination via `limit=250`
L'API REST Shopify pour les pages supporte `limit` (max 250) et le header `Link` pour la pagination. On utilise le même pattern de pagination déjà implémenté dans `products.py` et `collections.py` — boucle sur le header `Link: <...>; rel="next"`.

**Alternative écartée** : GraphQL Storefront — inutile ici, l'API Admin REST est suffisante pour les pages.

### Décision 2 : Même structure que `collections.py` pour les métafields
On réutilise la fonction `clone_metafields(source_gid, target_gid, client)` déjà présente dans `metafield-cloning`. Le GID GraphQL d'une page est `gid://shopify/OnlineStorePage/{id}`.

**Alternative écartée** : Inline dans `pages.py` — la factorisation existe déjà, autant l'utiliser.

### Décision 3 : Champ `handle` recopié tel quel
Le handle d'une page (ex : `contact`, `a-propos`) est recopié sans transformation. Si un handle existe déjà sur la cible, Shopify le déduplique automatiquement (ajout d'un suffixe numérique). C'est acceptable pour l'usage one-shot.

## Risks / Trade-offs

- **Rate limit** : si la boutique source a des centaines de pages avec métafields, les appels GraphQL peuvent saturer le quota. → Mitigation : le client existant gère déjà le backoff sur `extensions.cost`.
- **Handle déjà pris** : la page cible peut recevoir un handle différent du handle source si la cible a déjà une page avec ce nom. → Acceptable ; le rapport signalera la correspondance `id_source → id_cible`.
- **Images dans `body_html`** : les images embarquées dans le contenu HTML des pages pointent vers le CDN source. Le remapping de domaine remplacera les URLs si elles contiennent le domaine source, mais pas les images hébergées sur des CDN tiers. → Hors scope pour cette itération.
