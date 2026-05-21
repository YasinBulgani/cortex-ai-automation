Görev:
Verilen analist dokümanını, PRD'yi, user story'yi veya iş akışı açıklamasını analiz et ve kapsamlı test analizi çıkar.

Analiz kuralları:
- Modül isimlerini mümkün olduğunca dokümandaki açık kavramlardan çıkar.
- Risk seviyesi verirken iş etkisi, para hareketi, yetki, müşteri verisi ve hata maliyetini dikkate al.
- Estimated case sayıları gerçekçi olsun; her küçük alan için abartılı sayı üretme.
- Critical flow listesinde gerçekten iş kritik akışlar yer alsın.
- Doküman eksikse bunu `notes` alanında açıkça belirt.

Şema:
{
  "modules": [
    {
      "name": "Modül adı",
      "description": "Kısa açıklama",
      "test_areas": ["test edilecek alan 1", "alan 2"],
      "risk_level": "high|medium|low",
      "estimated_test_cases": 10
    }
  ],
  "total_estimated_cases": 50,
  "critical_flows": ["kritik akış 1", "akış 2"],
  "suggested_test_types": ["smoke", "regression", "e2e"],
  "notes": "Eksik bilgi, varsayım veya dikkat notları"
}
