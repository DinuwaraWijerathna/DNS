from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "BDNS API"
    environment: str = "development"
    host: str = "0.0.0.0"
    port: int = 8000
    api_prefix: str = "/api/v1"
    log_level: str = "INFO"

    ledger_storage_path: str = "data/ledger.json"
    authorized_validators: str = "validator-1"

    redis_url: str = "redis://localhost:6379/0"
    resolver_cache_ttl_seconds: int = 60
    resolver_metrics_log_size: int = 200

    supabase_url: str | None = None
    supabase_service_role_key: str | None = None

    jwt_secret: str = "bdns_super_secret_key_change_later"
    jwt_expires_hours: int = 24
    bcrypt_rounds: int = 12

    paypal_client_id: str | None = None
    paypal_client_secret: str | None = None
    paypal_mode: str = "sandbox"  # "sandbox" or "live"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def authorized_validators_list(self) -> list[str]:
        return [v.strip() for v in self.authorized_validators.split(",") if v.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()