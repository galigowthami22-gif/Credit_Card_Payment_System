from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL, make_url

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = PROJECT_ROOT / ".env"
if not ENV_FILE.is_file():
    ENV_FILE = PROJECT_ROOT / "Credit_Card" / ".env"


class Settings(BaseSettings):

    DATABASE_URL: str | None = None
    DB_NAME: str = "credit_cards_db"
    DB_USER: str = "root"
    DB_PASSWORD: str = ""
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    SECRET_KEY: str = "default-key"
    JWT_SECRET_KEY: str | None = None
    JWT_ALGORITHM: str = "HS256"

    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore")

    @property
    def async_database_url(self) -> URL:
        if self.DATABASE_URL:
            url = make_url(self.DATABASE_URL)
            if url.drivername.split("+", maxsplit=1)[0] != "mysql":
                raise ValueError("DATABASE_URL must use the MySQL dialect.")
            return url.set(drivername="mysql+aiomysql")

        return URL.create(
            "mysql+aiomysql",
            username=self.DB_USER,
            password=self.DB_PASSWORD,
            host=self.DB_HOST,
            port=self.DB_PORT,
            database=self.DB_NAME,
        )

    @property
    def jwt_signing_key(self) -> str:
        return self.JWT_SECRET_KEY or self.SECRET_KEY


settings = Settings()