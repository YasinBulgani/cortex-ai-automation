# BGTS Test Dönüşüm — Automation Proxy & Notification Testleri

**Doküman Versiyonu:** 1.0  
**Tarih:** 2026-04-03  
**Kapsam:** Engine proxy, WebSocket notification endpoint, NotificationBell bileşeni

---

## TS-PROXY-01: Automation Engine Proxy Testleri

**Router:** `backend/app/domains/automation/router.py`  
**Endpoint Prefix:** `/api/v1/automation`

### Kaynak Analiz
- `/automation/health` — Engine sağlık kontrolü (httpx ile `ENGINE_BASE/health`)
- `/automation/proxy/{path}` — Tüm HTTP metodları ile Engine'e transparent proxy
- Timeout: 60sn (proxy), 5sn (health)
- Engine erişilemezse: `{"status": "unreachable"}` döner

### Test Senaryoları

| ID | Başlık | Tip | Öncelik | Test Adımları | Beklenen |
|----|--------|-----|---------|---------------|----------|
| PRX-01 | Engine health check — erişilebilir | Pozitif | High | GET `/automation/health`, Engine çalışıyor | Engine'den gelen JSON yanıt |
| PRX-02 | Engine health check — erişilemez | Exception | High | GET `/automation/health`, Engine kapalı | `{"status": "unreachable", "engine_url": "..."}` |
| PRX-03 | Proxy GET isteği | Pozitif | High | GET `/automation/proxy/api/features` | Engine'den gelen yanıt aynı status + body |
| PRX-04 | Proxy POST isteği | Pozitif | High | POST `/automation/proxy/api/features` | Body ve headers Engine'e doğru aktarılır |
| PRX-05 | Proxy DELETE isteği | Pozitif | Medium | DELETE `/automation/proxy/api/features/1` | Engine'e DELETE iletilir |
| PRX-06 | Proxy timeout (60s) | Exception | Medium | Engine 60s yanıt vermezse | Timeout hatası; 504 veya 502 |
| PRX-07 | Proxy header filtering | Güvenlik | High | `Host`, `Content-Length` header'ları filtreleniyor mu | Proxy yasaklı header'ları iletmez |
| PRX-08 | Proxy SSRF koruması | Güvenlik | Critical | `/automation/proxy/http://internal-service` | İnternal URL'lere erişim engellenmeli |
| PRX-09 | Proxy query parameters | Pozitif | Medium | `?page=1&limit=10` ile GET | Query params Engine'e aktarılır |
| PRX-10 | Engine 500 döndüğünde proxy davranışı | Exception | Medium | Engine 500 Internal Error döner | Proxy aynı 500'ü döner; crash olmaz |

---

## TS-WS-01: WebSocket Notification Backend Testleri

**Router:** `backend/app/domains/notifications/router.py`  
**Endpoint:** `ws://.../api/v1/ws/notifications?token=<JWT>`

### Kaynak Analiz
- Token query parameter'dan alınır
- `decode_token(token)` ile doğrulanır; geçersizse `code=4001` ile kapatılır
- `user_id` (`sub` claim) yoksa `code=4001` ile kapatılır
- `ConnectionManager` ile kullanıcı bazlı bağlantı yönetimi
- Disconnect handling mevcut

### Test Senaryoları

| ID | Başlık | Tip | Öncelik | Beklenen |
|----|--------|-----|---------|----------|
| WS-B01 | Geçerli token ile WebSocket bağlantısı | Pozitif | Critical | Bağlantı kabul edilir; manager'a eklenir |
| WS-B02 | Geçersiz token ile WebSocket bağlantısı | Negatif | Critical | Bağlantı `code=4001` ile kapatılır |
| WS-B03 | Boş token ile WebSocket bağlantısı | Negatif | Critical | Bağlantı `code=4001` ile kapatılır |
| WS-B04 | Token olmadan WebSocket bağlantısı | Negatif | Critical | Query param yoksa `code=4001` |
| WS-B05 | Expired token ile WebSocket bağlantısı | Negatif | High | `decode_token` exception → `code=4001` |
| WS-B06 | Bağlantı sonrası mesaj broadcast | Pozitif | High | Manager üzerinden gönderilen mesaj client'a ulaşır |
| WS-B07 | Client disconnect handling | Pozitif | Medium | `WebSocketDisconnect` yakalanır; manager'dan çıkarılır |
| WS-B08 | Çoklu kullanıcı — mesaj izolasyonu | Pozitif | High | User-A'ya gönderilen mesaj User-B'ye gitmez |
| WS-B09 | Aynı kullanıcı çoklu bağlantı | Pozitif | Medium | Her iki bağlantıya da mesaj gider |
| WS-B10 | Büyük mesaj gönderimi | Boundary | Medium | 1MB+ mesaj gönderimi | Frame limit kontrolü |

---

## TS-NOTIF-01: NotificationBell Bileşeni (Frontend) Testleri

**Bileşen:** `apps/web/components/NotificationBell.tsx`

| ID | Başlık | Tip | Öncelik | Beklenen |
|----|--------|-----|---------|----------|
| NB-01 | Bell ikonu görünür | Pozitif | Medium | Header'da bildirim zili görünür |
| NB-02 | Bağlantı durumu göstergesi | Pozitif | Medium | WS connected → yeşil nokta; disconnected → kırmızı |
| NB-03 | Yeni bildirim badge'i | Pozitif | High | Okunmamış bildirim varsa sayı badge'i |
| NB-04 | Bildirim dropdown açılması | Pozitif | Medium | Tıklama ile bildirim listesi açılır |
| NB-05 | Bildirim listesi FIFO (max 50) | Boundary | Low | 50'den fazla bildirimde en eskiler düşer |

---

## Toplam Proxy & Notification Test Sayısı: 25

| Kategori | Sayı |
|----------|------|
| Engine Proxy | 10 |
| WebSocket Backend | 10 |
| NotificationBell UI | 5 |

---

## TÜM DOKÜMANLAR — NİHAİ GENEL TOPLAM

| Doküman | Test Sayısı |
|---------|------------|
| Ana Test Tasarımı (TSPM) | 75 |
| E2E UI Senaryoları | 59 |
| Güvenlik | 33 |
| Performans | 28 |
| RBAC Matrisi | 180+ |
| API Contract | 45+ |
| Cross-Cutting | 42 |
| İleri Seviye | 84 |
| Smoke / Release | 30 |
| Uzmanlaşmış (WS, i18n, Edge) | 49 |
| n8n + AI Chat | 24 |
| Sentetik Veri Modülü | 33 |
| Engine Proxy & Notifications | 25 |
| **BÜYÜK GENEL TOPLAM** | **707+** |
