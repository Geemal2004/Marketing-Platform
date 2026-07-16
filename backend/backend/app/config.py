"""
Configuration settings loaded from environment variables
"""
import os
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


def find_env_file() -> str:
    """
    Find .env file. Prefer backend/.env (next to start_services.bat),
    then nested backend package dirs.
    """
    app_dir = os.path.dirname(os.path.abspath(__file__))  # .../backend/backend/app
    package_dir = os.path.dirname(app_dir)                # .../backend/backend
    backend_root = os.path.dirname(package_dir)           # .../backend
    repo_root = os.path.dirname(backend_root)             # .../Marketing-Platform

    candidates = [
        os.path.join(backend_root, ".env"),      # backend/.env (canonical)
        os.path.join(package_dir, ".env"),        # backend/backend/.env
        os.path.join(app_dir, ".env"),            # backend/backend/app/.env
        os.path.join(repo_root, ".env"),          # repo root .env
    ]
    for path in candidates:
        if os.path.isfile(path):
            return path
    return os.path.join(backend_root, ".env")


_ENV_FILE = find_env_file()


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://agentsociety:dev_password@localhost:5433/agentsociety_db"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # MQTT
    mqtt_broker_host: str = "localhost"
    mqtt_broker_port: int = 1883
    mqtt_transport: str = "tcp"
    mqtt_path: str = ""

    # ChromaDB
    chroma_host: str = "localhost"
    chroma_port: int = 8000
    chroma_ssl: bool = False

    # AWS S3 (optional)
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_s3_bucket: str = "agentsociety-videos-dev"
    aws_region: str = "ap-south-1"

    # Google Gemini API (used by VLM video analysis)
    gemini_api_key: str = ""
    gemini_api_keys: str = ""  # comma-separated keys for rotation

    # Ollama Cloud LLM (used by simulation agents)
    ollama_api_url: str = "https://ollama.com/api/chat"
    ollama_model_name: str = "gemma4:31b-cloud"
    ollama_api_key: str = ""

    # Hugging Face media storage (project uploads)
    hf_access_token: str = ""
    hf_video_repo_id: str = "Geemal204/Marketing"
    hf_video_repo_type: str = "dataset"
    hf_video_path_prefix: str = "videos"

    # Security
    jwt_secret: str = "change_this_to_a_random_32_character_string"
    jwt_algorithm: str = "HS256"
    jwt_expiry_hours: int = 24

    # Simulation
    default_num_agents: int = 10
    default_simulation_days: int = 5

    # File Storage
    upload_dir: str = "uploads"

    model_config = SettingsConfigDict(
        env_file=_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache()
def get_settings() -> Settings:
    return Settings()


def clear_settings_cache() -> None:
    """Clear cached settings (e.g. after .env changes in tests)."""
    get_settings.cache_clear()
