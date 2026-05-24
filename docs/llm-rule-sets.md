# LLM Rule Sets

Bu dosya BGTS içinde daha kaliteli LLM çıktıları üretmek için kullanılan ana kural setlerini özetler.

## Kanonik Kaynak

- Merkezi prompt yönetimi [prompt_center/manifest.json](/Users/yasin_bulgan/Desktop/Cortex_Ai_Automation/prompt_center/manifest.json) üzerinden yapılır.
- Ortak policy parçaları [prompt_center/policies](/Users/yasin_bulgan/Desktop/Cortex_Ai_Automation/prompt_center/policies) altında tutulur.
- Gateway görev promptları [prompt_center/tasks](/Users/yasin_bulgan/Desktop/Cortex_Ai_Automation/prompt_center/tasks) altında tutulur.
- Engine servis promptları [prompt_center/engine](/Users/yasin_bulgan/Desktop/Cortex_Ai_Automation/prompt_center/engine) altında tutulur.
- [ai-gateway/app/core/prompts.py](/Users/yasin_bulgan/Desktop/Cortex_Ai_Automation/ai-gateway/app/core/prompts.py) yalnızca uyumluluk katmanıdır; kanonik içerik değildir.

## Evrensel Kurallar

- Uydurma bilgi üretme.
- Açık bilgi ile çıkarımı karıştırma.
- İstenen çıktı formatının dışına çıkma.
- Tekrarlı ve düşük değerli maddeler üretme.
- Test edilebilir, ölçülebilir ve uygulanabilir çıktı üretme.
- Bankacılık bağlamında yetki, limit, bakiye etkisi, hata yönetimi ve audit izini dikkate alma.

## Test Case Üretimi

- Pozitif, negatif, boundary ve edge-case kapsamı düşün.
- Her vaka ayrı bir davranış doğrulasın.
- Beklenen sonuç gözlemlenebilir olsun.
- Gereksiz duplicate case üretme.
- Önceliklendirmeyi iş riskiyle hizala.

## Gherkin Üretimi

- Türkçe ve iş davranışı odaklı başlıklar kullan.
- Her senaryoda en az bir anlamlı Then olsun.
- Background yalnızca ortak ön koşullar için kullanılsın.
- Gerektiğinde Scenario Outline + Examples tercih et.
- DSL ile uyumlu step üretmeye çalış; gerekirse `@needs-dsl` etiketi kullan.

## Kod Üretimi

- Stable locator önceliği: data-testid > role > label > text > CSS.
- Hard wait, sleep ve kırılgan selector kullanma.
- Kod derlenebilir ve mevcut framework stiline uyumlu olsun.
- Assertion'lar iş sonucunu doğrulasın.

## Debug Çıktıları

- Log'da doğrulanmayan nedeni kesin gerçek gibi yazma.
- En güçlü olası kök nedeni belirt.
- Yüzeysel çözüm yerine kalıcı çözüm öner.
- Gerekirse prevention maddesiyle sistemsel iyileştirme öner.

## Self-Healing ve Locator Onarma

- Locator sadece verilen accessibility tree'den türetilsin.
- Öncelik: data-testid > role + name > label > text > CSS.
- Dinamik index, uzun CSS zinciri ve kırılgan selector'lardan kaçınılsın.
- Çıktı tek satır, tek locator ve açıklamasız olsun.

## Assertion Analizi

- Eksik doğrulamalar iş sonucuna göre önceliklendirilsin.
- Trivial assertion yerine davranış, veri ve yan etki doğrulansın.
- UI testlerinde yalnızca görünürlük değil, anlamlı içerik veya durum değişimi de kontrol edilsin.
- API testlerinde status code yanında payload ve kalıcı etki de düşünülsün.

## Güvenlik Analizi

- Tarama çıktısında olmayan sömürü kabiliyeti kesin gerçek gibi yazılmasın.
- OWASP ve bankacılık riski birlikte değerlendirilsin.
- False positive olasılığı ve efor tahmini belirtilebilsin.
- Tekrarlı bulgular gruplanıp uygulanabilir düzeltme önerisi verilsin.

## Nerede Uygulanıyor

- [prompt_center/manifest.json](/Users/yasin_bulgan/Desktop/Cortex_Ai_Automation/prompt_center/manifest.json)
- [prompt_center/policies](/Users/yasin_bulgan/Desktop/Cortex_Ai_Automation/prompt_center/policies)
- [prompt_center/tasks](/Users/yasin_bulgan/Desktop/Cortex_Ai_Automation/prompt_center/tasks)
- [prompt_center/engine](/Users/yasin_bulgan/Desktop/Cortex_Ai_Automation/prompt_center/engine)
- [ai-gateway/app/core/prompts.py](/Users/yasin_bulgan/Desktop/Cortex_Ai_Automation/ai-gateway/app/core/prompts.py)
- [engine/prompts/bdd_generator_system.md](/Users/yasin_bulgan/Desktop/Cortex_Ai_Automation/engine/prompts/bdd_generator_system.md)
- [engine/prompts/test_generator_system.md](/Users/yasin_bulgan/Desktop/Cortex_Ai_Automation/engine/prompts/test_generator_system.md)
- [engine/prompts/self_healer_system.md](/Users/yasin_bulgan/Desktop/Cortex_Ai_Automation/engine/prompts/self_healer_system.md)
- [engine/prompts/assertion_analyzer_system.md](/Users/yasin_bulgan/Desktop/Cortex_Ai_Automation/engine/prompts/assertion_analyzer_system.md)
- [engine/prompts/security_analyzer_system.md](/Users/yasin_bulgan/Desktop/Cortex_Ai_Automation/engine/prompts/security_analyzer_system.md)
