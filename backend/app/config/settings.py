from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "SEO Intelligence Platform"
    DATABASE_URL: str = "sqlite:///./seo.db"

    class Config:
        env_file = ".env"

settings = Settings()
