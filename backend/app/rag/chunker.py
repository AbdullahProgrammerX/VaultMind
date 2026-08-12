"""
============================================================
VaultMind — Metin Parçalama (Text Chunker)
============================================================

BU DOSYA NE YAPIYOR?
--------------------
Büyük dokümanları küçük, anlamlı parçalara (chunk) böler.
Her chunk ayrı ayrı embed edilerek vektör veritabanına kaydedilir.

NEDEN CHUNKING GEREKLİ?
------------------------
1. LLM'lerin bağlam penceresi (context window) sınırlıdır
2. Büyük metinler tek vektöre çevrilirse anlam kaybolur
3. Küçük parçalar daha doğru arama sonuçları verir

CHUNKING STRATEJİLERİ:
-----------------------
a) Sabit boyut: Her chunk tam N karakter (basit ama kötü)
   "Yıllık izin hak" | "kı 14 gündür. Ç" | "alışanlar..."
   → Cümle ortasından keser, anlam kaybolur

b) Recursive (VaultMind'ın kullandığı): Doğal sınırlarda böler
   Önce başlıklarda (##), sonra paragraf aralarında (\n\n),
   sonra cümle sonlarında (.), en son kelimelerde böler
   → Anlam korunur!

c) Overlap (örtüşme): Parçalar arasında bağlam paylaşımı
   Chunk 1: "İzin hakkı 14 gündür. Kullanılmayan izinler..."
   Chunk 2: "Kullanılmayan izinler devredilir. Evlilik izni..."
   → "Kullanılmayan izinler" her iki chunk'ta da var
   → Arama sırasında bağlam kaybı önlenir

ÖĞRENME NOKTALARI:
-----------------
1. Chunking stratejileri — Metin bölme yaklaşımları
2. Overlap — Parçalar arası bağlam paylaşımı
3. Metadata preservation — Her parçanın kaynağını bilmesi
"""

from dataclasses import dataclass, field


@dataclass
class TextChunk:
    """
    Bir metin parçasını (chunk) temsil eder.

    Her chunk şunları bilir:
    - content: Parçanın metni
    - metadata: Hangi dokümanın hangi bölümünden geldiği
    - chunk_index: Doküman içindeki sırası (0, 1, 2, ...)

    Bu bilgiler, RAG cevabında kaynak gösterme (citation) için kritiktir:
    "Bu bilgi 'ik_politikasi.md' dokümanının 3. bölümünden alınmıştır."
    """
    content: str                                  # Parça metni
    metadata: dict = field(default_factory=dict)   # Kaynak bilgileri
    chunk_index: int = 0                           # Doküman içi sıra


def chunk_text(
    text: str,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
    metadata: dict | None = None,
) -> list[TextChunk]:
    """
    Bir metni akıllı parçalara böler (Recursive Character Splitting).

    NASIL ÇALIŞIR?
    1. Metni doğal ayırıcılarda böler (öncelik sırasıyla):
       - Başlıklar (## ) → En iyi bölme noktası
       - Çift yeni satır (\n\n) → Paragraf arası
       - Tek yeni satır (\n) → Satır arası
       - Cümle sonu (. ) → Cümle arası
       - Boşluk ( ) → Kelime arası
    2. Her parça chunk_size'ı geçmeyecek şekilde birleştirilir
    3. Parçalar arası chunk_overlap kadar örtüşme bırakılır

    Args:
        text: Bölünecek metin
        chunk_size: Maksimum parça boyutu (karakter)
                    1000 karakter ≈ 150-200 kelime ≈ yarım sayfa
        chunk_overlap: Parçalar arası örtüşme (karakter)
                       200 karakter ≈ 30-40 kelime
        metadata: Her parçaya eklenecek metadata (kaynak dosya bilgisi)

    Returns:
        list[TextChunk]: Parça listesi

    Kullanım:
        chunks = chunk_text(
            text="Uzun doküman metni...",
            chunk_size=1000,
            chunk_overlap=200,
            metadata={"source": "ik_politikasi.md"}
        )
        for chunk in chunks:
            print(f"Chunk {chunk.chunk_index}: {len(chunk.content)} karakter")
    """
    if not text or not text.strip():
        return []

    base_metadata = metadata or {}

    # Doğal ayırıcılar (öncelik sırasıyla)
    # Öğrenme notu: Bu sıralama çok önemli — önce en büyük
    # birimde (başlık), sonra giderek küçülen birimlerde böleriz
    separators = [
        "\n## ",    # Markdown başlıkları (en doğal bölme noktası)
        "\n### ",   # Alt başlıklar
        "\n\n",     # Paragraf arası
        "\n",       # Satır arası
        ". ",       # Cümle sonu
        " ",        # Kelime arası (son çare)
    ]

    # Recursive splitting — metni parçalara ayır
    raw_chunks = _recursive_split(text, separators, chunk_size)

    # Overlap uygula ve TextChunk nesnelerine dönüştür
    chunks = []
    for i, chunk_text_content in enumerate(raw_chunks):
        chunk_content = chunk_text_content.strip()
        if not chunk_content:
            continue

        chunk_metadata = {
            **base_metadata,
            "chunk_index": i,
            "chunk_size": len(chunk_content),
        }

        chunks.append(TextChunk(
            content=chunk_content,
            metadata=chunk_metadata,
            chunk_index=i,
        ))

    # Overlap ekleme — önceki chunk'ın sonunu mevcut chunk'ın başına ekle
    if chunk_overlap > 0 and len(chunks) > 1:
        chunks = _apply_overlap(chunks, chunk_overlap)

    return chunks


def _recursive_split(
    text: str,
    separators: list[str],
    chunk_size: int,
) -> list[str]:
    """
    Metni recursive olarak parçalar.

    Öğrenme notu — Recursive (özyinelemeli) yaklaşım:
    1. İlk ayırıcıyı dene (örn: "\\n## ")
    2. Eğer parçalar hâlâ çok büyükse, bir sonraki ayırıcıyı dene
    3. Hiçbir ayırıcı işe yaramazsa, sabit boyutta kes (son çare)
    """
    # Temel durum: Metin zaten yeterince küçükse, olduğu gibi döndür
    if len(text) <= chunk_size:
        return [text]

    # Hiç ayırıcı kalmadıysa, sabit boyutta kes (son çare)
    if not separators:
        return _force_split(text, chunk_size)

    # İlk ayırıcıyı dene
    separator = separators[0]
    remaining_separators = separators[1:]

    parts = text.split(separator)

    # Eğer ayırıcı metinde yoksa, bir sonraki ayırıcıyı dene
    if len(parts) == 1:
        return _recursive_split(text, remaining_separators, chunk_size)

    # Parçaları chunk_size'ı geçmeyecek şekilde birleştir
    result = []
    current_chunk = ""

    for part in parts:
        # Bu parçayı eklersek chunk_size'ı aşar mıyız?
        test_chunk = current_chunk + separator + part if current_chunk else part

        if len(test_chunk) <= chunk_size:
            current_chunk = test_chunk
        else:
            # Mevcut chunk'ı kaydet
            if current_chunk:
                result.append(current_chunk)

            # Yeni parça tek başına çok büyükse, recursive olarak böl
            if len(part) > chunk_size:
                sub_chunks = _recursive_split(part, remaining_separators, chunk_size)
                result.extend(sub_chunks)
                current_chunk = ""
            else:
                current_chunk = part

    # Son kalan chunk'ı ekle
    if current_chunk:
        result.append(current_chunk)

    return result


def _force_split(text: str, chunk_size: int) -> list[str]:
    """
    Metni sabit boyutta keser (son çare).
    Kelime sınırına dikkat eder — kelime ortasından kesmez.
    """
    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size

        # Metin sonuna geldiysek
        if end >= len(text):
            chunks.append(text[start:])
            break

        # Kelime sınırını bul (en yakın boşluk)
        space_idx = text.rfind(" ", start, end)
        if space_idx > start:
            end = space_idx

        chunks.append(text[start:end])
        start = end

    return chunks


def _apply_overlap(chunks: list[TextChunk], overlap_size: int) -> list[TextChunk]:
    """
    Parçalar arasına örtüşme (overlap) ekler.

    Neden overlap?
    Diyelim orijinal metin:
        "...izin hakkı 14 gündür. | Kullanılmayan izinler devredilebilir..."
        ← Chunk 1 sonu →         ← Chunk 2 başı →

    Kullanıcı "kullanılmayan izin devri" diye sorarsa,
    Chunk 2'yi bulur AMA bağlamı (14 gün bilgisi) Chunk 1'de kalmıştır.

    Overlap ile:
        Chunk 1: "...izin hakkı 14 gündür. Kullanılmayan izinler devr..."
        Chunk 2: "Kullanılmayan izinler devredilebilir. Evlilik izni..."
        → Her iki chunk'ta da bağlam var!
    """
    if len(chunks) <= 1:
        return chunks

    overlapped = [chunks[0]]  # İlk chunk'a overlap eklenmez

    for i in range(1, len(chunks)):
        prev_content = chunks[i - 1].content
        current_content = chunks[i].content

        # Önceki chunk'ın son overlap_size karakterini al
        overlap_text = prev_content[-overlap_size:] if len(prev_content) > overlap_size else prev_content

        # Kelime sınırında kes (kelime ortasından başlama)
        space_idx = overlap_text.find(" ")
        if space_idx > 0:
            overlap_text = overlap_text[space_idx + 1:]

        # Overlap'i mevcut chunk'ın başına ekle
        new_content = overlap_text + " " + current_content

        new_metadata = {
            **chunks[i].metadata,
            "has_overlap": True,
            "overlap_chars": len(overlap_text),
        }

        overlapped.append(TextChunk(
            content=new_content,
            metadata=new_metadata,
            chunk_index=chunks[i].chunk_index,
        ))

    return overlapped
