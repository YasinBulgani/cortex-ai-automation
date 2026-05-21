# legacy/2026-05-cleanup

**Arşiv tarihi:** 2026-05-18  
**Silinme tarihi:** 2026-11-18 (6 ay — ADR-0004)  
**Karar veren:** @yasin_bulgan

## Arşivlenen modüller

| Dizin | Açıklama | Son commit | Referans |
|-------|----------|------------|---------|
| `wt-editor-routes/` | Eski BGTS Test Dönüşüm worktree dump'ı (editor-routes branch). 248 MB, 2726 dosya. Aktif kodda referans yok. ~80 Dependabot alert'i taşıyordu. | 2026-04-24 | — |

## Geri alma

```bash
git checkout -b restore/wt-editor-routes
git mv legacy/2026-05-cleanup/wt-editor-routes <orijinal-yol>
# ADR yaz, PR aç
```

## Silme (2026-11-18'de)

```bash
git checkout -b chore/purge-2026-05-legacy
git rm -rf legacy/2026-05-cleanup/
git commit -m "chore: purge 2026-05 legacy archive (6 month retention expired)"
```

Politika detayları: [ADR-0004](../../docs/adr/0004-legacy-silme-politikasi.md)
