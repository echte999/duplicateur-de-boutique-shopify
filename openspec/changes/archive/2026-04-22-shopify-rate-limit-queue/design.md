## Context

`cloner/client.py` contient actuellement un `asyncio.Semaphore(20)` et un retry naïf sur 429 avec délais fixes (1s, 2s, 4s). Cette approche ne modélise pas le leaky bucket Shopify et ignore le header `Retry-After`. Sur des boutiques avec > 200 produits, des 429 persistants peuvent faire échouer le clonage.

La contrainte principale : aucune dépendance externe — tout doit être fait avec `asyncio`, `time`, et `random` (stdlib).

## Goals / Non-Goals

**Goals:**
- Modéliser le leaky bucket REST Shopify (40 tokens, récupération 2/s) pour lisser proactivement le débit
- Respecter le header `Retry-After` sur HTTP 429
- Surveiller le budget GraphQL via `extensions.cost.throttleStatus` et attendre si nécessaire
- Rendre la gestion transparente pour toutes les phases (zéro changement dans `products.py`, `collections.py`, etc.)

**Non-Goals:**
- Persistance de l'état du bucket entre deux clonages
- Métriques ou observabilité du rate limiting
- Support de plusieurs boutiques en parallèle (hors scope V2)

## Decisions

### Décision 1 : Classe `RateLimiter` séparée dans `client.py`

**Choix** : Créer une classe `RateLimiter` dans `cloner/client.py` (pas un module séparé) instanciée une fois par boutique (source et cible).

**Pourquoi pas un module séparé ?** Le projet est un outil personnel avec une seule couche d'abstraction. Séparer en `cloner/rate_limiter.py` ne ferait que multiplier les fichiers sans bénéfice.

**Alternative rejetée** : Décorateur `@rate_limited` sur chaque méthode — plus difficile à tester et à faire évoluer.

### Décision 2 : Leaky bucket proactif (pre-flight throttling)

**Choix** : Calculer `tokens_disponibles` avant d'envoyer la requête et attendre si nécessaire, plutôt que de réagir uniquement aux 429.

**Pourquoi** : Réduire les 429 à la source, pas seulement les gérer. Les 429 sur REST Shopify peuvent entraîner un délai de blocage côté Shopify si trop fréquents.

**Formule** : 
```python
now = time.monotonic()
tokens = min(40, tokens + (now - last_refill) * 2)
if tokens < 1:
    await asyncio.sleep((1 - tokens) / 2)
tokens -= 1
```

### Décision 3 : Jitter sur le backoff exponentiel

**Choix** : Ajouter un jitter de ±20% sur chaque délai de backoff.

**Pourquoi** : Évite le "thundering herd" si plusieurs tâches async reçoivent un 429 simultanément et repartent toutes en même temps.

### Décision 4 : Semaphore réduit à 4

**Choix** : Réduire `asyncio.Semaphore` de 20 à 4 requêtes simultanées par boutique.

**Pourquoi** : Avec le leaky bucket à 40 tokens et 2/s de récupération, envoyer 20 requêtes simultanées vide le bucket en ~0.3s. 4 requêtes simultanées maintient un flux plus stable et laisse de la marge pour le leaky bucket.

## Risks / Trade-offs

- **Clonage plus lent** sur petites boutiques → Mitigation : le leaky bucket ne ralentit que si le budget est bas ; pour < 100 requêtes il n'y a quasiment aucun impact
- **État du bucket non synchronisé avec Shopify** : le bucket local est une estimation. Si Shopify a un état différent (autre processus consommant le quota), on peut encore recevoir des 429 → Mitigation : le backoff sur 429 reste le filet de sécurité
- **Pas de queue persistée** : si le clonage est interrompu au milieu d'une phase à cause d'un rate limit non géré, la reprise sur erreur V2 prend le relais

## Migration Plan

1. Ajouter `RateLimiter` dans `cloner/client.py`
2. Modifier `ShopifyClient.__init__` pour instancier deux `RateLimiter` (source et cible)
3. Modifier les méthodes `get_source`, `post_target`, `graphql_source`, `graphql_target` pour passer par le RateLimiter
4. Aucun changement dans les fichiers `phases/` — interface publique inchangée
5. Tester manuellement sur une boutique avec > 100 produits

**Rollback** : revert sur `cloner/client.py` uniquement — aucune migration de données.

## Open Questions

- Faut-il logger les délais d'attente appliqués (pour diagnostiquer les clonages lents) ? → Recommandé : log DEBUG uniquement
