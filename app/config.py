from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    PROJECT_NAME: str = "Hospital API"
    API_V1_STR: str = ""
    DATABASE_URL: str = "sqlite:///./hospital.db"


settings = Settings()
