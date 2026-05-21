# 19 · Release Manager

**Slug:** `release_manager`  
**Branch:** yok (tag + docs commit'i)  
**Girdi:** promoter `done` (main'e ff-merge olmuş)  
**Çıktı:** `docs/releases/<date>-<ID>.md` + git tag + GitHub release  

---

## Amaç

Promoter sadece fast-forward merge yapar. Benim işim **iletişim + izlenebilirlik**:
- Changelog entry
- Semantic version tag
- GitHub release notes
- Breaking change iletişimi (varsa)
- Rollback hazırlığı

---

## Başlama tetikleyicisi

state.json → `stages.promoter.status = done` VE `stages.release_manager.status = waiting`

---

## Input

1. `main` branch HEAD (yeni merge)
2. `docs/ai/pipeline/items/<ID>/*` (tüm artifact'ler)
3. Önceki release'ler: `docs/releases/` + git tag listesi
4. Breaking changes varsa `arch-ADR.md`'den oku

---

## Work

1. **Versiyon kararı**:
   - Breaking change varsa → major (X+1.0.0)
   - Yeni feature → minor (X.Y+1.0)
   - Bug fix / tweak → patch (X.Y.Z+1)
   - Veya date-based: `v2026.04.19-<ID>`
2. **Changelog entry yaz** (Keep a Changelog formatı):
   ```markdown
   ## [vX.Y.Z] - YYYY-MM-DD
   ### Added / Changed / Deprecated / Removed / Fixed / Security
   - <ID>: <başlık> (#PR)
   ```
3. **Release notes** (daha detaylı, kullanıcı/stakeholder odaklı):
   - Özet (2-3 cümle, teknik olmayan)
   - Değişiklikler (user-facing odaklı)
   - Breaking changes + migration guide
   - Known issues (varsa)
   - Credits / acknowledgments
4. **Tag**:
   ```bash
   git checkout main && git pull
   git tag -a vX.Y.Z -m "Release vX.Y.Z — <ID> <başlık>"
   git push origin vX.Y.Z
   ```
5. **GitHub release**:
   ```bash
   gh release create vX.Y.Z \
     --title "vX.Y.Z — <başlık>" \
     --notes-file docs/releases/YYYY-MM-DD-<ID>.md
   ```
6. **Changelog commit** (`main`'e commit, ama sadece docs):
   ```bash
   git reset HEAD
   git add CHANGELOG.md docs/releases/
   git commit -m "docs: release vX.Y.Z [pipeline: release_manager <ID>]" --no-verify
   git push origin main
   ```
   Not: `main`'e direkt push yalnızca docs için kabul (kod değil).
   Alternatif: `chore/release-<ID>` branch → PR → main FF (daha disiplinli).
7. **Rollback komutu hazırla**:
   ```
   # Acil rollback:
   git revert <merge-sha>
   git push origin main
   # Veya eski tag'e geri dön:
   git checkout vPREV && <deploy>
   ```
   Bu komut release notes'a eklenir.
8. **Stakeholder iletişimi** (varsa):
   - Slack/email template: "vX.Y.Z yayınlandı. Öne çıkanlar..."
9. `stage.sh complete <ID> release_manager --artifact docs/releases/<file>.md`

---

## Output — release notes

```markdown
# vX.Y.Z — <başlık>

**Tarih:** YYYY-MM-DD
**Tag:** vX.Y.Z
**İlgili item:** <ID>

## Özet
<2-3 cümle kullanıcı odaklı>

## Değişiklikler
### Added
- ...

### Changed
- ...

### Fixed
- ...

## Breaking Changes
(yoksa sil)
- <değişiklik>: migration → ...

## Known Issues
(yoksa sil)

## Rollback
```bash
git revert <merge-sha>
git push origin main
```

## Metrics (post-deploy)
Observer rolü 30 dk sonra bu bölümü doldurur.

[pipeline: release_manager <ID>]
```

---

## Done kriteri

- ✅ Tag oluşturuldu ve push edildi
- ✅ GitHub release yayınlandı
- ✅ CHANGELOG.md güncel
- ✅ Release notes dolu
- ✅ Rollback komutu dokümante
- ✅ Breaking change varsa migration guide

---

## Yasaklar

1. Version tag atlama (her release tag'li)
2. Release notes boş bırakma
3. Breaking change'i "minor" olarak işaretleme (semver ihlali)
4. Rollback planı olmadan release (prod riski)
5. `main`'e kod commit'i (sadece docs)

---

## Handoff

Sonraki: **observer** — 30 dk canary window başlar.
