import logging
from contextlib import asynccontextmanager
from typing import Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)


class CamofoxClient:
    def __init__(
        self,
        base_url: str,
        user_id: str,
        timeout: float = 15.0,
        connect_timeout: float = 2.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.user_id = user_id
        self.timeout = httpx.Timeout(timeout, connect=connect_timeout)

    async def _request(
        self,
        method: str,
        path: str,
        retries: int = 1,
        **kwargs,
    ) -> httpx.Response:
        url = f"{self.base_url}{path}"
        kwargs.setdefault("timeout", self.timeout)

        @retry(
            stop=stop_after_attempt(retries + 1),
            wait=wait_exponential(multiplier=0.5, min=0.5, max=2),
            retry=retry_if_exception_type((httpx.ConnectError, httpx.TimeoutException)),
            reraise=True,
        )
        async def _make_request():
            async with httpx.AsyncClient() as client:
                response = await client.request(method, url, **kwargs)
                response.raise_for_status()
                return response

        return await _make_request()

    async def create_tab(self) -> str:
        logger.debug("Creating new Camofox tab")
        response = await self._request(
            "POST",
            "/tabs",
            json={"userId": self.user_id, "sessionKey": "screenshot"},
        )
        data = response.json()
        tab_id = data.get("tabId")
        if not tab_id:
            raise RuntimeError(f"Failed to create tab: {data}")
        logger.debug(f"Created tab: {tab_id}")
        return tab_id

    async def navigate(self, tab_id: str, url: str) -> None:
        logger.debug(f"Navigating tab {tab_id} to {url}")
        await self._request(
            "POST",
            f"/tabs/{tab_id}/navigate",
            json={
                "url": url,
                "userId": self.user_id,
                "viewport": {"width": 1280, "height": 720},
            },
        )

    async def get_snapshot(self, tab_id: str) -> str:
        response = await self._request(
            "GET",
            f"/tabs/{tab_id}/snapshot",
            params={"userId": self.user_id},
        )
        data = response.json()
        return data.get("snapshot", "")

    async def click(self, tab_id: str, ref: str) -> None:
        logger.debug(f"Clicking element {ref} in tab {tab_id}")
        await self._request(
            "POST",
            f"/tabs/{tab_id}/click",
            json={"ref": ref, "userId": self.user_id},
        )

    async def get_screenshot(self, tab_id: str) -> bytes:
        response = await self._request(
            "GET",
            f"/tabs/{tab_id}/screenshot",
            params={"userId": self.user_id},
        )
        return response.content

    async def delete_tab(self, tab_id: str) -> None:
        try:
            logger.debug(f"Deleting tab {tab_id}")
            await self._request(
                "DELETE",
                f"/tabs/{tab_id}",
                params={"userId": self.user_id},
            )
        except Exception as e:
            logger.warning(f"Failed to delete tab {tab_id}: {e}")

    async def is_healthy(self) -> bool:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/tabs",
                    params={"userId": self.user_id},
                    timeout=2.0,
                )
                return response.status_code == 200
        except (httpx.ConnectError, httpx.TimeoutException):
            return False

    OVERLAY_PATTERNS = [
        (r'button "Decline optional cookies" \[(e\d+)\]', "Decline optional cookies"),
        (r'button "Deny all" \[(e\d+)\]', "Deny all"),
        (r'button "Reject all" \[(e\d+)\]', "Reject all"),
        (r'button "Rejeter tout" \[(e\d+)\]', "Reject all"),
        (r'button "Not now" \[(e\d+)\]', "Not now"),
        (r'button "Allow all cookies" \[(e\d+)\]', "Allow all cookies"),
        (r'button "Allow All Cookies" \[(e\d+)\]', "Allow All Cookies"),
        (r'button "Accept all" \[(e\d+)\]', "Accept all"),
        (r'button "Accept All" \[(e\d+)\]', "Accept All"),
        (r'button "Accept cookies" \[(e\d+)\]', "Accept cookies"),
        (r'button "Accept" \[(e\d+)\]', "Accept"),
        (r'button "Close" \[(e\d+)\]', "Close"),
    ]

    def detect_overlay(self, snapshot: str) -> Optional[tuple[str, str]]:
        for pattern, label in self.OVERLAY_PATTERNS:
            import re
            match = re.search(pattern, snapshot)
            if match:
                return (match.group(1), label)
        return None

    @staticmethod
    def is_profile_unavailable(snapshot: str) -> bool:
        unavailable_phrases = [
            "Sorry, this page isn't available",
            "Profile isn't available",
        ]
        return any(phrase in snapshot for phrase in unavailable_phrases)

    @staticmethod
    def is_page_loaded(snapshot: str) -> bool:
        loaded_indicators = [
            "posts",
            "followers",
            "following",
            "followers",
            "img",
        ]
        snapshot_lower = snapshot.lower()
        count = sum(1 for ind in loaded_indicators if ind in snapshot_lower)
        return count >= 2


@asynccontextmanager
async def managed_tab(client: CamofoxClient):
    tab_id: Optional[str] = None
    try:
        tab_id = await client.create_tab()
        yield tab_id
    finally:
        if tab_id is not None:
            await client.delete_tab(tab_id)
