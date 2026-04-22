import asyncio
import json
import random
import time

import httpx

SHOPIFY_API_VERSION = "2024-01"
MAX_CONCURRENT_REQUESTS = 4


class ShopifyAPIError(Exception):
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        super().__init__(f"Shopify API error {status_code}: {message}")


class ShopifyRateLimitError(Exception):
    pass


class RateLimiter:
    def __init__(self, max_tokens: float = 40.0, refill_rate: float = 2.0):
        self._max_tokens = max_tokens
        self._refill_rate = refill_rate
        self._tokens = max_tokens
        self._last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    async def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(self._max_tokens, self._tokens + elapsed * self._refill_rate)
        self._last_refill = now

    async def acquire(self) -> None:
        async with self._lock:
            await self._refill()
            if self._tokens < 1:
                delay = (1 - self._tokens) / self._refill_rate
                print(f"  ⏳ Rate limit REST : attente {delay:.1f}s...")
                await asyncio.sleep(delay)
                await self._refill()
            self._tokens -= 1

    async def request_with_backoff(self, coro_factory, max_retries: int = 3):
        for attempt in range(1, max_retries + 1):
            await self.acquire()
            response = await coro_factory()
            if response.status_code != 429:
                return response
            retry_after = response.headers.get("Retry-After")
            if retry_after is not None:
                delay = float(retry_after)
            else:
                delay = (2 ** (attempt - 1)) * (1 + random.uniform(-0.2, 0.2))
            print(f"  ⚠️  HTTP 429 — tentative {attempt}/{max_retries} dans {delay:.1f}s")
            await asyncio.sleep(delay)
        raise ShopifyRateLimitError(f"Rate limit persists after {max_retries} retries")


class ShopifyClient:
    def __init__(
        self,
        source_shop: str,
        source_token: str,
        target_shop: str,
        target_token: str,
    ):
        self._source_shop = source_shop
        self._target_shop = target_shop
        self._source_base = f"https://{source_shop}/admin/api/{SHOPIFY_API_VERSION}/"
        self._target_base = f"https://{target_shop}/admin/api/{SHOPIFY_API_VERSION}/"
        self._source_headers = {"X-Shopify-Access-Token": source_token, "Content-Type": "application/json"}
        self._target_headers = {"X-Shopify-Access-Token": target_token, "Content-Type": "application/json"}
        self._http = httpx.AsyncClient(timeout=60.0)
        self._source_limiter = RateLimiter()
        self._target_limiter = RateLimiter()
        self._source_sem = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
        self._target_sem = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

    @property
    def _semaphore(self) -> asyncio.Semaphore:
        return self._source_sem

    async def close(self):
        await self._http.aclose()

    async def _request(self, method: str, url: str, headers: dict, limiter: RateLimiter, semaphore: asyncio.Semaphore, **kwargs) -> dict:
        async with semaphore:
            response = await limiter.request_with_backoff(
                lambda: self._http.request(method, url, headers=headers, **kwargs)
            )
        if response.status_code >= 400:
            raise ShopifyAPIError(response.status_code, response.text)
        return response.json()

    async def get_source(self, path: str, params: dict | None = None) -> dict:
        return await self._request("GET", self._source_base + path, self._source_headers, self._source_limiter, self._source_sem, params=params)

    async def post_source(self, path: str, data: dict) -> dict:
        return await self._request("POST", self._source_base + path, self._source_headers, self._source_limiter, self._source_sem, content=json.dumps(data))

    async def get_target(self, path: str, params: dict | None = None) -> dict:
        return await self._request("GET", self._target_base + path, self._target_headers, self._target_limiter, self._target_sem, params=params)

    async def post_target(self, path: str, data: dict) -> dict:
        return await self._request("POST", self._target_base + path, self._target_headers, self._target_limiter, self._target_sem, content=json.dumps(data))

    async def put_target(self, path: str, data: dict) -> dict:
        return await self._request("PUT", self._target_base + path, self._target_headers, self._target_limiter, self._target_sem, content=json.dumps(data))

    async def _graphql(self, shop: str, token: str, limiter: RateLimiter, semaphore: asyncio.Semaphore, query: str, variables: dict | None = None) -> dict:
        url = f"https://{shop}/admin/api/{SHOPIFY_API_VERSION}/graphql.json"
        headers = {"X-Shopify-Access-Token": token, "Content-Type": "application/json"}
        payload: dict = {"query": query}
        if variables:
            payload["variables"] = variables

        max_retries = 3
        for attempt in range(1, max_retries + 1):
            async with semaphore:
                response = await limiter.request_with_backoff(
                    lambda: self._http.post(url, headers=headers, content=json.dumps(payload))
                )
            if response.status_code >= 400:
                raise ShopifyAPIError(response.status_code, response.text)

            result = response.json()

            errors = result.get("errors", [])
            if any(e.get("extensions", {}).get("code") == "THROTTLED" for e in errors):
                print(f"  ⚠️  GraphQL THROTTLED — tentative {attempt}/{max_retries} dans 2s")
                await asyncio.sleep(2)
                continue

            cost = result.get("extensions", {}).get("cost", {})
            throttle = cost.get("throttleStatus", {})
            available = throttle.get("currentlyAvailable", 1000)
            maximum = throttle.get("maximumAvailable", 1000)
            restore_rate = throttle.get("restoreRate", 50)

            if maximum > 0 and available < maximum * 0.1 and restore_rate > 0:
                delay = (maximum * 0.5 - available) / restore_rate
                if delay > 0:
                    print(f"  ⏳ Budget GraphQL bas ({available:.0f}/{maximum:.0f}) : attente {delay:.1f}s...")
                    await asyncio.sleep(delay)

            return result

        raise ShopifyRateLimitError(f"GraphQL THROTTLED persists after {max_retries} retries")

    async def graphql_source(self, query: str, variables: dict | None = None) -> dict:
        return await self._graphql(self._source_shop, self._source_headers["X-Shopify-Access-Token"], self._source_limiter, self._source_sem, query, variables)

    async def graphql_target(self, query: str, variables: dict | None = None) -> dict:
        return await self._graphql(self._target_shop, self._target_headers["X-Shopify-Access-Token"], self._target_limiter, self._target_sem, query, variables)
