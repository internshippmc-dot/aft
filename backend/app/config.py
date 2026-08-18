from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://aft:changeme@localhost:5432/aft_console"
    app_env: str = "development"
    dev_cors_origin: str = "http://localhost:5173"

    # session policy — SECURITY.md section 3
    session_idle_minutes: int = 60
    session_absolute_hours: int = 12

    # ETA engine — TECH_SPEC.md section 7
    eta_window: int = 20
    eta_min_samples: int = 5
    default_leg_days: dict[str, int] = {
        "MFG_DISPATCH": 0,
        "CN_WAREHOUSE": 2,
        "FLIGHT": 3,
        "DELHI_WAREHOUSE": 3,
    }

    # consolidation — PRD.md section 8.1
    chargeable_minimum_kg: float = 10.0

    # SLA — PRD.md section 7
    sla_days: int = 14

    # Shopify sync — PRD.md F8. Token is minted once via a local OAuth script
    # (see Shopify-Excel-Exporter) and pasted in here, not obtained by this
    # app itself — custom app tokens don't expire, no need to run an OAuth
    # flow inside the production service for a one-time action.
    shopify_shop: str | None = None
    shopify_access_token: str | None = None
    shopify_api_version: str = "2026-01"
    shopify_sync_interval_seconds: int = 1800

    # iThink Logistics — booking + tracking. pickup/return address ids come
    # from the merchant's own iThink portal (Settings -> Addresses).
    ithink_access_token: str | None = None
    ithink_secret_key: str | None = None
    ithink_pickup_address_id: str | None = None
    ithink_return_address_id: str | None = None
    ithink_tracking_interval_seconds: int = 900

    @property
    def cookie_secure(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
