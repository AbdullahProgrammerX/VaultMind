# VaultMind — Mimari Dokümanı

## Genel Bakış

VaultMind, kurumsal bilgi yönetimi için tasarlanmış çoklu ajan (multi-agent) mimarisine sahip bir yapay zeka asistanıdır.

## Mimari Prensipler

1. **Veri Gizliliği (Privacy by Design)**: Varsayılan olarak tüm veriler yerel kalır
2. **Separation of Concerns**: Her modül tek bir sorumluluğa sahiptir
3. **Hibrit Esneklik**: LLM sağlayıcısı konfigürasyonla değiştirilebilir
4. **Ölçeklenebilirlik**: Küçük firmadan büyük kuruma kadar ölçeklenir

## Katman Mimarisi

```
┌─────────────────────────────────────────────────┐
│               Presentation Layer                 │
│        Next.js Frontend (Chat, Admin UI)         │
├─────────────────────────────────────────────────┤
│                  API Layer                        │
│        FastAPI (REST + SSE Streaming)             │
├─────────────────────────────────────────────────┤
│             Orchestration Layer                   │
│     LangGraph (Multi-Agent State Machine)         │
│  ┌──────┐ ┌─────┐ ┌──────────┐ ┌─────────┐     │
│  │Router│→│RBAC │→│Retrieval │→│Synthesize│     │
│  └──────┘ └─────┘ └──────────┘ └────┬────┘     │
│                                      ↕           │
│                                 ┌─────────┐     │
│                                 │Critique │     │
│                                 └─────────┘     │
├─────────────────────────────────────────────────┤
│              Intelligence Layer                   │
│   ┌──────────┐  ┌───────────┐  ┌────────────┐  │
│   │LLM       │  │Embedding  │  │Text-to-SQL │  │
│   │Provider  │  │Provider   │  │Agent       │  │
│   │(Hybrid)  │  │(Local)    │  │(Phase 8)   │  │
│   └──────────┘  └───────────┘  └────────────┘  │
├─────────────────────────────────────────────────┤
│                 Data Layer                        │
│   ┌──────────┐  ┌───────────┐                   │
│   │ChromaDB/ │  │PostgreSQL │                   │
│   │Qdrant    │  │           │                   │
│   │(Vectors) │  │(Metadata) │                   │
│   └──────────┘  └───────────┘                   │
└─────────────────────────────────────────────────┘
```

## Aşama Geçişleri

| Phase | Eklenen Katman | Durum |
|-------|---------------|-------|
| 0 | Proje iskeleti | ✅ Tamamlandı |
| 1 | LLM Provider | ⏳ Sırada |
| 2 | Document Pipeline | ⏳ |
| 3 | RAG Chain | ⏳ |
| 4 | LangGraph Agents | ⏳ |
| 5 | RBAC | ⏳ |
| 6 | FastAPI API | ⏳ |
| 7 | Next.js Frontend | ⏳ |
| 8 | Advanced Features | ⏳ |
