# HTTP Client koleksiyonu

IntelliJ Ultimate'in native HTTP Client'ı ile çalışan istek koleksiyonu.

## Kullanım

1. IntelliJ'de istediğin `.http` dosyasını aç
2. Sağ-üst dropdown'da ortam seç: **dev** / **staging** / **prod**
3. Her isteğin başındaki yeşil ▶ butonuna bas (veya `Ctrl+Shift+F10` / `Cmd+Shift+F10`)
4. Yanıtlar IDE'nin sağ panelinde gözükür, JSON/headers/timing dahil

## Dosyalar

| Dosya | İçerik |
|---|---|
| `health.http` | Tüm servislerin sağlık endpoint'leri (Run All ile toplu test) |
| `cortex.http` | Cortex Dashboard API — test koşumu tetikleme, SSE log akışı, AI sınıflandırma |
| `ai-gateway.http` | AI Gateway provider + chat/embedding testleri |
| `web-routes.http` | Next.js product family sayfaları (200 kontrolü) |
| `http-client.env.json` | Ortam değişkenleri (dev/staging/prod) |

## Faydalı kısayollar

- `{{cortexDashboard}}` gibi placeholder'lar env.json'dan dolar
- `> {% client.global.set(...) %}` ile bir istekten gelen değeri sonraki istekte kullan
- Response history: View → Tool Windows → Services → HTTP Client

## Yeni endpoint eklerken

1. İlgili `.http` dosyasını aç
2. `###` ayırıcısı + `GET/POST {{var}}/path` formatı
3. Body için `Content-Type: application/json` header altına JSON
