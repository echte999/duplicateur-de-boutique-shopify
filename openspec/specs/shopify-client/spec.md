## ADDED Requirements

### Requirement: Client HTTP async avec authentification Shopify
Le système SHALL fournir un client `httpx.AsyncClient` configuré avec les headers d'authentification Shopify (`X-Shopify-Access-Token`) et l'URL de base `https://{shop}/admin/api/2024-01/`.

#### Scenario: Requête authentifiée REST
- **WHEN** `client.get_source("products.json")` est appelé
- **THEN** la requête inclut `X-Shopify-Access-Token: {token_source}` et cible la boutique source

#### Scenario: Requête vers la boutique cible
- **WHEN** `client.post_target("products.json", data)` est appelé
- **THEN** la requête inclut le token cible et cible la boutique cible

### Requirement: Rate limiting REST avec Semaphore et backoff
Le système SHALL limiter les requêtes REST concurrentes via `asyncio.Semaphore(20)` et retenter automatiquement jusqu'à 3 fois sur erreur HTTP 429, avec délais 1s, 2s, 4s.

#### Scenario: Erreur 429 transitoire
- **WHEN** une requête reçoit HTTP 429
- **THEN** le système attend 1 seconde et retente, puis 2s, puis 4s avant d'échouer

#### Scenario: Limite de concurrence respectée
- **WHEN** 50 requêtes sont lancées simultanément
- **THEN** au plus 20 requêtes sont en vol en même temps

#### Scenario: Épuisement des tentatives
- **WHEN** 3 tentatives consécutives reçoivent HTTP 429
- **THEN** une exception `ShopifyRateLimitError` est levée

### Requirement: Requêtes GraphQL avec gestion du budget de coût
Le système SHALL envoyer les requêtes GraphQL vers `https://{shop}/admin/api/2024-01/graphql.json` et vérifier `extensions.cost.throttleStatus.currentlyAvailable` dans chaque réponse. Si `currentlyAvailable < requestedQueryCost`, le système SHALL attendre avant la prochaine requête.

#### Scenario: Budget GraphQL suffisant
- **WHEN** `currentlyAvailable` est supérieur au `requestedQueryCost`
- **THEN** la requête suivante est envoyée immédiatement

#### Scenario: Budget GraphQL épuisé
- **WHEN** `currentlyAvailable < requestedQueryCost`
- **THEN** le système calcule le temps d'attente nécessaire basé sur `restoreRate` et attend avant de continuer

### Requirement: Gestion des erreurs HTTP non-429
Le système SHALL lever une exception `ShopifyAPIError` pour toute réponse HTTP >= 400 autre que 429, avec le statut et le corps de la réponse.

#### Scenario: Erreur 422 (données invalides)
- **WHEN** Shopify retourne HTTP 422 avec un message d'erreur
- **THEN** `ShopifyAPIError` est levée avec le code 422 et le message d'erreur Shopify
