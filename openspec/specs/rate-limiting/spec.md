## ADDED Requirements

### Requirement: File d'attente REST avec leaky bucket
Le système SHALL implémenter un leaky bucket pour les requêtes REST Shopify : capacité maximale de 40 tokens, récupération de 2 tokens par seconde. Chaque requête consomme 1 token. Si le bucket est vide, le système SHALL attendre le temps nécessaire pour récupérer 1 token avant d'envoyer la requête.

#### Scenario: Bucket plein - requête immédiate
- **WHEN** le bucket REST contient au moins 1 token
- **THEN** la requête est envoyée immédiatement sans délai

#### Scenario: Bucket vide - attente calculée
- **WHEN** le bucket REST est à 0 token et une requête est demandée
- **THEN** le système calcule `délai = 1 / 2` (0.5s pour récupérer 1 token) et attend avant d'envoyer

#### Scenario: Pic de requêtes concurrentes
- **WHEN** 60 requêtes REST sont lancées simultanément
- **THEN** les 40 premières partent immédiatement, les suivantes attendent selon le taux de récupération

### Requirement: Backoff exponentiel avec jitter sur HTTP 429
Le système SHALL retenter automatiquement toute requête ayant reçu HTTP 429 avec un backoff exponentiel : base de 1 seconde, facteur 2, jitter aléatoire de +/-20%, maximum 3 tentatives. Si `Retry-After` est présent dans le header de la réponse 429, le système SHALL respecter ce délai en priorité.

#### Scenario: Header Retry-After présent
- **WHEN** HTTP 429 est reçu avec header `Retry-After: 3`
- **THEN** le système attend exactement 3 secondes avant de retenter

#### Scenario: Backoff sans Retry-After
- **WHEN** HTTP 429 est reçu sans header `Retry-After`
- **THEN** le système attend environ 1s, puis ~2s, puis ~4s (avec jitter +/-20%) avant chaque nouvelle tentative

#### Scenario: Épuisement des tentatives
- **WHEN** 3 tentatives consécutives reçoivent HTTP 429
- **THEN** une exception `ShopifyRateLimitError` est levée avec le nombre de tentatives et le dernier délai

### Requirement: Throttling GraphQL basé sur le coût
Le système SHALL surveiller `extensions.cost.throttleStatus` dans chaque réponse GraphQL. Si `currentlyAvailable < maximumAvailable * 0.1` (moins de 10% du budget disponible), le système SHALL calculer un délai d'attente basé sur `restoreRate` et attendre avant la prochaine requête GraphQL.

#### Scenario: Budget GraphQL abondant
- **WHEN** `currentlyAvailable >= maximumAvailable * 0.1`
- **THEN** la prochaine requête GraphQL est envoyée sans délai

#### Scenario: Budget GraphQL bas
- **WHEN** `currentlyAvailable < maximumAvailable * 0.1`
- **THEN** le système calcule `délai = (maximumAvailable * 0.5 - currentlyAvailable) / restoreRate` et attend ce délai

#### Scenario: Erreur THROTTLED GraphQL
- **WHEN** la réponse GraphQL contient `errors[].extensions.code == "THROTTLED"`
- **THEN** le système attend 2 secondes et retente la requête, jusqu'à 3 tentatives

### Requirement: Indicateurs visuels dans le terminal
Le système SHALL afficher des messages `print()` dans le terminal pour chaque événement de throttling, afin que l'opérateur comprenne pourquoi le clonage ralentit. Les messages doivent inclure le délai appliqué.

#### Scenario: Attente imposée par le bucket REST
- **WHEN** le bucket REST est vide et impose un délai avant d'envoyer une requête
- **THEN** le système affiche `  Rate limit REST : attente {délai:.1f}s...` avant de dormir

#### Scenario: Retry après HTTP 429
- **WHEN** une requête REST reçoit HTTP 429 et déclenche un backoff
- **THEN** le système affiche `  HTTP 429 - tentative {attempt}/{max} dans {délai:.1f}s` avant de dormir

#### Scenario: Budget GraphQL bas
- **WHEN** le budget GraphQL tombe sous 10% et impose un délai
- **THEN** le système affiche `  Budget GraphQL bas ({available}/{maximum}) : attente {délai:.1f}s...` avant de dormir

#### Scenario: Retry après erreur THROTTLED GraphQL
- **WHEN** la réponse GraphQL contient une erreur `THROTTLED`
- **THEN** le système affiche `  GraphQL THROTTLED - tentative {attempt}/{max} dans 2s` avant de dormir

### Requirement: Sérialisation des requêtes par boutique
Le système SHALL garantir qu'au maximum `MAX_CONCURRENT_REQUESTS = 4` requêtes sont en vol simultanément vers une même boutique (source ou cible), via `asyncio.Semaphore`.

#### Scenario: Concurrence limitée par boutique
- **WHEN** 10 requêtes vers la boutique source sont lancées simultanément
- **THEN** au plus 4 sont en vol en même temps, les autres attendent dans la file
