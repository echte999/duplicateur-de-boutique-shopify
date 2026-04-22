## MODIFIED Requirements

### Requirement: Rate limiting REST avec Semaphore et backoff
Le système SHALL limiter les requêtes REST concurrentes via `asyncio.Semaphore(4)` et déléguer entièrement la gestion du rate limiting au module `rate-limiting` (leaky bucket + backoff exponentiel). Le client ne doit pas implémenter sa propre logique de backoff — il délègue au RateLimiter.

#### Scenario: Erreur 429 transitoire
- **WHEN** une requête reçoit HTTP 429
- **THEN** le RateLimiter gère l'attente et la retentative (backoff exponentiel, Retry-After respecté), transparent pour l'appelant

#### Scenario: Limite de concurrence respectée
- **WHEN** 10 requêtes sont lancées simultanément vers une boutique
- **THEN** au plus 4 requêtes sont en vol en même temps

#### Scenario: Épuisement des tentatives
- **WHEN** 3 tentatives consécutives reçoivent HTTP 429
- **THEN** une exception `ShopifyRateLimitError` est propagée par le RateLimiter

### Requirement: Requêtes GraphQL avec gestion du budget de coût
Le système SHALL envoyer les requêtes GraphQL vers `https://{shop}/admin/api/2024-01/graphql.json` et déléguer la surveillance du budget de coût au module `rate-limiting`. Après chaque réponse GraphQL, le client SHALL transmettre `extensions.cost.throttleStatus` au RateLimiter pour mise à jour de l'état interne.

#### Scenario: Budget GraphQL suffisant
- **WHEN** `currentlyAvailable` est supérieur à 10% de `maximumAvailable`
- **THEN** la requête suivante est envoyée immédiatement

#### Scenario: Budget GraphQL bas
- **WHEN** `currentlyAvailable < maximumAvailable * 0.1`
- **THEN** le RateLimiter calcule et applique le délai d'attente avant la prochaine requête GraphQL

#### Scenario: Erreur THROTTLED GraphQL
- **WHEN** la réponse contient une erreur `THROTTLED`
- **THEN** le RateLimiter retente après 2 secondes (jusqu'à 3 tentatives)
