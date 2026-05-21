# Aday Görüşme Analizi (LLM)

Her aday klasöründeki `gorusme_notlari.md` dosyasını OpenAI (GPT) ile analiz eder ve `analiz.json` olarak aynı klasöre yazar.

## Yapı

```
aday_analizi/
├── __init__.py
├── config.py       # ADAY_KLASORU, OPENAI_* ayarları
├── file_utils.py   # adaylari_bul, gorusme_notunu_oku
├── analyzer.py     # chatgpt_analiz_et, analiz_kaydet
├── main.py         # Tüm adaylar için döngü
├── requirements.txt
├── env.example    # .env için şablon (cp env.example .env)
├── adaylar/        # Aday klasörleri
│   └── {aday_adi}/
│       ├── gorusme_notlari.md   # girdi
│       └── analiz.json          # çıktı (bu script ile oluşur)
└── README.md
```

## Kurulum

```bash
cd aday_analizi
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp env.example .env
# .env içine OPENAI_API_KEY=sk-... ekleyin
```

## Kullanım

Proje kökünden (Paribu/):

```bash
python -m aday_analizi
```

Alternatif:

```bash
python -m aday_analizi.main
```

## Ortam Değişkenleri

| Değişken       | Zorunlu | Açıklama                          | Varsayılan   |
|----------------|---------|-----------------------------------|--------------|
| `OPENAI_API_KEY` | Evet   | OpenAI API anahtarı               | -            |
| `ADAY_KLASORU` | Hayır   | Aday klasörlerinin dizini         | `./adaylar`  |
| `OPENAI_MODEL` | Hayır   | Model (örn. gpt-4o, gpt-4o-mini)  | `gpt-4o-mini`|

## analiz.json formatı

LLM aşağıdaki yapıda JSON üretir:

- `genel_degerlendirme`: Kısa özet
- `guclu_yonler`: Liste
- `riskler`: Liste
- `seviye_tahmini`: `"Junior"` | `"Mid"` | `"Senior"`
- `karar_onerisi`: `"Olumlu"` | `"Beklemede"` | `"Olumsuz"`

Parse edilemezse `yorum` (ham metin) ve `parse_hatasi: true` yazılır.

## Örnek aday

`adaylar/ornek_aday/gorusme_notlari.md` örnek olarak eklenmiştir. İlk çalıştırmada bu aday için `analiz.json` oluşturulur.
