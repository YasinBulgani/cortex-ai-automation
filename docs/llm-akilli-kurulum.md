# BGTS İçin Daha Akıllı LLM Kurulumu

Bu repo içinde LLM zaten birkaç yerde kullanılıyor:

- `backend/app/domains/ai/service.py`: OpenAI/Anthropic chat ve JSON üretimi
- `backend/app/domains/ai/gateway_client.py`: AI Gateway çağrıları
- `ai-gateway/`: Groq -> Gemini -> Ollama -> g4f fallback zinciri
- `backend/app/domains/tspm/`: test case, BDD, otomasyon ve chat servisleri

Sorun şu: mevcut yapı çoğunlukla "prompt gönder -> cevap al" şeklinde çalışıyor. Bu yüzden model bazen fazla genel konuşuyor, proje içindeki gerçek senaryo/gereksinim/hata kayıtlarını yeterince kullanmıyor.

## Bu değişiklikte ne eklendi?

İlk adım olarak query-aware grounding katmanı eklendi:

- `backend/app/domains/ai/context_builder.py`

Bu servis kullanıcı mesajına göre:

- ilgili senaryoları
- ilgili gereksinimleri
- son başarısız koşuları
- ilgili AI test case kayıtlarını
- gerekirse test veri setlerini

toplayıp LLM'e kompakt bir bağlam olarak veriyor.

Bu bağlam şu iki giriş noktasına bağlandı:

- `backend/app/domains/ai/router.py`
- `backend/app/domains/tspm/router.py`

Ayrıca chat prompt'ları grounding odaklı hale getirildi:

- `backend/app/domains/ai/service.py`
- `backend/app/domains/tspm/ai_chat_service.py`

## Neden bu yaklaşım?

Bu repo için en düşük riskli ve en hızlı kazanım sağlayan yöntem bu:

1. Mevcut veritabanı ve modeller zaten var.
2. Frontend ve gateway yapısını bozmadan kalite artışı sağlar.
3. Token maliyetini azaltır çünkü tüm proje yerine ilgili kayıtlar gönderilir.
4. Daha sonra gerçek RAG katmanına geçiş için iyi bir ara basamaktır.

## Bir sonraki doğru adım: Gerçek RAG

Bu ilk katman keyword/rule tabanlı retrieval yapar. Bir sonraki aşamada PGVector tabanlı semantic retrieval önerilir.

Önerilen mimari:

1. `tspm_scenarios`, `tspm_requirements`, `tspm_test_cases`, import edilen doküman chunk'ları için embedding üret.
2. Yeni tablo ekle:
   `ai_context_chunks(id, project_id, source_type, source_id, chunk_text, metadata, embedding)`
3. Doküman parse sonrası chunk'ları bu tabloya yaz.
4. Chat isteğinde:
   kullanıcı mesajı -> embedding -> vector search -> top-k chunk -> LLM
5. Cevap üretirken structured citations döndür:
   senaryo adı, gereksinim ID'si, koşu adı gibi.

## Bundan sonra önerdiğim 4 faz

### Faz 1
Grounded chat + seçmeli bağlam

Bu commit'te yapılan kısım.

### Faz 2
PGVector + semantic search

Şunlar eklenmeli:

- Postgres `vector` extension
- embedding üretim servisi
- chunk indexleme job'ı
- chat retrieval pipeline

### Faz 3
Tool-calling / function-calling

Model sadece konuşmasın, gerektiğinde şu araçları çağırabilsin:

- son koşu özetini getir
- coverage gaps getir
- belirli senaryoyu aç
- ilgili requirement linklerini getir
- failed execution detayını getir

Bu repo için en değerli tool'lar backend API üzerinden kolayca çıkarılabilir.

### Faz 4
Eval + guardrails

Eklenmesi gerekenler:

- prompt regression testi
- grounding doğruluk ölçümü
- hallucination kontrolü
- yanıt tipi bazlı kalite rubric'i

## OpenAI tarafında pratik öneri

Bu proje için iyi bir üretim akışı:

1. Basit sınıflama:
   soru coverage/debug/automation/data/chat hangisi
2. Buna göre retrieval:
   doğru tablo ve kayıtları çek
3. System prompt:
   rol + cevap kuralları
4. Context:
   sadece ilgili proje verisi
5. Output format:
   gerekirse JSON, gerekirse normal metin

Yani "daha akıllı LLM" için asıl fark modeli büyütmekten çok doğru bağlamı doğru anda vermek.

## Bu repo için teknik not

Eğer ikinci adımı da yapmak istersen en mantıklı yerler:

- embedding/indexleme: `backend/app/domains/ai/`
- chunk üretimi: `backend/app/domains/tspm/document_parser.py`
- chat orchestration: `backend/app/domains/tspm/ai_chat_service.py`
- gateway entegrasyonu: `backend/app/domains/ai/gateway_client.py`

## Kısa sonuç

Bu repo için önerilen sıra:

1. Grounding
2. Semantic retrieval
3. Tool calling
4. Eval/guardrail

Sadece model ismini büyütmek yerine bu sıralamayla gidersen LLM gerçekten daha "akıllı" görünür.
