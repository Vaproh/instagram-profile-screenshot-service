import logging
import os
import re
import uuid
from contextlib import asynccontextmanager
from typing import Annotated

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, Response, Path

from card_generator import generate_card
from config import get_settings
from profile_fetcher import fetch_profile

settings = get_settings()

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class InstagramUsernameValidator:
    PATTERN = re.compile(r"^[a-zA-Z0-9._]{1,30}$")

    @classmethod
    def validate(cls, username: str) -> bool:
        return bool(cls.PATTERN.match(username))


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Instagram Profile Card Service")
    yield


app = FastAPI(
    title="Instagram Profile Card Service",
    description="Generates aesthetic profile cards for Instagram users",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health", tags=["health"])
async def health():
    return {"status": "healthy", "service": "instagram-profile-card"}


@app.get(
    "/profile/{username}",
    tags=["profile"],
    responses={
        200: {"content": {"image/png": {}}, "description": "Profile card image"},
        400: {"description": "Invalid username"},
        404: {"description": "Profile not found"},
        429: {"description": "Rate limit exceeded"},
        500: {"description": "Internal error"},
    },
)
async def profile_card(username: Annotated[str, Path(min_length=1, max_length=30)]):
    if not InstagramUsernameValidator.validate(username):
        raise HTTPException(status_code=400, detail="Invalid username")

    request_id = str(uuid.uuid4())
    logger.info(f"[{request_id}] Fetching profile data for: {username}")

    proxy_url = ""
    if settings.proxy_enabled and settings.proxy_server:
        port = settings.proxy_port or 8291
        proxy_url = f"http://{settings.proxy_username}:{settings.proxy_password}@{settings.proxy_server}:{port}"

    data = fetch_profile(username, proxy_url)

    if data.get("status") == "missing":
        raise HTTPException(status_code=404, detail="Profile not found")

    if data.get("status") == "rate_limited":
        raise HTTPException(status_code=429, detail="Rate limited by Instagram")

    if data.get("status") == "error":
        logger.error(f"[{request_id}] Error fetching {username}: {data.get('error')}")
        raise HTTPException(status_code=500, detail="Failed to fetch profile")

    try:
        card_bytes = generate_card(data)
        logger.info(f"[{request_id}] Profile card generated for: {username} ({len(card_bytes)} bytes)")
        return Response(content=card_bytes, media_type="image/png")
    except Exception as e:
        logger.error(f"[{request_id}] Error generating card for {username}: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate card")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
    )