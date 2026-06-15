import logging
import random
from typing import Any, Dict

from curl_cffi import requests as cffi_requests

logger = logging.getLogger(__name__)

API_URL = "https://i.instagram.com/api/v1/users/web_profile_info/?username={}"

USER_AGENTS = [
    "Instagram 320.0.0.0 Android (33; 33; SM-S908B; SM-S908B; 33; 33; exynos2200; en_US; 701237498)",
    "Instagram 319.0.0.0 Android (34; 34; Pixel 8 Pro; Pixel 8 Pro; 34; 34; shiba; en_US; 701237498)",
    "Instagram 318.0.0.0 Android (33; 33; SM-A546B; SM-A546B; 33; 33; exynos1380; en_US; 701237498)",
    "Instagram 317.0.0.0 Android (14; 14; SM-S918B; SM-S918B; 14; 14; qcom; en_US; 701237498)",
    "Instagram 316.0.0.0 Android (33; 33; SM-A536B; SM-A536B; 33; 33; exynos1280; en_US; 701237498)",
    "Instagram 315.0.0.0 Android (34; 34; Pixel 7a; Pixel 7a; 34; 34; lynx; en_US; 701237498)",
    "Instagram 314.0.0.0 Android (33; 33; SM-S906B; SM-S906B; 33; 33; exynos2200; en_US; 701237498)",
    "Instagram 313.0.0.0 Android (33; 33; SM-A546E; SM-A546E; 33; 33; exynos1380; en_US; 701237498)",
    "Instagram 312.0.0.0 Android (14; 14; Pixel 8; Pixel 8; 14; 14; shiba; en_US; 701237498)",
    "Instagram 311.0.0.0 Android (33; 33; SM-S916B; SM-S916B; 33; 33; exynos2400; en_US; 701237498)",
]


def build_headers() -> Dict[str, str]:
    user_agent = random.choice(USER_AGENTS)
    return {
        "User-Agent": user_agent,
        "x-ig-app-id": "936619743392459",
        "Accept": "*/*",
        "Accept-Language": "en-US",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
    }


def fetch_profile(username: str, proxy_url: str = None) -> Dict[str, Any]:
    url = API_URL.format(username)
    headers = build_headers()

    try:
        resp = cffi_requests.get(
            url,
            headers=headers,
            timeout=15,
            proxies={"https": proxy_url, "http": proxy_url} if proxy_url else None,
            impersonate="chrome",
        )

        if resp.status_code == 404:
            return {"status": "missing", "error": "Profile not found"}

        if resp.status_code == 429:
            return {"status": "rate_limited", "error": "Rate limited by Instagram"}

        if resp.status_code != 200:
            return {"status": "error", "error": f"HTTP {resp.status_code}"}

        data = resp.json()

        user = data.get("data", {}).get("user")
        if not user:
            return {"status": "missing", "error": "User data not found in response"}

        return {
            "status": "ok",
            "username": user.get("username", username),
            "full_name": user.get("full_name", ""),
            "bio": user.get("biography", ""),
            "followers": user.get("edge_followed_by", {}).get("count", 0),
            "following": user.get("edge_follow", {}).get("count", 0),
            "posts": user.get("edge_owner_to_timeline_media", {}).get("count", 0),
            "is_private": user.get("is_private", False),
            "is_verified": user.get("is_verified", False),
            "profile_pic_url": user.get("profile_pic_url_hd", user.get("profile_pic_url", "")),
            "external_url": user.get("external_url", ""),
        }

    except Exception as e:
        logger.error(f"Error fetching profile {username}: {e}")
        return {"status": "error", "error": str(e)}