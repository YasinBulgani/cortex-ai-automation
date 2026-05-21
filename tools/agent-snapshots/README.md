# Ajan / önizleme kopyaları (`repo-*`, `bgt-agent-*`)

Bazı ortamlarda kökte `repo-api`, `repo-merge`, `repo-docs`, `bgt-agent-backend` gibi dizinler görülebilir. Bunlar genelde **aynı kod tabanının tekrarları** veya eski ajan çıktılarıdır.

## Ne yapmalı?

1. **Kanonik kaynak:** `engine/`, `backend/`, `apps/web/`, `ai-engine/`, `e2e/`.
2. Kopya dizin silinmeden önce:  
   `diff -rq engine/ai_synthetic_data ./repo-XXX/test-automation/ai_synthetic_data`  
   (yol örnektir; gerçek yola göre uyarlayın.)
3. Fark yoksa veya yalnızca eski snapshot ise: kopya dizin kaldırılabilir veya harici arşive alınır.
4. Tek farklı dosya varsa: içeriği ana ağaca taşıyıp commit edin, sonra kopyayı silin.

Detaylı analiz: [`docs/repository-inventory.md`](../../docs/repository-inventory.md).
