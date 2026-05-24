from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # 1. Database configurations
    DATABASE_URL: str

    # 2. JWT & Security configurations
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Pydantic Settings config: tells Pydantic to read from the ".env" file in root
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore" # Ignore any extra environment variables in the file
    )

# Instantiate settings so we can import 'settings' directly elsewhere
settings = Settings()
