## Why

L'API Shopify impose des limites strictes sur le nombre de requêtes (REST : bucket de 40 appels, récupération de 2/s ; GraphQL : quota par coût de requête). Sans gestion explicite, les clonages de boutiques avec beaucoup de produits ou de ressources génèrent des erreurs 429 qui font échouer le processus. Il faut une file d'attente avec backoff automatique pour rendre le clonage robuste sur toute taille de boutique.

## What Changes

- **Nouveau** : File d'attente centralisée dans `cloner/client.py` qui régule tous les appels API REST et GraphQL
- **Nouveau** : Backoff exponentiel automatique sur les erreurs 429 (REST et GraphQL `THROTTLED`)
- **Modifié** : Le client `ShopifyClient` intègre la gestion de rate limiting directement (REST bucket + GraphQL cost tracking)
- **Modifié** : Toutes les phases (`products.py`, `collections.py`, `pages.py`, `blogs.py`, `menus.py`, `discounts.py`, `theme.py`) passent par le client centralisé sans gérer le rate limiting elles-mêmes

## Capabilities

### New Capabilities
- `rate-limiting`: File d'attente avec backoff exponentiel pour REST (bucket leaky) et GraphQL (cost-based throttling)

### Modified Capabilities
- `shopify-client`: Le client HTTP gère désormais le rate limiting REST et GraphQL de façon transparente pour les phases

## Impact

- `cloner/client.py` : ajout de la logique de queue et backoff
- Aucun changement d'interface publique pour les phases — elles continuent d'appeler `client.get()`, `client.post()`, etc.
- Dépendances : stdlib uniquement (`asyncio`, `time`) — aucune nouvelle dépendance externe
