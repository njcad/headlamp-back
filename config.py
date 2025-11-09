from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    supabase_url: str | None = None
    supabase_key: str | None = None
    openai_api_key: str | None = None
    app_name: str = "Headlamp API"
    debug: bool = False

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")


def get_settings() -> Settings:
    return Settings()


settings = get_settings()
