# AI Workflow Release Signoff Runbook

Bu runbook, AI workflow katmaninin release oncesi nasil kanitlanacagini
standartlastirir. Amac, "lokalde calisti" bilgisini tekil ve denetlenebilir
bir JSON evidence pack haline getirmek, staging/prod adimlarini ise yalnizca
operator onayi ile calistirmaktir.

## 1. Local full gate

Release dalinda once tum yerel ve zarar vermeyen kontrolleri calistir:

```bash
scripts/ops/ai-workflow-release-signoff.py --profile full
```

Beklenen sonuc:

- `release_decision` degeri `needs_external_soak_and_dr_signoff` olur.
- `failed_required_checks` bos olur.
- `reports/ai-workflow-signoff-*.json` uretilir.
- `workflow_soak` ve `dr_restore_drill` adimlari `skipped` kalir; bu normaldir.

Bu adim; prompt manifest lock, direct LLM import guard, script compile,
artifact retention dry-run, bash syntax, YAML parse, compose config, backend
workflow testleri ve frontend type-check kontrollerini tek raporda toplar.

PR'larda ayni kanit zincirinin hizli profili otomatik olarak
`.github/workflows/ai-workflow-release-signoff.yml` tarafindan calistirilir.
Manuel `workflow_dispatch` ile `full` profil de secilebilir.

Artifact retention dry-run kaniti her gun
`.github/workflows/ai-workflow-retention.yml` ile uretilir. Destructive
`--apply` modu yalnizca manuel `workflow_dispatch` ile ve backup/onay sonrasi
calistirilir.

## 2. Staging signoff

Sadece onayli staging veritabani ve artifact dizini hedeflenmelidir.
`DATABASE_URL`, `ARTIFACTS_DIR`, `PGHOST`, `PGPORT`, `PGUSER`, `SOURCE_DB` ve
`RESTORE_DB` degiskenlerini staging icin ayarla. Restore drill, `RESTORE_DB`
veritabanini yeniden olusturur.

```bash
scripts/ops/ai-workflow-release-signoff.py \
  --profile full \
  --run-soak \
  --run-dr-drill \
  --confirm-data-write
```

Beklenen sonuc:

- `workflow_soak` pass.
- `dr_restore_drill` pass.
- `release_decision` degeri `ready_for_operator_approval`.
- JSON evidence pack release ticket'a eklenir.

## 3. Production signoff

Production icin komut yalnizca prod-like ama izole hedefte, change window
icinde, backup alindiktan ve operator yazili onayi verildikten sonra
calistirilir. Production restore drill dogrudan ana production DB uzerinde
calistirilmamalidir; restore hedefi ayri bir `RESTORE_DB` olmalidir.

Zorunlu onceki adimlar:

- Backup manifest uretilmis olmali:

```bash
scripts/ops/backup-postgres-artifacts.sh
```

- Restore hedefinin destructive olarak yeniden olusturulacagi kabul edilmeli.
- Release ticket'ta hedef DB, hedef artifact dizini ve operator onayi yer almali.

Production signoff komutu:

```bash
scripts/ops/ai-workflow-release-signoff.py \
  --profile full \
  --run-soak \
  --run-dr-drill \
  --confirm-data-write \
  --confirm-production-target
```

Script, prod-like ortam algilarsa `--confirm-production-target` olmadan
soak/DR adimlarini baslatmaz. Ayrica `SOURCE_DB == RESTORE_DB` veya
`ARTIFACTS_DIR == RESTORE_ARTIFACTS_DIR` durumunda DR drill durdurulur.

## 4. Stop conditions

Asagidaki durumlardan biri olursa release durdurulur:

- `failed_required_checks` bos degilse.
- `prompt_manifest_integrity` fail ise.
- `direct_llm_import_guard` fail ise.
- `artifact_retention_dry_run` fail ise.
- `backend_ai_workflow_tests` veya `frontend_type_check` fail ise.
- `workflow_soak` veya `dr_restore_drill` fail ise.
- Evidence pack JSON'u release ticket'a eklenemiyorsa.

## 5. Evidence review checklist

Operator, JSON raporda sunlari kontrol eder:

- `context.env_keys_present` beklenen staging/prod degiskenlerini iceriyor.
- `context.data_write_confirmed` true.
- Prod-like ortamda `context.production_target_confirmed` true.
- Tum required check'ler pass.
- Soak/DR adimlari skipped degil, pass.
- `operator_next_steps` release onayina uygun.

Bu kosullar saglanmadan AI workflow release'i "tamam" sayilmaz.

## 6. Required GitHub checks

Repository branch protection ayarinda en az su check'ler required olmalidir:

- `AI workflow signoff evidence`
- `Eval Harness Unit`
- `Eval Suites`
- `Engine LLM Eval (grounding-only)`
- Ana backend/web CI job'lari

Bu ayar GitHub repository settings uzerinden yapilir; kod degisikligi tek
basina branch protection'i etkinlestirmez.
