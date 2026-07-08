"""
============================================================
VaultMind — LLM Provider Factory (Fabrika Kalıbı)
============================================================

BU DOSYA NE YAPIYOR?
--------------------
Konfigürasyona (.env dosyasına) bakarak doğru LLM provider'ı
otomatik oluşturur. Bu, "Factory Pattern" tasarım kalıbıdır.

FABRİKA KALIBININ AMACI:
-------------------------
Provider oluşturma mantığını TEK BİR YERDE toplar:

    .env'de LLM_PROVIDER=ollama   → OllamaProvider oluşturulur
    .env'de LLM_PROVIDER=openai   → OpenAIProvider oluşturulur

Kodun geri kalanı sadece şunu yapar:
    provider = create_llm_provider()
    response = await provider.generate([...])

Hangi provider olduğunu bilmez, bilmek zorunda da değildir.

GERÇEK HAYAT BENZETMESİ:
------------------------
Bir araba kiralama şirketi düşünün:
- Müşteri: "Bir araba istiyorum" (create_llm_provider)
- Şirket konfigürasyona bakar: "Bu müşteri premium → BMW ver"
- Müşteri arabayı kullanır: gaz, fren, direksiyon (generate, stream, embed)
- Müşteri BMW mi Toyota mı kullandığını umursamaz — arayüz aynı

ÖĞRENME NOKTALARI:
-----------------
1. Factory Pattern — Nesne oluşturmayı merkezi yönetim
2. Loose coupling — Bileşenler birbirine gevşek bağlı
3. Single Responsibility — Her fonksiyon tek bir iş yapar
"""

from app.config import get_settings
from app.llm.base import BaseLLMProvider


def create_llm_provider() -> BaseLLMProvider:
    """
    Konfigürasyona göre uygun LLM provider'ı oluşturur ve döndürür.

    .env'deki LLM_PROVIDER değerine göre:
    - "ollama"  → OllamaProvider (yerel, veri gizliliği)
    - "openai"  → OpenAIProvider (bulut, yüksek kalite)

    Returns:
        BaseLLMProvider: Kullanıma hazır LLM provider

    Raises:
        ValueError: Bilinmeyen provider adı

    Kullanım:
        provider = create_llm_provider()
        response = await provider.generate([
            ChatMessage(role="user", content="Merhaba!")
        ])

    Öğrenme notu — Neden burada import yapıyoruz?
    "Lazy import" denir. Provider sınıflarını sadece gerektiğinde
    import ediyoruz. Bu, gereksiz bağımlılık yüklenmesini önler.
    Örneğin Ollama kullanıyorsanız OpenAI kütüphanesi yüklenmez.
    """
    settings = get_settings()
    provider_name = settings.llm_provider.lower()

    if provider_name == "ollama":
        # Lazy import — sadece Ollama seçildiyse import et
        from app.llm.ollama_provider import OllamaProvider

        return OllamaProvider(
            base_url=settings.ollama_base_url,
            model=settings.ollama_model,
            embedding_model=settings.ollama_embedding_model,
        )

    elif provider_name == "openai":
        from app.llm.openai_provider import OpenAIProvider

        return OpenAIProvider(
            api_key=settings.openai_api_key,
            model=settings.openai_model,
        )

    else:
        # Desteklenmeyen provider adı
        supported = ["ollama", "openai"]
        raise ValueError(
            f"Bilinmeyen LLM provider: '{provider_name}'\n"
            f"Desteklenen provider'lar: {supported}\n"
            f".env dosyasinda LLM_PROVIDER degerini kontrol edin."
        )


# ============================================================
# Kolaylık (Convenience) — Tekil Provider Erişimi
# ============================================================
# Uygulama genelinde aynı provider'ı paylaşmak için bir cache.
# Bu, her istekte yeni provider oluşturmayı önler.

_provider_instance: BaseLLMProvider | None = None


def get_llm_provider() -> BaseLLMProvider:
    """
    Uygulama genelinde kullanılan tekil (singleton) provider'ı döndürür.

    İlk çağrıda provider oluşturulur, sonraki çağrılarda önbellekten döner.

    Öğrenme notu — Singleton Pattern:
    Bazı nesnelerden sadece BİR TANE olması gerekir (veritabanı bağlantısı,
    LLM provider gibi). Singleton pattern bunu garanti eder.

    Returns:
        BaseLLMProvider: Paylaşılan provider instance
    """
    global _provider_instance
    if _provider_instance is None:
        _provider_instance = create_llm_provider()
    return _provider_instance


def reset_provider():
    """
    Provider önbelleğini temizler (test ve konfigürasyon değişikliği için).

    Öğrenme notu:
    Test yazarken provider'ı sıfırlayıp farklı ayarlarla yeniden
    oluşturmak gerekebilir. Bu fonksiyon bunu sağlar.
    """
    global _provider_instance
    _provider_instance = None
