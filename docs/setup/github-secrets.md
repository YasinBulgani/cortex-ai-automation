# GitHub Actions — Required Secrets

Bu sayfa `.github/workflows/` dosyalarının kullandığı tüm secret'ları listeler.

**Eklemek için:** GitHub → repo → Settings → Secrets and variables → Actions → New repository secret

---

## Zorunlu Secret'lar

### `SEMGREP_APP_TOKEN` (opsiyonel ama önerilir)

| Amaç | Semgrep Cloud'da tarama sonuçlarını görüntülemek, PR annotation'larını etkinleştirmek |
|---|---|
| Gerekli mi? | Opsiyonel — token olmadan `semgrep ci` **yerel modda** çalışır, SARIF üretir ama Cloud dashboard'a gönderemez |
| Nasıl alınır? | [semgrep.dev](https://semgrep.dev) → Settings → Tokens → Create token |
| Workflow | `.github/workflows/security-sast.yml` |

> Token yoksa CI yine çalışır. `SEMGREP_APP_TOKEN` tanımlı değilse `semgrep ci` çıkış kodu 0 döner ama findings Cloud'da görünmez.
> SARIF dosyası üretilir ve GitHub Security sekmesine yüklenir (bu kısım token'sız da çalışır).

---

## Opsiyonel Secret'lar

| Secret | Kullanım yeri | Açıklama |
|---|---|---|
| `SLACK_WEBHOOK_URL` | `notify.sh` / Jenkinsfile | CI sonuç bildirimleri |
| `HCM_AES_KEY` | Backend runtime | AES/GCM şifreleme anahtarı (32 byte hex) — prod/staging env'de gerekli |
| `HF_API_TOKEN` | Backend AI servisleri | HuggingFace model erişimi |

---

## Secret Doğrulama

Secret'ların tanımlı olup olmadığını kontrol etmek için:

```bash
# GitHub CLI ile repo secret listesi:
gh secret list --repo YasinBulgani/cortex-ai-automation
```

---

## Güvenlik Notu

- Secret'ları asla `.env` dosyasına veya kaynak koda ekleme
- `password.properties`, `storage-state.json` dosyaları `.gitignore`'da — git'e commit etme
- Rotate etmen gereken token'lar için GitHub'da `SEMGREP_APP_TOKEN` expiry date ayarla
