# -*- coding: utf-8 -*-
"""
============================================================
VaultMind — Dokuman Pipeline Test Script'i
============================================================

BU DOSYA NE YAPIYOR?
--------------------
Phase 2'de olusturdugumuz tum pipeline'i test eder:
1. Dokuman yukleme (3 ornek dosya)
2. Chunking (akilli parcalama)
3. ChromaDB'ye kaydetme (embedding + vektor depolama)
4. Anlamsal arama (soru sor, ilgili parcalari bul)

NASIL CALISTIRILIR?
-------------------
    cd backend
    python -m tests.test_document_pipeline
"""

import asyncio
import sys
import os
import time

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
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
    print("\n" + "VaultMind -- Dokuman Pipeline Test".center(60))
    print("=" * 60)

    results = {}

    # ============================================================
    # Test 1: Dokuman Yukleme
    # ============================================================
    print_header("Test 1: Dokuman Yukleme")

    try:
        from app.rag import load_directory

        # sample_docs klasorundeki tum dokumanlari yukle
        sample_dir = os.path.join(os.path.dirname(__file__), "..", "..", "sample_docs")
        docs = load_directory(sample_dir)

        print(f"  Yuklenen dokuman sayisi: {len(docs)}")
        for doc in docs:
            print(f"    - {doc.metadata['source']}: {doc.metadata.get('char_count', 0)} karakter")

        print_result("Dokuman yukleme", len(docs) > 0, f"{len(docs)} dokuman yuklendi")
        results["Yukleme"] = len(docs) > 0

    except Exception as e:
        import traceback
        print_result("Dokuman yukleme basarisiz", False, str(e))
        traceback.print_exc()
        results["Yukleme"] = False
        return

    # ============================================================
    # Test 2: Chunking (Parcalama)
    # ============================================================
    print_header("Test 2: Chunking (Akilli Parcalama)")

    try:
        from app.rag import chunk_text

        all_chunks = []
        for doc in docs:
            chunks = chunk_text(
                text=doc.content,
                chunk_size=1000,
                chunk_overlap=200,
                metadata=doc.metadata,
            )
            all_chunks.extend(chunks)
            print(f"  {doc.metadata['source']}: {len(chunks)} parca")
            # Ilk chunk'in boyutunu goster
            if chunks:
                print(f"    Ornek (ilk 80 karakter): \"{chunks[0].content[:80]}...\"")

        print()
        print_result(
            "Chunking",
            len(all_chunks) > 0,
            f"Toplam {len(all_chunks)} parca olusturuldu"
        )
        results["Chunking"] = len(all_chunks) > 0

    except Exception as e:
        import traceback
        print_result("Chunking basarisiz", False, str(e))
        traceback.print_exc()
        results["Chunking"] = False
        return

    # ============================================================
    # Test 3: ChromaDB'ye Kaydetme (Embedding + Depolama)
    # ============================================================
    print_header("Test 3: ChromaDB'ye Kaydetme")

    try:
        from app.rag import VectorStore

        store = VectorStore(
            collection_name="test_collection",
            persist_directory="./test_chroma_db",
        )

        # Onceki test verilerini temizle
        store.clear()

        print(f"  {len(all_chunks)} parca embed edilip kaydedilecek...")
        print(f"  (Bu islem biraz surebilir - her parca icin embedding hesaplaniyor)")
        print()

        start_time = time.time()

        # Dokumanlara guvenlik seviyesi ata
        security_map = {
            "ik_politikasi.md": "internal",       # Calisanlar gorebilir
            "teknik_kilavuz.md": "confidential",   # Sadece yoneticiler
            "proje_raporu_q3.md": "confidential",  # Sadece yoneticiler
        }

        saved_count = 0
        for doc in docs:
            doc_chunks = [c for c in all_chunks if c.metadata.get("source") == doc.metadata["source"]]
            security = security_map.get(doc.metadata["source"], "public")
            count = await store.add_chunks(doc_chunks, security_level=security)
            saved_count += count
            print(f"  [OK] {doc.metadata['source']}: {count} parca kaydedildi (guvenlik: {security})")

        elapsed = time.time() - start_time

        stats = store.get_stats()
        print()
        print_result(
            "ChromaDB kayit",
            saved_count > 0,
            f"{saved_count} parca kaydedildi, sure: {elapsed:.1f}s"
        )
        print(f"     Koleksiyon: {stats['collection_name']}, toplam: {stats['total_chunks']}")

        results["ChromaDB"] = saved_count > 0

    except Exception as e:
        import traceback
        print_result("ChromaDB kayit basarisiz", False, str(e))
        traceback.print_exc()
        results["ChromaDB"] = False
        return

    # ============================================================
    # Test 4: Anlamsal Arama
    # ============================================================
    print_header("Test 4: Anlamsal Arama")

    try:
        test_queries = [
            {
                "query": "Yillik izin hakki kac gun?",
                "expected_source": "ik_politikasi.md",
                "description": "IK sorusu -> IK dokumanini bulmali",
            },
            {
                "query": "Kubernetes deployment pipeline CI/CD",
                "expected_source": "teknik_kilavuz.md",
                "description": "Teknik soru -> Teknik kilavuzu bulmali",
            },
            {
                "query": "Proje butcesi ne kadar harcandi?",
                "expected_source": "proje_raporu_q3.md",
                "description": "Butce sorusu -> Proje raporunu bulmali",
            },
        ]

        search_passed = True
        for test in test_queries:
            print(f"\n  Soru: \"{test['query']}\"")
            print(f"  Beklenen: {test['expected_source']}")

            search_results = await store.search(test["query"], top_k=3)

            if search_results:
                top_result = search_results[0]
                found_source = top_result["metadata"].get("source", "?")
                score = top_result["relevance_score"]

                # Top-3 icerisinde beklenen kaynak var mi kontrol et
                top3_sources = [r["metadata"].get("source", "?") for r in search_results]
                is_in_top3 = test["expected_source"] in top3_sources
                is_top1 = found_source == test["expected_source"]

                status = "TOP-1" if is_top1 else ("TOP-3" if is_in_top3 else "MISS")
                print_result(
                    test["description"],
                    is_in_top3,  # Top-3'te olmasi yeterli
                    f"Bulunan: {found_source} (skor: {score:.4f}) [{status}]"
                )
                if not is_in_top3:
                    search_passed = False

                # Tum top-3 sonuclarini goster
                for j, r in enumerate(search_results):
                    src = r["metadata"].get("source", "?")
                    s = r["relevance_score"]
                    marker = " <--" if src == test["expected_source"] else ""
                    print(f"     #{j+1} {src} (skor: {s:.4f}){marker}")
            else:
                print_result(test["description"], False, "Sonuc bulunamadi")
                search_passed = False

        results["Arama"] = search_passed

    except Exception as e:
        import traceback
        print_result("Arama basarisiz", False, str(e))
        traceback.print_exc()
        results["Arama"] = False

    # ============================================================
    # Test 5: Guvenlik Filtreli Arama (RBAC Onizleme)
    # ============================================================
    print_header("Test 5: Guvenlik Filtreli Arama (RBAC)")

    try:
        # Sadece "internal" dokumanlar arasinda ara
        print("  Filtre: Sadece 'internal' (calisan) seviyesi")
        print("  Soru: 'izin hakki'")

        filtered_results = await store.search(
            query="izin hakki",
            top_k=5,
            security_filter=["internal", "public"],
        )

        # Sonuclarda "confidential" dokuman OLMAMALI
        has_confidential = any(
            r["metadata"].get("security_level") == "confidential"
            for r in filtered_results
        )

        print()
        for r in filtered_results:
            src = r["metadata"].get("source", "?")
            sec = r["metadata"].get("security_level", "?")
            print(f"    - {src} (guvenlik: {sec}, skor: {r['relevance_score']:.4f})")

        print()
        print_result(
            "Guvenlik filtresi",
            not has_confidential,
            "Confidential dokumanlar filtrelendi" if not has_confidential
            else "HATA: Confidential dokumanlar sonuclarda gorunuyor!"
        )

        results["RBAC"] = not has_confidential

    except Exception as e:
        import traceback
        print_result("RBAC testi basarisiz", False, str(e))
        traceback.print_exc()
        results["RBAC"] = False

    # ============================================================
    # Temizlik
    # ============================================================
    # ChromaDB baglantisinii kapat (Windows dosya kilidi icin)
    try:
        store.close()
        import shutil
        import gc
        gc.collect()  # Garbage collector'u calistir
        time.sleep(0.5)  # Dosya kilidinin serbest kalmasi icin bekle
        if os.path.exists("./test_chroma_db"):
            shutil.rmtree("./test_chroma_db", ignore_errors=True)
    except Exception:
        pass  # Temizlik hatalari kritik degil

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
        print("\n  [SUCCESS] Tum testler basarili! Dokuman pipeline hazir.\n")
    else:
        print("\n  [WARNING] Bazi testler basarisiz oldu.\n")


if __name__ == "__main__":
    asyncio.run(main())
