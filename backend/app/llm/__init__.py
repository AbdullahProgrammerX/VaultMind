"""
VaultMind — LLM Provider Paketi

Bu paket, VaultMind'ın hibrit LLM stratejisini uygular:
- BaseLLMProvider: Tüm provider'ların uyduğu soyut arayüz
- OllamaProvider: Yerel LLM (veri gizliliği)
- OpenAIProvider: Bulut LLM (yüksek kalite)
- create_llm_provider: Factory fonksiyonu (konfigürasyondan otomatik seçim)
- get_llm_provider: Singleton erişimi

Kullanım:
    from app.llm import get_llm_provider, ChatMessage

    provider = get_llm_provider()
    response = await provider.generate([
        ChatMessage(role="user", content="Merhaba!")
    ])
"""

from app.llm.base import BaseLLMProvider, ChatMessage, LLMResponse, EmbeddingResponse
from app.llm.factory import create_llm_provider, get_llm_provider, reset_provider

__all__ = [
    "BaseLLMProvider",
    "ChatMessage",
    "LLMResponse",
    "EmbeddingResponse",
    "create_llm_provider",
    "get_llm_provider",
    "reset_provider",
]
