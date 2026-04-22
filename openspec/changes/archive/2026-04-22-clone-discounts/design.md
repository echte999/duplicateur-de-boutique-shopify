## Context

La phase de clonage des réductions est la dernière pièce manquante de la V1. Le fichier `cloner/phases/discounts.py` est déjà scaffoldé et contient une implémentation partielle via l'API REST Shopify (`price_rules` + `discount_codes`). Shopify modélise les réductions en deux couches : une *price rule* (configuration : type, valeur, conditions, dates) et un ou plusieurs *discount codes* attachés à cette rule.

L'API REST est utilisée car les price rules et discount codes sont bien exposés via REST. L'API GraphQL Shopify (DiscountNodes) existe pour les *automatic discounts* (sans code), mais ces dernières sont moins courantes et plus complexes à manipuler ; le scope MVP se limite aux réductions basées sur un code.

## Goals / Non-Goals

**Goals:**
- Cloner toutes les price rules de la boutique source vers la cible avec remapping des IDs produits/collections
- Copier tous les codes de réduction associés à chaque price rule
- Garantir que les compteurs d'utilisation (`usage_count`) repartent à zéro sur la cible
- Intégrer la phase dans le pipeline principal et le rapport post-clonage

**Non-Goals:**
- Réductions automatiques (automatic discounts sans code) — hors périmètre V1
- Réductions basées sur des scripts Shopify (deprecated)
- Conserver l'historique d'utilisation des codes

## Decisions

### 1. Exclure `usage_count` explicitement du payload

**Décision** : Ajouter `usage_count` à la liste des champs exclus lors de la construction du payload.

**Pourquoi** : Bien que Shopify ignore probablement `usage_count` à la création (champ read-only), l'exclure explicitement rend l'intention claire et évite toute ambiguïté si l'API change.

**Alternatif considéré** : Ne rien faire et laisser Shopify gérer — risque de comportement implicite non documenté.

### 2. Conserver l'API REST (pas GraphQL)

**Décision** : Utiliser `GET /price_rules.json` et `POST /price_rules.json` plutôt que l'API GraphQL DiscountNodes.

**Pourquoi** : L'API REST est complète pour les price rules avec codes, plus simple, et cohérente avec le reste du pipeline. L'API GraphQL pour les discounts est plus adaptée aux automatic discounts, hors scope ici.

### 3. Silently skip les codes en doublon

**Décision** : Ignorer les erreurs de création de discount codes (bloc `except Exception: pass`).

**Pourquoi** : Un code peut déjà exister sur la boutique cible (clonage re-lancé). La réduction est quand même utilisable. Logger l'échec serait du bruit sans valeur.

## Risks / Trade-offs

- **Rate limits** : Si la boutique source a beaucoup de price rules avec de nombreux codes, les appels imbriqués (un GET codes par rule) peuvent consommer rapidement le bucket REST. → Le client `ShopifyClient` gère déjà le backoff sur 429.
- **Champs read-only non filtrés** : D'autres champs Shopify comme `id`, `created_at`, `updated_at` sont déjà exclus. Si Shopify ajoute de nouveaux champs read-only, la création pourrait échouer avec 422. → Filtrer les erreurs et logger clairement.
- **Pagination des price rules** : L'appel actuel utilise `?limit=250` sans pagination. Si la boutique source a plus de 250 rules, certaines seront manquées. → Acceptable en V1, à corriger en V2 avec pagination cursor-based.
