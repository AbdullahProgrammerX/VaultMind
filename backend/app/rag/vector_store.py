"""
============================================================
VaultMind — Vektör Deposu (Vector Store — ChromaDB)
============================================================

BU DOSYA NE YAPIYOR?
--------------------
Metin parçalarını (chunk) vektörlere dönüştürüp ChromaDB'ye kaydeder
ve anlamsal (semantic) arama yapar.

GELENEKSEL DB vs VEKTÖR DB:
----------------------------
PostgreSQL (geleneksel):
    SELECT * FROM docs WHERE content LIKE '%izin%'
    → Sadece "izin" kelimesini içeren dokümanları bulur
    → "tatil hakkı", "yıllık dinlenme" bulunamaz ❌

ChromaDB (vektör):
    Soru: "izin hakkım ne kadar?"
    → "Yıllık izin hakkı 14 gündür" ✅ (anlamca benzer)
    → "Çalışanların tatil günleri" ✅ (anlamca benzer)
    → "Hava durumu güneşli" ❌ (anlamca farklı)

CHROMADB NASIL ÇALIŞIR?
-----------------------
1. Her metin parçası bir vektöre dönüştürülür (embedding)
2. Vektörler ChromaDB'ye kaydedilir (persist_directory'de disk'e yazılır)
3. Arama sırasında: soru → vektör → en yakın vektörler bulunur
4. En yakın vektörlerin metinleri döndürülür

ÖĞRENME NOKTALARI:
-----------------
1. Vektör veritabanı — Anlamsal arama altyapısı
2. Collection — ChromaDB'de bir "tablo" karşılığı
3. Upsert — Insert + Update (varsa güncelle, yoksa ekle)
4. Metadata filtering — Vektör aramasında ek filtre uygulama
"""

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.rag.chunker import TextChunk
from app.llm import get_llm_provider
from app.config import get_settings


class VectorStore:
    """
    ChromaDB üzerinde vektör depolama ve arama işlemleri.

    Kullanım:
        store = VectorStore()

        # Chunk'ları kaydet
        await store.add_chunks(chunks)

        # Arama yap
        results = await store.search("izin hakkım ne?", top_k=5)
    """

    def __init__(
        self,
        collection_name: str = "vaultmind_docs",
        persist_directory: str | None = None,
    ):
        """
        VectorStore'u başlatır.

        Args:
            collection_name: ChromaDB koleksiyonu adı (tablo gibi)
            persist_directory: Vektörlerin kaydedileceği disk konumu
                              None ise config'den alınır

        Öğrenme notu — Collection:
        ChromaDB'de "collection" bir SQL tablosuna benzer.
        Her collection, belirli bir türdeki vektörleri tutar.
        VaultMind'da tüm doküman chunk'ları tek bir collection'da.
        """
        settings = get_settings()
        persist_dir = persist_directory or settings.chroma_persist_dir

        # ChromaDB istemcisini oluştur
        # PersistentClient: Vektörleri diske yazar, uygulama kapansa bile kalır
        self._client = chromadb.PersistentClient(
            path=persist_dir,
            settings=ChromaSettings(
                anonymized_telemetry=False,  # Telemetri kapalı (gizlilik)
            ),
        )

        # Collection'ı al veya oluştur
        # get_or_create: Varsa getir, yoksa yeni oluştur
        # hnsw:space="cosine" → Cosine mesafesi kullanır (embedding için en uygun)
        # L2 (Euclidean) yerine cosine kullanıyoruz çünkü:
        # - Embedding vektörleri yön (direction) ile anlam kodlar
        # - Cosine, yön benzerliğini ölçer (büyüklükten bağımsız)
        # - L2 ise mutlak mesafeyi ölçer (büyüklüğe bağımlı)
        self._collection_name = collection_name
        self._collection_metadata = {
            "description": "VaultMind document chunks",
            "hnsw:space": "cosine",
        }

        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            metadata=self._collection_metadata,
        )

    async def add_chunks(
        self,
        chunks: list[TextChunk],
        security_level: str = "public",
    ) -> int:
        """
        Metin parçalarını vektöre dönüştürüp ChromaDB'ye kaydeder.

        İşlem adımları:
        1. Her chunk için benzersiz bir ID oluştur
        2. Her chunk'ı embed et (metin → vektör)
        3. Vektörleri metadata ile birlikte ChromaDB'ye kaydet

        Args:
            chunks: Kaydedilecek metin parçaları
            security_level: Güvenlik seviyesi (RBAC için)
                "public"       → Herkes görebilir
                "internal"     → Sadece çalışanlar
                "confidential" → Sadece yöneticiler
                "hr_only"      → Sadece İK departmanı

        Returns:
            int: Kaydedilen chunk sayısı

        Öğrenme notu — Neden güvenlik seviyesi metadata'da?
        Vektör aramasında metadata filtresi uygulayarak, kullanıcının
        görmemesi gereken dokümanları arama sonuçlarından çıkarıyoruz.
        Bu, RBAC'ın vektör veritabanı seviyesindeki uygulamasıdır.
        """
        if not chunks:
            return 0

        provider = get_llm_provider()

        ids = []
        embeddings = []
        documents = []
        metadatas = []

        for i, chunk in enumerate(chunks):
            # Benzersiz ID oluştur
            source = chunk.metadata.get("source", "unknown")
            chunk_id = f"{source}__chunk_{chunk.chunk_index}"

            # Metni vektöre dönüştür
            embed_result = await provider.embed(chunk.content)

            # Metadata'ya güvenlik seviyesini ekle
            chunk_metadata = {
                **chunk.metadata,
                "security_level": security_level,
            }
            # ChromaDB metadata sadece str, int, float, bool destekler
            # Karmaşık tipleri temizle
            clean_metadata = {
                k: v for k, v in chunk_metadata.items()
                if isinstance(v, (str, int, float, bool))
            }

            ids.append(chunk_id)
            embeddings.append(embed_result.embedding)
            documents.append(chunk.content)
            metadatas.append(clean_metadata)

        # ChromaDB'ye toplu ekleme (upsert = varsa güncelle, yoksa ekle)
        self._collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )

        return len(ids)

    async def search(
        self,
        query: str,
        top_k: int = 5,
        security_filter: list[str] | None = None,
    ) -> list[dict]:
        """
        Anlamsal (semantic) arama yapar.

        İşlem adımları:
        1. Soruyu vektöre dönüştür (embed)
        2. ChromaDB'de en yakın vektörleri bul
        3. Güvenlik filtresini uygula (RBAC)
        4. Sonuçları döndür

        Args:
            query: Arama sorgusu (doğal dil)
            top_k: Kaç sonuç döndürülecek
            security_filter: İzin verilen güvenlik seviyeleri
                Örn: ["public", "internal"] → Sadece bu seviyeleri ara

        Returns:
            list[dict]: Her sonuç şu bilgileri içerir:
                - content: Bulunan metin parçası
                - metadata: Kaynak bilgileri
                - distance: Sorguya olan uzaklık (düşük = daha benzer)
                - relevance_score: Benzerlik skoru (0-1, yüksek = daha benzer)
        """
        provider = get_llm_provider()

        # Soruyu vektöre dönüştür
        query_embedding = await provider.embed(query)

        # ChromaDB where filtresi oluştur
        where_filter = None
        if security_filter:
            where_filter = {
                "security_level": {"$in": security_filter}
            }

        # ChromaDB'de arama yap
        results = self._collection.query(
            query_embeddings=[query_embedding.embedding],
            n_results=top_k,
            where=where_filter,
            include=["documents", "metadatas", "distances"],
        )

        # Sonuçları düzenli bir formata dönüştür
        search_results = []

        if results and results["documents"] and results["documents"][0]:
            for i in range(len(results["documents"][0])):
                distance = results["distances"][0][i] if results["distances"] else 0

                # Cosine mesafesi: 0 = aynı, 1 = ortogonal, 2 = zıt
                # Benzerlik skoru: 1 - mesafe → [0, 1] aralığında
                relevance = max(0.0, 1.0 - distance)

                search_results.append({
                    "content": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    "distance": round(distance, 4),
                    "relevance_score": round(relevance, 4),
                })

        return search_results

    def get_stats(self) -> dict:
        """Collection istatistiklerini döndürür."""
        return {
            "collection_name": self._collection.name,
            "total_chunks": self._collection.count(),
        }

    def clear(self):
        """Tüm vektörleri siler (test için)."""
        # Collection'ı silip yeniden oluştur (cosine ayarını koru)
        self._client.delete_collection(self._collection_name)
        self._collection = self._client.get_or_create_collection(
            name=self._collection_name,
            metadata=self._collection_metadata,
        )

    def close(self):
        """
        ChromaDB bağlantısını kapatır.
        Windows'ta dosya kilidi sorununu önlemek için gerekli.
        """
        del self._collection
        del self._client
        self._collection = None
        self._client = None
