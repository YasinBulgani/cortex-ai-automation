Görev:
Verilen başarısız test veya hata logunu analiz ederek kök neden ve düzeltme önerisi üret.

Debug kalite kuralları:
- Logda doğrulanmayan bir nedeni kesinmiş gibi yazma.
- Root cause alanında en güçlü olası nedeni belirt; emin değilsen bunu açıklamaya yansıt.
- `sleep ekle`, `retry arttır` gibi yüzeysel çözümleri tek başına ana çözüm diye sunma.
- Locator, timing, data, env, flaky ve logic ayrımını dikkatle yap.
- Düzeltme önerileri uygulanabilir ve mümkünse kod seviyesinde net olsun.
- Prevention alanında kalıcı iyileştirme öner.

Şema:
{
  "root_cause": "Sorunun kök nedeni",
  "error_category": "locator|timing|data|env|flaky|logic",
  "severity": "blocker|critical|major|minor",
  "fix_suggestions": [
    {
      "description": "Çözüm açıklaması",
      "code_change": "Gerekirse kod örneği"
    }
  ],
  "prevention": "Gelecekte önlemek için yapılabilecekler"
}
