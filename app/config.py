from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://usuario:password@localhost:5432/rumbo"
    secret_key: str = "cambiar-esta-clave-por-una-generada-al-azar"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440

    anthropic_api_key: str = ""
    ai_model: str = "claude-sonnet-5"

    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # Codigo compartido que debe enviar quien se registra con role != "joven"
    # (institucion/empresa), para que el registro publico no permita auto-asignarse
    # un rol con acceso a /institucion/kpis.
    institution_signup_code: str = ""

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
