import asyncio
import logging

import httpx

from ..config import settings

log = logging.getLogger(__name__)


def build_http_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=10.0,
        headers={"User-Agent": settings.user_agent},
        follow_redirects=True,
    )


async def get_with_retry(
    client: httpx.AsyncClient, url: str, **kwargs
) -> httpx.Response:
    """One retry on 429/5xx with a short backoff."""
    resp = await client.get(url, **kwargs)
    if resp.status_code == 429 or resp.status_code >= 500:
        await asyncio.sleep(1.5)
        resp = await client.get(url, **kwargs)
    resp.raise_for_status()
    return resp
