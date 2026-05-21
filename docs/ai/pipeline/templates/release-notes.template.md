# {{VERSION}} — {{TITLE}}

> **Tarih:** {{DATE}}  
> **Tag:** `{{VERSION}}`  
> **İlgili item:** {{ID}}  
> **Commit:** {{SHA}}

---

## Özet

<2-3 cümle, non-teknik — kullanıcıya ne değişti, ne kazandı>

---

## Değişiklikler

### Added

- <yeni feature / endpoint / ekran>

### Changed

- <davranış/görünüm değişikliği>

### Deprecated

- (yoksa sil) — <kullanımdan kalkmak üzere işaretlenen>

### Removed

- (yoksa sil) — <silinen özellik>

### Fixed

- <bug fix>

### Security

- <CVE patch, security hardening>

---

## Breaking Changes

(yoksa "Bu sürümde breaking change yok.")

### BC-1: <başlık>

- **Ne değişti:** <açıklama>
- **Etkilenen:** <endpoint / API / config>
- **Migration:**
  ```
  <eski>
  →
  <yeni>
  ```
- **Timeline:** immediate | deprecate X sürüm sonra kaldırılacak

---

## Known Issues

(yoksa sil)

- <issue> — workaround: <...>

---

## Upgrade Guide

```bash
# API consumer için:
# 1. <adım>
# 2. <adım>

# DB migration:
cd backend && .venv/bin/alembic upgrade head
```

---

## Rollback

Acil durum için:

```bash
# Revert deployment
git revert {{SHA}}
git push origin main

# Veya eski tag'e geri dön
git checkout {{PREV_VERSION}}
# <deploy komutları>

# DB rollback (varsa)
cd backend && .venv/bin/alembic downgrade -1
```

---

## Metrics (post-deploy)

*Observer rolü 30 dk sonra doldurur:*

- Error rate: <baseline vs post-deploy>
- p95 latency: <baseline vs post-deploy>
- Rollout: <% kullanıcı>

---

## Credits

- Pipeline items: {{ID}}
- Contributors: <pipeline agent'ları>

---

[pipeline: release_manager {{ID}}]
