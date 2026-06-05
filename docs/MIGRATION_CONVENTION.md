# Alembic Migration Naming Convention

## Standart Format (Zorunlu)

```
YYYYMMDD_NNNN_kisik_aciklama.py
```

| Parça | Açıklama | Örnek |
|-------|----------|-------|
| `YYYYMMDD` | UTC tarih (migration yazıldığı gün) | `20260605` |
| `NNNN` | O güne ait sıra numarası, 4 hane, sıfır dolgulu | `0001`, `0002` |
| `kisik_aciklama` | Alt çizgi ile ayrılmış, küçük harf, kısa fiil-nesne | `add_webhook_subscriptions` |

**Örnek:**

```
20260605_0001_add_webhook_subscriptions.py
20260605_0002_add_webhook_events_index.py
20260606_0001_drop_legacy_tspm_columns.py
```

---

## Neden Tarih Bazlı?

1. **Okuma kolaylığı:** Dosya adından migration'ın hangi gün yazıldığı anında anlaşılır; hash-bazlı isimlerde bağlam yoktur.
2. **Sıralama:** `ls` veya IDE ağaç görünümü doğal kronolojik sırayla listeler; tarihin ardından gelen 4 haneli sıra numarası aynı güne ait migration'ları doğru sıralar.
3. **Conflict tespiti:** Aynı gün aynı sıra numarasını iki farklı branch kullansa çakışma anında görülür; hash çakışması nadirdir ve fark edilmesi zordur.
4. **Tarihçe takibi:** `git log --follow` ya da `git blame` ile "bu tablo ne zaman eklendi?" sorusuna dosya adından yanıt verilebilir.
5. **Ekip uyumu:** Hash, Alembic'in ürettiği rastgele bir değerdir ve anlamlı taşımaz; tarih + sıra insan tarafından üretilir ve tutarlı kalır.

---

## Nasıl Yeni Migration Oluşturulur?

### 1. Skill ile (Önerilen)

```bash
# Proje kökünden:
/migrate   # mevcut durum + bekleyen migration listesi
/new-migration add_webhook_subscriptions
```

### 2. Manuel Alembic komutu

```bash
cd backend

# Autogenerate (model değişikliklerini otomatik algıla)
alembic revision --autogenerate -m "add_webhook_subscriptions"

# Boş migration (el ile yazılacak)
alembic revision -m "add_webhook_subscriptions"
```

> **Dikkat:** `--autogenerate` ile üretilen dosyanın adı `alembic.ini`deki `file_template` ayarına göre
> `YYYYMMDD_<rev>_add_webhook_subscriptions.py` formatında oluşur.
> Sıra numarasını (`_NNNN_`) dosya adına ve `Revision ID` yorumuna **elle ekleyin**.

### 3. Dosya adı düzenleme adımları

```bash
# Üretilen dosya: 20260605_abc12345_add_webhook_subscriptions.py
# Hedef:          20260605_0001_add_webhook_subscriptions.py

mv backend/alembic/versions/20260605_abc12345_add_webhook_subscriptions.py \
   backend/alembic/versions/20260605_0001_add_webhook_subscriptions.py
```

Dosya içindeki `revision` ve `down_revision` değerlerini **değiştirmeyin**; yalnızca dosya adını düzenleyin.

### 4. Migration uygulama

```bash
# Tüm bekleyen migration'ları uygula
alembic upgrade head

# Belirli bir revision'a git
alembic upgrade 20260605_0001

# Bir adım geri al
alembic downgrade -1
```

---

## Mevcut Hash-Bazlı Migration'lar

Aşağıdaki dosyalar, tarih bazlı standart benimsenmeden önce oluşturulmuştur. **Yeniden adlandırılmazlar** çünkü Alembic revision zinciri dosya adını değil, dosya içindeki `revision` değerini kullanır. Dosya adı değiştirilse bile zincir bozulmaz; ancak tutarlılık açısından bu dosyalar olduğu gibi bırakılmıştır.

| Dosya | Kapsam |
|-------|--------|
| `86656e38793d_tspm_tables.py` | TSPM temel tabloları |
| `a1b2c3d4e5f6_add_parent_id_to_cases.py` | Test case'lere parent_id ekleme |
| `b0d0e2195677_add_settings_data_to_test_management_.py` | Test management ayar verisi |
| `b2c3d4e5f6a7_add_case_dependencies_table.py` | Case bağımlılık tablosu |
| `b4682f9d1d6c_merge_nexus_repo_and_runtime_core.py` | Merge noktası |
| `c56588566379_add_jira_integrations_table.py` | Jira entegrasyon tablosu |
| `f3990e7f3667_add_shared_steps_table.py` | Paylaşımlı adım tablosu |

### Bu dosyalar için kurallar

- **Yeniden adlandırmayın** (Alembic zinciri dosya adına değil revision hash'e bağlıdır; yeniden adlandırma karışıklık yaratır).
- **Silmeyin** (zincir kırılır, `alembic upgrade head` hata verir).
- **Yeni migration** eklerken bu formattan kaçının; standart `YYYYMMDD_NNNN_*` formatını kullanın.

---

## alembic.ini Ayarları

`backend/alembic.ini` içinde `file_template` değeri tarih bazlı format üretecek şekilde ayarlanmıştır:

```ini
file_template = %%(year)d%%(month).2d%%(day).2d_%%(rev)s_%%(slug)s
```

Bu ayar `alembic revision -m "aciklama"` komutunun çıktısını şu formatta üretir:

```
20260605_abc12345_aciklama.py
```

> Sıra numarasını (`_NNNN_`) otomatik ekleyecek yerel bir Alembic hook mevcut değildir.
> Dosya oluşturulduktan sonra sıra numarasını elle ekleyip dosyayı yeniden adlandırın
> (bkz. "Dosya adı düzenleme adımları" bölümü).

---

## Özet Kontrol Listesi

Yeni bir migration eklemeden önce:

- [ ] Dosya adı `YYYYMMDD_NNNN_kisik_aciklama.py` formatında mı?
- [ ] Aynı güne ait migration'larla sıra numarası çakışıyor mu? (Kontrol: `ls backend/alembic/versions/ | grep $(date +%Y%m%d)`)
- [ ] `revision` ve `down_revision` değerleri dosya içinde doğru mu?
- [ ] `alembic upgrade head` lokal ortamda başarıyla tamamlandı mı?
- [ ] Migration geri alınabilir mi? (`downgrade` metodu dolu mu?)
