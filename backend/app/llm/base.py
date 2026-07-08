"""
============================================================
VaultMind — Soyut LLM Provider Arayüzü (Abstract Base Class)
============================================================

BU DOSYA NE YAPIYOR?
--------------------
Tüm LLM sağlayıcılarının (Ollama, OpenAI, Azure, vb.) uyması gereken
"sözleşmeyi" (contract/interface) tanımlar.

NEDEN GEREKLİ?
--------------
VaultMind'ın hibrit LLM stratejisi:
- Müşteri A: Ollama (yerel, veri gizliliği)
- Müşteri B: OpenAI (bulut, yüksek kalite)
- Müşteri C: Azure OpenAI (kurumsal bulut)

Hepsi farklı API'ler kullanır ama VaultMind'ın geri kalanı (ajanlar,
RAG pipeline) bundan etkilenmemeli. İşte bu dosya bunu sağlar.

NASIL ÇALIŞIR?
--------------
Python'da "Abstract Base Class" (ABC) mekanizması kullanılır:
1. BaseLLMProvider, tüm provider'ların sahip olması GEREKEN
   metodları tanımlar (generate, stream, embed)
2. Bu metotlar @abstractmethod ile işaretlenir — yani alt sınıflar
   bunları ZORUNLU olarak implemente etmelidir
3. BaseLLMProvider'dan doğrudan nesne oluşturulamaz

Gerçek hayat benzetmesi:
- BaseLLMProvider = "Araba" kavramı (soyut — süremezsiniz)
- OllamaProvider = "Toyota Corolla" (somut — sürebilirsiniz)
- OpenAIProvider = "BMW 3 Serisi" (somut — sürebilirsiniz)
- Hepsi "araba" arayüzüne uyar: gaz, fren, direksiyon

ÖĞRENME NOKTALARI:
-----------------
1. ABC (Abstract Base Class) — Python'da soyut sınıf oluşturma
2. @abstractmethod — Alt sınıfların implemente etmek ZORUNDA olduğu metot
3. Type Hints — Fonksiyonların giriş/çıkış tiplerini belirtme
4. AsyncIterator — Streaming (token token) veri akışı için
5. Dataclass — Basit veri taşıma nesneleri oluşturma
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import AsyncIterator


# ============================================================
# Veri Modelleri (Data Models)
# ============================================================
# Bu sınıflar, LLM ile iletişimde kullanılan veri yapılarını tanımlar.
# @dataclass dekoratörü, Python'da basit veri taşıma nesneleri oluşturur.
# __init__, __repr__ gibi metotları otomatik üretir.

@dataclass
class ChatMessage:
    """
    Bir sohbet mesajını temsil eder.

    Roller (roles):
    - "system": Modelin genel davranışını belirler
      Örnek: "Sen VaultMind adlı kurumsal bir bilgi asistanısın"
    - "user": Kullanıcının sorusu
      Örnek: "Yıllık izin hakkım kaç gün?"
    - "assistant": Modelin önceki cevabı (çok turlu sohbet için)
      Örnek: "Yıllık izin hakkınız 14 gündür."

    Bu format, OpenAI'ın chat completion API'siyle aynıdır.
    Ollama da bu formatı destekler. Bu sayede tüm provider'lar
    aynı mesaj formatını kullanır.
    """
    role: str       # "system", "user", veya "assistant"
    content: str    # Mesajın içeriği


@dataclass
class LLMResponse:
    """
    LLM'den gelen cevabı temsil eder.

    Sadece cevap metnini değil, ek bilgileri de taşır:
    - content: Cevap metni
    - model: Hangi model kullandı (debug için)
    - usage: Token kullanımı (maliyet takibi için)
    - metadata: Provider'a özgü ek bilgiler
    """
    content: str                          # Cevap metni
    model: str = ""                       # Kullanılan model adı
    usage: dict = field(default_factory=dict)  # Token kullanımı
    metadata: dict = field(default_factory=dict)  # Ek bilgiler


@dataclass
class EmbeddingResponse:
    """
    Embedding (vektör) sonucunu temsil eder.

    Bir metin → sayı dizisi (vektör) dönüşümünün sonucu.
    Örnek: "Yıllık izin" → [0.23, -0.87, 0.45, 0.12, ...]

    - embedding: Sayı dizisi (vektör)
    - model: Hangi embedding modeli kullanıldı
    - dimensions: Vektörün boyutu (örn: 768)
    """
    embedding: list[float]  # Sayı dizisi (vektör)
    model: str = ""         # Kullanılan embedding modeli
    dimensions: int = 0     # Vektör boyutu


# ============================================================
# Soyut Temel Sınıf (Abstract Base Class)
# ============================================================

class BaseLLMProvider(ABC):
    """
    Tüm LLM sağlayıcılarının uyması gereken soyut arayüz.

    Bu sınıftan doğrudan nesne OLUŞTURAMAZSINIZ:
        provider = BaseLLMProvider()  # ❌ TypeError!

    Alt sınıflar tüm @abstractmethod'ları implemente ETMELİDİR:
        class OllamaProvider(BaseLLMProvider):
            async def generate(self, ...): ...  # ✅ Zorunlu
            async def stream(self, ...): ...    # ✅ Zorunlu
            async def embed(self, ...): ...     # ✅ Zorunlu

    3 TEMEL YETENEK:
    1. generate() — Tam cevap üretme (soru sor → cevap al)
    2. stream()   — Token token cevap alma (gerçek zamanlı UI için)
    3. embed()    — Metin → vektör dönüşümü (RAG için)
    """

    @abstractmethod
    async def generate(
        self,
        messages: list[ChatMessage],
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        """
        Verilen mesajlara göre tam bir cevap üretir.

        Args:
            messages: Sohbet geçmişi (system + user + assistant mesajları)
            temperature: Yaratıcılık seviyesi (0.0 = deterministik, 1.0 = yaratıcı)
                         RAG için düşük (0.1-0.3), sohbet için orta (0.5-0.7)
            max_tokens: Maksimum cevap uzunluğu (None = model varsayılanı)

        Returns:
            LLMResponse: Cevap metni + metadata

        Kullanım:
            response = await provider.generate([
                ChatMessage(role="user", content="Merhaba!")
            ])
            print(response.content)
        """
        ...

    @abstractmethod
    async def stream(
        self,
        messages: list[ChatMessage],
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> AsyncIterator[str]:
        """
        Cevabı token token (streaming) üretir.

        Neden streaming?
        - Kullanıcı, cevabın oluştuğunu gerçek zamanlı görür
        - UI çok daha canlı ve responsive hisseder
        - ChatGPT, Claude gibi ürünlerin hepsi bunu yapar

        Args:
            messages: Sohbet geçmişi
            temperature: Yaratıcılık seviyesi
            max_tokens: Maksimum cevap uzunluğu

        Yields:
            str: Her adımda bir token (kelime parçası)

        Kullanım:
            async for token in provider.stream([...]):
                print(token, end="", flush=True)
        """
        ...

    @abstractmethod
    async def embed(self, text: str) -> EmbeddingResponse:
        """
        Bir metni sayı dizisine (vektöre) dönüştürür.

        Bu, RAG pipeline'ının temelidir:
        1. Dokümanlar embed edilir → vektör veritabanına kaydedilir
        2. Kullanıcı sorusu embed edilir → en yakın vektörler bulunur
        3. Bulunan dokümanlar LLM'e verilir → cevap üretilir

        Args:
            text: Embed edilecek metin

        Returns:
            EmbeddingResponse: Vektör + metadata
        """
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Sağlayıcının erişilebilir olup olmadığını kontrol eder.

        Returns:
            bool: True = sağlayıcı çalışıyor, False = erişilemiyor
        """
        ...

    @abstractmethod
    def get_provider_name(self) -> str:
        """
        Sağlayıcının adını döndürür (loglama ve debug için).

        Returns:
            str: Örn: "ollama", "openai", "azure"
        """
        ...
