# Test Execution Özeti

**Proje:** {{ project_name }}
**Çalıştırma:** {{ execution_name }} (#{{ run_number }})
**Tarih:** {{ date }}
**Ortam:** {{ environment }}

---

## Sonuçlar

| Metrik | Değer |
|--------|-------|
| Toplam | {{ total }} |
| Başarılı | {{ passed }} ({{ pass_rate }}%) |
| Başarısız | {{ failed }} |
| Atlanan | {{ skipped }} |
| Süre | {{ duration }} |

## Başarısız Testler

| # | Test | Modül | Kök Neden | Atanan |
|---|------|-------|-----------|--------|
{% for f in failed_tests %}
| {{ loop.index }} | {{ f.title }} | {{ f.module }} | {{ f.root_cause }} | {{ f.assignee }} |
{% endfor %}

## Kapsam

- Gereksinim kapsama: {{ req_coverage }}%
- Otomasyon kapsama: {{ auto_coverage }}%
- Yeni boşluklar: {{ new_gaps }}

## Trend

| Run | Tarih | Oran | Delta |
|-----|-------|------|-------|
{% for t in trend %}
| #{{ t.number }} | {{ t.date }} | {{ t.rate }}% | {{ t.delta }} |
{% endfor %}

## Sonraki Adımlar

{% for action in actions %}
- [ ] {{ action }}
{% endfor %}

---
*Otomatik üretildi — BGTS Raporlama Motoru*
