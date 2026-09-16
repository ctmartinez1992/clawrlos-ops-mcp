from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    supabase_url: str
    supabase_key: str

    refresh_interval_hours: float = 6
    retention_hours: int = 48
    hn_top_n: int = 60
    user_agent: str = "clawrlos-ops-mcp/0.1"
    github_token: str | None = None
    log_level: str = "INFO"


settings = Settings()
