"""
============================================================
VaultMind — OpenAI LLM Provider (Bulut LLM Sağlayıcısı)
============================================================

BU DOSYA NE YAPIYOR?
--------------------
BaseLLMProvider'ın OpenAI implementasyonu. OpenAI'ın bulut API'sine
istekler göndererek GPT-4o gibi modelleri kullanır.

DİKKAT — VERİ GİZLİLİĞİ:
--------------------------
Bu provider kullanıldığında veriler OpenAI sunucularına gönderilir!
Gizli kurumsal veriler için OllamaProvider tercih edilmelidir.

DURUM:
------
Bu dosya şu anda bir STUB (taslak) — tam implementasyon gerektiğinde
doldurulacak. Ama arayüz hazır, yani provider factory ve config
sistemi bunu zaten tanıyor.

ÖĞRENME NOKTALARI:
-----------------
1. Stub pattern — Arayüzü hazırla, implementasyonu ertele
2. NotImplementedError — "Bu henüz yazılmadı" sinyali
3. Hibrit mimari — Aynı arayüz, farklı implementasyonlar
"""

import httpx
from typing import AsyncIterator

from app.llm.base import BaseLLMProvider, ChatMessage, LLMResponse, EmbeddingResponse


class OpenAIProvider(BaseLLMProvider):
    """
    OpenAI API üzerinden bulut LLM erişimi sağlayan provider.

    NOT: Bu provider, verileri OpenAI sunucularına gönderir.
    Gizli veriler için OllamaProvider kullanın.

    Kullanım (API key gerektirir):
        provider = OpenAIProvider(
            api_key="sk-...",
            model="gpt-4o"
        )
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "gpt-4o",
        embedding_model: str = "text-embedding-3-small",
        base_url: str = "https://api.openai.com/v1",
        timeout: float = 60.0,
    ):
        """
        OpenAIProvider'ı başlatır.

        Args:
            api_key: OpenAI API anahtarı (zorunlu)
            model: Kullanılacak model (varsayılan: gpt-4o)
            embedding_model: Embedding modeli
            base_url: API base URL (Azure için değiştirilebilir)
            timeout: HTTP istek zaman aşımı
        """
        if not api_key:
            raise ValueError(
                "OpenAI API anahtari gerekli. "
                ".env dosyasinda OPENAI_API_KEY degerini ayarlayin."
            )

        self._api_key = api_key
        self._model = model
        self._embedding_model = embedding_model
        self._base_url = base_url
        self._timeout = timeout

        # OpenAI API için gerekli HTTP headers
        self._headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    async def generate(
        self,
        messages: list[ChatMessage],
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        """
        OpenAI'dan tam bir cevap alır.

        OpenAI API formatı:
        POST https://api.openai.com/v1/chat/completions
        {
            "model": "gpt-4o",
            "messages": [{"role": "user", "content": "Merhaba!"}],
            "temperature": 0.7
        }
        """
        formatted_messages = [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]

        request_body = {
            "model": self._model,
            "messages": formatted_messages,
            "temperature": temperature,
        }

        if max_tokens is not None:
            request_body["max_tokens"] = max_tokens

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                f"{self._base_url}/chat/completions",
                headers=self._headers,
                json=request_body,
            )
            response.raise_for_status()
            data = response.json()

            choice = data["choices"][0]
            usage = data.get("usage", {})

            return LLMResponse(
                content=choice["message"]["content"],
                model=data.get("model", self._model),
                usage={
                    "prompt_tokens": usage.get("prompt_tokens", 0),
                    "completion_tokens": usage.get("completion_tokens", 0),
                    "total_tokens": usage.get("total_tokens", 0),
                },
                metadata={"provider": "openai"},
            )

    async def stream(
        self,
        messages: list[ChatMessage],
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> AsyncIterator[str]:
        """
        OpenAI'dan streaming cevap alır.

        OpenAI, Server-Sent Events (SSE) formatında streaming yapar:
            data: {"choices": [{"delta": {"content": "Mer"}}]}
            data: {"choices": [{"delta": {"content": "ha"}}]}
            data: [DONE]
        """
        formatted_messages = [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]

        request_body = {
            "model": self._model,
            "messages": formatted_messages,
            "temperature": temperature,
            "stream": True,
        }

        if max_tokens is not None:
            request_body["max_tokens"] = max_tokens

        import json

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            async with client.stream(
                "POST",
                f"{self._base_url}/chat/completions",
                headers=self._headers,
                json=request_body,
            ) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue

                    payload = line[6:]  # "data: " kısmını kes

                    if payload.strip() == "[DONE]":
                        return

                    try:
                        data = json.loads(payload)
                        token = data["choices"][0].get("delta", {}).get("content", "")
                        if token:
                            yield token
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue

    async def embed(self, text: str) -> EmbeddingResponse:
        """
        OpenAI'dan embedding alır.

        OpenAI API formatı:
        POST https://api.openai.com/v1/embeddings
        {"model": "text-embedding-3-small", "input": "metin"}
        """
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                f"{self._base_url}/embeddings",
                headers=self._headers,
                json={
                    "model": self._embedding_model,
                    "input": text,
                },
            )
            response.raise_for_status()
            data = response.json()

            embedding = data["data"][0]["embedding"]

            return EmbeddingResponse(
                embedding=embedding,
                model=data.get("model", self._embedding_model),
                dimensions=len(embedding),
            )

    async def health_check(self) -> bool:
        """OpenAI API'nin erişilebilir olup olmadığını kontrol eder."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    f"{self._base_url}/models",
                    headers=self._headers,
                )
                return response.status_code == 200
        except Exception:
            return False

    def get_provider_name(self) -> str:
        """Provider adını döndürür."""
        return "openai"
