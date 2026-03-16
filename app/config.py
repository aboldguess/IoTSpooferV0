"""Configuration module.

Purpose:
- Centralize runtime configuration for the IoT spoofer service.
- Provide environment-variable driven settings for secure deployment.

Structure:
- `Settings`: Pydantic settings object loaded from env/.env.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """App settings loaded from environment variables."""

    app_name: str = "IoT Dashboard Spoofer"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    log_level: str = "INFO"
    cors_origins: str = "*"
    max_camera_image_bytes: int = 2_500_000

    mqtt_default_host: str = "localhost"
    mqtt_default_port: int = 1883
    mqtt_default_client_id: str = "iot-spoofer-client"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
