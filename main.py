import logging
import os
import re
import time
import uuid
from contextlib import asynccontextmanager
from typing import Annotated

from dotenv import load_dotenv
load_dotenv()

import httpx
from fastapi import FastAPI, HTTPException, Request, Response, Path
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from tenacity import RetryError

from camofox import CamofoxClient, managed_tab
from config import get_settings
from cropper import process_screenshot

settings = get_settings()

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[f"{settings.rate_limit_per_minute}/minute"],
)


class InstagramUsernameValidator:
    PATTERN = re.compile(r"^[a-zA-Z0-9._]{1,30}$")

    @classmethod
    def validate(cls, username: str) -> bool:
        return bool(cls.PATTERN.match(username))


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Instagram Screenshot Service")
    yield
    logger.info("Shutting down Instagram Screenshot Service")


app = FastAPI(
    title="Instagram Profile Screenshot Service",
    description="Capture cropped screenshots of Instagram profiles using Camofox browser",
    version="1.0.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request.state.request_id = request_id

    start_time = time.perf_counter()
    response = await call_next(request)
    process_time = time.perf_counter() - start_time

    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time"] = f"{process_time:.3f}s"

    logger.info(
        f"{request_id} | {request.method} {request.url.path} | "
        f"{response.status_code} | {process_time:.3f}s"
    )

    return response


def get_camofox_client() -> CamofoxClient:
    return CamofoxClient(
        base_url=settings.camofox_url,
        user_id=settings.camofox_user_id,
        timeout=settings.camofox_timeout,
        connect_timeout=settings.camofox_connect_timeout,
    )


@app.get("/health", tags=["health"])
async def health():
    camofox = get_camofox_client()
    camofox_ok = await camofox.is_healthy()
    return {
        "status": "ok" if camofox_ok else "degraded",
        "camofox": camofox_ok,
    }


@app.get("/health/live", tags=["health"])
async def liveness():
    return {"status": "ok"}


@app.get("/health/ready", tags=["health"])
async def readiness():
    camofox = get_camofox_client()
    camofox_ok = await camofox.is_healthy()
    if not camofox_ok:
        raise HTTPException(status_code=503, detail="Camofox not available")
    return {"status": "ok", "camofox": camofox_ok}


@app.get(
    "/screenshot/{username}",
    tags=["screenshot"],
    responses={
        200: {"content": {"image/png": {}}, "description": "Profile screenshot (cropped or raw)"},
        400: {"description": "Invalid username"},
        404: {"description": "Profile unavailable"},
        429: {"description": "Rate limit exceeded"},
        503: {"description": "Camofox not available"},
        504: {"description": "Page load timeout"},
    },
)
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def screenshot(
    request: Request,
    username: Annotated[str, Path(min_length=1, max_length=30)],
    crop: bool = False,
):
    if not InstagramUsernameValidator.validate(username):
        logger.warning(f"Invalid username attempted: {username}")
        raise HTTPException(status_code=400, detail="Invalid username")

    logger.info(f"Taking screenshot for username: {username}")

    client = get_camofox_client()

    try:
        async with managed_tab(client) as tab_id:
            await client.navigate(tab_id, f"https://www.instagram.com/{username}")

            import asyncio
            await asyncio.sleep(settings.page_load_wait)

            for _ in range(10):
                snapshot = await client.get_snapshot(tab_id)

                if client.is_profile_unavailable(snapshot):
                    logger.info(f"Profile unavailable: {username}")
                    raise HTTPException(status_code=404, detail="profile isn't available")

                overlay = client.detect_overlay(snapshot)
                if overlay:
                    ref, label = overlay
                    logger.debug(f"Dismissing '{label}' overlay for: {username}")
                    await asyncio.sleep(2)
                    await client.click(tab_id, ref)
                    await asyncio.sleep(settings.overlay_dismiss_wait)
                    continue

                if client.is_page_loaded(snapshot):
                    break

                break

            await asyncio.sleep(1)

            screenshot_bytes = await client.get_screenshot(tab_id)

            if crop:
                result_bytes = process_screenshot(
                    screenshot_bytes,
                    ref_width=settings.crop_ref_width,
                    ref_height=settings.crop_ref_height,
                    left=settings.crop_left,
                    top=settings.crop_top,
                    right=settings.crop_right,
                    bottom=settings.crop_bottom,
                )
                logger.info(f"Screenshot captured for: {username} ({len(result_bytes)} bytes, cropped)")
            else:
                result_bytes = screenshot_bytes
                logger.info(f"Screenshot captured for: {username} ({len(result_bytes)} bytes, raw)")

            return Response(content=result_bytes, media_type="image/png")

    except RetryError as e:
        logger.error(f"Retry error capturing {username}: {e}")
        raise HTTPException(status_code=504, detail="Page load timeout")

    except httpx.ConnectError:
        logger.error(f"Camofox connection failed for: {username}")
        raise HTTPException(status_code=503, detail="Camofox browser not available")

    except httpx.TimeoutException:
        logger.error(f"Timeout capturing {username}")
        raise HTTPException(status_code=504, detail="Page load timeout")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
    )
