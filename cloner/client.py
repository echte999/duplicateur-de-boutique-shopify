import asyncio
import json
import httpx

SHOPIFY_API_VERSION = "2024-01"


class ShopifyAPIError(Exception):
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        super().__init__(f"Shopify API error {status_code}: {message}")


class ShopifyRateLimitError(Exception):
    pass


class ShopifyClient:
    def __init__(
        self,
        source_shop: str,
        source_token: str,
        target_shop: str,
        target_token: str,
    ):
        self._source_base = f"https://{source_shop}/admin/api/{SHOPIFY_API_VERSION}/"
        self._target_base = f"https://{target_shop}/admin/api/{SHOPIFY_API_VERSION}/"
        self._source_headers = {"X-Shopify-Access-Token": source_token, "Content-Type": "application/json"}
        self._target_headers = {"X-Shopify-Access-Token": target_token, "Content-Type": "application/json"}
        self._http = httpx.AsyncClient(timeout=60.0)
        self._semaphore = asyncio.Semaphore(20)

    async def close(self):
        await self._http.aclose()

    async def _request(self, method: str, url: str, headers: dict, **kwargs) -> dict:
        delays = [1, 2, 4]
        async with self._semaphore:
            for attempt, delay in enumerate(delays + [None]):
                response = await self._http.request(method, url, headers=headers, **kwargs)
                if response.status_code == 429:
                    if delay is None:
                        raise ShopifyRateLimitError(f"Rate limit persists after {len(delays)} retries: {url}")
                    await asyncio.sleep(delay)
                    continue
                if response.status_code >= 400:
                    raise ShopifyAPIError(response.status_code, response.text)
                return response.json()

    async def get_source(self, path: str, params: dict | None = None) -> dict:
        return await self._request("GET", self._source_base + path, self._source_headers, params=params)

    async def post_source(self, path: str, data: dict) -> dict:
        return await self._request("POST", self._source_base + path, self._source_headers, content=json.dumps(data))

    async def get_target(self, path: str, params: dict | None = None) -> dict:
        return await self._request("GET", self._target_base + path, self._target_headers, params=params)

    async def post_target(self, path: str, data: dict) -> dict:
        return await self._request("POST", self._target_base + path, self._target_headers, content=json.dumps(data))

    async def put_target(self, path: str, data: dict) -> dict:
        return await self._request("PUT", self._target_base + path, self._target_headers, content=json.dumps(data))

    async def _graphql(self, shop: str, token: str, query: str, variables: dict | None = None) -> dict:
        url = f"https://{shop}/admin/api/{SHOPIFY_API_VERSION}/graphql.json"
        headers = {"X-Shopify-Access-Token": token, "Content-Type": "application/json"}
        payload: dict = {"query": query}
        if variables:
            payload["variables"] = variables

        async with self._semaphore:
            response = await self._http.post(url, headers=headers, content=json.dumps(payload))
            if response.status_code >= 400:
                raise ShopifyAPIError(response.status_code, response.text)

        result = response.json()

        cost = result.get("extensions", {}).get("cost", {})
        throttle = cost.get("throttleStatus", {})
        available = throttle.get("currentlyAvailable", 1000)
        restore_rate = throttle.get("restoreRate", 50)
        requested = cost.get("requestedQueryCost", 0)

        if available < requested and restore_rate > 0:
            wait_seconds = (requested - available) / restore_rate
            await asyncio.sleep(wait_seconds)

        return result

    async def graphql_source(self, query: str, variables: dict | None = None) -> dict:
        shop = self._source_base.split("/")[2]
        token = self._source_headers["X-Shopify-Access-Token"]
        return await self._graphql(shop, token, query, variables)

    async def graphql_target(self, query: str, variables: dict | None = None) -> dict:
        shop = self._target_base.split("/")[2]
        token = self._target_headers["X-Shopify-Access-Token"]
        return await self._graphql(shop, token, query, variables)
