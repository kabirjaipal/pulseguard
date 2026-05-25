from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # 1. Database configurations
    DATABASE_URL: str

    # 2. JWT & Security configurations
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # 3. Redis configuration for Celery
    REDIS_URL: str = "redis://localhost:6379/0"

    # 4. SMTP configuration for email alerts
    SMTP_HOST: str | None = None
    SMTP_PORT: int = 587
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    SMTP_FROM_EMAIL: str = "alerts@pulseguard.io"

    # Pydantic Settings config: tells Pydantic to read from the ".env" file in root
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore" # Ignore any extra environment variables in the file
    )

# Instantiate settings so we can import 'settings' directly elsewhere
settings = Settings()
