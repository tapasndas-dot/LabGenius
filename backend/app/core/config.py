from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "LabGenius"
    APP_VERSION: str = "0.1.0"

    SUPABASE_URL: str
    SUPABASE_KEY: str
    DATABASE_URL: str

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]

class Settings(BaseSettings):
    APP_NAME: str = "LabGenius"
    APP_VERSION: str = "0.1.0"

    SUPABASE_URL: str
    SUPABASE_KEY: str
    DATABASE_URL: str

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        extra="ignore",
    )
print("CONFIG FILE:", __file__)
print("BASE_DIR:", BASE_DIR)
settings = Settings()