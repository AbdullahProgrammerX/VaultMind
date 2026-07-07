"""
============================================================
VaultMind — FastAPI Ana Giriş Noktası (Entry Point)
============================================================

BU DOSYA NE YAPIYOR?
--------------------
FastAPI uygulamasını başlatır. Şu anda sadece bir sağlık kontrolü
(health check) endpoint'i var. İlerleyen aşamalarda (Phase 6) buraya
chat, document ve auth router'ları eklenecek.

NASIL ÇALIŞTIRILIR?
-------------------
    uvicorn app.main:app --reload

Tarayıcıda açın:
    http://localhost:8000        → Sağlık kontrolü
    http://localhost:8000/docs   → Swagger API dokümantasyonu (otomatik)
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings

# Konfigürasyonu yükle
settings = get_settings()

# FastAPI uygulaması oluştur
app = FastAPI(
    title=settings.app_name,
    description="AI-powered enterprise knowledge assistant",
    version="0.1.0",
    docs_url="/docs",       # Swagger UI adresi
    redoc_url="/redoc",     # ReDoc adresi (alternatif dokümantasyon)
)

# CORS Middleware — Frontend'in backend'e erişebilmesi için
# (Cross-Origin Resource Sharing)
# Öğrenme notu: Tarayıcılar güvenlik nedeniyle farklı port'lardan
# gelen istekleri engeller. CORS bu engeli kontrollü şekilde kaldırır.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],  # Sadece frontend'e izin ver
    allow_credentials=True,
    allow_methods=["*"],     # GET, POST, PUT, DELETE hepsine izin ver
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """
    Sağlık kontrolü (Health Check) endpoint'i.
    Uygulamanın çalıştığını ve konfigürasyonun doğru yüklendiğini doğrular.
    """
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": "0.1.0",
        "llm_provider": settings.llm_provider,
        "environment": settings.app_env,
    }


@app.get("/health")
async def health_check():
    """
    Detaylı sağlık kontrolü.
    İleride Ollama bağlantısı, veritabanı durumu vb. kontrol edilecek.
    """
    return {
        "status": "healthy",
        "services": {
            "api": True,
            "ollama": None,     # Phase 1'de eklenecek
            "vector_db": None,  # Phase 2'de eklenecek
            "database": None,   # Phase 5'te eklenecek
        }
    }
