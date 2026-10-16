"""Typed settings. Every value comes from the environment — never a literal model ID."""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # .env lives at the repo root (prototype/), one level above backend/.
    model_config = SettingsConfigDict(
        env_file=(Path(__file__).resolve().parents[2] / ".env"), extra="ignore")

    gcp_project: str = ""
    gcp_region: str = "asia-south1"
    vertex_region: str = ""
    gemini_model: str = ""
    embed_model: str = ""
    bq_dataset: str = "plant"
    gcs_bucket: str = ""
    rag_corpus: str = ""
    firestore_db: str = "(default)"
    demo_access_code: str = ""

    plant_backend: str = "csv"
    state_backend: str = "memory"
    docs_backend: str = "local"
    files_backend: str = "local"
    replay_case: str = ""

    def require_model(self) -> str:
        if not self.gemini_model:
            raise RuntimeError("GEMINI_MODEL is not set. Models are never hard-coded.")
        return self.gemini_model

    def require_embed_model(self) -> str:
        if not self.embed_model:
            raise RuntimeError("EMBED_MODEL is not set. Models are never hard-coded.")
        return self.embed_model


@lru_cache
def get_settings() -> Settings:
    return Settings()
