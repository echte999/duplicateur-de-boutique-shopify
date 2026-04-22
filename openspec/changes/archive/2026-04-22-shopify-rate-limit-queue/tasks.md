## 1. Classe RateLimiter dans client.py

- [x] 1.1 Ajouter `import time` et `import random` en tête de `cloner/client.py`
- [x] 1.2 Créer la classe `RateLimiter` avec `__init__(self, max_tokens=40, refill_rate=2.0)` : initialiser `self._tokens = max_tokens`, `self._last_refill = time.monotonic()`, `self._lock = asyncio.Lock()`
- [x] 1.3 Implémenter `async def _refill(self)` : calculer les tokens récupérés depuis `_last_refill`, mettre à jour `_tokens = min(max_tokens, _tokens + elapsed * refill_rate)`, mettre à jour `_last_refill`
- [x] 1.4 Implémenter `async def acquire(self)` : acquérir `_lock`, appeler `_refill()`, si `_tokens < 1` calculer le délai `(1 - tokens) / refill_rate` et `await asyncio.sleep(délai)`, décrémenter `_tokens`
- [x] 1.5 Implémenter `async def request_with_backoff(self, coro_factory, max_retries=3)` : boucle sur max_retries, appeler `await self.acquire()`, exécuter la coroutine, si 429 lire `Retry-After` ou calculer backoff `(2**attempt) * (1 + random.uniform(-0.2, 0.2))`, lever `ShopifyRateLimitError` après épuisement

## 2. Intégration dans ShopifyClient (REST)

- [x] 2.1 Dans `ShopifyClient.__init__`, remplacer `self._semaphore = asyncio.Semaphore(20)` par deux instances : `self._source_limiter = RateLimiter()` et `self._target_limiter = RateLimiter()`, plus `self._source_sem = asyncio.Semaphore(4)` et `self._target_sem = asyncio.Semaphore(4)`
- [x] 2.2 Refactoriser `_request(self, method, url, headers, limiter, semaphore, **kwargs)` pour prendre le `limiter` et `semaphore` en paramètre et déléguer les retries 429 à `limiter.request_with_backoff`
- [x] 2.3 Mettre à jour `get_source`, `post_source` pour passer `self._source_limiter` et `self._source_sem`
- [x] 2.4 Mettre à jour `get_target`, `post_target`, `put_target` pour passer `self._target_limiter` et `self._target_sem`

## 3. Intégration dans ShopifyClient (GraphQL)

- [x] 3.1 Refactoriser `_graphql` pour accepter un `limiter` et `semaphore` en paramètre
- [x] 3.2 Wrapper l'envoi de la requête GraphQL dans `limiter.request_with_backoff` (gérer les erreurs HTTP 429 et les erreurs `THROTTLED` dans `errors[].extensions.code`)
- [x] 3.3 Après chaque réponse GraphQL réussie, vérifier `extensions.cost.throttleStatus` : si `currentlyAvailable < maximumAvailable * 0.1`, calculer et attendre `(maximumAvailable * 0.5 - currentlyAvailable) / restoreRate` secondes
- [x] 3.4 Mettre à jour `graphql_source` et `graphql_target` pour passer les limiters respectifs

## 4. Vérification

- [ ] 4.1 Lancer un clonage complet sur une boutique test et vérifier dans les logs qu'aucun 429 non géré ne remonte
- [x] 4.2 Vérifier que les phases `products.py`, `collections.py`, `pages.py`, `blogs.py`, `menus.py`, `discounts.py`, `theme.py` n'ont subi aucune modification
- [x] 4.3 Dans `RateLimiter.acquire`, ajouter `print(f"  ⏳ Rate limit REST : attente {delay:.1f}s...")` juste avant le `await asyncio.sleep`
- [x] 4.4 Dans `request_with_backoff`, ajouter `print(f"  ⚠️  HTTP 429 — tentative {attempt}/{max_retries} dans {delay:.1f}s")` avant chaque sleep de backoff
- [x] 4.5 Dans `_graphql`, ajouter `print(f"  ⏳ Budget GraphQL bas ({available}/{maximum}) : attente {delay:.1f}s...")` avant le sleep de throttling GraphQL
- [x] 4.6 Dans `_graphql`, ajouter `print(f"  ⚠️  GraphQL THROTTLED — tentative {attempt}/{max_retries} dans 2s")` avant chaque sleep sur erreur THROTTLED
