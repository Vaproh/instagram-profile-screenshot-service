import os
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    camofox_url: str = "http://localhost:9377"
    camofox_user_id: str = "ig-screenshot-service"
    camofox_timeout: float = 15.0
    camofox_connect_timeout: float = 2.0
    page_load_wait: float = 5.0
    overlay_dismiss_wait: float = 2.0

    host: str = "0.0.0.0"
    port: int = 8080

    log_level: str = "INFO"

    proxy_enabled: bool = False
    proxy_server: str = ""
    proxy_port: int = 8291
    proxy_username: str = ""
    proxy_password: str = ""

    rate_limit_per_minute: int = 30

    crop_ref_width: int = 1280
    crop_ref_height: int = 720
    crop_left: int = 610
    crop_top: int = 65
    crop_right: int = 1210
    crop_bottom: int = 270


@lru_cache
def get_settings() -> Settings:
    return Settings()
