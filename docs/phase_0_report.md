# Phase 0 Raporu — Proje İskeleti & Geliştirme Ortamı

**Tarih**: 7 Temmuz 2026
**Commit**: `feat: initialize project structure and development environment`
**GitHub**: https://github.com/AbdullahProgrammerX/VaultMind

---

## Ne İnşa Ettik?

Bu aşamada VaultMind projesinin temelini attık:

| Dosya | Amaç |
|---|---|
| `backend/app/main.py` | FastAPI giriş noktası, sağlık kontrolü endpoint'leri |
| `backend/app/config.py` | Konfigürasyon yönetimi (pydantic-settings ile .env okuma) |
| `backend/tests/test_ollama_connection.py` | Ollama bağlantı, model, chat ve embedding testleri |
| `backend/requirements.txt` | 30+ Python bağımlılığı (açıklamalı) |
| `.env.example` | Ortam değişkenleri şablonu (hibrit LLM konfigürasyonu) |
| `.gitignore` | Git'in takip etmeyeceği dosyalar |
| `README.md` | Profesyonel proje tanıtımı ve mimari diyagram |
| `docs/architecture.md` | Katmanlı mimari dokümanı |

## Proje Yapısı

```
VaultMind/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py          ← FastAPI giriş noktası
│   │   ├── config.py        ← Konfigürasyon yönetimi
│   │   ├── llm/             ← (Phase 1'de doldurulacak)
│   │   ├── agents/          ← (Phase 4'te doldurulacak)
│   │   ├── rag/             ← (Phase 2'de doldurulacak)
│   │   ├── db/              ← (Phase 5'te doldurulacak)
│   │   └── api/             ← (Phase 6'da doldurulacak)
│   ├── tests/
│   │   └── test_ollama_connection.py
│   └── requirements.txt
├── docs/
│   └── architecture.md
├── sample_docs/
├── .env.example
├── .env                     ← (Git'e girmez!)
├── .gitignore
└── README.md
```

## Öğrenilen Kavramlar

### 1. Monorepo Yapısı
Tüm proje (backend, frontend, docs) tek bir Git repo'sunda yaşar. Bu, versiyon kontrolünü basitleştirir ve tüm bileşenlerin uyumlu kalmasını sağlar.

### 2. Virtual Environment (Sanal Ortam)
`python -m venv venv` ile izole bir Python ortamı oluşturduk. Bu, projenin bağımlılıklarının sistem Python'ını etkilememesini sağlar.

### 3. Pydantic Settings
`.env` dosyasındaki değerleri otomatik olarak Python nesnelerine dönüştüren bir kütüphane. Tip güvenliği ve doğrulama sağlar:
```python
settings = get_settings()
print(settings.llm_provider)  # → "ollama" (.env'den okur)
```

### 4. FastAPI Temelleri
Modern, async Python web framework'ü. Otomatik API dokümantasyonu (Swagger) sağlar:
- `GET /` → Sağlık kontrolü
- `GET /docs` → Swagger UI (otomatik)

### 5. CORS (Cross-Origin Resource Sharing)
Tarayıcılar, farklı port'lardan gelen istekleri güvenlik nedeniyle engeller. Frontend (port 3000) ve backend (port 8000) farklı portlarda çalışacağı için CORS middleware ekledik.

### 6. Ollama API
Ollama, yerel bir REST API sunar:
- `/api/tags` → Yüklü modeller
- `/api/chat` → Sohbet (LLM)
- `/api/embeddings` → Metin → vektör dönüşümü

### 7. Embedding Kavramı
Metin → sayı dizisi (vektör) dönüşümü. "Yıllık izin" ve "tatil hakkı" birbirine yakın vektörler üretir çünkü anlamca benzerler. Bu, RAG'ın temelidir (Phase 2-3'te detaylandırılacak).

## Test Sonuçları

```
[OK] Ollama bağlantısı (localhost:11434)
[OK] Modeller yüklü (qwen3.5:4b + nomic-embed-text)
[OK] LLM cevap üretiyor ("Ben VaultMind, kurumsal bilgi asistanıyım")
[OK] Embedding üretiyor (768 boyutlu vektör)
```

## Mimari Kararlar ve Nedenleri

| Karar | Neden? |
|---|---|
| pydantic-settings kullanımı | .env → Python objesi dönüşümünde tip güvenliği |
| FastAPI seçimi | Async, otomatik dokümantasyon, modern |
| Monorepo yapısı | Tek repo'da tüm bileşenler, basit yönetim |
| `.env` dosyasının Git'e girmemesi | Güvenlik — API anahtarları sızmamalı |

## Sonraki Adım: Phase 1

LLM Provider Soyutlama Katmanı:
- `BaseLLMProvider` soyut sınıfı
- `OllamaProvider` implementasyonu
- `OpenAIProvider` (stub)
- Factory pattern ile dinamik provider seçimi
- Streaming (token token) cevap alma
