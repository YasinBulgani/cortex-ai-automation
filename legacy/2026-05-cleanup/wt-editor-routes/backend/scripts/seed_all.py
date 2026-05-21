"""
Kapsamlı dummy data — tüm tabloları gerçekçi Türkçe verilerle doldurur.

Çalıştırma:
  cd backend && PYTHONPATH=. python scripts/seed_all.py

Mevcut demo projeler silinip yeniden oluşturulur.
"""

from __future__ import annotations

import os
import random
import sys
import uuid
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select, delete
from sqlalchemy.orm import Session

from app.infra.database import SessionLocal
from app.infra.models import User, Role, RolePermission
from app.domains.auth.service import hash_password
from app.domains.auth.permissions import ROLE_PERMISSIONS
from app.domains.tspm.models import (
    TspmProject,
    TspmScenario,
    TspmScenarioVersion,
    TspmExecution,
    TspmExecutionResult,
    TspmExecutionMetrics,
    TspmFlow,
    TspmRegressionSet,
    TspmApproval,
    TspmImport,
    TspmRequirement,
    TspmScenarioRequirement,
    TspmSchedule,
    TspmTestDataSet,
    TspmScenarioDataBinding,
    TspmProjectMember,
    TspmIntegration,
    TspmApiCollection,
    TspmApiRequest,
    TspmApiTestRun,
    TspmAiBatch,
    TspmTestCase,
    TspmAutomationArtifact,
    utcnow,
)

random.seed(42)


def rand_past(days_back: int = 90) -> datetime:
    return utcnow() - timedelta(days=random.randint(1, days_back), hours=random.randint(0, 23))


def rand_future(days_ahead: int = 30) -> datetime:
    return utcnow() + timedelta(days=random.randint(1, days_ahead), hours=random.randint(0, 23))


# ──────────────────────────────────────────────
# Users & Roles
# ──────────────────────────────────────────────

USERS = [
    {"email": "admin@example.com", "password": "admin123", "role": "admin"},
    {"email": "ahmet.yilmaz@bgtest.com", "password": "test1234", "role": "operator"},
    {"email": "elif.demir@bgtest.com", "password": "test1234", "role": "operator"},
    {"email": "mehmet.kaya@bgtest.com", "password": "test1234", "role": "viewer"},
    {"email": "zeynep.celik@bgtest.com", "password": "test1234", "role": "viewer"},
    {"email": "can.ozturk@bgtest.com", "password": "test1234", "role": "operator"},
]

# ──────────────────────────────────────────────
# Projects
# ──────────────────────────────────────────────

PROJECTS = [
    {
        "name": "E-Ticaret Platformu",
        "description": "Ana e-ticaret uygulamasının fonksiyonel, entegrasyon ve regresyon testleri. Ödeme, sepet, kullanıcı yönetimi modüllerini kapsar.",
    },
    {
        "name": "Mobil Bankacılık API",
        "description": "Mobil bankacılık uygulamasının backend API testleri. Havale, EFT, kredi başvurusu ve hesap yönetimi akışları.",
    },
    {
        "name": "İK Yönetim Sistemi",
        "description": "İnsan kaynakları portalının test süreçleri. İzin yönetimi, bordro, performans değerlendirme modülleri.",
    },
]

# ──────────────────────────────────────────────
# Scenarios per project
# ──────────────────────────────────────────────

SCENARIOS_BY_PROJECT = {
    "E-Ticaret Platformu": [
        {"title": "Ürün arama ve filtreleme", "description": "Kullanıcı anahtar kelime ile ürün arayabilmeli, kategori ve fiyat aralığına göre filtreleyebilmeli.", "status": "approved", "tags": ["smoke", "search", "catalog", "regression"],
         "steps": [{"order": 0, "keyword": "Olduğu gibi", "text": "kullanıcı ana sayfadadır"}, {"order": 1, "keyword": "Eğer", "text": "arama kutusuna 'laptop' yazar"}, {"order": 2, "keyword": "O zaman", "text": "laptop içeren ürünler listelenir"}, {"order": 3, "keyword": "Ve", "text": "fiyat filtresi uygulanabilir"}]},
        {"title": "Sepete ürün ekleme", "description": "Kullanıcı ürün detay sayfasından sepete ürün ekleyebilmeli.", "status": "approved", "tags": ["smoke", "cart", "regression"],
         "steps": [{"order": 0, "keyword": "Olduğu gibi", "text": "kullanıcı ürün detay sayfasındadır"}, {"order": 1, "keyword": "Eğer", "text": "Sepete Ekle butonuna tıklar"}, {"order": 2, "keyword": "O zaman", "text": "ürün sepete eklenir"}, {"order": 3, "keyword": "Ve", "text": "sepet sayacı güncellenir"}]},
        {"title": "Sepetten ürün çıkarma", "description": "Kullanıcı sepet sayfasından ürün çıkarabilmeli.", "status": "approved", "tags": ["cart", "regression"],
         "steps": [{"order": 0, "keyword": "Olduğu gibi", "text": "sepette en az bir ürün vardır"}, {"order": 1, "keyword": "Eğer", "text": "ürünün yanındaki Kaldır butonuna tıklar"}, {"order": 2, "keyword": "O zaman", "text": "ürün sepetten kaldırılır"}]},
        {"title": "Kredi kartı ile ödeme", "description": "Kullanıcı geçerli kredi kartı bilgileri ile ödeme yapabilmeli.", "status": "approved", "tags": ["smoke", "payment", "critical", "regression"],
         "steps": [{"order": 0, "keyword": "Olduğu gibi", "text": "kullanıcı ödeme sayfasındadır"}, {"order": 1, "keyword": "Eğer", "text": "geçerli kart bilgilerini girer"}, {"order": 2, "keyword": "Ve", "text": "Ödemeyi Tamamla butonuna tıklar"}, {"order": 3, "keyword": "O zaman", "text": "ödeme başarıyla tamamlanır"}, {"order": 4, "keyword": "Ve", "text": "sipariş onay sayfası görüntülenir"}]},
        {"title": "Geçersiz kart ile ödeme reddi", "description": "Yetersiz bakiye veya geçersiz kart ile ödeme reddedilmeli.", "status": "approved", "tags": ["payment", "negative", "security"],
         "steps": [{"order": 0, "keyword": "Olduğu gibi", "text": "kullanıcı ödeme sayfasındadır"}, {"order": 1, "keyword": "Eğer", "text": "yetersiz bakiyeli kart bilgisi girer"}, {"order": 2, "keyword": "O zaman", "text": "ödeme reddedilir ve hata mesajı gösterilir"}]},
        {"title": "Sipariş geçmişi görüntüleme", "description": "Kullanıcı tamamlanmış siparişlerini listeleyebilmeli.", "status": "approved", "tags": ["orders", "regression"],
         "steps": [{"order": 0, "keyword": "Olduğu gibi", "text": "kullanıcı sisteme giriş yapmıştır"}, {"order": 1, "keyword": "Eğer", "text": "Siparişlerim sayfasını açar"}, {"order": 2, "keyword": "O zaman", "text": "geçmiş siparişler tarih sırasına göre listelenir"}]},
        {"title": "Kupon kodu uygulama", "description": "Geçerli kupon kodu ile sepet toplamında indirim uygulanabilmeli.", "status": "approved", "tags": ["promotion", "cart", "regression"],
         "steps": [{"order": 0, "keyword": "Olduğu gibi", "text": "sepette ürün vardır"}, {"order": 1, "keyword": "Eğer", "text": "geçerli bir kupon kodu girer"}, {"order": 2, "keyword": "O zaman", "text": "indirim tutarı sepet toplamından düşülür"}]},
        {"title": "Geçersiz kupon kodu reddi", "description": "Süresi dolmuş veya geçersiz kupon kodu reddedilmeli.", "status": "approved", "tags": ["promotion", "negative"],
         "steps": [{"order": 0, "keyword": "Olduğu gibi", "text": "sepette ürün vardır"}, {"order": 1, "keyword": "Eğer", "text": "süresi dolmuş bir kupon kodu girer"}, {"order": 2, "keyword": "O zaman", "text": "'Geçersiz kupon kodu' hatası gösterilir"}]},
        {"title": "Adres ekleme ve düzenleme", "description": "Kullanıcı teslimat adresi ekleyebilmeli ve düzenleyebilmeli.", "status": "approved", "tags": ["profile", "address"],
         "steps": [{"order": 0, "keyword": "Olduğu gibi", "text": "kullanıcı adres yönetimi sayfasındadır"}, {"order": 1, "keyword": "Eğer", "text": "yeni adres bilgilerini doldurur"}, {"order": 2, "keyword": "O zaman", "text": "adres başarıyla kaydedilir"}]},
        {"title": "Ürün yorum ve puanlama", "description": "Kullanıcı satın aldığı ürünü puanlayabilmeli ve yorum yapabilmeli.", "status": "draft", "tags": ["review", "catalog"],
         "steps": [{"order": 0, "keyword": "Olduğu gibi", "text": "kullanıcı satın aldığı ürünün sayfasındadır"}, {"order": 1, "keyword": "Eğer", "text": "puan verir ve yorum yazar"}, {"order": 2, "keyword": "O zaman", "text": "yorum moderasyon onayına gönderilir"}]},
        {"title": "Stok kontrolü", "description": "Stokta olmayan ürün sepete eklenememeli.", "status": "approved", "tags": ["cart", "inventory", "negative"],
         "steps": [{"order": 0, "keyword": "Olduğu gibi", "text": "ürün stokta yoktur"}, {"order": 1, "keyword": "Eğer", "text": "kullanıcı Sepete Ekle butonuna tıklar"}, {"order": 2, "keyword": "O zaman", "text": "'Stokta yok' mesajı görüntülenir"}]},
        {"title": "İade talebi oluşturma", "description": "Kullanıcı teslim edilen sipariş için iade talebi oluşturabilmeli.", "status": "draft", "tags": ["orders", "returns"],
         "steps": [{"order": 0, "keyword": "Olduğu gibi", "text": "sipariş teslim edilmiştir"}, {"order": 1, "keyword": "Eğer", "text": "iade nedeni seçer ve talebi gönderir"}, {"order": 2, "keyword": "O zaman", "text": "iade talebi oluşturulur"}]},
        {"title": "Favori listesine ekleme", "description": "Kullanıcı ürünleri favori listesine ekleyebilmeli.", "status": "approved", "tags": ["catalog", "wishlist"],
         "steps": [{"order": 0, "keyword": "Olduğu gibi", "text": "kullanıcı ürün detay sayfasındadır"}, {"order": 1, "keyword": "Eğer", "text": "kalp ikonuna tıklar"}, {"order": 2, "keyword": "O zaman", "text": "ürün favorilere eklenir"}]},
        {"title": "Kargo takibi", "description": "Kullanıcı kargoya verilen siparişin takip numarasını görebilmeli.", "status": "draft", "tags": ["orders", "shipping"],
         "steps": [{"order": 0, "keyword": "Olduğu gibi", "text": "sipariş kargoya verilmiştir"}, {"order": 1, "keyword": "Eğer", "text": "sipariş detayını açar"}, {"order": 2, "keyword": "O zaman", "text": "kargo takip numarası ve durum bilgisi görüntülenir"}]},
        {"title": "Çoklu dil desteği", "description": "Kullanıcı arayüz dilini değiştirebilmeli.", "status": "draft", "tags": ["i18n", "settings"],
         "steps": [{"order": 0, "keyword": "Olduğu gibi", "text": "kullanıcı ayarlar sayfasındadır"}, {"order": 1, "keyword": "Eğer", "text": "dil seçeneğini İngilizce olarak değiştirir"}, {"order": 2, "keyword": "O zaman", "text": "tüm arayüz metinleri İngilizce olarak gösterilir"}]},
    ],
    "Mobil Bankacılık API": [
        {"title": "Hesap bakiye sorgulama", "description": "Müşteri anlık hesap bakiyesini sorgulayabilmeli.", "status": "approved", "tags": ["smoke", "account", "api", "regression"],
         "steps": [{"order": 0, "keyword": "Olduğu gibi", "text": "müşteri oturum açmıştır"}, {"order": 1, "keyword": "Eğer", "text": "bakiye sorgulama isteği gönderir"}, {"order": 2, "keyword": "O zaman", "text": "güncel bakiye bilgisi döner"}]},
        {"title": "Hesaplar arası havale", "description": "Müşteri kendi hesapları arasında para transferi yapabilmeli.", "status": "approved", "tags": ["smoke", "transfer", "banking", "critical", "regression"],
         "steps": [{"order": 0, "keyword": "Olduğu gibi", "text": "müşterinin birden fazla hesabı vardır"}, {"order": 1, "keyword": "Eğer", "text": "kaynak ve hedef hesabı seçerek tutar girer"}, {"order": 2, "keyword": "Ve", "text": "transfer isteği gönderir"}, {"order": 3, "keyword": "O zaman", "text": "bakiyeler güncellenir"}]},
        {"title": "EFT gönderimi", "description": "Farklı bankadaki hesaba EFT yapılabilmeli.", "status": "approved", "tags": ["transfer", "eft", "banking", "regression"],
         "steps": [{"order": 0, "keyword": "Olduğu gibi", "text": "müşteri transfer sayfasındadır"}, {"order": 1, "keyword": "Eğer", "text": "IBAN, ad-soyad ve tutarı girer"}, {"order": 2, "keyword": "Ve", "text": "EFT gönder butonuna tıklar"}, {"order": 3, "keyword": "O zaman", "text": "EFT işlemi kuyruğa alınır"}]},
        {"title": "Yetersiz bakiye kontrolü", "description": "Bakiyeden fazla tutar transferinde hata verilmeli.", "status": "approved", "tags": ["transfer", "negative", "banking"],
         "steps": [{"order": 0, "keyword": "Olduğu gibi", "text": "hesap bakiyesi 1000 TL'dir"}, {"order": 1, "keyword": "Eğer", "text": "2000 TL tutarında transfer isteği gönderir"}, {"order": 2, "keyword": "O zaman", "text": "'Yetersiz bakiye' hatası döner"}]},
        {"title": "Kredi başvurusu", "description": "Müşteri bireysel kredi başvurusu yapabilmeli.", "status": "approved", "tags": ["credit", "banking", "regression"],
         "steps": [{"order": 0, "keyword": "Olduğu gibi", "text": "müşteri kredi başvuru sayfasındadır"}, {"order": 1, "keyword": "Eğer", "text": "tutar ve vade bilgilerini girer"}, {"order": 2, "keyword": "O zaman", "text": "başvuru değerlendirmeye alınır"}]},
        {"title": "Kredi kartı ekstre görüntüleme", "description": "Müşteri kredi kartı ekstresini görüntüleyebilmeli.", "status": "approved", "tags": ["credit", "account", "api"],
         "steps": [{"order": 0, "keyword": "Olduğu gibi", "text": "müşterinin aktif kredi kartı vardır"}, {"order": 1, "keyword": "Eğer", "text": "ekstre görüntüleme isteği gönderir"}, {"order": 2, "keyword": "O zaman", "text": "dönem harcamaları listelenir"}]},
        {"title": "Otomatik ödeme talimatı", "description": "Fatura için otomatik ödeme talimatı verilebilmeli.", "status": "approved", "tags": ["payment", "banking"],
         "steps": [{"order": 0, "keyword": "Olduğu gibi", "text": "müşteri otomatik ödeme sayfasındadır"}, {"order": 1, "keyword": "Eğer", "text": "kurum seçer ve talimat oluşturur"}, {"order": 2, "keyword": "O zaman", "text": "talimat aktif olarak kaydedilir"}]},
        {"title": "İki faktörlü doğrulama", "description": "Yüksek tutarlı işlemlerde SMS doğrulama kodu istenmeli.", "status": "approved", "tags": ["smoke", "security", "2fa", "critical", "regression"],
         "steps": [{"order": 0, "keyword": "Olduğu gibi", "text": "müşteri 10.000 TL üzeri transfer yapmaktadır"}, {"order": 1, "keyword": "Eğer", "text": "transfer isteği gönderir"}, {"order": 2, "keyword": "O zaman", "text": "SMS doğrulama kodu istenir"}, {"order": 3, "keyword": "Ve", "text": "doğru kod girilince işlem tamamlanır"}]},
        {"title": "Hesap hareketleri listeleme", "description": "Son 30 günlük hesap hareketleri tarih sırasına göre listelenmeli.", "status": "approved", "tags": ["account", "api", "regression"],
         "steps": [{"order": 0, "keyword": "Olduğu gibi", "text": "müşteri oturum açmıştır"}, {"order": 1, "keyword": "Eğer", "text": "hesap hareketleri sayfasını açar"}, {"order": 2, "keyword": "O zaman", "text": "son 30 günlük hareketler listelenir"}]},
        {"title": "Döviz kuru sorgulama", "description": "Güncel döviz kurları sorgulanabilmeli.", "status": "draft", "tags": ["forex", "api"],
         "steps": [{"order": 0, "keyword": "Olduğu gibi", "text": "müşteri döviz sayfasındadır"}, {"order": 1, "keyword": "Eğer", "text": "döviz çifti seçer"}, {"order": 2, "keyword": "O zaman", "text": "güncel alış ve satış kuru gösterilir"}]},
        {"title": "Döviz alım/satım", "description": "Müşteri döviz alım satım işlemi yapabilmeli.", "status": "draft", "tags": ["forex", "banking"],
         "steps": [{"order": 0, "keyword": "Olduğu gibi", "text": "müşteri döviz işlemleri sayfasındadır"}, {"order": 1, "keyword": "Eğer", "text": "alım miktarını girer ve onayla butonuna tıklar"}, {"order": 2, "keyword": "O zaman", "text": "döviz alım işlemi gerçekleşir"}]},
        {"title": "Şifre değiştirme", "description": "Müşteri uygulama şifresini değiştirebilmeli.", "status": "approved", "tags": ["security", "auth", "regression"],
         "steps": [{"order": 0, "keyword": "Olduğu gibi", "text": "müşteri güvenlik ayarları sayfasındadır"}, {"order": 1, "keyword": "Eğer", "text": "mevcut ve yeni şifresini girer"}, {"order": 2, "keyword": "O zaman", "text": "şifre başarıyla güncellenir"}]},
    ],
    "İK Yönetim Sistemi": [
        {"title": "Yıllık izin talebi", "description": "Çalışan yıllık izin talebi oluşturabilmeli.", "status": "approved", "tags": ["smoke", "leave", "hr", "regression"],
         "steps": [{"order": 0, "keyword": "Olduğu gibi", "text": "çalışan izin modülündedir"}, {"order": 1, "keyword": "Eğer", "text": "tarih aralığı seçerek izin talebi oluşturur"}, {"order": 2, "keyword": "O zaman", "text": "talep yöneticiye onaya gider"}]},
        {"title": "İzin bakiyesi görüntüleme", "description": "Çalışan kalan izin günlerini görebilmeli.", "status": "approved", "tags": ["leave", "hr"],
         "steps": [{"order": 0, "keyword": "Olduğu gibi", "text": "çalışan izin modülündedir"}, {"order": 1, "keyword": "Eğer", "text": "izin bakiyesi sayfasını açar"}, {"order": 2, "keyword": "O zaman", "text": "kalan yıllık, mazeret ve sağlık izin günleri gösterilir"}]},
        {"title": "İzin onaylama/reddetme", "description": "Yönetici çalışanın izin talebini onaylayabilmeli veya reddedebilmeli.", "status": "approved", "tags": ["leave", "hr", "approval", "regression"],
         "steps": [{"order": 0, "keyword": "Olduğu gibi", "text": "yönetici bekleyen izin taleplerini görüntülemektedir"}, {"order": 1, "keyword": "Eğer", "text": "bir talebi onaylar"}, {"order": 2, "keyword": "O zaman", "text": "izin durumu 'onaylandı' olur ve çalışana bildirim gider"}]},
        {"title": "Bordro görüntüleme", "description": "Çalışan aylık bordrosunu PDF olarak görüntüleyebilmeli.", "status": "approved", "tags": ["smoke", "payroll", "hr", "regression"],
         "steps": [{"order": 0, "keyword": "Olduğu gibi", "text": "çalışan bordro sayfasındadır"}, {"order": 1, "keyword": "Eğer", "text": "ay seçer ve Görüntüle butonuna tıklar"}, {"order": 2, "keyword": "O zaman", "text": "bordro PDF olarak indirilir"}]},
        {"title": "Performans hedefi oluşturma", "description": "Yönetici çalışan için performans hedefi tanımlayabilmeli.", "status": "approved", "tags": ["performance", "hr"],
         "steps": [{"order": 0, "keyword": "Olduğu gibi", "text": "yönetici performans modülündedir"}, {"order": 1, "keyword": "Eğer", "text": "hedef başlığı, ağırlık ve bitiş tarihini girer"}, {"order": 2, "keyword": "O zaman", "text": "hedef çalışana atanır"}]},
        {"title": "Performans değerlendirme", "description": "Çalışan kendi performans hedeflerini değerlendirebilmeli.", "status": "approved", "tags": ["performance", "hr", "regression"],
         "steps": [{"order": 0, "keyword": "Olduğu gibi", "text": "değerlendirme dönemi açıktır"}, {"order": 1, "keyword": "Eğer", "text": "çalışan hedeflerine not ve yorum girer"}, {"order": 2, "keyword": "O zaman", "text": "değerlendirme yöneticiye gönderilir"}]},
        {"title": "Organizasyon şeması görüntüleme", "description": "Şirket organizasyon yapısı görsel olarak görüntülenebilmeli.", "status": "draft", "tags": ["org", "hr"],
         "steps": [{"order": 0, "keyword": "Olduğu gibi", "text": "kullanıcı organizasyon sayfasındadır"}, {"order": 1, "keyword": "Eğer", "text": "bir departmanı seçer"}, {"order": 2, "keyword": "O zaman", "text": "departman hiyerarşisi ağaç yapısında gösterilir"}]},
        {"title": "Masraf beyanı oluşturma", "description": "Çalışan iş seyahati masraflarını girebilmeli.", "status": "approved", "tags": ["expense", "hr", "regression"],
         "steps": [{"order": 0, "keyword": "Olduğu gibi", "text": "çalışan masraf modülündedir"}, {"order": 1, "keyword": "Eğer", "text": "masraf kalemlerini ve fişleri yükler"}, {"order": 2, "keyword": "O zaman", "text": "masraf beyanı onaya gönderilir"}]},
        {"title": "Çalışan profili güncelleme", "description": "Çalışan iletişim bilgilerini güncelleyebilmeli.", "status": "approved", "tags": ["profile", "hr"],
         "steps": [{"order": 0, "keyword": "Olduğu gibi", "text": "çalışan profil sayfasındadır"}, {"order": 1, "keyword": "Eğer", "text": "telefon numarasını günceller"}, {"order": 2, "keyword": "O zaman", "text": "bilgi başarıyla kaydedilir"}]},
        {"title": "Eğitim katılım kaydı", "description": "Çalışan şirket içi eğitimlere kayıt olabilmeli.", "status": "draft", "tags": ["training", "hr"],
         "steps": [{"order": 0, "keyword": "Olduğu gibi", "text": "çalışan eğitim kataloğundadır"}, {"order": 1, "keyword": "Eğer", "text": "bir eğitimi seçer ve kayıt ol butonuna tıklar"}, {"order": 2, "keyword": "O zaman", "text": "katılım kaydı oluşturulur"}]},
    ],
}

# ──────────────────────────────────────────────
# Requirements per project
# ──────────────────────────────────────────────

REQUIREMENTS_BY_PROJECT = {
    "E-Ticaret Platformu": [
        {"external_id": "REQ-EC-001", "title": "Ürün Kataloğu Arama", "description": "Kullanıcılar ürünleri isim, kategori ve fiyata göre arayabilmeli.", "priority": "high", "source": "PRD v2.1"},
        {"external_id": "REQ-EC-002", "title": "Alışveriş Sepeti", "description": "Kullanıcılar ürünleri sepete ekleyip çıkarabilmeli, miktar güncelleyebilmeli.", "priority": "critical", "source": "PRD v2.1"},
        {"external_id": "REQ-EC-003", "title": "Ödeme İşlemleri", "description": "Kredi kartı ve banka kartı ile güvenli ödeme yapılabilmeli.", "priority": "critical", "source": "PRD v2.1"},
        {"external_id": "REQ-EC-004", "title": "Sipariş Yönetimi", "description": "Kullanıcı sipariş geçmişini görebilmeli, iade talebi oluşturabilmeli.", "priority": "high", "source": "PRD v2.1"},
        {"external_id": "REQ-EC-005", "title": "Kupon Sistemi", "description": "Kampanya kupon kodları sepete uygulanabilmeli.", "priority": "medium", "source": "Marketing Brief"},
        {"external_id": "REQ-EC-006", "title": "Adres Yönetimi", "description": "Kullanıcılar birden fazla teslimat adresi tanımlayabilmeli.", "priority": "medium", "source": "PRD v2.1"},
        {"external_id": "REQ-EC-007", "title": "Stok Yönetimi", "description": "Stokta olmayan ürünler satışa kapatılmalı.", "priority": "high", "source": "Ops Team"},
    ],
    "Mobil Bankacılık API": [
        {"external_id": "REQ-MB-001", "title": "Hesap Sorgulama API", "description": "Bakiye, IBAN ve hesap bilgileri REST API ile sorgulanabilmeli.", "priority": "critical", "source": "API Spec v3"},
        {"external_id": "REQ-MB-002", "title": "Para Transferi", "description": "Havale ve EFT işlemleri güvenli şekilde gerçekleştirilebilmeli.", "priority": "critical", "source": "API Spec v3"},
        {"external_id": "REQ-MB-003", "title": "2FA Doğrulama", "description": "Yüksek tutarlı işlemlerde SMS doğrulama zorunlu olmalı.", "priority": "critical", "source": "Güvenlik Politikası"},
        {"external_id": "REQ-MB-004", "title": "Kredi Başvurusu", "description": "Bireysel kredi başvurusu API üzerinden yapılabilmeli.", "priority": "high", "source": "API Spec v3"},
        {"external_id": "REQ-MB-005", "title": "Döviz İşlemleri", "description": "Döviz alım/satım ve kur sorgulama desteklenmeli.", "priority": "medium", "source": "API Spec v3"},
    ],
    "İK Yönetim Sistemi": [
        {"external_id": "REQ-IK-001", "title": "İzin Yönetimi", "description": "Çalışanlar izin talebi oluşturabilmeli, yöneticiler onaylayabilmeli.", "priority": "critical", "source": "HR Module Spec"},
        {"external_id": "REQ-IK-002", "title": "Bordro Görüntüleme", "description": "Çalışanlar aylık bordrolarını PDF olarak indirebilmeli.", "priority": "high", "source": "HR Module Spec"},
        {"external_id": "REQ-IK-003", "title": "Performans Yönetimi", "description": "Hedef tanımlama, takip ve değerlendirme süreci desteklenmeli.", "priority": "high", "source": "HR Module Spec"},
        {"external_id": "REQ-IK-004", "title": "Masraf Yönetimi", "description": "Çalışanlar masraf beyanı oluşturup fatura yükleyebilmeli.", "priority": "medium", "source": "Finance Team"},
    ],
}

# ──────────────────────────────────────────────
# Helper: scenario-requirement links
# ──────────────────────────────────────────────

SCENARIO_REQ_LINKS = {
    "E-Ticaret Platformu": {0: [0], 1: [1], 2: [1], 3: [2], 4: [2], 5: [3], 6: [4], 7: [4], 8: [5], 10: [6], 11: [3], 12: [1]},
    "Mobil Bankacılık API": {0: [0], 1: [1], 2: [1], 3: [1], 4: [3], 5: [0], 6: [0], 7: [2], 8: [0], 9: [4], 10: [4], 11: [2]},
    "İK Yönetim Sistemi": {0: [0], 1: [0], 2: [0], 3: [1], 4: [2], 5: [2], 7: [3], 8: [0]},
}


def _seed_ai_pipeline(db: Session, project, scenarios: list, admin_user) -> None:
    """AI batch → test cases → onaylananlar senaryo'ya bağlı → otomasyon artifact."""
    import os
    from pathlib import Path
    from datetime import timezone

    batch = TspmAiBatch(
        project_id=project.id,
        source_type="document",
        source_name="Mobil Bankacılık API Spec v3.pdf",
        source_text_preview="Mobil bankacılık uygulamasının REST API gereksinimleri. "
                            "Havale, EFT, bakiye sorgulama, 2FA ve kredi başvurusu akışlarını kapsar.",
        ai_provider="openai",
        ai_model="gpt-4o",
        extra_instructions="Güvenlik ve negatif akışlara özellikle dikkat et.",
        status="ready",
        total_generated=5,
        approved_count=3,
        rejected_count=1,
        completed_at=utcnow() - timedelta(days=5),
    )
    db.add(batch)
    db.flush()

    test_cases_data = [
        {
            "title": "Başarılı havale işlemi — yeterli bakiye",
            "description": "Kaynak hesapta yeterli bakiye varken iç transfer başarıyla tamamlanmalı.",
            "module_name": "Transfer", "feature_area": "Havale",
            "test_type": "functional", "priority": "critical", "risk_level": "high",
            "preconditions": ["Müşteri oturum açmış olmalı", "Kaynak hesapta en az 500 TL bakiye olmalı"],
            "steps": [
                {"order": 1, "action": "Kaynak hesabı seç", "expected": "Hesap listesi görüntülenir"},
                {"order": 2, "action": "Hedef hesabı seç ve 500 TL gir", "expected": "Tutar alanı dolu"},
                {"order": 3, "action": "Transfer isteği gönder", "expected": "HTTP 201 — transfer ID döner"},
                {"order": 4, "action": "Bakiyeleri kontrol et", "expected": "Kaynak -500, Hedef +500 TL"},
            ],
            "expected_result": "Transfer tamamlanır, bakiyeler güncellenir, işlem geçmişine kaydedilir.",
            "tags": ["transfer", "banking", "smoke", "critical"],
            "review_status": "approved",
            "scenario_idx": 1,  # Hesaplar arası havale
        },
        {
            "title": "2FA olmadan yüksek tutarlı transfer reddi",
            "description": "10.000 TL üzeri transferde SMS doğrulaması yapılmadan işlem tamamlanamamalı.",
            "module_name": "Transfer", "feature_area": "Güvenlik",
            "test_type": "security", "priority": "critical", "risk_level": "high",
            "preconditions": ["Müşteri oturum açmış", "Bakiye > 10.000 TL"],
            "steps": [
                {"order": 1, "action": "15.000 TL transfer isteği gönder", "expected": "HTTP 202 — OTP istenir"},
                {"order": 2, "action": "OTP göndermeden işlemi onayla", "expected": "HTTP 403 — doğrulama gerekli"},
            ],
            "expected_result": "Transfer tamamlanmaz. 403 hatası ve 'OTP doğrulaması gerekli' mesajı döner.",
            "tags": ["security", "2fa", "negative", "critical"],
            "review_status": "approved",
            "scenario_idx": 7,  # İki faktörlü doğrulama
        },
        {
            "title": "Hesap hareketleri pagination",
            "description": "Çok sayıda hareket olduğunda sayfalama doğru çalışmalı.",
            "module_name": "Hesap", "feature_area": "Hareketler",
            "test_type": "functional", "priority": "medium", "risk_level": "low",
            "preconditions": ["Hesapta 100+ hareket mevcut"],
            "steps": [
                {"order": 1, "action": "GET /accounts/{id}/transactions?page=1&limit=20", "expected": "HTTP 200 — 20 kayıt"},
                {"order": 2, "action": "GET /accounts/{id}/transactions?page=2&limit=20", "expected": "HTTP 200 — sonraki 20 kayıt"},
                {"order": 3, "action": "Son sayfada limit aşımı", "expected": "HTTP 200 — boş liste"},
            ],
            "expected_result": "Sayfalama doğru çalışır, fazla kayıt dönmez.",
            "tags": ["account", "api", "pagination"],
            "review_status": "approved",
            "scenario_idx": 8,  # Hesap hareketleri listeleme
        },
        {
            "title": "Rate limit aşımında throttling",
            "description": "Dakikada 60'tan fazla API isteğinde throttling devreye girmeli.",
            "module_name": "API", "feature_area": "Rate Limiting",
            "test_type": "negative", "priority": "high", "risk_level": "medium",
            "preconditions": ["API key geçerli"],
            "steps": [
                {"order": 1, "action": "60 istek/dk limit dahilinde istek gönder", "expected": "HTTP 200"},
                {"order": 2, "action": "61. isteği gönder", "expected": "HTTP 429 — Too Many Requests"},
            ],
            "expected_result": "429 hatası ve Retry-After header'ı döner.",
            "tags": ["api", "security", "performance"],
            "review_status": "pending",
            "scenario_idx": None,
        },
        {
            "title": "SQL injection denemesi — IBAN alanı",
            "description": "IBAN alanına SQL injection payload'u girildiğinde sistem güvenli yanıt vermeli.",
            "module_name": "Transfer", "feature_area": "Güvenlik",
            "test_type": "security", "priority": "critical", "risk_level": "high",
            "preconditions": [],
            "steps": [
                {"order": 1, "action": "IBAN alanına \"' OR '1'='1\" gir", "expected": "HTTP 400 — geçersiz IBAN"},
            ],
            "expected_result": "400 hatası döner. DB sorgusu çalıştırılmaz.",
            "tags": ["security", "injection", "negative"],
            "review_status": "rejected",
            "reviewer_note": "Bu tür güvenlik testleri dedicated pentest sürecine aktarıldı.",
            "scenario_idx": None,
        },
    ]

    approved_scenario_ids: list[str] = []
    for tc_data in test_cases_data:
        sc_idx = tc_data.pop("scenario_idx")
        linked_sc_id = scenarios[sc_idx].id if sc_idx is not None and sc_idx < len(scenarios) else None
        tc = TspmTestCase(
            project_id=project.id,
            batch_id=batch.id,
            title=tc_data["title"],
            description=tc_data["description"],
            module_name=tc_data["module_name"],
            feature_area=tc_data["feature_area"],
            test_type=tc_data["test_type"],
            priority=tc_data["priority"],
            risk_level=tc_data["risk_level"],
            preconditions=tc_data["preconditions"],
            steps=tc_data["steps"],
            expected_result=tc_data["expected_result"],
            tags=tc_data["tags"],
            review_status=tc_data["review_status"],
            reviewer_note=tc_data.get("reviewer_note"),
            scenario_id=linked_sc_id if tc_data["review_status"] == "approved" else None,
        )
        db.add(tc)
        if tc_data["review_status"] == "approved":
            approved_scenario_ids.append(tc_data["title"][:30])
    db.flush()
    print(f"  AI batch: {len(test_cases_data)} test case ({batch.approved_count} onaylı, {batch.rejected_count} reddedildi)")

    # ── Automation artifacts ──
    artifacts_dir = Path(os.environ.get("ARTIFACTS_BASE_DIR",
                         Path(__file__).resolve().parent.parent / "artifacts")) / batch.id
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    gherkin_content = """Feature: Mobil Bankacılık Transfer İşlemleri
  Mobil bankacılık API'sinin para transfer akışlarını doğrular.
  AI destekli test senaryolarından üretilmiştir.

  Background:
    Given müşteri oturum açmıştır
    And hesapta yeterli bakiye mevcuttur

  @smoke @critical @transfer
  Scenario: Başarılı iç transfer
    Given kaynak hesap TR000000000000000000000001 seçilmiştir
    When hedef hesap TR000000000000000000000002 için 500 TL transfer isteği gönderilir
    Then HTTP 201 yanıt kodu alınır
    And kaynak hesap bakiyesi 500 TL azalmıştır
    And hedef hesap bakiyesi 500 TL artmıştır

  @security @critical @2fa
  Scenario: 2FA olmadan yüksek tutarlı transfer engellenir
    Given müşteri 15000 TL transfer yapmak istemektedir
    When OTP doğrulaması yapılmadan transfer isteği gönderilir
    Then HTTP 403 yanıt kodu alınır
    And hata mesajı "OTP doğrulaması gerekli" içerir

  @account @api
  Scenario: Hesap hareketleri sayfalama
    Given hesapta 100 hareket bulunmaktadır
    When GET /accounts/{id}/transactions?page=1&limit=20 isteği gönderilir
    Then HTTP 200 yanıt kodu alınır
    And yanıtta tam olarak 20 kayıt bulunur
"""

    playwright_content = """import { test, expect } from '@playwright/test';

/**
 * Mobil Bankacılık API — Transfer Test Suite
 * AI destekli test case'lerinden otomatik üretilmiştir.
 * Batch ID: {batch_id}
 */

const BASE_URL = process.env.BANKING_API_URL || 'https://api.bgbank.test/v1';
const TEST_TOKEN = process.env.BANKING_TEST_TOKEN || 'test-token-demo';

test.describe('Transfer İşlemleri', () => {{
  let authHeaders: {{ Authorization: string }};

  test.beforeAll(async () => {{
    authHeaders = {{ Authorization: `Bearer ${{TEST_TOKEN}}` }};
  }});

  test('@smoke @critical başarılı iç transfer', async ({{ request }}) => {{
    const response = await request.post(`${{BASE_URL}}/transfers/internal`, {{
      headers: authHeaders,
      data: {{
        from_account: 'TR000000000000000000000001',
        to_account: 'TR000000000000000000000002',
        amount: 500,
        currency: 'TRY',
      }},
    }});
    expect(response.status()).toBe(201);
    const body = await response.json();
    expect(body).toHaveProperty('transfer_id');
    expect(body.status).toBe('completed');
  }});

  test('@security @critical 2FA olmadan yüksek tutarlı transfer reddi', async ({{ request }}) => {{
    const response = await request.post(`${{BASE_URL}}/transfers/internal`, {{
      headers: authHeaders,
      data: {{ from_account: 'TR000000000000000000000001', to_account: 'TR000000000000000000000002', amount: 15000 }},
    }});
    expect(response.status()).toBe(403);
    const body = await response.json();
    expect(body.error).toContain('OTP');
  }});

  test('@account hesap hareketleri pagination', async ({{ request }}) => {{
    const response = await request.get(
      `${{BASE_URL}}/accounts/TR000000000000000000000001/transactions?page=1&limit=20`,
      {{ headers: authHeaders }}
    );
    expect(response.status()).toBe(200);
    const body = await response.json();
    expect(body.data).toHaveLength(20);
    expect(body).toHaveProperty('total');
  }});
}});
""".replace("{batch_id}", batch.id)

    gherkin_path = artifacts_dir / "mobil_bankacilik_transfer.feature"
    playwright_path = artifacts_dir / "mobil_bankacilik_transfer.spec.ts"
    gherkin_path.write_text(gherkin_content, encoding="utf-8")
    playwright_path.write_text(playwright_content, encoding="utf-8")

    db.add(TspmAutomationArtifact(
        project_id=project.id,
        batch_id=batch.id,
        artifact_type="gherkin",
        feature_name="Mobil Bankacılık Transfer İşlemleri",
        filename="mobil_bankacilik_transfer.feature",
        storage_path=str(gherkin_path),
        mime_type="text/plain",
        size_bytes=gherkin_path.stat().st_size,
        source_test_case_count=3,
    ))
    db.add(TspmAutomationArtifact(
        project_id=project.id,
        batch_id=batch.id,
        artifact_type="playwright",
        feature_name="Mobil Bankacılık Transfer İşlemleri",
        filename="mobil_bankacilik_transfer.spec.ts",
        storage_path=str(playwright_path),
        mime_type="text/typescript",
        size_bytes=playwright_path.stat().st_size,
        source_test_case_count=3,
    ))
    db.flush()
    print(f"  2 otomasyon artifact oluşturuldu ({artifacts_dir})")


def _seed_historical_executions(db: Session, project, scenarios: list) -> None:
    """Son 90 gün için gerçekçi koşu geçmişi — analytics grafikleri için."""
    approved = [s for s in scenarios if s.status == "approved"]
    if not approved:
        return

    # Pass rate zamanla artan bir trend: ilk ay ~75%, son hafta ~95%
    history_configs = [
        # (days_ago, pass_rate_target, name_suffix)
        (85, 0.70, "Haftalık Regresyon W-12"),
        (78, 0.72, "Smoke Test W-11"),
        (71, 0.75, "Haftalık Regresyon W-11"),
        (64, 0.78, "Smoke Test W-10"),
        (57, 0.80, "Haftalık Regresyon W-10"),
        (50, 0.82, "Sprint 1 Final"),
        (43, 0.85, "Haftalık Regresyon W-9"),
        (36, 0.85, "Smoke Test W-8"),
        (29, 0.88, "Haftalık Regresyon W-8"),
        (22, 0.90, "Sprint 2 Final"),
        (15, 0.92, "Haftalık Regresyon W-7"),
        (8,  0.93, "Smoke Test W-6"),
        (4,  0.95, "Haftalık Regresyon W-6"),
        (2,  0.95, "Smoke Test — Dün"),
        (1,  0.97, "Nightly Build — Bugün"),
    ]

    for days_ago, target_rate, name in history_configs:
        subset = approved[:min(8, len(approved))]
        total = len(subset)
        passed = round(total * target_rate)
        failed = total - passed
        results = ["passed"] * passed + ["failed"] * failed
        random.shuffle(results)

        ex = TspmExecution(
            project_id=project.id,
            name=name,
            status="completed",
        )
        db.add(ex)
        db.flush()

        for sc, res in zip(subset, results):
            db.add(TspmExecutionResult(execution_id=ex.id, scenario_id=sc.id, status=res))

        executed_at = utcnow() - timedelta(days=days_ago, hours=random.randint(0, 4))
        db.add(TspmExecutionMetrics(
            project_id=project.id,
            execution_id=ex.id,
            total=total,
            passed=passed,
            failed=failed,
            skipped=0,
            pass_rate=round(passed / total * 100, 1),
            duration_seconds=round(random.uniform(45, 240), 1),
            executed_at=executed_at,
        ))
    db.flush()
    print(f"  {len(history_configs)} tarihsel koşu eklendi (90 gün, artan trend)")


def seed_all(db: Session) -> None:
    # ── 1. Roles & Permissions ──
    roles: dict[str, Role] = {}
    for name in ["admin", "operator", "viewer"]:
        r = db.scalar(select(Role).where(Role.name == name))
        if r is None:
            r = Role(name=name)
            db.add(r)
            db.flush()
        roles[name] = r

    for role_name, perms in ROLE_PERMISSIONS.items():
        role = roles.get(role_name)
        if role is None:
            continue
        existing = {rp.permission for rp in role.permissions}
        for perm in perms:
            if perm not in existing:
                db.add(RolePermission(role_id=role.id, permission=perm))
    db.flush()
    print("Roller ve izinler hazır.")

    # ── 2. Users ──
    user_objs: dict[str, User] = {}
    for u in USERS:
        user = db.scalar(select(User).where(User.email == u["email"]))
        if user is None:
            user = User(email=u["email"], password_hash=hash_password(u["password"]), is_active=True)
            db.add(user)
            db.flush()
        if roles[u["role"]] not in user.roles:
            user.roles.append(roles[u["role"]])
        user_objs[u["email"]] = user
    db.flush()
    print(f"{len(user_objs)} kullanıcı hazır.")

    admin_user = user_objs["admin@example.com"]

    # ── 3. Clean up existing demo projects ──
    for p_data in PROJECTS:
        existing = db.scalar(select(TspmProject).where(TspmProject.name == p_data["name"]))
        if existing:
            db.delete(existing)
    db.flush()

    # ── 4. Projects ──
    for p_idx, p_data in enumerate(PROJECTS):
        print(f"\n{'='*60}")
        print(f"Proje: {p_data['name']}")
        print(f"{'='*60}")

        project = TspmProject(name=p_data["name"], description=p_data["description"])
        db.add(project)
        db.flush()

        # ── Members ──
        members = [
            TspmProjectMember(project_id=project.id, user_id=admin_user.id, role="admin"),
        ]
        operator_emails = ["ahmet.yilmaz@bgtest.com", "elif.demir@bgtest.com", "can.ozturk@bgtest.com"]
        viewer_emails = ["mehmet.kaya@bgtest.com", "zeynep.celik@bgtest.com"]
        for email in operator_emails[:2]:
            members.append(TspmProjectMember(project_id=project.id, user_id=user_objs[email].id, role="editor"))
        for email in viewer_emails[:1]:
            members.append(TspmProjectMember(project_id=project.id, user_id=user_objs[email].id, role="viewer"))
        db.add_all(members)
        db.flush()
        print(f"  {len(members)} proje üyesi eklendi")

        # ── Scenarios ──
        scenarios_data = SCENARIOS_BY_PROJECT[p_data["name"]]
        scenario_objs: list[TspmScenario] = []
        for s in scenarios_data:
            sc = TspmScenario(
                project_id=project.id,
                title=s["title"],
                description=s["description"],
                status=s["status"],
                steps=s["steps"],
                tags=s.get("tags", []),
                current_version=1,
            )
            db.add(sc)
            scenario_objs.append(sc)
        db.flush()
        print(f"  {len(scenario_objs)} senaryo oluşturuldu")

        # ── Scenario Versions ──
        for sc in scenario_objs:
            db.add(TspmScenarioVersion(
                scenario_id=sc.id,
                version_number=1,
                title=sc.title,
                description=sc.description,
                steps=sc.steps,
                status=sc.status,
                changed_by=admin_user.id,
            ))
        for sc in random.sample(scenario_objs, min(5, len(scenario_objs))):
            db.add(TspmScenarioVersion(
                scenario_id=sc.id,
                version_number=2,
                title=sc.title + " (güncellendi)",
                description=sc.description,
                steps=sc.steps,
                status=sc.status,
                changed_by=user_objs["ahmet.yilmaz@bgtest.com"].id,
            ))
            sc.current_version = 2
        db.flush()
        print(f"  Senaryo versiyonları oluşturuldu")

        # ── Requirements ──
        reqs_data = REQUIREMENTS_BY_PROJECT[p_data["name"]]
        req_objs: list[TspmRequirement] = []
        for r in reqs_data:
            req = TspmRequirement(
                project_id=project.id,
                external_id=r["external_id"],
                title=r["title"],
                description=r["description"],
                priority=r["priority"],
                source=r.get("source"),
            )
            db.add(req)
            req_objs.append(req)
        db.flush()
        print(f"  {len(req_objs)} gereksinim oluşturuldu")

        # ── Scenario ↔ Requirement links ──
        links_map = SCENARIO_REQ_LINKS.get(p_data["name"], {})
        link_count = 0
        for sc_idx, req_indices in links_map.items():
            if sc_idx < len(scenario_objs):
                for ri in req_indices:
                    if ri < len(req_objs):
                        db.add(TspmScenarioRequirement(
                            scenario_id=scenario_objs[sc_idx].id,
                            requirement_id=req_objs[ri].id,
                        ))
                        link_count += 1
        db.flush()
        print(f"  {link_count} senaryo-gereksinim bağlantısı oluşturuldu")

        # ── Test Data Sets ──
        test_data_sets = []
        if p_data["name"] == "E-Ticaret Platformu":
            ds1 = TspmTestDataSet(
                project_id=project.id,
                name="Ödeme Test Verileri",
                description="Farklı kart tipleri ve sonuçları ile ödeme senaryoları",
                columns=[
                    {"name": "kart_no", "type": "string"},
                    {"name": "son_kullanma", "type": "string"},
                    {"name": "cvv", "type": "string"},
                    {"name": "tutar", "type": "number"},
                    {"name": "beklenen_sonuc", "type": "string"},
                ],
                rows=[
                    ["4111111111111111", "12/28", "123", 150.00, "başarılı"],
                    ["4222222222222222", "06/25", "456", 500.00, "süresi dolmuş"],
                    ["5111111111111111", "03/29", "789", 10000.00, "yetersiz bakiye"],
                    ["4333333333333333", "09/27", "321", 75.50, "başarılı"],
                    ["4444444444444444", "01/26", "654", 0.01, "başarılı"],
                ],
            )
            ds2 = TspmTestDataSet(
                project_id=project.id,
                name="Kupon Kodları",
                description="Geçerli ve geçersiz kupon kodları test verisi",
                columns=[
                    {"name": "kupon_kodu", "type": "string"},
                    {"name": "indirim_orani", "type": "number"},
                    {"name": "gecerlilik", "type": "string"},
                    {"name": "beklenen_sonuc", "type": "string"},
                ],
                rows=[
                    ["YENI2024", 15.0, "geçerli", "indirim uygulanır"],
                    ["SUMMER50", 50.0, "süresi dolmuş", "hata mesajı"],
                    ["VIP10", 10.0, "geçerli", "indirim uygulanır"],
                    ["INVALIDX", 0.0, "geçersiz", "hata mesajı"],
                ],
            )
            test_data_sets = [ds1, ds2]
        elif p_data["name"] == "Mobil Bankacılık API":
            ds1 = TspmTestDataSet(
                project_id=project.id,
                name="Transfer Test Verileri",
                description="Havale ve EFT senaryoları için test hesapları",
                columns=[
                    {"name": "kaynak_iban", "type": "string"},
                    {"name": "hedef_iban", "type": "string"},
                    {"name": "tutar", "type": "number"},
                    {"name": "beklenen_sonuc", "type": "string"},
                ],
                rows=[
                    ["TR000000000000000000000001", "TR000000000000000000000002", 500.0, "başarılı"],
                    ["TR000000000000000000000001", "TR000000000000000000000003", 999999.0, "yetersiz bakiye"],
                    ["TR000000000000000000000002", "TR000000000000000000000001", 1250.75, "başarılı"],
                ],
            )
            test_data_sets = [ds1]
        else:
            ds1 = TspmTestDataSet(
                project_id=project.id,
                name="İzin Talebi Test Verileri",
                description="Farklı izin türleri ve gün sayıları",
                columns=[
                    {"name": "calisan", "type": "string"},
                    {"name": "izin_turu", "type": "string"},
                    {"name": "gun_sayisi", "type": "number"},
                    {"name": "beklenen_sonuc", "type": "string"},
                ],
                rows=[
                    ["Ahmet Yılmaz", "yıllık", 5, "onaya gider"],
                    ["Elif Demir", "mazeret", 1, "otomatik onay"],
                    ["Mehmet Kaya", "yıllık", 20, "bakiye yetersiz"],
                    ["Zeynep Çelik", "sağlık", 3, "onaya gider"],
                ],
            )
            test_data_sets = [ds1]

        db.add_all(test_data_sets)
        db.flush()
        print(f"  {len(test_data_sets)} test veri seti oluşturuldu")

        # ── Data Bindings ──
        if test_data_sets and len(scenario_objs) >= 4:
            db.add(TspmScenarioDataBinding(
                scenario_id=scenario_objs[3].id,
                data_set_id=test_data_sets[0].id,
                parameter_mapping={"kart_no": "{{kart_no}}", "tutar": "{{tutar}}"},
            ))
            db.flush()
            print(f"  Veri bağlantıları oluşturuldu")

        # ── Executions ──
        num_scenarios = len(scenario_objs)
        execution_configs = [
            {"name": f"Sprint 1 Koşusu — {p_data['name']}", "indices": list(range(min(6, num_scenarios))),
             "results_fn": lambda n: ["passed"] * max(0, n - 1) + ["failed"] if n > 0 else []},
            {"name": f"Sprint 2 Koşusu — {p_data['name']}", "indices": list(range(min(6, num_scenarios), min(10, num_scenarios))),
             "results_fn": lambda n: ["passed"] * n},
            {"name": f"Regresyon Koşusu — {p_data['name']}", "indices": list(range(min(8, num_scenarios))),
             "results_fn": lambda n: random.choices(["passed", "passed", "passed", "failed"], k=n)},
            {"name": f"Smoke Test — {p_data['name']}", "indices": [0, 2, 4] if num_scenarios > 4 else [0],
             "results_fn": lambda n: ["passed"] * n},
        ]

        for ex_cfg in execution_configs:
            indices = [i for i in ex_cfg["indices"] if i < num_scenarios]
            if not indices:
                continue
            results = ex_cfg["results_fn"](len(indices))
            total = len(indices)
            passed = results.count("passed")
            failed = results.count("failed")
            skipped = results.count("skipped")
            pass_rate = (passed / total * 100) if total > 0 else 0

            ex = TspmExecution(project_id=project.id, name=ex_cfg["name"], status="completed")
            db.add(ex)
            db.flush()
            for idx, res in zip(indices, results):
                db.add(TspmExecutionResult(
                    execution_id=ex.id,
                    scenario_id=scenario_objs[idx].id,
                    status=res,
                ))
            db.add(TspmExecutionMetrics(
                project_id=project.id,
                execution_id=ex.id,
                total=total,
                passed=passed,
                failed=failed,
                skipped=skipped,
                pass_rate=round(pass_rate, 1),
                duration_seconds=round(random.uniform(12, 180), 1),
                executed_at=rand_past(30),
            ))
        db.flush()
        print(f"  {len(execution_configs)} test koşusu oluşturuldu")

        # ── Flows ──
        flows = [
            TspmFlow(
                project_id=project.id,
                name="Ana İş Akışı",
                description=f"{p_data['name']} temel kullanıcı akışı",
                nodes=[
                    {"id": "n1", "type": "input", "position": {"x": 50, "y": 100}, "data": {"label": "Başlangıç"}},
                    {"id": "n2", "type": "default", "position": {"x": 250, "y": 50}, "data": {"label": "Giriş Yap"}},
                    {"id": "n3", "type": "default", "position": {"x": 450, "y": 50}, "data": {"label": "Ana İşlem"}},
                    {"id": "n4", "type": "default", "position": {"x": 450, "y": 150}, "data": {"label": "Hata Durumu"}},
                    {"id": "n5", "type": "output", "position": {"x": 650, "y": 100}, "data": {"label": "Sonuç"}},
                ],
                edges=[
                    {"id": "e1-2", "source": "n1", "target": "n2"},
                    {"id": "e2-3", "source": "n2", "target": "n3"},
                    {"id": "e2-4", "source": "n2", "target": "n4"},
                    {"id": "e3-5", "source": "n3", "target": "n5"},
                    {"id": "e4-5", "source": "n4", "target": "n5"},
                ],
            ),
            TspmFlow(
                project_id=project.id,
                name="Hata Yönetimi Akışı",
                description="Hata tespiti ve raporlama süreci",
                nodes=[
                    {"id": "n1", "type": "input", "position": {"x": 50, "y": 80}, "data": {"label": "Hata Tespit"}},
                    {"id": "n2", "type": "default", "position": {"x": 250, "y": 80}, "data": {"label": "Loglama"}},
                    {"id": "n3", "type": "default", "position": {"x": 450, "y": 80}, "data": {"label": "Bildirim"}},
                    {"id": "n4", "type": "output", "position": {"x": 650, "y": 80}, "data": {"label": "Rapor"}},
                ],
                edges=[
                    {"id": "e1-2", "source": "n1", "target": "n2"},
                    {"id": "e2-3", "source": "n2", "target": "n3"},
                    {"id": "e3-4", "source": "n3", "target": "n4"},
                ],
            ),
        ]
        db.add_all(flows)
        db.flush()
        print(f"  {len(flows)} akış oluşturuldu")

        # ── Regression Sets ──
        approved_indices = [i for i, s in enumerate(scenario_objs) if s.status == "approved"]
        reg_sets = [
            TspmRegressionSet(
                project_id=project.id,
                name=f"Kritik Akışlar — {p_data['name']}",
                description="Her deploy öncesi koşulacak minimum senaryo seti",
                scenario_ids=[scenario_objs[i].id for i in approved_indices[:5]],
            ),
            TspmRegressionSet(
                project_id=project.id,
                name=f"Tam Regresyon — {p_data['name']}",
                description="Release öncesi tüm onaylı senaryolar",
                scenario_ids=[scenario_objs[i].id for i in approved_indices],
            ),
            TspmRegressionSet(
                project_id=project.id,
                name=f"Sprint 3 Regresyon",
                description="Sprint 3 kapsamındaki senaryolar",
                scenario_ids=[scenario_objs[i].id for i in approved_indices[2:7] if i < len(scenario_objs)],
            ),
        ]
        db.add_all(reg_sets)
        db.flush()
        print(f"  {len(reg_sets)} regresyon seti oluşturuldu")

        # ── Approvals ──
        approval_data = [
            {"title": f"{scenario_objs[0].title} — v1 onayı", "status": "approved", "sc_idx": 0},
            {"title": f"{scenario_objs[1].title} — güncelleme onayı", "status": "approved", "sc_idx": 1},
            {"title": f"{scenario_objs[min(3, num_scenarios-1)].title} — risk değerlendirmesi", "status": "pending", "sc_idx": min(3, num_scenarios - 1)},
            {"title": f"Toplu senaryo onayı — Sprint 2", "status": "pending", "sc_idx": None},
            {"title": f"{scenario_objs[min(5, num_scenarios-1)].title} — SLA kontrolü", "status": "rejected", "sc_idx": min(5, num_scenarios - 1)},
        ]
        for ap in approval_data:
            sc_id = scenario_objs[ap["sc_idx"]].id if ap["sc_idx"] is not None and ap["sc_idx"] < num_scenarios else None
            obj = TspmApproval(
                project_id=project.id,
                title=ap["title"],
                status=ap["status"],
                scenario_id=sc_id,
            )
            if ap["status"] != "pending":
                obj.decided_at = rand_past(15)
            db.add(obj)
        db.flush()
        print(f"  {len(approval_data)} onay kaydı oluşturuldu")

        # ── Imports ──
        imports = [
            TspmImport(project_id=project.id, filename="sprint1_senaryolari.xlsx", status="completed", scenario_count=6,
                        raw_payload={"source": "Excel", "version": "1.0"}),
            TspmImport(project_id=project.id, filename="regression_export.json", status="completed", scenario_count=12,
                        raw_payload={"source": "JSON", "format": "TestwrightAI"}),
            TspmImport(project_id=project.id, filename="api_tests.yaml", status="failed", scenario_count=0,
                        raw_payload={"source": "YAML", "error": "Geçersiz format"}),
        ]
        db.add_all(imports)
        db.flush()
        print(f"  {len(imports)} import kaydı oluşturuldu")

        # ── Schedules ──
        schedules = [
            TspmSchedule(
                project_id=project.id,
                name="Günlük Smoke Test",
                cron_expression="0 8 * * *",
                regression_set_id=reg_sets[0].id,
                scenario_ids=[scenario_objs[i].id for i in approved_indices[:3]],
                is_active=True,
                last_run_at=rand_past(1),
                next_run_at=rand_future(1),
                created_by=admin_user.id,
            ),
            TspmSchedule(
                project_id=project.id,
                name="Haftalık Regresyon",
                cron_expression="0 22 * * 5",
                regression_set_id=reg_sets[1].id,
                scenario_ids=[scenario_objs[i].id for i in approved_indices],
                is_active=True,
                last_run_at=rand_past(7),
                next_run_at=rand_future(7),
                created_by=admin_user.id,
            ),
            TspmSchedule(
                project_id=project.id,
                name="Sprint Sonu Koşusu",
                cron_expression="0 18 */14 * *",
                regression_set_id=reg_sets[2].id,
                scenario_ids=[scenario_objs[i].id for i in approved_indices[2:7] if i < len(scenario_objs)],
                is_active=False,
                created_by=user_objs["ahmet.yilmaz@bgtest.com"].id,
            ),
        ]
        db.add_all(schedules)
        db.flush()
        print(f"  {len(schedules)} zamanlama oluşturuldu")

        # ── Integrations ──
        integrations = [
            TspmIntegration(
                project_id=project.id,
                provider="jira",
                config={"base_url": "https://bgtest.atlassian.net", "project_key": "BGTS", "api_token": "***"},
                is_active=True,
                last_sync_at=rand_past(2),
            ),
            TspmIntegration(
                project_id=project.id,
                provider="slack",
                config={"webhook_url": "https://hooks.slack.com/services/T00/B00/xxx", "channel": "#test-notifications"},
                is_active=True,
                last_sync_at=rand_past(1),
            ),
            TspmIntegration(
                project_id=project.id,
                provider="jenkins",
                config={"base_url": "https://jenkins.bgtest.internal", "job_name": "regression-pipeline"},
                is_active=False,
            ),
        ]
        db.add_all(integrations)
        db.flush()
        print(f"  {len(integrations)} entegrasyon oluşturuldu")

        # ── API Collections & Requests ──
        if p_data["name"] == "Mobil Bankacılık API":
            col1 = TspmApiCollection(
                project_id=project.id,
                name="Hesap İşlemleri",
                description="Hesap sorgulama ve yönetim API'leri",
                base_url="https://api.bgbank.test/v1",
                headers={"Authorization": "Bearer {{token}}", "Content-Type": "application/json"},
            )
            db.add(col1)
            db.flush()
            api_requests_1 = [
                TspmApiRequest(collection_id=col1.id, name="Bakiye Sorgula", method="GET", path="/accounts/{{account_id}}/balance",
                               headers=None, body=None, assertions=[{"type": "status", "expected": 200}], order=1),
                TspmApiRequest(collection_id=col1.id, name="Hesap Detayı", method="GET", path="/accounts/{{account_id}}",
                               headers=None, body=None, assertions=[{"type": "status", "expected": 200}, {"type": "jsonpath", "path": "$.iban", "expected": "TR*"}], order=2),
                TspmApiRequest(collection_id=col1.id, name="Hesap Hareketleri", method="GET", path="/accounts/{{account_id}}/transactions?limit=30",
                               headers=None, body=None, assertions=[{"type": "status", "expected": 200}], order=3),
            ]
            db.add_all(api_requests_1)

            col2 = TspmApiCollection(
                project_id=project.id,
                name="Transfer İşlemleri",
                description="Havale, EFT ve döviz transferi API'leri",
                base_url="https://api.bgbank.test/v1",
                headers={"Authorization": "Bearer {{token}}", "Content-Type": "application/json"},
            )
            db.add(col2)
            db.flush()
            api_requests_2 = [
                TspmApiRequest(collection_id=col2.id, name="Havale Gönder", method="POST", path="/transfers/internal",
                               headers=None, body={"from_account": "{{source}}", "to_account": "{{target}}", "amount": 500},
                               assertions=[{"type": "status", "expected": 201}], order=1),
                TspmApiRequest(collection_id=col2.id, name="EFT Gönder", method="POST", path="/transfers/eft",
                               headers=None, body={"from_account": "{{source}}", "to_iban": "{{iban}}", "amount": 1000, "description": "Test EFT"},
                               assertions=[{"type": "status", "expected": 202}], order=2),
            ]
            db.add_all(api_requests_2)
            db.flush()

            db.add(TspmApiTestRun(collection_id=col1.id, status="completed",
                                   results=[{"request": "Bakiye Sorgula", "status": 200, "passed": True, "duration_ms": 45},
                                            {"request": "Hesap Detayı", "status": 200, "passed": True, "duration_ms": 62},
                                            {"request": "Hesap Hareketleri", "status": 200, "passed": True, "duration_ms": 120}]))
            db.add(TspmApiTestRun(collection_id=col2.id, status="completed",
                                   results=[{"request": "Havale Gönder", "status": 201, "passed": True, "duration_ms": 230},
                                            {"request": "EFT Gönder", "status": 500, "passed": False, "duration_ms": 5100, "error": "Timeout"}]))
            db.flush()
            print(f"  2 API koleksiyonu, {len(api_requests_1)+len(api_requests_2)} istek ve 2 test koşusu oluşturuldu")

        elif p_data["name"] == "E-Ticaret Platformu":
            col = TspmApiCollection(
                project_id=project.id,
                name="Ürün & Sepet API",
                description="E-ticaret ürün kataloğu ve sepet işlemleri",
                base_url="https://api.ecommerce.test/v2",
                headers={"Authorization": "Bearer {{token}}", "Content-Type": "application/json"},
            )
            db.add(col)
            db.flush()
            reqs = [
                TspmApiRequest(collection_id=col.id, name="Ürün Listele", method="GET", path="/products?page=1&limit=20",
                               headers=None, body=None, assertions=[{"type": "status", "expected": 200}], order=1),
                TspmApiRequest(collection_id=col.id, name="Ürün Detay", method="GET", path="/products/{{product_id}}",
                               headers=None, body=None, assertions=[{"type": "status", "expected": 200}], order=2),
                TspmApiRequest(collection_id=col.id, name="Sepete Ekle", method="POST", path="/cart/items",
                               headers=None, body={"product_id": "{{product_id}}", "quantity": 1},
                               assertions=[{"type": "status", "expected": 201}], order=3),
                TspmApiRequest(collection_id=col.id, name="Sepeti Görüntüle", method="GET", path="/cart",
                               headers=None, body=None, assertions=[{"type": "status", "expected": 200}], order=4),
            ]
            db.add_all(reqs)
            db.flush()

            db.add(TspmApiTestRun(collection_id=col.id, status="completed",
                                   results=[{"request": "Ürün Listele", "status": 200, "passed": True, "duration_ms": 85},
                                            {"request": "Ürün Detay", "status": 200, "passed": True, "duration_ms": 42},
                                            {"request": "Sepete Ekle", "status": 201, "passed": True, "duration_ms": 156},
                                            {"request": "Sepeti Görüntüle", "status": 200, "passed": True, "duration_ms": 38}]))
            db.flush()
            print(f"  1 API koleksiyonu, {len(reqs)} istek ve 1 test koşusu oluşturuldu")

    # ── 5. Bankacılık projesi için AI Pipeline demo verisi ──
    banking_project = db.scalar(select(TspmProject).where(TspmProject.name == "Mobil Bankacılık API"))
    if banking_project:
        bank_scenarios = list(db.execute(
            select(TspmScenario).where(TspmScenario.project_id == banking_project.id)
        ).scalars().all())
        _seed_ai_pipeline(db, banking_project, bank_scenarios, admin_user)
        _seed_historical_executions(db, banking_project, bank_scenarios)
        print("\nBankacılık AI pipeline ve tarihsel koşu verileri eklendi.")

    db.commit()
    print(f"\n{'='*60}")
    print("TÜM DUMMY VERİLER BAŞARIYLA YÜKLENDİ!")
    print(f"{'='*60}")
    print(f"\nKullanıcılar:")
    for u in USERS:
        print(f"  {u['email']} / {u['password']} ({u['role']})")
    print(f"\nProjeler:")
    for p in PROJECTS:
        print(f"  - {p['name']}")
    print(f"\nUI: http://localhost:3000")


if __name__ == "__main__":
    s = SessionLocal()
    try:
        seed_all(s)
    finally:
        s.close()
