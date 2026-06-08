"use client";

import { useState, useMemo } from "react";
import { cn } from "@/lib/utils";

// ─── Permission Level Types ────────────────────────────────────────────────────

type PermLevel = "full" | "limited" | "view" | "none";

interface RbacRow {
  module: string;
  group: string;
  description: string;
  owner: PermLevel;
  admin: PermLevel;
  test_lead: PermLevel;
  qa_engineer: PermLevel;
  developer: PermLevel;
  business_analyst: PermLevel;
  viewer: PermLevel;
  critical?: boolean;
}

// ─── Role Definitions ─────────────────────────────────────────────────────────

const ROLES: {
  key: keyof Omit<RbacRow, "module" | "group" | "description" | "critical">;
  label: string;
  qaLabel: string;
  color: string;
  bg: string;
  border: string;
  description: string;
}[] = [
  {
    key: "owner",
    label: "Owner",
    qaLabel: "Proje Sahibi",
    color: "text-amber-400",
    bg: "bg-amber-500/10",
    border: "border-amber-500/30",
    description: "Tüm yetkiler + proje silme ve sahiplik devri",
  },
  {
    key: "admin",
    label: "Admin",
    qaLabel: "Admin",
    color: "text-purple-400",
    bg: "bg-purple-500/10",
    border: "border-purple-500/30",
    description: "Tüm QA operasyonları, üye yönetimi, proje ayarları",
  },
  {
    key: "test_lead",
    label: "Test Lead",
    qaLabel: "Test Lead",
    color: "text-teal-400",
    bg: "bg-teal-500/10",
    border: "border-teal-500/30",
    description: "Test planlaması, onay süreçleri, release signoff",
  },
  {
    key: "qa_engineer",
    label: "QA Engineer",
    qaLabel: "QA Mühendisi",
    color: "text-blue-400",
    bg: "bg-blue-500/10",
    border: "border-blue-500/30",
    description: "Test yazma, çalıştırma, defect oluşturma",
  },
  {
    key: "developer",
    label: "Developer",
    qaLabel: "Geliştirici",
    color: "text-indigo-400",
    bg: "bg-indigo-500/10",
    border: "border-indigo-500/30",
    description: "Test sonuçlarını görüntüleme, defect kapatma",
  },
  {
    key: "business_analyst",
    label: "BA",
    qaLabel: "İş Analisti",
    color: "text-sky-400",
    bg: "bg-sky-500/10",
    border: "border-sky-500/30",
    description: "Gereksinim yönetimi, rapor görüntüleme",
  },
  {
    key: "viewer",
    label: "Viewer",
    qaLabel: "İzleyici",
    color: "text-fg-muted",
    bg: "bg-surface-overlay",
    border: "border-border",
    description: "Salt okunur erişim — tüm modüller",
  },
];

// ─── RBAC Matrix Data ─────────────────────────────────────────────────────────

const RBAC_MATRIX: RbacRow[] = [
  // ── Test Case Yönetimi ────────────────────────────────────────────────────
  {
    module: "Test Case — Görüntüle",
    group: "Test Case Yönetimi",
    description: "Tüm test case'leri listele ve detay görüntüle",
    owner: "full", admin: "full", test_lead: "full", qa_engineer: "full", developer: "view", business_analyst: "view", viewer: "view",
  },
  {
    module: "Test Case — Oluştur",
    group: "Test Case Yönetimi",
    description: "Yeni test case, adım ve parametre ekle",
    owner: "full", admin: "full", test_lead: "full", qa_engineer: "full", developer: "none", business_analyst: "none", viewer: "none",
  },
  {
    module: "Test Case — Düzenle",
    group: "Test Case Yönetimi",
    description: "Mevcut test case içeriğini güncelle",
    owner: "full", admin: "full", test_lead: "full", qa_engineer: "full", developer: "none", business_analyst: "none", viewer: "none",
  },
  {
    module: "Test Case — Klonla",
    group: "Test Case Yönetimi",
    description: "Mevcut case'i kopyalayarak yeni case oluştur",
    owner: "full", admin: "full", test_lead: "full", qa_engineer: "full", developer: "none", business_analyst: "none", viewer: "none",
  },
  {
    module: "Test Case — Arşivle",
    group: "Test Case Yönetimi",
    description: "Case'i arşivle (soft delete — geri alınabilir)",
    owner: "full", admin: "full", test_lead: "full", qa_engineer: "none", developer: "none", business_analyst: "none", viewer: "none",
    critical: true,
  },
  {
    module: "Test Case — Kalıcı Sil",
    group: "Test Case Yönetimi",
    description: "Case'i geri dönüşümsüz sil",
    owner: "full", admin: "full", test_lead: "none", qa_engineer: "none", developer: "none", business_analyst: "none", viewer: "none",
    critical: true,
  },
  {
    module: "Test Case — İnceleme Gönder",
    group: "Test Case Yönetimi",
    description: "Onay için review workflow başlat",
    owner: "full", admin: "full", test_lead: "full", qa_engineer: "full", developer: "none", business_analyst: "none", viewer: "none",
  },
  {
    module: "Test Case — Onayla/Reddet",
    group: "Test Case Yönetimi",
    description: "Review kuyruğundaki case'leri onayla veya reddet",
    owner: "full", admin: "full", test_lead: "full", qa_engineer: "none", developer: "none", business_analyst: "none", viewer: "none",
    critical: true,
  },
  {
    module: "Test Case — AI ile Üret",
    group: "Test Case Yönetimi",
    description: "Requirement veya açıklamadan AI ile test case üret",
    owner: "full", admin: "full", test_lead: "full", qa_engineer: "full", developer: "none", business_analyst: "none", viewer: "none",
  },
  {
    module: "Test Case — Toplu İşlem",
    group: "Test Case Yönetimi",
    description: "Çoklu case'e toplu güncelleme, taşıma, arşivleme",
    owner: "full", admin: "full", test_lead: "full", qa_engineer: "limited", developer: "none", business_analyst: "none", viewer: "none",
  },

  // ── Suite & Klasör ────────────────────────────────────────────────────────
  {
    module: "Suite — Görüntüle",
    group: "Suite & Klasör",
    description: "Test suite ve klasör ağacını görüntüle",
    owner: "full", admin: "full", test_lead: "full", qa_engineer: "full", developer: "view", business_analyst: "view", viewer: "view",
  },
  {
    module: "Suite — Oluştur/Düzenle",
    group: "Suite & Klasör",
    description: "Yeni suite veya klasör ekle, yeniden adlandır",
    owner: "full", admin: "full", test_lead: "full", qa_engineer: "full", developer: "none", business_analyst: "none", viewer: "none",
  },
  {
    module: "Suite — Sil",
    group: "Suite & Klasör",
    description: "Suite veya klasörü ve içeriğini sil",
    owner: "full", admin: "full", test_lead: "full", qa_engineer: "none", developer: "none", business_analyst: "none", viewer: "none",
    critical: true,
  },
  {
    module: "Suite — Sürükle/Bırak Sırala",
    group: "Suite & Klasör",
    description: "Suite ve klasörleri sürükle bırak ile yeniden sırala",
    owner: "full", admin: "full", test_lead: "full", qa_engineer: "full", developer: "none", business_analyst: "none", viewer: "none",
  },

  // ── Test Koşumu ────────────────────────────────────────────────────────────
  {
    module: "Test Koşumu — Görüntüle",
    group: "Test Koşumu",
    description: "Tüm test run'larını ve sonuçlarını görüntüle",
    owner: "full", admin: "full", test_lead: "full", qa_engineer: "full", developer: "view", business_analyst: "view", viewer: "view",
  },
  {
    module: "Test Koşumu — Oluştur",
    group: "Test Koşumu",
    description: "Manuel veya otomatik yeni test run oluştur",
    owner: "full", admin: "full", test_lead: "full", qa_engineer: "full", developer: "none", business_analyst: "none", viewer: "none",
  },
  {
    module: "Test Koşumu — Çalıştır",
    group: "Test Koşumu",
    description: "Test run üzerinde case'leri execute et",
    owner: "full", admin: "full", test_lead: "full", qa_engineer: "full", developer: "none", business_analyst: "none", viewer: "none",
  },
  {
    module: "Test Koşumu — Sonuç Gir",
    group: "Test Koşumu",
    description: "Pass/Fail/Block/Skip sonuçlarını kaydet",
    owner: "full", admin: "full", test_lead: "full", qa_engineer: "full", developer: "none", business_analyst: "none", viewer: "none",
  },
  {
    module: "Test Koşumu — Tamamla",
    group: "Test Koşumu",
    description: "Run'ı kapatıp tamamlandı olarak işaretle",
    owner: "full", admin: "full", test_lead: "full", qa_engineer: "full", developer: "none", business_analyst: "none", viewer: "none",
  },
  {
    module: "Test Koşumu — Sil",
    group: "Test Koşumu",
    description: "Test run'ı ve tüm sonuçlarını kalıcı sil",
    owner: "full", admin: "full", test_lead: "none", qa_engineer: "none", developer: "none", business_analyst: "none", viewer: "none",
    critical: true,
  },

  // ── Defect Yönetimi ───────────────────────────────────────────────────────
  {
    module: "Defect — Görüntüle",
    group: "Defect Yönetimi",
    description: "Tüm defect'leri listele ve detay görüntüle",
    owner: "full", admin: "full", test_lead: "full", qa_engineer: "full", developer: "full", business_analyst: "view", viewer: "view",
  },
  {
    module: "Defect — Oluştur",
    group: "Defect Yönetimi",
    description: "Test run veya execution'dan defect aç",
    owner: "full", admin: "full", test_lead: "full", qa_engineer: "full", developer: "none", business_analyst: "none", viewer: "none",
  },
  {
    module: "Defect — Güncelle",
    group: "Defect Yönetimi",
    description: "Defect bilgilerini, durumunu, önceliğini güncelle",
    owner: "full", admin: "full", test_lead: "full", qa_engineer: "full", developer: "limited", business_analyst: "none", viewer: "none",
  },
  {
    module: "Defect — Kapat/Çöz",
    group: "Defect Yönetimi",
    description: "Defect'i çözüldü veya reddedildi olarak kapat",
    owner: "full", admin: "full", test_lead: "full", qa_engineer: "limited", developer: "full", business_analyst: "none", viewer: "none",
  },
  {
    module: "Defect — Sil",
    group: "Defect Yönetimi",
    description: "Defect kaydını kalıcı sil",
    owner: "full", admin: "full", test_lead: "none", qa_engineer: "none", developer: "none", business_analyst: "none", viewer: "none",
    critical: true,
  },
  {
    module: "Defect — AI Root Cause Analizi",
    group: "Defect Yönetimi",
    description: "AI ile kök neden analizi çalıştır",
    owner: "full", admin: "full", test_lead: "full", qa_engineer: "full", developer: "none", business_analyst: "none", viewer: "none",
  },

  // ── Planlama ──────────────────────────────────────────────────────────────
  {
    module: "Test Planı — Görüntüle",
    group: "Planlama",
    description: "Test planları ve döngüleri görüntüle",
    owner: "full", admin: "full", test_lead: "full", qa_engineer: "full", developer: "view", business_analyst: "view", viewer: "view",
  },
  {
    module: "Test Planı — Oluştur/Düzenle",
    group: "Planlama",
    description: "Yeni plan oluştur, döngü ekle, sprint yönet",
    owner: "full", admin: "full", test_lead: "full", qa_engineer: "none", developer: "none", business_analyst: "none", viewer: "none",
  },
  {
    module: "Test Planı — Sil",
    group: "Planlama",
    description: "Test planını tüm döngüleriyle sil",
    owner: "full", admin: "full", test_lead: "none", qa_engineer: "none", developer: "none", business_analyst: "none", viewer: "none",
    critical: true,
  },
  {
    module: "Regresyon Seti — Görüntüle",
    group: "Planlama",
    description: "Kayıtlı regresyon setlerini görüntüle",
    owner: "full", admin: "full", test_lead: "full", qa_engineer: "full", developer: "view", business_analyst: "view", viewer: "view",
  },
  {
    module: "Regresyon Seti — Oluştur/Düzenle",
    group: "Planlama",
    description: "Regresyon seti oluştur, case ekle/çıkar",
    owner: "full", admin: "full", test_lead: "full", qa_engineer: "limited", developer: "none", business_analyst: "none", viewer: "none",
  },
  {
    module: "Sürüm Onayı (Release Signoff)",
    group: "Planlama",
    description: "Release için GO/NO-GO kararı ver",
    owner: "full", admin: "full", test_lead: "full", qa_engineer: "none", developer: "none", business_analyst: "none", viewer: "none",
    critical: true,
  },

  // ── Gereksinimler ─────────────────────────────────────────────────────────
  {
    module: "Gereksinim — Görüntüle",
    group: "Gereksinimler",
    description: "Gereksinim listesini ve izlenebilirlik matrisini gör",
    owner: "full", admin: "full", test_lead: "full", qa_engineer: "full", developer: "full", business_analyst: "full", viewer: "view",
  },
  {
    module: "Gereksinim — Oluştur/Düzenle",
    group: "Gereksinimler",
    description: "Manuel gereksinim ekle ve düzenle",
    owner: "full", admin: "full", test_lead: "full", qa_engineer: "none", developer: "none", business_analyst: "full", viewer: "none",
  },
  {
    module: "Gereksinim — TC ile Bağla",
    group: "Gereksinimler",
    description: "Gereksinimi test case ile ilişkilendir",
    owner: "full", admin: "full", test_lead: "full", qa_engineer: "full", developer: "none", business_analyst: "limited", viewer: "none",
  },
  {
    module: "Gereksinim — İçe Aktar",
    group: "Gereksinimler",
    description: "Jira, Confluence, Excel'den toplu gereksinim içe aktar",
    owner: "full", admin: "full", test_lead: "full", qa_engineer: "none", developer: "none", business_analyst: "full", viewer: "none",
  },

  // ── Raporlama ─────────────────────────────────────────────────────────────
  {
    module: "Raporlar — Görüntüle",
    group: "Raporlama",
    description: "Tüm proje raporlarını görüntüle",
    owner: "full", admin: "full", test_lead: "full", qa_engineer: "full", developer: "full", business_analyst: "full", viewer: "view",
  },
  {
    module: "Raporlar — Export (PDF/CSV)",
    group: "Raporlama",
    description: "Raporu PDF veya CSV olarak dışa aktar",
    owner: "full", admin: "full", test_lead: "full", qa_engineer: "full", developer: "none", business_analyst: "full", viewer: "none",
  },
  {
    module: "Denetim İzi — Görüntüle",
    group: "Raporlama",
    description: "Kim ne yaptı, ne zaman değiştirildi logları",
    owner: "full", admin: "full", test_lead: "view", qa_engineer: "none", developer: "none", business_analyst: "none", viewer: "none",
    critical: true,
  },
  {
    module: "Stand-up Raporu",
    group: "Raporlama",
    description: "Günlük test ilerleme ve sağlık raporunu görüntüle",
    owner: "full", admin: "full", test_lead: "full", qa_engineer: "full", developer: "view", business_analyst: "view", viewer: "none",
  },

  // ── Tasarım Teknikleri ────────────────────────────────────────────────────
  {
    module: "Tasarım Tekniği — Çalıştır",
    group: "Test Tasarımı",
    description: "BVA, EQ, DT, Pairwise tekniklerini çalıştır",
    owner: "full", admin: "full", test_lead: "full", qa_engineer: "full", developer: "none", business_analyst: "none", viewer: "none",
  },
  {
    module: "BDD/Gherkin Üret",
    group: "Test Tasarımı",
    description: "AI ile Gherkin/BDD senaryosu oluştur",
    owner: "full", admin: "full", test_lead: "full", qa_engineer: "full", developer: "none", business_analyst: "limited", viewer: "none",
  },
  {
    module: "Paylaşılan Adım — Yönet",
    group: "Test Tasarımı",
    description: "Yeniden kullanılabilir test adımları oluştur ve yönet",
    owner: "full", admin: "full", test_lead: "full", qa_engineer: "full", developer: "none", business_analyst: "none", viewer: "none",
  },

  // ── İçe/Dışa Aktarma ─────────────────────────────────────────────────────
  {
    module: "İçe Aktar (CSV/Excel)",
    group: "İçe/Dışa Aktarma",
    description: "CSV veya Excel'den test case toplu içe aktar",
    owner: "full", admin: "full", test_lead: "full", qa_engineer: "limited", developer: "none", business_analyst: "none", viewer: "none",
  },
  {
    module: "Dışa Aktar",
    group: "İçe/Dışa Aktarma",
    description: "Test case'leri CSV/Excel olarak dışa aktar",
    owner: "full", admin: "full", test_lead: "full", qa_engineer: "full", developer: "none", business_analyst: "full", viewer: "none",
  },

  // ── Yönetim ───────────────────────────────────────────────────────────────
  {
    module: "Üye — Davet Et",
    group: "Proje Yönetimi",
    description: "Projeye yeni üye davet et",
    owner: "full", admin: "full", test_lead: "none", qa_engineer: "none", developer: "none", business_analyst: "none", viewer: "none",
    critical: true,
  },
  {
    module: "Üye — Rol Değiştir",
    group: "Proje Yönetimi",
    description: "Mevcut üyenin rolünü güncelle",
    owner: "full", admin: "full", test_lead: "none", qa_engineer: "none", developer: "none", business_analyst: "none", viewer: "none",
    critical: true,
  },
  {
    module: "Üye — Kaldır",
    group: "Proje Yönetimi",
    description: "Üyeyi projeden çıkar",
    owner: "full", admin: "full", test_lead: "none", qa_engineer: "none", developer: "none", business_analyst: "none", viewer: "none",
    critical: true,
  },
  {
    module: "Proje Ayarları",
    group: "Proje Yönetimi",
    description: "Proje adı, modüller, etiketler, bildirimler",
    owner: "full", admin: "full", test_lead: "limited", qa_engineer: "none", developer: "none", business_analyst: "none", viewer: "none",
    critical: true,
  },
  {
    module: "API Anahtarları — Yönet",
    group: "Proje Yönetimi",
    description: "API anahtarı oluştur, iptal et, görüntüle",
    owner: "full", admin: "full", test_lead: "none", qa_engineer: "none", developer: "none", business_analyst: "none", viewer: "none",
    critical: true,
  },
  {
    module: "Entegrasyon — Yönet",
    group: "Proje Yönetimi",
    description: "Jira, Azure DevOps, GitLab entegrasyonlarını kur",
    owner: "full", admin: "full", test_lead: "none", qa_engineer: "none", developer: "none", business_analyst: "none", viewer: "none",
    critical: true,
  },
  {
    module: "Proje — Sil/Arşivle",
    group: "Proje Yönetimi",
    description: "Projeyi arşivle veya kalıcı olarak sil",
    owner: "full", admin: "none", test_lead: "none", qa_engineer: "none", developer: "none", business_analyst: "none", viewer: "none",
    critical: true,
  },
];

// ─── Permission Cell ──────────────────────────────────────────────────────────

const PERM_CONFIG: Record<PermLevel, {
  icon: string;
  label: string;
  cellBg: string;
  textColor: string;
  title: string;
}> = {
  full:    { icon: "✓",  label: "Tam",         cellBg: "bg-emerald-500/10", textColor: "text-emerald-400", title: "Tam Yetki — Tüm işlemler" },
  limited: { icon: "◐",  label: "Kısıtlı",     cellBg: "bg-blue-500/10",    textColor: "text-blue-400",    title: "Kısıtlı — Bazı işlemler" },
  view:    { icon: "◎",  label: "Görüntüle",   cellBg: "bg-surface-overlay", textColor: "text-fg-muted",   title: "Sadece Görüntüle" },
  none:    { icon: "—",  label: "Yok",          cellBg: "",                   textColor: "text-fg-disabled", title: "Erişim Yok" },
};

function PermCell({ level, critical }: { level: PermLevel; critical?: boolean }) {
  const cfg = PERM_CONFIG[level];
  return (
    <td
      title={cfg.title}
      className={cn(
        "border-b border-border px-3 py-2 text-center",
        cfg.cellBg,
        critical && level !== "none" ? "ring-inset ring-1 ring-amber-500/20" : "",
      )}
    >
      <span className={cn("text-[13px] font-medium", cfg.textColor)}>
        {cfg.icon}
      </span>
    </td>
  );
}

// ─── Export CSV ───────────────────────────────────────────────────────────────

function exportCSV(rows: RbacRow[]) {
  const headers = ["Modül", "Grup", "Açıklama", "Proje Sahibi", "Admin", "Test Lead", "QA Mühendisi", "Geliştirici", "İş Analisti", "İzleyici"];
  const lines = [
    headers.join(";"),
    ...rows.map(r =>
      [
        r.module, r.group, r.description,
        r.owner, r.admin, r.test_lead, r.qa_engineer,
        r.developer, r.business_analyst, r.viewer,
      ].map(v => `"${v}"`).join(";")
    ),
  ];
  const blob = new Blob(["﻿" + lines.join("\n")], { type: "text/csv;charset=utf-8;" });
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement("a");
  a.href = url; a.download = "yetki-matrisi.csv"; a.click();
  URL.revokeObjectURL(url);
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function PermissionsPage() {
  const [groupFilter,   setGroupFilter]   = useState<string>("all");
  const [roleFilter,    setRoleFilter]    = useState<string>("all");
  const [criticalOnly,  setCriticalOnly]  = useState(false);
  const [search,        setSearch]        = useState("");

  const groups = useMemo(() => {
    const unique = new Set(RBAC_MATRIX.map(r => r.group));
    return ["all", ...Array.from(unique)];
  }, []);

  const filtered = useMemo(() => {
    let rows = RBAC_MATRIX;
    if (groupFilter !== "all") rows = rows.filter(r => r.group === groupFilter);
    if (criticalOnly) rows = rows.filter(r => r.critical);
    if (search.trim()) {
      const q = search.trim().toLowerCase();
      rows = rows.filter(r =>
        r.module.toLowerCase().includes(q) ||
        r.description.toLowerCase().includes(q) ||
        r.group.toLowerCase().includes(q)
      );
    }
    return rows;
  }, [groupFilter, criticalOnly, search]);

  const visibleRoles = useMemo(
    () => roleFilter === "all" ? ROLES : ROLES.filter(r => r.key === roleFilter),
    [roleFilter],
  );

  // Coverage stats per role
  const stats = useMemo(() => {
    return ROLES.map(role => {
      const total   = RBAC_MATRIX.length;
      const full    = RBAC_MATRIX.filter(r => r[role.key] === "full").length;
      const limited = RBAC_MATRIX.filter(r => r[role.key] === "limited").length;
      const view    = RBAC_MATRIX.filter(r => r[role.key] === "view").length;
      const none    = RBAC_MATRIX.filter(r => r[role.key] === "none").length;
      return { ...role, total, full, limited, view, none };
    });
  }, []);

  // Group rows for rendering
  const grouped = useMemo(() => {
    const map = new Map<string, RbacRow[]>();
    for (const row of filtered) {
      if (!map.has(row.group)) map.set(row.group, []);
      map.get(row.group)!.push(row);
    }
    return map;
  }, [filtered]);

  return (
    <div className="min-h-full bg-surface-base">
      {/* ── Header ────────────────────────────────────────────────────────── */}
      <div className="border-b border-border bg-surface-raised px-6 py-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-widest text-fg-subtle">Neurex Management</p>
            <h1 className="mt-1 text-[18px] font-semibold text-fg">Rol & Yetki Matrisi</h1>
            <p className="mt-1 text-[12px] text-fg-muted">
              {RBAC_MATRIX.length} izin satırı · {ROLES.length} rol · {groups.length - 1} modül grubu
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => exportCSV(filtered)}
              className="flex items-center gap-1.5 rounded-xl border border-border bg-surface-overlay px-3 py-2 text-[12px] font-medium text-fg-muted hover:text-fg hover:border-border-strong transition-colors"
            >
              <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/>
              </svg>
              CSV İndir
            </button>
            <button
              onClick={() => window.print()}
              className="flex items-center gap-1.5 rounded-xl border border-border bg-surface-overlay px-3 py-2 text-[12px] font-medium text-fg-muted hover:text-fg hover:border-border-strong transition-colors"
            >
              <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 9V2h12v7M6 18H4a2 2 0 01-2-2v-5a2 2 0 012-2h16a2 2 0 012 2v5a2 2 0 01-2 2h-2"/>
                <rect x="6" y="14" width="12" height="8"/>
              </svg>
              Yazdır
            </button>
          </div>
        </div>

        {/* ── Role Cards ──────────────────────────────────────────────────── */}
        <div className="mt-5 grid gap-2 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-7">
          {stats.map(role => (
            <button
              key={role.key}
              onClick={() => setRoleFilter(prev => prev === role.key ? "all" : role.key)}
              className={cn(
                "rounded-xl border p-3 text-left transition-all",
                roleFilter === role.key
                  ? cn(role.border, role.bg)
                  : "border-border bg-surface-overlay hover:border-border-strong",
              )}
            >
              <div className="flex items-center gap-2 mb-1.5">
                <span className={cn("h-2 w-2 rounded-full", role.bg.replace("bg-", "bg-").replace("/10", ""))}>
                  <span className={cn("flex h-full w-full rounded-full", role.color.replace("text-", "bg-").replace("-400", "-500"))} />
                </span>
                <span className={cn("text-[11px] font-semibold", roleFilter === role.key ? role.color : "text-fg")}>
                  {role.qaLabel}
                </span>
              </div>
              <div className="flex items-center gap-2 text-[10px] tabular-nums">
                <span className="text-emerald-400">{role.full} tam</span>
                {role.limited > 0 && <span className="text-blue-400">{role.limited} kısıtlı</span>}
                <span className="text-fg-disabled">{role.none} yok</span>
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* ── Filters ───────────────────────────────────────────────────────── */}
      <div className="flex flex-wrap items-center gap-3 border-b border-border bg-surface-raised px-6 py-3">
        {/* Search */}
        <div className="relative">
          <svg className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-fg-disabled" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <circle cx="11" cy="11" r="8"/><path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-4.35-4.35"/>
          </svg>
          <input
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Modül veya açıklama ara…"
            className="h-8 w-56 rounded-lg border border-border bg-surface-overlay pl-8 pr-3 text-[12px] text-fg placeholder:text-fg-disabled focus:border-brand/40 focus:outline-none"
          />
        </div>

        {/* Group filter */}
        <select
          value={groupFilter}
          onChange={e => setGroupFilter(e.target.value)}
          className="h-8 rounded-lg border border-border bg-surface-overlay px-3 text-[12px] text-fg focus:border-brand/40 focus:outline-none"
        >
          <option value="all">Tüm Modül Grupları</option>
          {groups.filter(g => g !== "all").map(g => (
            <option key={g} value={g}>{g}</option>
          ))}
        </select>

        {/* Critical toggle */}
        <button
          onClick={() => setCriticalOnly(v => !v)}
          className={cn(
            "flex h-8 items-center gap-1.5 rounded-lg border px-3 text-[12px] font-medium transition-colors",
            criticalOnly
              ? "border-amber-500/40 bg-amber-500/10 text-amber-400"
              : "border-border bg-surface-overlay text-fg-muted hover:border-border-strong hover:text-fg",
          )}
        >
          <span className="text-[10px]">⚠</span>
          Kritik İzinler
        </button>

        {/* Results count */}
        <span className="ml-auto text-[11px] text-fg-subtle">
          {filtered.length} izin gösteriliyor
          {search || groupFilter !== "all" || criticalOnly ? ` (toplam: ${RBAC_MATRIX.length})` : ""}
        </span>
      </div>

      {/* ── Legend ────────────────────────────────────────────────────────── */}
      <div className="flex flex-wrap items-center gap-4 border-b border-border bg-surface-overlay px-6 py-2">
        {(Object.entries(PERM_CONFIG) as [PermLevel, typeof PERM_CONFIG[PermLevel]][]).map(([level, cfg]) => (
          <div key={level} className="flex items-center gap-1.5">
            <span className={cn("text-[12px] font-semibold", cfg.textColor)}>{cfg.icon}</span>
            <span className="text-[10px] text-fg-muted">{cfg.label}</span>
          </div>
        ))}
        <div className="flex items-center gap-1.5">
          <span className="h-3 w-3 rounded border border-amber-500/40 bg-amber-500/10" />
          <span className="text-[10px] text-fg-muted">Kritik İzin</span>
        </div>
      </div>

      {/* ── Matrix Table ──────────────────────────────────────────────────── */}
      <div className="overflow-x-auto">
        {grouped.size === 0 ? (
          <div className="flex flex-col items-center justify-center gap-2 py-16 text-center">
            <span className="text-3xl opacity-30">🔍</span>
            <p className="text-[13px] font-medium text-fg-muted">Filtrelere uyan izin bulunamadı</p>
            <button
              onClick={() => { setSearch(""); setGroupFilter("all"); setCriticalOnly(false); }}
              className="text-[11px] text-brand hover:underline"
            >
              Filtreleri temizle
            </button>
          </div>
        ) : (
          <table className="w-full border-collapse min-w-[800px]">
            <thead className="sticky top-0 z-10 bg-surface-raised">
              <tr>
                <th className="border-b border-border px-4 py-3 text-left text-[10px] font-semibold uppercase tracking-widest text-fg-subtle w-64 min-w-[200px]">
                  İzin / Modül
                </th>
                <th className="border-b border-border px-4 py-3 text-left text-[10px] font-semibold uppercase tracking-widest text-fg-subtle hidden xl:table-cell">
                  Açıklama
                </th>
                {visibleRoles.map(role => (
                  <th
                    key={role.key}
                    className={cn(
                      "border-b border-border px-3 py-3 text-center text-[10px] font-semibold uppercase tracking-widest w-24",
                      role.color,
                    )}
                  >
                    <div>{role.label}</div>
                    <div className="text-fg-disabled normal-case tracking-normal font-normal text-[9px] mt-0.5">{role.qaLabel}</div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {Array.from(grouped.entries()).map(([group, rows]) => (
                <>
                  {/* Group header row */}
                  <tr key={`g-${group}`}>
                    <td
                      colSpan={2 + visibleRoles.length}
                      className="border-b border-border bg-surface-overlay px-4 py-2"
                    >
                      <span className="text-[10px] font-bold uppercase tracking-widest text-fg-subtle">
                        {group}
                      </span>
                      <span className="ml-2 text-[10px] text-fg-disabled">
                        ({rows.length} izin)
                      </span>
                    </td>
                  </tr>
                  {/* Permission rows */}
                  {rows.map((row, idx) => (
                    <tr
                      key={row.module}
                      className={cn(
                        "group transition-colors hover:bg-surface-overlay",
                        idx % 2 === 0 ? "" : "bg-surface-base/50",
                      )}
                    >
                      <td className="border-b border-border px-4 py-2.5">
                        <div className="flex items-center gap-2">
                          {row.critical && (
                            <span className="shrink-0 text-[10px] text-amber-400" title="Kritik güvenlik izni">⚠</span>
                          )}
                          <span className="text-[12px] font-medium text-fg leading-snug">{row.module}</span>
                        </div>
                      </td>
                      <td className="border-b border-border px-4 py-2.5 hidden xl:table-cell">
                        <span className="text-[11px] text-fg-muted leading-snug">{row.description}</span>
                      </td>
                      {visibleRoles.map(role => (
                        <PermCell key={role.key} level={row[role.key]} critical={row.critical} />
                      ))}
                    </tr>
                  ))}
                </>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* ── Role Descriptions Footer ──────────────────────────────────────── */}
      <div className="border-t border-border bg-surface-raised px-6 py-5">
        <p className="mb-3 text-[11px] font-semibold uppercase tracking-widest text-fg-subtle">Roller Hakkında</p>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-7">
          {ROLES.map(role => (
            <div key={role.key} className={cn("rounded-xl border p-3", role.border, role.bg)}>
              <p className={cn("text-[11px] font-semibold", role.color)}>{role.qaLabel}</p>
              <p className="mt-1 text-[10px] text-fg-muted leading-relaxed">{role.description}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
