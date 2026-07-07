"""
============================================================
VaultMind — Konfigürasyon Yönetimi (Configuration Management)
============================================================

BU DOSYA NE YAPIYOR?
--------------------
.env dosyasındaki ortam değişkenlerini (environment variables) Python
nesnelerine dönüştürür. Bu sayede:

1. Tip güvenliği: Her ayar doğru tipte olur (str, int, bool)
2. Doğrulama: Eksik veya yanlış ayarlar uygulama başlamadan yakalanır
3. Tek kaynak: Tüm konfigürasyon tek bir yerden yönetilir
4. Dokümantasyon: Her ayarın ne işe yaradığı açıkça bellidir

NASIL ÇALIŞIR?
--------------
pydantic-settings kütüphanesi .env dosyasını okur ve Settings sınıfına
otomatik olarak değerleri atar. Örneğin:

    .env dosyasında: LLM_PROVIDER=ollama
    Python'da:       settings.llm_provider → "ollama"
"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Uygulama konfigürasyonu.

    Her alan (field) bir ortam değişkenine karşılık gelir.
    Varsayılan değerler geliştirme ortamı (development) içindir.
    """

    # ---- Application ----
    app_name: str = "VaultMind"
    app_env: str = "development"  # development, staging, production
    app_debug: bool = True
    app_secret_key: str = "change-this-to-a-random-secret-key"

    # ---- LLM Provider ----
    # Hibrit mimari: Hangi LLM sağlayıcısının kullanılacağını belirler
    # "ollama" → Yerel (veri gizliliği), "openai" → Bulut (yüksek kalite)
    llm_provider: str = "ollama"

    # ---- Ollama (Local LLM) ----
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen3.5:4b"
    ollama_embedding_model: str = "nomic-embed-text"

    # ---- OpenAI (Cloud LLM - Optional) ----
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o"

    # ---- Azure OpenAI (Enterprise - Optional) ----
    azure_openai_api_key: str | None = None
    azure_openai_endpoint: str | None = None
    azure_openai_model: str = "gpt-4o"

    # ---- Database ----
    database_url: str = "postgresql://vaultmind:vaultmind@localhost:5432/vaultmind"

    # ---- Vector Database ----
    vector_db_provider: str = "chroma"  # "chroma" veya "qdrant"
    chroma_persist_dir: str = "./chroma_db"

    # ---- CORS ----
    frontend_url: str = "http://localhost:3000"

    # ---- Pydantic Settings Config ----
    # Bu konfigürasyon, pydantic-settings'e .env dosyasını nerede
    # bulacağını ve nasıl okuyacağını söyler
    model_config = SettingsConfigDict(
        env_file=".env",           # .env dosyasının konumu
        env_file_encoding="utf-8", # Türkçe karakterler için UTF-8
        case_sensitive=False,      # LLM_PROVIDER = llm_provider
        extra="ignore",            # Bilinmeyen değişkenleri yoksay
    )


@lru_cache()
def get_settings() -> Settings:
    """
    Settings nesnesini döndürür.

    @lru_cache() dekoratörü sayesinde Settings nesnesi sadece bir kez
    oluşturulur ve sonraki çağrılarda önbellekten döner. Bu, .env
    dosyasının her seferinde tekrar okunmasını önler.

    Kullanım:
        from app.config import get_settings
        settings = get_settings()
        print(settings.llm_provider)  # → "ollama"
    """
    return Settings()
