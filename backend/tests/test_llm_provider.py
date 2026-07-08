# -*- coding: utf-8 -*-
"""
============================================================
VaultMind — LLM Provider Test Script'i
============================================================

BU DOSYA NE YAPIYOR?
--------------------
Phase 1'de oluşturduğumuz LLM Provider katmanını test eder:
1. Factory pattern'in dogru provider'i olusturmasini
2. generate() — tam cevap almay
3. stream() — token token cevap almay
4. embed() — metin -> vektor donusumunu
5. health_check() — provider saglik kontrolunu

NASIL CALISTIRILIR?
-------------------
    cd backend
    python -m tests.test_llm_provider
"""

import asyncio
import sys
import os
import time

# Windows terminal Unicode fix
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

# Backend klasorunu Python path'ine ekle
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def print_header(text: str):
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}")


def print_result(test_name: str, success: bool, detail: str = ""):
    icon = "[OK]" if success else "[FAIL]"
    print(f"  {icon} {test_name}")
    if detail:
        print(f"     -> {detail}")


async def main():
    """Tum LLM Provider testlerini calistirir."""

    print("\n" + "VaultMind -- LLM Provider Test".center(60))
    print("=" * 60)

    results = {}

    # ============================================================
    # Test 1: Factory Pattern
    # ============================================================
    print_header("Test 1: Factory Pattern -- Provider Olusturma")

    try:
        from app.llm import create_llm_provider, ChatMessage

        provider = create_llm_provider()
        provider_name = provider.get_provider_name()

        print_result(
            "Provider olusturuldu",
            True,
            f"Provider: {provider_name} (config'den otomatik secildi)"
        )
        results["Factory"] = True

    except Exception as e:
        print_result("Provider olusturulamadi", False, str(e))
        results["Factory"] = False
        print("\n  Provider olusturulamadigi icin diger testler atlanacak.")
        return

    # ============================================================
    # Test 2: Health Check
    # ============================================================
    print_header("Test 2: Saglik Kontrolu (Health Check)")

    try:
        is_healthy = await provider.health_check()
        print_result(
            "Saglik kontrolu",
            is_healthy,
            "Provider erisilebilir" if is_healthy else "Provider erisilemez!"
        )
        results["Health"] = is_healthy

        if not is_healthy:
            print("\n  Provider erisilemez. Diger testler atlanacak.")
            return

    except Exception as e:
        print_result("Saglik kontrolu basarisiz", False, str(e))
        results["Health"] = False
        return

    # ============================================================
    # Test 3: generate() — Tam Cevap
    # ============================================================
    print_header("Test 3: generate() -- Tam Cevap")

    try:
        print("  Soru: 'Python nedir? Bir cumleyle acikla.'")
        print("  Cevap bekleniyor...")
        print()

        start_time = time.time()

        response = await provider.generate(
            messages=[
                ChatMessage(
                    role="system",
                    content="Sen VaultMind adli kurumsal bir bilgi asistanisin. Kisa ve oz cevap ver."
                ),
                ChatMessage(
                    role="user",
                    content="Python nedir? Bir cumleyle acikla."
                ),
            ],
            temperature=0.3,  # RAG icin dusuk temperature
        )

        elapsed = time.time() - start_time

        print_result("Tam cevap alindi", True)
        print(f"     Cevap: {response.content[:200]}")
        print(f"     Model: {response.model}")
        print(f"     Sure: {elapsed:.1f} saniye")
        print(f"     Token kullanimi: {response.usage}")

        results["Generate"] = True

    except Exception as e:
        import traceback
        print_result("Tam cevap basarisiz", False, str(e))
        traceback.print_exc()
        results["Generate"] = False

    # ============================================================
    # Test 4: stream() — Token Token Cevap
    # ============================================================
    print_header("Test 4: stream() -- Streaming (Token Token)")

    try:
        print("  Soru: 'FastAPI nedir? Kisa acikla.'")
        print("  Streaming cevap (her token aninda gorunur):")
        print()
        print("  >> ", end="")

        start_time = time.time()
        token_count = 0

        async for token in provider.stream(
            messages=[
                ChatMessage(
                    role="system",
                    content="Sen VaultMind adli kurumsal bir bilgi asistanisin. Kisa ve oz cevap ver."
                ),
                ChatMessage(
                    role="user",
                    content="FastAPI nedir? Kisa acikla."
                ),
            ],
            temperature=0.3,
        ):
            print(token, end="", flush=True)
            token_count += 1

        elapsed = time.time() - start_time
        print()  # Yeni satir
        print()
        print_result("Streaming basarili", True)
        print(f"     Toplam token: {token_count}")
        print(f"     Sure: {elapsed:.1f} saniye")
        print(f"     Hiz: {token_count / elapsed:.1f} token/saniye")

        results["Stream"] = True

    except Exception as e:
        print()
        print_result("Streaming basarisiz", False, str(e))
        results["Stream"] = False

    # ============================================================
    # Test 5: embed() — Embedding (Vektor Donusumu)
    # ============================================================
    print_header("Test 5: embed() -- Metin -> Vektor")

    try:
        # Iki benzer ve bir farkli metin embed edelim
        texts = [
            "Yillik izin hakki 14 gundur",
            "Calisanlarin yil izni 14 gun olarak belirlenmistir",
            "Bugunun hava durumu gunesli"
        ]

        embeddings = []
        for text in texts:
            result = await provider.embed(text)
            embeddings.append(result.embedding)
            print(f"  Metin: \"{text}\"")
            print(f"     -> Vektor boyutu: {result.dimensions}, ilk 3: {[round(x, 4) for x in result.embedding[:3]]}")
            print()

        # Kosinüs benzerliği hesapla (basit versiyon)
        # Bu, iki vektörün ne kadar benzer olduğunu ölçer (0-1 arası)
        def cosine_similarity(a: list[float], b: list[float]) -> float:
            dot_product = sum(x * y for x, y in zip(a, b))
            norm_a = sum(x ** 2 for x in a) ** 0.5
            norm_b = sum(x ** 2 for x in b) ** 0.5
            if norm_a == 0 or norm_b == 0:
                return 0.0
            return dot_product / (norm_a * norm_b)

        sim_12 = cosine_similarity(embeddings[0], embeddings[1])
        sim_13 = cosine_similarity(embeddings[0], embeddings[2])

        print(f"  Benzerlik (izin vs izin):  {sim_12:.4f}  (yuksek olmali)")
        print(f"  Benzerlik (izin vs hava):  {sim_13:.4f}  (dusuk olmali)")

        # Anlamca benzer metinler daha yüksek skor almalı
        is_correct = sim_12 > sim_13
        print_result(
            "Semantik benzerlik dogru calisyor",
            is_correct,
            f"Benzer metinler daha yuksek skor ({sim_12:.4f} > {sim_13:.4f})" if is_correct
            else f"HATALI: Benzer metinler daha dusuk skor aldi!"
        )

        results["Embed"] = is_correct

    except Exception as e:
        print_result("Embedding basarisiz", False, str(e))
        results["Embed"] = False

    # ============================================================
    # SONUC OZETI
    # ============================================================
    print_header("SONUC OZETI")

    all_passed = True
    for name, passed in results.items():
        print_result(name, passed)
        if not passed:
            all_passed = False

    if all_passed:
        print("\n  [SUCCESS] Tum testler basarili! LLM Provider katmani hazir.\n")
    else:
        print("\n  [WARNING] Bazi testler basarisiz oldu.\n")


if __name__ == "__main__":
    asyncio.run(main())
