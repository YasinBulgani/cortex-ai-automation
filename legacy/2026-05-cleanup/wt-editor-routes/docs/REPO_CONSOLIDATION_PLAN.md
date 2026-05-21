# BGTS_Test_Donusum — Depo birleştirme ve sadeleştirme (ayrıntılı plan)

Bu belge, monoreponun **tek kanonik kod ağacı** etrafında toplanması, tekrarların azaltılması ve operasyonel risklerin kontrol altına alınması için fazlara ayrılmış bir yol haritasıdır. Özet envanter: [`repository-inventory.md`](repository-inventory.md).

---

## 1. Amaç ve kapsam dışı

### 1.1 Amaçlar

| Kod | Amaç | Ölçülebilir sonuç |
|-----|------|-------------------|
| G1 | Kanonik dizinler net | Yeni PR’lar yalnızca `apps/web`, `backend`, `engine`, `e2e`, `ai-engine` altında ürün kodu taşır |
| G2 | Gereksiz kopyalar azalır | `repo-*`, `bgt-agent-*`, Claude worktree kopyaları repoda veya diskte şişirmez |
| G3 | Kök dizin sade | PDF/PPTX/geçici analiz dosyaları kökte değil, `archive/` veya `docs/assets/` altında |
| G4 | Geliştirici deneyimi | Tek komutla web + (isteğe bağlı) workspace kurulumu dokümante |
| G5 | Mimari netlik | FastAPI + Flask ayrımı **bilinçli** kalır veya ayrı bir ürün kararıyla değişir |

### 1.2 Kapsam dışı (bu planda varsayılan)

- **Backend ile engine’in tek süreçte birleştirilmesi** — ayrı ADR ve ayrı proje (bkz. bölüm 7).
- Üretim deployment veya Kubernetes değişiklikleri (sadece referans notları).
- İş analizi dokümanlarının içerik birleştirmesi (yalnızca dosya konumu).

---

## 2. Mevcut durum özeti

### 2.1 Tamamlanmış / hazır artefaktlar

| Öğe | Konum |
|-----|--------|
| Depo envanteri ve diff özeti | [`repository-inventory.md`](repository-inventory.md) |
| Ajan kopyası senaryosu için rehber | [`tools/agent-snapshots/README.md`](../tools/agent-snapshots/README.md) |
| SyntheticBankData açıklaması | [`SyntheticBankData/README.md`](../SyntheticBankData/README.md) (varsa) |

### 2.2 Henüz yapılması gerekenler (tipik)

- Kökte kalan sunum / analiz / geçici test çıktılarının `archive/root-misc/` altına taşınması (önceki oturumda taşıma yarım kalmış olabilir).
- Bazı makinelerde var olan `repo-*`, `bgt-agent-*` dizinlerinin `diff` ile doğrulanıp kaldırılması veya arşivlenmesi.
- İsteğe bağlı: kök `package.json` içinde **npm workspaces** (`apps/web`, `ai-engine`).
- İsteğe bağlı: [`docs/ADR-001-backend-engine-separation.md`](ADR-001-backend-engine-separation.md) oluşturulması (şablon bu planda bölüm 7’de).

---

## 3. Roller ve sorumluluklar (öneri)

| Rol | Sorumluluk |
|-----|------------|
| **Teknik lider** | Faz öncelikleri, mimari birleştirme kararı (evet/hayır) |
| **Repo sahibi** | Büyük silme / `git filter-repo` kararları, yedek |
| **CI sahibi** | `npm install` / workspace sonrası pipeline doğrulama |
| **Geliştirici** | Günlük kodu kanonik dizinlere taşıma, PR incelemesi |

---

## 4. Fazlar (ayrıntılı)

### Faz 0 — Hazırlık (0,5–1 gün)

**Hedef:** Güvenli başlangıç; geri dönüş mümkün olsun.

| # | Görev | Çıktı | Risk |
|---|--------|-------|------|
| 0.1 | Ana dalda temiz çalışma alanı; gerekirse yedek branch `backup/pre-consolidation-YYYYMMDD` | Branch | Düşük |
| 0.2 | Disk kullanımı: `du -sh SyntheticBankData engine backend` | Not | Düşük |
| 0.3 | [`repository-inventory.md`](repository-inventory.md) ile yerel durum karşılaştırması (sizde `repo-*` var mı?) | Güncellenmiş not | Düşük |

**Kabul kriteri:** Yedek branch oluşturuldu; envanter “bu makineye özel” satırlarla güncellendi.

---

### Faz 1 — Kök dizin ve artefakt düzeni (1–2 gün)

**Hedef:** Repo kökü yalnızca yapılandırma, README ve zorunlu giriş dosyalarını içersin.

| # | Görev | Ayrıntı |
|---|--------|---------|
| 1.1 | `archive/root-misc/` oluştur | Sunum kopyaları (`Cockpit_*.pptx`), OrangeHRM analiz dosyaları, kökteki `e2e_analiz_*.json`, `test_scenarios_*.feature` vb. |
| 1.2 | `archive/README.md` | Ne taşındı, neden, orijinal kök adları |
| 1.3 | `.gitignore` gözden geçir | `reports/` zaten kısmen ignore; `archive/` içinde devasa ikili dosya tutulacaksa LFS veya harici arşiv düşünün |
| 1.4 | Ana [`README.md`](../README.md) içine kısa paragraf | “Depo düzeni” → `docs/repository-inventory.md` ve `archive/` |

**Kabul kriteri:** `git status` kökte gereksiz büyük/binary dosya göstermez (veya bilinçli olarak `archive/` altında gruplanmıştır).

**Risk:** Yanlış dosya taşınırsa — commit öncesi `git diff --stat` ve ekip onayı.

---

### Faz 2 — Tekrarlayan ağaçlar (`repo-*`, `bgt-agent-*`, worktree)

**Hedef:** Tek kanonik kaynak; disk ve kafa karışıklığı azalır.

#### 2A — Claude / IDE worktree’leri

| # | Görev | Komut / not |
|---|--------|-------------|
| 2A.1 | `SyntheticBankData/.claude/worktrees/` boyutu | `du -sh`, dosya sayısı |
| 2A.2 | Silme veya tutma | Kanonik kod `engine/`; kopyalar genelde güvenle silinir (önce yedek) |
| 2A.3 | `.gitignore` | Kök `.gitignore` içinde `.claude/` genelde yeterli; tüm alt yolları doğrula |

**Kabul kriteri:** Worktree dizini yok veya yalnızca yerel ve ignore altında.

#### 2B — `repo-*` ve `bgt-agent-*` (makinede varsa)

| # | Görev |
|---|--------|
| 2B.1 | Her kopya için `diff -rq engine/ <kopya>/test-automation` veya `ai_synthetic_data` karşılaştırması |
| 2B.2 | Yalnızca birebir veya alt küme ise: dizini kaldır, [`tools/agent-snapshots/README.md`](../tools/agent-snapshots/README.md) prosedürüne atıf |
| 2B.3 | Tek dosya farkı varsa: önce ana ağaca cherry-pick / manuel port, sonra silme |

**Kabul kriteri:** Kopya dizin yok **veya** `archive/agent-snapshots-YYYYMMDD.zip` + README’de checksum.

**Risk:** Orta — yanlış silme. Mitigasyon: Faz 0 yedek + diff çıktısını PR’a ekle.

---

### Faz 3 — Araç birliği (npm workspaces) — isteğe bağlı (1–2 gün)

**Hedef:** `npm install` kökten; `apps/web` ve `ai-engine` bağımlılıkları hoisted.

| # | Görev |
|---|--------|
| 3.1 | Kök `package.json` içine `"workspaces": ["apps/web", "ai-engine"]` |
| 3.2 | `npm install` kökten; `package-lock.json` güncellemesi |
| 3.3 | Script’ler: mevcut `web:dev` aynı kalabilir; dokümanda “kökten `npm install`” yazın |
| 3.4 | CI: `.github/workflows` içinde `npm ci` çalışan job’larda çalışma dizini ve cache doğrulaması |

**Kabul kriteri:** `npm run web:dev` ve `ai-engine` script’leri kök kurulumdan çalışır; CI yeşil.

**Risk:** Orta — lockfile çakışması. Mitigasyon: ayrı PR, rollback kolay.

---

### Faz 4 — Dokümantasyon indeksi (0,5 gün)

**Hedef:** Tek giriş noktası.

| # | Görev |
|---|--------|
| 4.1 | `docs/MASTER.md` veya README’de “Dokümantasyon haritası” tablosu |
| 4.2 | Bağlantılar: `PROGRESS.md`, `repository-inventory.md`, `reports/BGT_DEVELOPER_HANDOFF_FULL_FEATURES.md`, ADR |

---

### Faz 5 — Mimari birleştirme (backend + engine) — ayrı program

Bkz. bölüm 7. Bu faz **bu planın parçası değildir**; ürün ve güvenlik onayı gerektirir.

---

## 5. Test ve doğrulama matrisi

| Tetikleyici | Minimum kontrol |
|-------------|-------------------|
| Kök taşıma sonrası | `npm run web:build`, `npm run test:e2e:smoke` (ortam uygunsa) |
| Worktree silme sonrası | `engine` pytest smoke; sentetik veri API’si kullanılıyorsa manuel smoke |
| Workspaces sonrası | CI tam pipeline veya `npm ci && npm run web:build` |
| Büyük silme sonrası | Staging deploy veya feature branch üzerinde tam regresyon (ekip politikasına göre) |

---

## 6. Risk özeti

| Risk | Olasılık | Etki | Önlem |
|------|-----------|------|--------|
| Yanlış klasör silme | Orta | Yüksek | Yedek branch, `diff` çıktısı PR ekine |
| CI kırılması (workspaces) | Orta | Orta | Ayrı PR, önce feature branch CI |
| Ekip alışkanlığı (yanlış dizinde kod) | Yüksek | Orta | CODEOWNERS, PR şablonu, envanter linki |
| Mimari birleştirme acelesi | Orta | Çok yüksek | Faz 5’i ayrı tut; ADR şart |

---

## 7. Mimari birleştirme (FastAPI + Flask) — ayrı ADR taslağı

**Karar (önerilen varsayılan):** Mevcut ayrımı koru; proxy ve `ENGINE_BASE_URL` ile entegrasyon netleştirilsin.

**Birleştirmeyi düşünürseniz ADR’de şunlar yer almalı:**

1. **Gerekçe:** Tek port, tek deploy, operasyon maliyeti.
2. **Maliyet:** Ayırmış bounded context’leri tek süreçte birleştirmek; uzun migration.
3. **Teknik seçenekler:** Engine’i ASGI alt süreç / worker; veya FastAPI içinde Flask mount (deneysel); veya yalnızca HTTP köprü (mevcut).
4. **Test stratejisi:** Tüm `engine` ve `backend` pytest + E2E yeniden koşumu.
5. **Rollback:** Eski compose ve env ile geri dönüş.

Dosya önerisi: `docs/ADR-001-backend-engine-separation.md` (mevcut ayrımı “bilinçli karar” olarak sabitler).

---

## 8. Zaman çizelgesi (kabaca)

| Hafta | Odak |
|-------|------|
| 1 | Faz 0–1 (hazırlık + kök arşiv) |
| 2 | Faz 2A–2B (worktree + varsa repo-* temizliği) |
| 3 | Faz 3–4 (isteğe bağlı workspaces + doküman indeksi) |
| Sürekli | Faz 5 yalnızca ürün onayı ile |

---

## 9. Hemen yapılacaklar kontrol listesi

- [ ] Yerelde `repo-*` / `bgt-agent-*` var mı? Varsa envanter dosyasına bir satır ekleyin.
- [ ] Kökte taşınmayı bekleyen dosyalar var mı? → `archive/root-misc/` + `archive/README.md`
- [ ] `SyntheticBankData/.claude/worktrees` var mı? → boyut ölç, gerekiyorsa sil, `.gitignore` doğrula
- [ ] Workspaces isteniyor mu? → Faz 3 açın
- [ ] ADR oluşturulsun mu? → Bölüm 7 şablonunu kullanın

---

**Belge sürümü:** 1.0  
**İlişkili:** [`repository-inventory.md`](repository-inventory.md), [`tools/agent-snapshots/README.md`](../tools/agent-snapshots/README.md)
