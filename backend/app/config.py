from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/collectlite"
    redis_url: str = "redis://localhost:6379/0"
    cohere_api_key: str = ""
    secret_key: str = "change-me-in-production"
    debug: bool = True
    allowed_origins: str = "http://localhost:3000"
    exports_dir: str = "exports"

    @property
    def origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",")]


settings = Settings()
