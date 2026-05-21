Görev:
Verilen test case listesini analiz ederek risk bazlı optimal regresyon seti öner.

Kurallar:
- Critical sete yalnızca deploy öncesi vazgeçilmez iş akışlarını koy.
- Standard set günlük veya CI için dengeli kapsam sunsun.
- Extended set kalan yüksek değerli kapsamı tamamlasın.
- Süre tahminleri gerçekçi olsun.
- Coverage yüzdesini abartma; belirsizlik varsa muhafazakar kal.
- Seçim kriterlerinde risk, değişim sıklığı, iş etkisi ve hata geçmişini referans al.

Şema:
{
  "regression_set": {
    "critical": {
      "description": "Her deploydan önce çalıştırılmalı",
      "test_ids": ["TC-001", "TC-002"],
      "estimated_duration_minutes": 15,
      "rationale": "Neden seçildi"
    },
    "standard": {
      "description": "Günlük CI/CD'de çalıştırılmalı",
      "test_ids": ["TC-003", "TC-004"],
      "estimated_duration_minutes": 45,
      "rationale": "Neden seçildi"
    },
    "extended": {
      "description": "Sprint sonu tam regresyon",
      "test_ids": ["TC-005"],
      "estimated_duration_minutes": 120,
      "rationale": "Neden seçildi"
    }
  },
  "selection_criteria": "Seçim kriterleri açıklaması",
  "coverage_percentage": 85
}
