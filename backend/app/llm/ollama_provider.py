"""
============================================================
VaultMind — Ollama LLM Provider (Yerel LLM Sağlayıcısı)
============================================================

BU DOSYA NE YAPIYOR?
--------------------
BaseLLMProvider'ın Ollama implementasyonu. Ollama'nın yerel API'sine
HTTP istekleri göndererek LLM ve embedding işlemlerini gerçekleştirir.

VERİ GİZLİLİĞİ:
----------------
Bu provider'ın en büyük avantajı: TÜM VERİLER YEREL KALIR.
- Hiçbir veri internete gönderilmez
- Ollama, localhost:11434 üzerinde çalışır
- Şirketlerin en hassas dokümanları bile güvenle işlenebilir

OLLAMA API YAPISI:
-----------------
Ollama basit bir REST API sunar:
- POST /api/chat        → Sohbet (streaming veya tam cevap)
- POST /api/embeddings  → Metin → vektör dönüşümü
- GET  /api/tags        → Yüklü model listesi

ÖĞRENME NOKTALARI:
-----------------
1. ABC implementasyonu — Soyut sınıfı somutlaştırma
2. httpx — Modern, async HTTP client
3. AsyncIterator — Streaming veri akışı (yield ile)
4. Error handling — Hata yönetimi ve anlamlı hata mesajları
5. Dependency Injection — Bağımlılıkları dışarıdan enjekte etme
"""

import httpx
from typing import AsyncIterator

from app.llm.base import BaseLLMProvider, ChatMessage, LLMResponse, EmbeddingResponse


class OllamaProvider(BaseLLMProvider):
    """
    Ollama üzerinden yerel LLM erişimi sağlayan provider.

    Kullanım:
        provider = OllamaProvider(
            base_url="http://localhost:11434",
            model="qwen3.5:4b",
            embedding_model="nomic-embed-text"
        )

        # Tam cevap
        response = await provider.generate([
            ChatMessage(role="user", content="Merhaba!")
        ])

        # Streaming cevap
        async for token in provider.stream([...]):
            print(token, end="")

        # Embedding
        result = await provider.embed("Yıllık izin hakkı")
    """

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "qwen3.5:4b",
        embedding_model: str = "nomic-embed-text",
        timeout: float = 180.0,
    ):
        """
        OllamaProvider'ı başlatır.

        Öğrenme notu — Dependency Injection:
        base_url, model gibi değerleri dışarıdan alıyoruz (config'den).
        Bu sayede test yazarken farklı değerler verebiliriz,
        veya farklı müşteriler farklı modeller kullanabilir.

        Args:
            base_url: Ollama sunucu adresi (varsayılan: localhost:11434)
            model: Kullanılacak LLM modeli (varsayılan: qwen3.5:4b)
            embedding_model: Embedding modeli (varsayılan: nomic-embed-text)
            timeout: HTTP istek zaman aşımı (saniye)
        """
        self._base_url = base_url
        self._model = model
        self._embedding_model = embedding_model
        self._timeout = timeout

    async def generate(
        self,
        messages: list[ChatMessage],
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        """
        Ollama'dan tam bir cevap alır (streaming kapalı).

        İç işleyiş:
        1. ChatMessage listesini Ollama'nın beklediği formata çevir
        2. POST /api/chat endpoint'ine gönder
        3. Cevabı LLMResponse nesnesine dönüştür

        Öğrenme notu — async/await:
        'async def' bu fonksiyonun asenkron olduğunu belirtir.
        'await' ise I/O işleminin (HTTP isteği) tamamlanmasını bekler.
        Bu sürede Python başka işler yapabilir (paralel çalışma).
        """
        # ChatMessage nesnelerini Ollama'nın beklediği dict formatına çevir
        formatted_messages = [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]

        # Ollama API'sine gönderilecek istek gövdesi
        request_body = {
            "model": self._model,
            "messages": formatted_messages,
            "stream": False,  # Tam cevap istiyoruz
            "options": {
                "temperature": temperature,
            },
        }

        # max_tokens belirtilmişse ekle
        if max_tokens is not None:
            request_body["options"]["num_predict"] = max_tokens

        # HTTP isteği gönder
        # httpx.AsyncClient — her istekte yeni bağlantı açmak yerine
        # bağlantıyı yeniden kullanır (performans)
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                response = await client.post(
                    f"{self._base_url}/api/chat",
                    json=request_body,
                )
                response.raise_for_status()  # HTTP hatası varsa exception fırlat
                data = response.json()

                # Ollama cevabını VaultMind formatına dönüştür
                return LLMResponse(
                    content=data.get("message", {}).get("content", ""),
                    model=data.get("model", self._model),
                    usage={
                        "prompt_tokens": data.get("prompt_eval_count", 0),
                        "completion_tokens": data.get("eval_count", 0),
                        "total_duration_ms": data.get("total_duration", 0) / 1_000_000,
                    },
                    metadata={
                        "provider": "ollama",
                        "done": data.get("done", False),
                    },
                )

            except httpx.ConnectError:
                raise ConnectionError(
                    f"Ollama sunucusuna baglanilamiyor: {self._base_url}\n"
                    "Ollama calistigindan emin olun: 'ollama serve'"
                )
            except httpx.HTTPStatusError as e:
                raise RuntimeError(
                    f"Ollama API hatasi: {e.response.status_code}\n"
                    f"Detay: {e.response.text}"
                )

    async def stream(
        self,
        messages: list[ChatMessage],
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> AsyncIterator[str]:
        """
        Cevabı token token (streaming) üretir.

        İç işleyiş:
        1. Ollama'ya stream=True ile istek gönder
        2. Ollama, cevabı satır satır (NDJSON) gönderir
        3. Her satırda bir token gelir, biz bunu yield ile döneriz

        Öğrenme notu — yield vs return:
        - return: Fonksiyon bir değer döndürür ve BİTER
        - yield: Fonksiyon bir değer döndürür ama DURAKLAR
                 Tekrar çağrıldığında kaldığı yerden devam eder

        Bu, streaming'in temelidir:
            async for token in provider.stream([...]):
                # Her yield'de burası çalışır
                print(token, end="")

        Öğrenme notu — NDJSON (Newline Delimited JSON):
        Ollama streaming cevabı şu formatta gönderir:
            {"message": {"content": "Mer"}, "done": false}
            {"message": {"content": "ha"}, "done": false}
            {"message": {"content": "ba"}, "done": false}
            {"message": {"content": "!"}, "done": true}
        Her satır bağımsız bir JSON nesnesidir.
        """
        formatted_messages = [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]

        request_body = {
            "model": self._model,
            "messages": formatted_messages,
            "stream": True,  # Streaming AÇIK
            "options": {
                "temperature": temperature,
            },
        }

        if max_tokens is not None:
            request_body["options"]["num_predict"] = max_tokens

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                # stream=True → HTTP cevabını satır satır oku
                async with client.stream(
                    "POST",
                    f"{self._base_url}/api/chat",
                    json=request_body,
                ) as response:
                    response.raise_for_status()

                    # Her satırı (NDJSON) ayrıştır
                    import json
                    async for line in response.aiter_lines():
                        if not line.strip():
                            continue

                        try:
                            data = json.loads(line)
                            # Token'ı al ve yield et
                            token = data.get("message", {}).get("content", "")
                            if token:
                                yield token

                            # "done": true geldiğinde streaming biter
                            if data.get("done", False):
                                return

                        except json.JSONDecodeError:
                            continue  # Bozuk satırı atla

            except httpx.ConnectError:
                raise ConnectionError(
                    f"Ollama sunucusuna baglanilamiyor: {self._base_url}"
                )

    async def embed(self, text: str) -> EmbeddingResponse:
        """
        Bir metni vektöre dönüştürür.

        İç işleyiş:
        1. Metni Ollama'nın /api/embeddings endpoint'ine gönder
        2. 768 boyutlu bir float dizisi geri al
        3. EmbeddingResponse nesnesine dönüştür

        Öğrenme notu — Neden 768 boyut?
        nomic-embed-text modeli, her metni 768 boyutlu bir uzayda
        temsil eder. Bu, BERT ailesinden gelen bir standarttır.
        768 sayı, metnin anlamını matematiksel olarak kodlar.
        """
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            try:
                response = await client.post(
                    f"{self._base_url}/api/embeddings",
                    json={
                        "model": self._embedding_model,
                        "prompt": text,
                    },
                )
                response.raise_for_status()
                data = response.json()

                embedding = data.get("embedding", [])

                return EmbeddingResponse(
                    embedding=embedding,
                    model=self._embedding_model,
                    dimensions=len(embedding),
                )

            except httpx.ConnectError:
                raise ConnectionError(
                    f"Ollama sunucusuna baglanilamiyor: {self._base_url}"
                )

    async def health_check(self) -> bool:
        """
        Ollama sunucusunun erişilebilir olup olmadığını kontrol eder.
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self._base_url}/api/tags")
                return response.status_code == 200
        except Exception:
            return False

    def get_provider_name(self) -> str:
        """Provider adını döndürür."""
        return "ollama"
