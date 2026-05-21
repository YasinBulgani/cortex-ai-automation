"""
TSPM dummy data — projeler, senaryolar, koşular, akışlar, regresyon setleri,
onaylar ve import kayıtları ile dolu gerçekçi demo verisi.

Çalıştırma:
  cd backend && PYTHONPATH=. python scripts/seed_tspm.py

Tekrar çalıştırılırsa ``DEMO_PROJECT`` adlı proje zaten varsa atlar.
"""

from __future__ import annotations

import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.infra.database import SessionLocal
from app.domains.tspm.models import (
    TspmApproval,
    TspmExecution,
    TspmExecutionResult,
    TspmFlow,
    TspmImport,
    TspmProject,
    TspmRegressionSet,
    TspmScenario,
)

DEMO_PROJECT = "BGTS Demo Projesi"

SCENARIOS = [
    {
        "title": "Kullanıcı başarılı giriş yapabilmeli",
        "description": "Geçerli e-posta ve şifre ile sisteme giriş yapıldığında kullanıcı ana sayfaya yönlendirilmeli.",
        "status": "approved",
        "steps": [
            {"order": 0, "keyword": "Olduğu gibi", "text": "kullanıcı giriş sayfasındadır"},
            {"order": 1, "keyword": "Eğer", "text": "geçerli e-posta ve şifre girer"},
            {"order": 2, "keyword": "Ve", "text": "Giriş Yap butonuna tıklar"},
            {"order": 3, "keyword": "O zaman", "text": "ana sayfaya yönlendirilir"},
            {"order": 4, "keyword": "Ve", "text": "hoş geldiniz mesajı görüntülenir"},
        ],
    },
    {
        "title": "Hatalı şifre ile giriş reddedilmeli",
        "description": "Yanlış şifre girildiğinde hata mesajı gösterilmeli, kullanıcı giriş sayfasında kalmalı.",
        "status": "approved",
        "steps": [
            {"order": 0, "keyword": "Olduğu gibi", "text": "kullanıcı giriş sayfasındadır"},
            {"order": 1, "keyword": "Eğer", "text": "geçerli e-posta ama yanlış şifre girer"},
            {"order": 2, "keyword": "O zaman", "text": "'Geçersiz kimlik bilgileri' hatası görüntülenir"},
            {"order": 3, "keyword": "Ve", "text": "kullanıcı giriş sayfasında kalır"},
        ],
    },
    {
        "title": "Boş form ile giriş denemesi engellenmeli",
        "description": "E-posta ve şifre alanları boşken form gönderilemez.",
        "status": "approved",
        "steps": [
            {"order": 0, "keyword": "Olduğu gibi", "text": "kullanıcı giriş sayfasındadır"},
            {"order": 1, "keyword": "Eğer", "text": "hiçbir alan doldurmadan giriş yapmaya çalışır"},
            {"order": 2, "keyword": "O zaman", "text": "zorunlu alan uyarıları görüntülenir"},
        ],
    },
    {
        "title": "Yeni kullanıcı kaydı oluşturulabilmeli",
        "description": "Geçerli bilgilerle yeni hesap oluşturulabilmeli ve onay e-postası gönderilmeli.",
        "status": "approved",
        "steps": [
            {"order": 0, "keyword": "Olduğu gibi", "text": "kullanıcı kayıt sayfasındadır"},
            {"order": 1, "keyword": "Eğer", "text": "ad, e-posta ve şifre alanlarını doldurur"},
            {"order": 2, "keyword": "Ve", "text": "Kayıt Ol butonuna tıklar"},
            {"order": 3, "keyword": "O zaman", "text": "hesap başarıyla oluşturulur"},
            {"order": 4, "keyword": "Ve", "text": "onay e-postası gönderilir"},
        ],
    },
    {
        "title": "Mevcut e-posta ile tekrar kayıt olunamamalı",
        "description": "Daha önce kayıtlı bir e-posta ile yeni kayıt denemesinde hata verilmeli.",
        "status": "approved",
        "steps": [
            {"order": 0, "keyword": "Olduğu gibi", "text": "kullanıcı kayıt sayfasındadır"},
            {"order": 1, "keyword": "Eğer", "text": "daha önce kayıtlı bir e-posta adresi girer"},
            {"order": 2, "keyword": "O zaman", "text": "'Bu e-posta zaten kayıtlı' hatası görüntülenir"},
        ],
    },
    {
        "title": "Şifre sıfırlama e-postası gönderilebilmeli",
        "description": "Kayıtlı e-posta ile şifre sıfırlama bağlantısı talep edilebilmeli.",
        "status": "approved",
        "steps": [
            {"order": 0, "keyword": "Olduğu gibi", "text": "kullanıcı şifremi unuttum sayfasındadır"},
            {"order": 1, "keyword": "Eğer", "text": "kayıtlı e-posta adresini girer"},
            {"order": 2, "keyword": "Ve", "text": "Gönder butonuna tıklar"},
            {"order": 3, "keyword": "O zaman", "text": "şifre sıfırlama bağlantısı e-posta ile gönderilir"},
        ],
    },
    {
        "title": "Dashboard istatistikleri doğru gösterilmeli",
        "description": "Ana sayfa dashboard'unda senaryo sayısı, koşu istatistikleri ve bekleyen onaylar doğru görüntülenmeli.",
        "status": "approved",
        "steps": [
            {"order": 0, "keyword": "Olduğu gibi", "text": "kullanıcı sisteme giriş yapmıştır"},
            {"order": 1, "keyword": "Eğer", "text": "proje dashboard sayfasını açar"},
            {"order": 2, "keyword": "O zaman", "text": "toplam senaryo sayısı doğru gösterilir"},
            {"order": 3, "keyword": "Ve", "text": "son koşu başarı oranı gösterilir"},
            {"order": 4, "keyword": "Ve", "text": "bekleyen onay sayısı gösterilir"},
        ],
    },
    {
        "title": "Yeni senaryo oluşturulabilmeli",
        "description": "Senaryolar sayfasından yeni test senaryosu eklenebilmeli.",
        "status": "approved",
        "steps": [
            {"order": 0, "keyword": "Olduğu gibi", "text": "kullanıcı senaryolar sayfasındadır"},
            {"order": 1, "keyword": "Eğer", "text": "başlık ve açıklama girerek yeni senaryo oluşturur"},
            {"order": 2, "keyword": "O zaman", "text": "senaryo 'taslak' durumunda kaydedilir"},
            {"order": 3, "keyword": "Ve", "text": "senaryolar listesinde görünür"},
        ],
    },
    {
        "title": "Senaryo düzenlenebilmeli",
        "description": "Mevcut bir senaryonun başlığı, açıklaması ve adımları güncellenebilmeli.",
        "status": "approved",
        "steps": [
            {"order": 0, "keyword": "Olduğu gibi", "text": "kullanıcı bir senaryonun detay sayfasındadır"},
            {"order": 1, "keyword": "Eğer", "text": "başlığı ve adımları günceller"},
            {"order": 2, "keyword": "Ve", "text": "Kaydet butonuna tıklar"},
            {"order": 3, "keyword": "O zaman", "text": "senaryo versiyonu artırılır"},
            {"order": 4, "keyword": "Ve", "text": "değişiklikler kaydedilir"},
        ],
    },
    {
        "title": "Senaryo silinebilmeli",
        "description": "Senaryo toplu silme işlemi başarıyla yapılabilmeli.",
        "status": "draft",
        "steps": [
            {"order": 0, "keyword": "Olduğu gibi", "text": "kullanıcı senaryolar sayfasındadır"},
            {"order": 1, "keyword": "Eğer", "text": "bir veya birden fazla senaryoyu seçer"},
            {"order": 2, "keyword": "Ve", "text": "Sil butonuna tıklar"},
            {"order": 3, "keyword": "O zaman", "text": "onay diyalogu görüntülenir"},
            {"order": 4, "keyword": "Ve", "text": "onaylandığında senaryolar silinir"},
        ],
    },
    {
        "title": "Senaryolarda arama yapılabilmeli",
        "description": "Senaryo listesi başlığa göre filtrelenebilmeli.",
        "status": "approved",
        "steps": [
            {"order": 0, "keyword": "Olduğu gibi", "text": "kullanıcı senaryolar sayfasındadır"},
            {"order": 1, "keyword": "Eğer", "text": "arama kutusuna anahtar kelime yazar"},
            {"order": 2, "keyword": "O zaman", "text": "sadece eşleşen senaryolar listelenir"},
        ],
    },
    {
        "title": "Test koşusu başlatılabilmeli",
        "description": "Seçilen senaryolarla yeni bir test koşusu oluşturulabilmeli.",
        "status": "approved",
        "steps": [
            {"order": 0, "keyword": "Olduğu gibi", "text": "kullanıcı koşular sayfasındadır"},
            {"order": 1, "keyword": "Eğer", "text": "koşu adı girer ve senaryoları seçer"},
            {"order": 2, "keyword": "Ve", "text": "Başlat butonuna tıklar"},
            {"order": 3, "keyword": "O zaman", "text": "koşu 'çalışıyor' durumunda oluşturulur"},
            {"order": 4, "keyword": "Ve", "text": "tüm sonuçlar 'beklemede' olarak işaretlenir"},
        ],
    },
    {
        "title": "Test sonucu geçti/kaldı olarak işaretlenebilmeli",
        "description": "Koşu detayında her senaryo sonucu ayrı ayrı güncellenebilmeli.",
        "status": "approved",
        "steps": [
            {"order": 0, "keyword": "Olduğu gibi", "text": "kullanıcı koşu detay sayfasındadır"},
            {"order": 1, "keyword": "Eğer", "text": "bir senaryonun sonucunu 'Geçti' olarak işaretler"},
            {"order": 2, "keyword": "O zaman", "text": "sonuç durumu güncellenir"},
            {"order": 3, "keyword": "Ve", "text": "başarı oranı yeniden hesaplanır"},
        ],
    },
    {
        "title": "Koşu tekrar çalıştırılabilmeli",
        "description": "Tamamlanmış bir koşu aynı senaryolarla yeniden başlatılabilmeli.",
        "status": "approved",
        "steps": [
            {"order": 0, "keyword": "Olduğu gibi", "text": "kullanıcı tamamlanmış bir koşunun detay sayfasındadır"},
            {"order": 1, "keyword": "Eğer", "text": "Tekrar Çalıştır butonuna tıklar"},
            {"order": 2, "keyword": "O zaman", "text": "aynı senaryolarla yeni bir koşu oluşturulur"},
            {"order": 3, "keyword": "Ve", "text": "eski koşu değişmez"},
        ],
    },
    {
        "title": "Regresyon seti oluşturulabilmeli",
        "description": "Sprint veya release bazlı senaryo grubu oluşturulabilmeli.",
        "status": "approved",
        "steps": [
            {"order": 0, "keyword": "Olduğu gibi", "text": "kullanıcı regresyon setleri sayfasındadır"},
            {"order": 1, "keyword": "Eğer", "text": "set adı girer ve Oluştur butonuna tıklar"},
            {"order": 2, "keyword": "O zaman", "text": "boş bir regresyon seti oluşturulur"},
        ],
    },
    {
        "title": "Regresyon setine senaryo eklenebilmeli",
        "description": "Mevcut bir regresyon setine projeden senaryo eklenebilmeli.",
        "status": "approved",
        "steps": [
            {"order": 0, "keyword": "Olduğu gibi", "text": "kullanıcı regresyon seti detay sayfasındadır"},
            {"order": 1, "keyword": "Eğer", "text": "eklenebilir senaryolardan seçim yapar"},
            {"order": 2, "keyword": "Ve", "text": "Seçilenleri Ekle butonuna tıklar"},
            {"order": 3, "keyword": "O zaman", "text": "senaryolar sete eklenir"},
            {"order": 4, "keyword": "Ve", "text": "senaryo sayısı güncellenir"},
        ],
    },
    {
        "title": "Test akışı (flow) oluşturulabilmeli",
        "description": "Görsel editörde yeni bir test akışı tanımlanabilmeli.",
        "status": "draft",
        "steps": [
            {"order": 0, "keyword": "Olduğu gibi", "text": "kullanıcı akışlar sayfasındadır"},
            {"order": 1, "keyword": "Eğer", "text": "akış adı girer ve Oluştur butonuna tıklar"},
            {"order": 2, "keyword": "O zaman", "text": "boş bir akış oluşturulur"},
            {"order": 3, "keyword": "Ve", "text": "görsel editör açılır"},
        ],
    },
    {
        "title": "Onay talebi oluşturulabilmeli",
        "description": "Senaryo için onay süreci başlatılabilmeli.",
        "status": "approved",
        "steps": [
            {"order": 0, "keyword": "Olduğu gibi", "text": "kullanıcı senaryo detay sayfasındadır"},
            {"order": 1, "keyword": "Eğer", "text": "Onaya Gönder butonuna tıklar"},
            {"order": 2, "keyword": "O zaman", "text": "onay talebi 'beklemede' durumunda oluşturulur"},
        ],
    },
    {
        "title": "Onay kabul/red edilebilmeli",
        "description": "Bekleyen onay talebi onaylanabilir veya reddedilebilmeli.",
        "status": "approved",
        "steps": [
            {"order": 0, "keyword": "Olduğu gibi", "text": "kullanıcı onaylar sayfasındadır"},
            {"order": 1, "keyword": "Eğer", "text": "bekleyen bir onay talebi için Onayla butonuna tıklar"},
            {"order": 2, "keyword": "O zaman", "text": "onay durumu 'onaylandı' olarak güncellenir"},
            {"order": 3, "keyword": "Ve", "text": "karar tarihi kaydedilir"},
        ],
    },
    {
        "title": "BDD senaryoları AI ile üretilebilmeli",
        "description": "Analiz dokümanı girilerek otomatik BDD senaryoları üretilebilmeli.",
        "status": "draft",
        "steps": [
            {"order": 0, "keyword": "Olduğu gibi", "text": "kullanıcı senaryo üretim sayfasındadır"},
            {"order": 1, "keyword": "Eğer", "text": "analiz dokümanını yapıştırır"},
            {"order": 2, "keyword": "Ve", "text": "Üret butonuna tıklar"},
            {"order": 3, "keyword": "O zaman", "text": "AI Gherkin formatında senaryolar üretir"},
            {"order": 4, "keyword": "Ve", "text": "üretilen senaryolar önizleme olarak gösterilir"},
        ],
    },
    {
        "title": "Dosyadan senaryo import edilebilmeli",
        "description": "Harici dosyadan test senaryoları sisteme aktarılabilmeli.",
        "status": "draft",
        "steps": [
            {"order": 0, "keyword": "Olduğu gibi", "text": "kullanıcı import sayfasındadır"},
            {"order": 1, "keyword": "Eğer", "text": "dosya seçer ve Yükle butonuna tıklar"},
            {"order": 2, "keyword": "O zaman", "text": "dosya işlenir ve senaryolar oluşturulur"},
            {"order": 3, "keyword": "Ve", "text": "import kaydı 'tamamlandı' durumunda listelenir"},
        ],
    },
    {
        "title": "Oturum süresi dolduğunda yeniden giriş istenmeli",
        "description": "JWT token süresi dolduğunda kullanıcı giriş sayfasına yönlendirilmeli.",
        "status": "approved",
        "steps": [
            {"order": 0, "keyword": "Olduğu gibi", "text": "kullanıcı sisteme giriş yapmıştır"},
            {"order": 1, "keyword": "Ve", "text": "oturum süresi dolmuştur"},
            {"order": 2, "keyword": "Eğer", "text": "herhangi bir sayfaya istek gönderir"},
            {"order": 3, "keyword": "O zaman", "text": "401 hatası alınır"},
            {"order": 4, "keyword": "Ve", "text": "giriş sayfasına yönlendirilir"},
        ],
    },
    {
        "title": "Proje oluşturulabilmeli",
        "description": "Yeni bir test projesi oluşturularak senaryolar bu proje altında yönetilebilmeli.",
        "status": "approved",
        "steps": [
            {"order": 0, "keyword": "Olduğu gibi", "text": "kullanıcı projeler sayfasındadır"},
            {"order": 1, "keyword": "Eğer", "text": "proje adı ve açıklaması girer"},
            {"order": 2, "keyword": "Ve", "text": "Oluştur butonuna tıklar"},
            {"order": 3, "keyword": "O zaman", "text": "proje başarıyla oluşturulur"},
            {"order": 4, "keyword": "Ve", "text": "proje listesinde görünür"},
        ],
    },
    {
        "title": "Eşzamanlı kullanıcı girişinde veri tutarlılığı korunmalı",
        "description": "Birden fazla kullanıcı aynı anda işlem yaptığında veriler tutarlı kalmalı.",
        "status": "draft",
        "steps": [
            {"order": 0, "keyword": "Olduğu gibi", "text": "iki kullanıcı aynı senaryoyu düzenlemektedir"},
            {"order": 1, "keyword": "Eğer", "text": "her ikisi de aynı anda kaydet butonuna tıklar"},
            {"order": 2, "keyword": "O zaman", "text": "son kaydeden kullanıcının değişiklikleri geçerli olur"},
            {"order": 3, "keyword": "Ve", "text": "versiyon numarası doğru artırılır"},
        ],
    },
    {
        "title": "Büyük senaryo listesi sayfalanarak gösterilmeli",
        "description": "100+ senaryo olduğunda performans düşmeden liste render edilmeli.",
        "status": "draft",
        "steps": [
            {"order": 0, "keyword": "Olduğu gibi", "text": "projede 200+ senaryo bulunmaktadır"},
            {"order": 1, "keyword": "Eğer", "text": "kullanıcı senaryolar sayfasını açar"},
            {"order": 2, "keyword": "O zaman", "text": "sayfa 3 saniyeden kısa sürede yüklenir"},
            {"order": 3, "keyword": "Ve", "text": "liste sorunsuz kaydırılabilir"},
        ],
    },
    {
        "title": "API yanıt süreleri kabul edilebilir olmalı",
        "description": "Tüm API endpoint'leri 500ms altında yanıt vermeli.",
        "status": "draft",
        "steps": [
            {"order": 0, "keyword": "Olduğu gibi", "text": "sistem normal yük altındadır"},
            {"order": 1, "keyword": "Eğer", "text": "herhangi bir API endpoint'ine istek gönderilir"},
            {"order": 2, "keyword": "O zaman", "text": "yanıt 500ms içinde döner"},
        ],
    },
    {
        "title": "Geçersiz e-posta formatı reddedilmeli",
        "description": "Kayıt veya giriş formlarında geçersiz e-posta formatı kabul edilmemeli.",
        "status": "approved",
        "steps": [
            {"order": 0, "keyword": "Olduğu gibi", "text": "kullanıcı kayıt sayfasındadır"},
            {"order": 1, "keyword": "Eğer", "text": "'test@' gibi geçersiz bir e-posta girer"},
            {"order": 2, "keyword": "O zaman", "text": "'Geçerli bir e-posta adresi girin' hatası gösterilir"},
        ],
    },
    {
        "title": "Şifre minimum 8 karakter olmalı",
        "description": "Kayıt sırasında 8 karakterden kısa şifre kabul edilmemeli.",
        "status": "approved",
        "steps": [
            {"order": 0, "keyword": "Olduğu gibi", "text": "kullanıcı kayıt sayfasındadır"},
            {"order": 1, "keyword": "Eğer", "text": "5 karakterlik bir şifre girer"},
            {"order": 2, "keyword": "O zaman", "text": "'Şifre en az 8 karakter olmalıdır' hatası gösterilir"},
        ],
    },
    {
        "title": "Çıkış yapıldığında oturum temizlenmeli",
        "description": "Kullanıcı çıkış yaptığında token silinmeli ve giriş sayfasına yönlendirilmeli.",
        "status": "approved",
        "steps": [
            {"order": 0, "keyword": "Olduğu gibi", "text": "kullanıcı sisteme giriş yapmıştır"},
            {"order": 1, "keyword": "Eğer", "text": "Çıkış Yap butonuna tıklar"},
            {"order": 2, "keyword": "O zaman", "text": "oturum tokeni silinir"},
            {"order": 3, "keyword": "Ve", "text": "giriş sayfasına yönlendirilir"},
        ],
    },
]

REGRESSION_SETS = [
    {
        "name": "Sprint 1 — Temel Giriş Akışları",
        "description": "İlk sprint kapsamında kimlik doğrulama ve kayıt akışlarının regresyon testi.",
        "scenario_indices": [0, 1, 2, 3, 4, 5, 27, 28, 29],
    },
    {
        "name": "Sprint 2 — CRUD ve Yönetim",
        "description": "Senaryo, proje ve koşu CRUD işlemlerinin regresyon seti.",
        "scenario_indices": [7, 8, 9, 10, 11, 12, 13, 14, 15, 22],
    },
    {
        "name": "Kritik Akışlar — Smoke Test",
        "description": "Her deploy öncesi koşulması gereken minimum kritik senaryolar.",
        "scenario_indices": [0, 3, 6, 7, 11, 14, 22],
    },
    {
        "name": "Release v1.0 — Tam Regresyon",
        "description": "v1.0 release öncesi tüm onaylanmış senaryoların kapsamlı regresyon testi.",
        "scenario_indices": list(range(20)),
    },
]

EXECUTIONS = [
    {
        "name": "Sprint 1 Koşusu #1",
        "scenario_indices": [0, 1, 2, 3, 4, 5],
        "results": ["passed", "passed", "passed", "passed", "failed", "passed"],
    },
    {
        "name": "Sprint 1 Koşusu #2 (re-run)",
        "scenario_indices": [0, 1, 2, 3, 4, 5],
        "results": ["passed", "passed", "passed", "passed", "passed", "passed"],
    },
    {
        "name": "Sprint 2 Koşusu #1",
        "scenario_indices": [7, 8, 9, 10, 11, 12, 13],
        "results": ["passed", "passed", "failed", "passed", "passed", "passed", "pending"],
    },
    {
        "name": "Smoke Test — v0.9",
        "scenario_indices": [0, 3, 6, 7, 11],
        "results": ["passed", "passed", "passed", "passed", "passed"],
    },
]

FLOWS = [
    {
        "name": "Kullanıcı Kayıt Akışı",
        "description": "Kayıt → E-posta doğrulama → İlk giriş akışı",
        "nodes": [
            {"id": "n1", "type": "input", "position": {"x": 50, "y": 50}, "data": {"label": "Kayıt Sayfası"}},
            {"id": "n2", "type": "default", "position": {"x": 250, "y": 50}, "data": {"label": "Form Doldur"}},
            {"id": "n3", "type": "default", "position": {"x": 450, "y": 50}, "data": {"label": "E-posta Doğrula"}},
            {"id": "n4", "type": "output", "position": {"x": 650, "y": 50}, "data": {"label": "İlk Giriş"}},
        ],
        "edges": [
            {"id": "e1-2", "source": "n1", "target": "n2"},
            {"id": "e2-3", "source": "n2", "target": "n3"},
            {"id": "e3-4", "source": "n3", "target": "n4"},
        ],
    },
    {
        "name": "Test Koşusu Yaşam Döngüsü",
        "description": "Koşu oluştur → Sonuçları işaretle → Tekrar çalıştır",
        "nodes": [
            {"id": "n1", "type": "input", "position": {"x": 50, "y": 100}, "data": {"label": "Koşu Oluştur"}},
            {"id": "n2", "type": "default", "position": {"x": 300, "y": 50}, "data": {"label": "Sonuç: Geçti"}},
            {"id": "n3", "type": "default", "position": {"x": 300, "y": 150}, "data": {"label": "Sonuç: Kaldı"}},
            {"id": "n4", "type": "default", "position": {"x": 550, "y": 150}, "data": {"label": "Tekrar Koş"}},
            {"id": "n5", "type": "output", "position": {"x": 550, "y": 50}, "data": {"label": "Tamamlandı"}},
        ],
        "edges": [
            {"id": "e1-2", "source": "n1", "target": "n2"},
            {"id": "e1-3", "source": "n1", "target": "n3"},
            {"id": "e3-4", "source": "n3", "target": "n4"},
            {"id": "e2-5", "source": "n2", "target": "n5"},
            {"id": "e4-5", "source": "n4", "target": "n5"},
        ],
    },
    {
        "name": "Regresyon Seti Yönetimi",
        "description": "Set oluştur → Senaryo ekle → AI öneri → Koşu başlat",
        "nodes": [
            {"id": "n1", "type": "input", "position": {"x": 50, "y": 100}, "data": {"label": "Set Oluştur"}},
            {"id": "n2", "type": "default", "position": {"x": 250, "y": 50}, "data": {"label": "Manuel Senaryo Ekle"}},
            {"id": "n3", "type": "default", "position": {"x": 250, "y": 150}, "data": {"label": "AI ile Öner"}},
            {"id": "n4", "type": "default", "position": {"x": 500, "y": 100}, "data": {"label": "Seti Gözden Geçir"}},
            {"id": "n5", "type": "output", "position": {"x": 700, "y": 100}, "data": {"label": "Koşu Başlat"}},
        ],
        "edges": [
            {"id": "e1-2", "source": "n1", "target": "n2"},
            {"id": "e1-3", "source": "n1", "target": "n3"},
            {"id": "e2-4", "source": "n2", "target": "n4"},
            {"id": "e3-4", "source": "n3", "target": "n4"},
            {"id": "e4-5", "source": "n4", "target": "n5"},
        ],
    },
]

APPROVALS = [
    {"title": "Kullanıcı giriş senaryosu — v2 onayı", "status": "approved", "scenario_idx": 0},
    {"title": "Kayıt akışı güncelleme onayı", "status": "approved", "scenario_idx": 3},
    {"title": "Dashboard istatistik senaryosu onayı", "status": "approved", "scenario_idx": 6},
    {"title": "Senaryo silme akışı — risk değerlendirmesi", "status": "pending", "scenario_idx": 9},
    {"title": "BDD üretim senaryosu — AI doğrulaması", "status": "pending", "scenario_idx": 19},
    {"title": "Performans testi senaryosu — SLA kontrolü", "status": "rejected", "scenario_idx": 25},
    {"title": "Eşzamanlılık testi — veri tutarlılığı", "status": "pending", "scenario_idx": 23},
]

IMPORTS = [
    {"filename": "sprint1_senaryolari.xlsx", "status": "completed", "scenario_count": 6},
    {"filename": "login_test_cases.csv", "status": "completed", "scenario_count": 4},
    {"filename": "regression_v1_export.json", "status": "completed", "scenario_count": 15},
    {"filename": "api_test_suite.yaml", "status": "failed", "scenario_count": 0},
]


def seed_tspm(db: Session) -> None:
    existing = db.scalar(select(TspmProject).where(TspmProject.name == DEMO_PROJECT))
    if existing is not None:
        print(f"Demo proje zaten mevcut: {DEMO_PROJECT} (id: {existing.id})")
        print("Tekrar yüklemek için projeyi silin veya farklı isim kullanın.")
        return

    project = TspmProject(
        name=DEMO_PROJECT,
        description="TestwrightAI Test Süreç Platformu demo projesi — tüm modülleri test etmek için gerçekçi dummy veriler içerir.",
    )
    db.add(project)
    db.flush()
    print(f"Proje oluşturuldu: {project.name} ({project.id})")

    scenario_objs: list[TspmScenario] = []
    for s in SCENARIOS:
        sc = TspmScenario(
            project_id=project.id,
            title=s["title"],
            description=s["description"],
            status=s["status"],
            steps=s["steps"],
        )
        db.add(sc)
        scenario_objs.append(sc)
    db.flush()
    print(f"  {len(scenario_objs)} senaryo oluşturuldu")

    for rs_data in REGRESSION_SETS:
        ids = [scenario_objs[i].id for i in rs_data["scenario_indices"] if i < len(scenario_objs)]
        rs = TspmRegressionSet(
            project_id=project.id,
            name=rs_data["name"],
            description=rs_data["description"],
            scenario_ids=ids,
        )
        db.add(rs)
    db.flush()
    print(f"  {len(REGRESSION_SETS)} regresyon seti oluşturuldu")

    for ex_data in EXECUTIONS:
        ex = TspmExecution(
            project_id=project.id,
            name=ex_data["name"],
            status="completed",
        )
        db.add(ex)
        db.flush()
        for idx, result_status in zip(ex_data["scenario_indices"], ex_data["results"]):
            if idx < len(scenario_objs):
                db.add(TspmExecutionResult(
                    execution_id=ex.id,
                    scenario_id=scenario_objs[idx].id,
                    status=result_status,
                ))
    db.flush()
    print(f"  {len(EXECUTIONS)} test koşusu oluşturuldu")

    for fl_data in FLOWS:
        fl = TspmFlow(
            project_id=project.id,
            name=fl_data["name"],
            description=fl_data["description"],
            nodes=fl_data["nodes"],
            edges=fl_data["edges"],
        )
        db.add(fl)
    db.flush()
    print(f"  {len(FLOWS)} akış oluşturuldu")

    for ap_data in APPROVALS:
        sc_id = scenario_objs[ap_data["scenario_idx"]].id if ap_data["scenario_idx"] < len(scenario_objs) else None
        ap = TspmApproval(
            project_id=project.id,
            title=ap_data["title"],
            status=ap_data["status"],
            scenario_id=sc_id,
        )
        if ap_data["status"] != "pending":
            from app.domains.tspm.models import utcnow
            ap.decided_at = utcnow()
        db.add(ap)
    db.flush()
    print(f"  {len(APPROVALS)} onay kaydı oluşturuldu")

    for im_data in IMPORTS:
        im = TspmImport(
            project_id=project.id,
            filename=im_data["filename"],
            status=im_data["status"],
            scenario_count=im_data["scenario_count"],
            raw_payload={"source": "seed_tspm", "note": "Demo verisi"},
        )
        db.add(im)
    db.flush()
    print(f"  {len(IMPORTS)} import kaydı oluşturuldu")

    db.commit()
    print(f"\nTSPM demo verisi yüklendi!")
    print(f"  Proje ID:          {project.id}")
    print(f"  Senaryo sayısı:    {len(scenario_objs)}")
    print(f"  Regresyon seti:    {len(REGRESSION_SETS)}")
    print(f"  Test koşusu:       {len(EXECUTIONS)}")
    print(f"  Akış:              {len(FLOWS)}")
    print(f"  Onay:              {len(APPROVALS)}")
    print(f"  Import:            {len(IMPORTS)}")
    print(f"\nUI'da: Projeler → {DEMO_PROJECT}")


if __name__ == "__main__":
    s = SessionLocal()
    try:
        seed_tspm(s)
    finally:
        s.close()
