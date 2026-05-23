# BGTS Test Dönüşüm — n8n Workflow & AI Chat Test Senaryoları

**Doküman Versiyonu:** 1.0  
**Tarih:** 2026-04-03  
**Kapsam:** n8n Workflow entegrasyonu, AI Chat sessions (model tabanlı analiz)

> Bu senaryolar `TspmN8nWorkflow`, `TspmN8nExecution`, `AiChatSession`, `AiChatMessage` modelleri temel alınarak hazırlanmıştır.

---

## TS-N8N-01: n8n Workflow Entegrasyonu

### Kaynak Model Analizi

```
TspmN8nWorkflow
├── project_id (FK → tspm_projects)
├── n8n_workflow_id (string)
├── name, description
├── trigger_on: "manual" | diğer
├── entity_type: opsiyonel
├── is_active: boolean
├── webhook_path: opsiyonel
├── config: JSONB
└── executions → TspmN8nExecution[]

TspmN8nExecution
├── workflow_link_id (FK → n8n_workflows)
├── n8n_execution_id (string)
├── status: "running" | "completed" | "failed"
├── input_data, output_data: JSONB
├── error: Text
├── started_at, finished_at
```

### Test Senaryoları

| ID | Başlık | Tip | Öncelik | Beklenen |
|----|--------|-----|---------|----------|
| N8N-01 | n8n workflow kaydı oluşturma | Pozitif | High | Workflow projeye bağlanır; is_active=true |
| N8N-02 | Workflow listesi görüntüleme | Pozitif | Medium | Projeye ait workflow'lar listelenir |
| N8N-03 | Workflow etkinleştirme/devre dışı bırakma | Pozitif | Medium | is_active toggle edilir |
| N8N-04 | Manuel workflow tetikleme | Pozitif | High | Execution kaydı oluşturulur; status: "running" |
| N8N-05 | Workflow execution başarılı tamamlanma | Pozitif | High | Status: "completed"; output_data dolu; finished_at set |
| N8N-06 | Workflow execution başarısız | Negatif | High | Status: "failed"; error mesajı dolu |
| N8N-07 | Webhook callback ile durum güncelleme | Pozitif | Critical | Signed webhook ile execution statusü güncellenir |
| N8N-08 | Invalid webhook signature reddi | Negatif | Critical | Geçersiz imza ile gelen callback reddedilir |
| N8N-09 | Workflow silme (cascade executions) | Pozitif | Medium | Workflow ve tüm execution'ları silinir |
| N8N-10 | Proje silindiğinde workflow temizliği | Pozitif | High | Cascade ile tüm workflow'lar silinir |
| N8N-11 | Aynı n8n_workflow_id ile duplicate kayıt | Boundary | Medium | Aynı ID ile birden fazla kayıt oluşturulabilir mi? Unique constraint kontrolü |
| N8N-12 | Execution timeout yönetimi | Exception | Medium | Uzun süre "running" kalan execution timeout ile "failed" olmalı |

---

## TS-CHAT-01: AI Chat Session Testleri

### Kaynak Model Analizi

```
AiChatSession
├── project_id (FK → tspm_projects)
├── user_id (FK → sd_users)
├── title: "Yeni Sohbet" (varsayılan)
├── created_at, updated_at
└── messages → AiChatMessage[] (ordered by created_at)

AiChatMessage
├── session_id (FK → ai_chat_sessions)
├── role: "user" | "assistant"
├── content: Text
├── created_at
```

### Test Senaryoları

| ID | Başlık | Tip | Öncelik | Beklenen |
|----|--------|-----|---------|----------|
| CHAT-01 | Yeni chat session oluşturma | Pozitif | High | Session oluşturulur; title: "Yeni Sohbet" |
| CHAT-02 | Kullanıcı mesajı gönderme | Pozitif | High | Message kaydı oluşturulur; role: "user" |
| CHAT-03 | AI yanıtı alma | Pozitif | High | Assistant mesajı oluşturulur; role: "assistant" |
| CHAT-04 | Session mesaj geçmişi | Pozitif | Medium | Mesajlar created_at'e göre sıralı döner |
| CHAT-05 | Session başlığı güncelleme | Pozitif | Low | Title değiştirilebilir |
| CHAT-06 | Farklı kullanıcı başka session'a erişemez | Negatif | Critical | Kullanıcı yalnızca kendi session'larını görebilir |
| CHAT-07 | Session silme (cascade messages) | Pozitif | Medium | Session ve tüm mesajları silinir |
| CHAT-08 | Boş mesaj gönderme | Boundary | Medium | 422 veya reddedilir |
| CHAT-09 | Çok uzun mesaj (10.000+ karakter) | Boundary | Low | Kaydedilir veya limit uygulanır |
| CHAT-10 | Eşzamanlı mesaj gönderme | Concurrency | Medium | Mesaj sırası korunur; duplicate yok |
| CHAT-11 | Proje silindiğinde session temizliği | Pozitif | High | Cascade ile tüm session ve mesajlar silinir |
| CHAT-12 | LLM servisi erişilemezken mesaj gönderme | Exception | High | Kullanıcı mesajı kaydedilir; AI yanıtı hata mesajı ile döner |

---

## Toplam n8n + AI Chat Test Sayısı: 24

| Kategori | Sayı |
|----------|------|
| n8n Workflow | 12 |
| AI Chat Session | 12 |

---

## Güncellenmiş Genel Toplam

| Doküman | Test Sayısı |
|---------|------------|
| Ana Test Tasarımı | 75 |
| E2E UI Senaryoları | 59 |
| Güvenlik | 33 |
| Performans | 28 |
| RBAC Matrisi | 180+ |
| API Contract | 45+ |
| Cross-Cutting | 42 |
| İleri Seviye | 84 |
| Smoke / Release | 30 |
| Uzmanlaşmış | 49 |
| n8n + AI Chat | 24 |
| **GENEL TOPLAM** | **649+** |
