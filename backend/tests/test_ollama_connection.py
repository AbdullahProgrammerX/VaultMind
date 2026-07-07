# -*- coding: utf-8 -*-
"""
============================================================
VaultMind — Ollama Bağlantı Testi
============================================================

BU DOSYA NE YAPIYOR?
--------------------
Ollama'nın çalışıp çalışmadığını kontrol eder ve basit bir soru-cevap
testi yapar. Phase 0'ın doğrulama adımıdır.

3 ŞEYİ TEST EDER:
1. Ollama sunucusuna bağlanabiliyor muyuz?
2. Gerekli modeller (qwen3.5:4b, nomic-embed-text) yüklü mü?
3. Basit bir soru sorduğumuzda cevap alıyor muyuz?

NASIL ÇALIŞTIRILIR?
-------------------
    python -m backend.tests.test_ollama_connection

ÖNEMLİ KAVRAMLAR:
-----------------
- httpx: Python'da HTTP istekleri yapmak için modern, async bir kütüphane
- Ollama API: http://localhost:11434 adresinde çalışan yerel REST API
  - /api/tags → Yüklü modellerin listesi
  - /api/chat → Sohbet (chat completion)
  - /api/embeddings → Metin → vektör dönüşümü
"""

import httpx
import sys
import os

# Windows terminal'de Unicode sorunlarini onle
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
import json

# Ollama'nın varsayılan adresi
OLLAMA_BASE_URL = "http://localhost:11434"

# VaultMind'ın ihtiyaç duyduğu modeller
REQUIRED_MODELS = ["qwen3.5:4b", "nomic-embed-text"]


def print_header(text: str):
    """Güzel bir başlık yazdırır."""
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}")


def print_result(test_name: str, success: bool, detail: str = ""):
    """Test sonucunu renkli yazdırır."""
    icon = "[OK]" if success else "[FAIL]"
    print(f"  {icon} {test_name}")
    if detail:
        print(f"     → {detail}")


def test_connection() -> bool:
    """
    Test 1: Ollama sunucusuna bağlanabiliyor muyuz?

    Ollama çalışırken http://localhost:11434 adresinde bir API sunar.
    Bu teste basit bir GET isteği göndererek sunucunun ayakta olup
    olmadığını kontrol ediyoruz.
    """
    print_header("Test 1: Ollama Bağlantısı")
    try:
        response = httpx.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5.0)
        response.raise_for_status()
        print_result("Ollama sunucusuna bağlanıldı", True, OLLAMA_BASE_URL)
        return True
    except httpx.ConnectError:
        print_result(
            "Ollama sunucusuna bağlanılamadı", False,
            "Ollama çalışıyor mu? 'ollama serve' komutuyla başlatın."
        )
        return False
    except Exception as e:
        print_result("Beklenmeyen hata", False, str(e))
        return False


def test_models() -> bool:
    """
    Test 2: Gerekli modeller yüklü mü?

    /api/tags endpoint'i yüklü tüm modelleri listeler.
    VaultMind için qwen3.5:4b (LLM) ve nomic-embed-text (embedding) lazım.
    """
    print_header("Test 2: Model Kontrolü")
    try:
        response = httpx.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5.0)
        data = response.json()

        # Yüklü model isimlerini çıkar
        installed_models = [model["name"] for model in data.get("models", [])]

        print(f"  Yüklü modeller: {installed_models}")
        print()

        all_found = True
        for required in REQUIRED_MODELS:
            # Model isminin başlangıcını kontrol et (tag'li versiyonlar için)
            found = any(
                m.startswith(required.split(":")[0])
                for m in installed_models
            )
            print_result(f"Model: {required}", found,
                        "Yüklü" if found else f"Eksik! 'ollama pull {required}' ile yükleyin")
            if not found:
                all_found = False

        return all_found

    except Exception as e:
        print_result("Model listesi alınamadı", False, str(e))
        return False


def test_chat() -> bool:
    """
    Test 3: Basit bir soru-cevap testi.

    Ollama'nın /api/chat endpoint'ine bir soru gönderiyoruz.
    Bu, tüm pipeline'ın (model yükleme → inference → cevap) çalıştığını doğrular.

    Öğrenme notu:
    - "messages" formatı OpenAI'ın chat completion API'sine benzer
    - "role": "system" → Modelin genel davranışını belirler
    - "role": "user" → Kullanıcının sorusu
    - "stream": False → Cevabı tek seferde al (streaming değil)
    """
    print_header("Test 3: Soru-Cevap Testi")
    try:
        print("  Soru: 'Merhaba! Sen kimsin? Bir cümleyle cevap ver.'")
        print("  Cevap bekleniyor (bu birkaç saniye sürebilir)...")
        print()

        response = httpx.post(
            f"{OLLAMA_BASE_URL}/api/chat",
            json={
                "model": "qwen3.5:4b",
                "messages": [
                    {
                        "role": "system",
                        "content": "Sen VaultMind adlı bir kurumsal bilgi asistanısın. Kısa ve öz cevap ver."
                    },
                    {
                        "role": "user",
                        "content": "Merhaba! Sen kimsin? Bir cümleyle cevap ver."
                    }
                ],
                "stream": False,  # Streaming kapalı — tüm cevabı bir kerede al
            },
            timeout=180.0,  # İlk çağrıda model GPU'ya yüklenir, uzun sürebilir
        )

        data = response.json()
        answer = data.get("message", {}).get("content", "Cevap alınamadı")

        print_result("LLM cevap üretti", True)
        print(f"     >> {answer[:200]}")  # Ilk 200 karakter

        return True

    except httpx.ReadTimeout:
        print_result("Zaman aşımı", False, "Model cevap üretmesi çok uzun sürdü. GPU/RAM yeterli mi?")
        return False
    except Exception as e:
        print_result("Soru-cevap başarısız", False, str(e))
        return False


def test_embedding() -> bool:
    """
    Test 4: Embedding testi.

    Bir metni sayı dizisine (vektöre) dönüştürmeyi test eder.
    Bu, RAG pipeline'ının temelini oluşturur (Phase 2'de detaylı göreceğiz).

    Öğrenme notu:
    - Embedding: "Yıllık izin 14 gündür" → [0.23, -0.87, 0.45, ...]
    - Bu sayı dizileri, metinlerin anlamını matematiksel olarak temsil eder
    - Benzer anlamlı metinler → benzer sayı dizileri (vektörler)
    """
    print_header("Test 4: Embedding Testi")
    try:
        response = httpx.post(
            f"{OLLAMA_BASE_URL}/api/embeddings",
            json={
                "model": "nomic-embed-text",
                "prompt": "VaultMind kurumsal bilgi asistanı"
            },
            timeout=30.0,
        )

        data = response.json()
        embedding = data.get("embedding", [])

        if embedding:
            print_result("Embedding üretildi", True,
                        f"Vektör boyutu: {len(embedding)} (ilk 5 değer: {[round(x, 4) for x in embedding[:5]]})")
            return True
        else:
            print_result("Embedding boş döndü", False)
            return False

    except Exception as e:
        print_result("Embedding testi başarısız", False, str(e))
        return False


def main():
    """Tüm testleri çalıştırır ve özet rapor verir."""
    print("\n" + "VaultMind -- Ollama Baglanti Testi".center(60))
    print("=" * 60)

    results = {}

    # Test 1: Bağlantı
    results["Bağlantı"] = test_connection()

    if not results["Bağlantı"]:
        print("\n⚠️  Ollama çalışmıyor. Diğer testler atlanıyor.")
        print("   Çözüm: Terminal'de 'ollama serve' komutunu çalıştırın.\n")
        sys.exit(1)

    # Test 2: Modeller
    results["Modeller"] = test_models()

    # Test 3: Soru-Cevap
    results["Soru-Cevap"] = test_chat()

    # Test 4: Embedding
    results["Embedding"] = test_embedding()

    # Özet
    print_header("SONUÇ ÖZETİ")
    all_passed = True
    for name, passed in results.items():
        print_result(name, passed)
        if not passed:
            all_passed = False

    if all_passed:
        print("\n  [SUCCESS] Tum testler basarili! VaultMind gelistirmeye hazir.\n")
    else:
        print("\n  [WARNING] Bazi testler basarisiz oldu. Yukaridaki hatalari kontrol edin.\n")

    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
