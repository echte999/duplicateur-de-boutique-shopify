## Context

L'API Shopify REST expose les politiques du site via `GET /admin/api/2024-01/policies.json`. Les politiques sont en lecture seule au sens où Shopify les gère par type (`refund_policy`, `privacy_policy`, `terms_of_service`, `shipping_policy`, `legal_notice`, `subscription_policy`). Chaque politique a un `body` en HTML qui peut contenir le domaine source et le nom de la boutique source.

La phase `domain-remapping` (`cloner/domain.py`) remplace déjà les domaines dans les contenus HTML. Il faut l'étendre pour remplacer aussi le nom de la boutique source (le "shop name" affiché dans les politiques légales).

Le nom de la boutique source est récupéré depuis `GET /admin/api/2024-01/shop.json` (champ `name`). Le nom de la boutique cible est disponible de la même manière.

## Goals / Non-Goals

**Goals:**
- Lire toutes les politiques de la boutique source
- Appliquer le remapping domaine + nom de boutique sur le `body` HTML
- Écrire les politiques remappées sur la boutique cible via `PUT /admin/api/2024-01/policies/<type>.json` — ou via l'endpoint consolidé si disponible
- Inclure les politiques dans le rapport post-clonage

**Non-Goals:**
- Remapping des politiques dans d'autres phases (hors scope)
- Gestion des politiques custom non exposées par l'API Shopify

## Decisions

### 1. Récupération du nom de boutique en début de clonage

Le nom de la boutique source est récupéré une seule fois via `GET /shop.json` et passé à `cloner/domain.py` en même temps que les domaines. Cela évite de multiplier les appels API et centralise la logique de remapping dans `domain.py`.

**Alternative écartée :** récupérer le nom dans `policies.py` seulement — trop couplé, alors que le nom peut aussi apparaître dans d'autres contenus (pages, articles).

### 2. Écriture politique par politique via PUT

Shopify impose une route par type de politique : `PUT /admin/api/2024-01/policies/<type>.json` avec le body `{ "policy": { "body": "..." } }`. Il n'y a pas d'endpoint batch.

### 3. Extension de `domain.py` plutôt que logique dans `policies.py`

Le remplacement du nom de boutique est centralisé dans `domain.py` (fonction `remap_content`) afin que toutes les phases bénéficient de ce remapping (pages, articles, politiques). `policies.py` appelle simplement `remap_content` comme les autres phases.

## Risks / Trade-offs

- **API Shopify read-only sur certaines politiques** → si une politique n'est pas modifiable via l'API (certains plans Shopify restreignent les politiques custom), l'écriture retourne une erreur 422. Mitigation : logger l'erreur sans bloquer le clonage, marquer la politique comme `skipped` dans le rapport.
- **Nom de boutique dans des contextes inattendus** → le remplacement du nom peut créer des faux positifs si le nom de la boutique source est un mot commun. Mitigation : le remplacement est case-sensitive et limité aux occurrences exactes.

## Migration Plan

Aucune migration de données requise. La phase `policies` s'insère en position 6 dans l'orchestrateur `main.py` sans modifier les phases existantes.
