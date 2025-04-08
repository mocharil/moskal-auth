import os
from dotenv import load_dotenv
from pydantic import BaseModel

# Load environment variables from .env file
load_dotenv()

class Settings(BaseModel):
    # Application Settings
    BASE_URL: str = "http://localhost:8000"  # Default value for local development
    FRONTEND_URL: str = "http://localhost:3000"  # Default frontend URL
    
    # JWT Settings
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int

    # Database Settings
    DB_HOST: str
    DB_PORT: str
    DB_USER: str
    DB_PASSWORD: str
    DB_NAME: str
    DATABASE_URL: str

    @classmethod
    def from_env(cls):
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            db_host = os.getenv("DB_HOST", "localhost")
            db_port = os.getenv("DB_PORT", "3306")
            db_user = os.getenv("DB_USER", "root")
            db_password = os.getenv("DB_PASSWORD", "")
            db_name = os.getenv("DB_NAME", "auth_db")
            database_url = f"mysql+pymysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

        return cls(
            BASE_URL=os.getenv("BASE_URL", "http://localhost:8000"),
            FRONTEND_URL=os.getenv("FRONTEND_URL", "http://localhost:3000"),
            JWT_SECRET_KEY=os.getenv("JWT_SECRET_KEY", "your-secret-key-here"),
            JWT_ALGORITHM=os.getenv("JWT_ALGORITHM", "HS256"),
            ACCESS_TOKEN_EXPIRE_MINUTES=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")),
            DB_HOST=os.getenv("DB_HOST", "localhost"),
            DB_PORT=os.getenv("DB_PORT", "3306"),
            DB_USER=os.getenv("DB_USER", "root"),
            DB_PASSWORD=os.getenv("DB_PASSWORD", ""),
            DB_NAME=os.getenv("DB_NAME", "auth_db"),
            DATABASE_URL=database_url
        )

settings = Settings.from_env()
