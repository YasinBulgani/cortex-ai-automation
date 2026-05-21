# AI Workflow Incident Runbook

Bu runbook, AI workflow operasyon olaylarinda uygulanacak ilk mudahale
adimlarini standartlastirir.

## 1. DLQ artisi

Belirti:

- `dead_letters_total` artar.
- `ai_workflow_dead_letters_total` alert'i calar.
- `/ai-workflows` panelinde son DLQ kayitlari gorunur.

Ilk kontrol:

```bash
scripts/ops/ai-workflow-release-signoff.py --profile quick
```

Yapilacaklar:

- DLQ kaydindaki `queue_name`, `reason`, `run_id` ve `last_error` alanlarini incele.
- Ayni hata tipi tekrar ediyorsa yeni workflow enqueue islemini durdur.
- Queue/worker ayakta mi kontrol et.
- Hata artifact ya da schema kaynakliysa ilgili run'in event listesini release ticket'a ekle.

Stop condition:

- Ayni hata 3 veya daha fazla run'da tekrarlarsa yeni AI workflow release'i durdurulur.

## 2. Queue backlog

Belirti:

- Queue depth yukselir.
- `oldest_active_seconds` beklenen SLO'yu asar.

Ilk kontrol:

```bash
docker-compose ps ai-worker redis
docker-compose logs --tail=200 ai-worker
```

Yapilacaklar:

- Worker sayisi, Redis baglantisi ve RQ queue adini kontrol et.
- Worker restart sadece ayni run'lar Postgres'te durable oldugu dogrulandiktan sonra yapilir.
- Backlog cost artisiyla beraber geliyorsa budget gate ve provider latency kontrol edilir.

Stop condition:

- `oldest_active_seconds` 30 dakikayi asarsa operator onayi olmadan yeni bulk workflow baslatilmaz.

## 3. Artifact integrity failure

Belirti:

- Artifact download `409` doner.
- Event listesinde `artifact_integrity_failed` gorulur.
- `BgtsAiWorkflowArtifactIntegrityFailure` alert'i calar.

Ilk kontrol:

```bash
scripts/ops/ai-workflow-release-signoff.py --profile quick
```

Yapilacaklar:

- Artifact dosyasinin SHA-256 degeri ile kayitli metadata karsilastirilir.
- Dosya beklenmeden degismisse artifact volume mount, retention job ve manuel dosya islemleri incelenir.
- Run tamamlanmis olsa bile ilgili artifact release kaniti olarak kullanilmaz.
- Gerekirse workflow tekrar uretilir.

Stop condition:

- Integrity failure olan artifact kullanilarak approval veya release verilemez.

## 4. Schema failed_validation artisi

Belirti:

- Run status `failed_validation`.
- Schema alert veya eval gate fail.

Ilk kontrol:

```bash
PYTHONPATH=backend pytest \
  backend/app/domains/agents/v2/tests/test_ai_gateway.py \
  backend/app/domains/agents/v2/tests/test_run_store_and_api.py -q
```

Yapilacaklar:

- Prompt manifest degisti mi kontrol et:

```bash
python3 scripts/ops/check-prompt-manifest.py
```

- Provider/model degisimi olduysa gateway trace ve task schema policy incelenir.
- Fail-open workaround uygulanmaz; schema uyumu duzeltilir.

Stop condition:

- `failed_validation` sebebi aciklanmadan production release onayi verilmez.

## 5. Cost spike

Belirti:

- Workflow cost veya token metrikleri normal bandi asar.

Ilk kontrol:

```bash
scripts/ops/ai-workflow-release-signoff.py --profile quick
```

Yapilacaklar:

- Son run'larda `workflow_type`, `tokens_used`, `llm_calls_count` ve cache durumlari incelenir.
- Budget preflight kapaliysa release durdurulur.
- Provider fallback loop veya retry storm var mi kontrol edilir.

Stop condition:

- Tenant/default budget dogrulanmadan yuksek hacimli workflow calistirilmaz.

## 6. Retention job failure

Belirti:

- `AI Workflow Artifact Retention` workflow fail olur.
- Disk kullanim uyarisi gelir.

Ilk kontrol:

```bash
scripts/ops/ai-workflow-artifact-retention.py --days 30
```

Yapilacaklar:

- Dry-run JSON icindeki `skipped_reason`, `errors`, `bytes_reclaimable` incelenir.
- `--apply` sadece operator onayi ve backup sonrasi calistirilir.
- Artifact path'leri `artifacts_dir` disina cikiyorsa cleanup uygulanmaz.

Stop condition:

- Backup olmadan destructive retention apply yapilmaz.
