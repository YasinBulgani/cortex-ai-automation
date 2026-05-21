"""
ProjectScannerAgent — Ajan 0 (Sıfır Müdahale İçin Kritik)

Görevi:
  Kullanıcıdan HİÇBİR GİRDİ almadan projeyi otomatik tarar:
  - Alembic/SQLAlchemy modellerinden DB şeması çıkarır
  - FastAPI router'larından API endpoint listesi çıkarır
  - Mevcut feature/spec dosyalarını okur
  - Git log'dan son değişiklikleri alır
  - KnowledgeStore'dan geçmiş bağlamı çeker
  - Hepsini birleştirerek pipeline için hazır context üretir

Bu ajan çalıştıktan sonra kullanıcı hiçbir şey doldurmak zorunda değildir.
"""

from __future__ import annotations

import ast
import json
import logging
import subprocess
from pathlib import Path
from typing import Any

from app.config import settings
from .base_agent import BaseAgent, AgentResult

logger = logging.getLogger(__name__)

# Proje kökü
REPO_ROOT = Path(__file__).resolve().parents[5]


class ProjectScannerAgent(BaseAgent):
    name = "Proje Tarayıcı"
    # Bu ajan LLM kullanmaz — sadece dosya okur, hızlı çalışır
    temperature = 0.0
    # ProjectScanner proje bağlamının KAYNAĞIDIR — enjeksiyon yapma (döngüsel bağımlılık)
    inject_project_context = False

    def run(self, context: dict) -> AgentResult:
        """
        context keys (hepsi opsiyonel — scanner kendisi doldurur):
          project_hint — hangi modüle odaklanılsın (opsiyonel)
        """
        hint = context.get("project_hint", "")
        result: dict[str, Any] = {}

        # ── 1. DB Şeması ─────────────────────────────────────────────
        result["db_schema"] = self._scan_db_schema()

        # ── 2. API Endpoint'leri ──────────────────────────────────────
        result["api_docs"] = self._scan_api_endpoints()

        # ── 3. Mevcut Feature Dosyaları ───────────────────────────────
        result["existing_features"] = self._scan_feature_files()

        # ── 4. Mevcut E2E Testler ─────────────────────────────────────
        result["existing_tests"] = self._scan_e2e_specs()

        # ── 5. Git Son Değişiklikler ──────────────────────────────────
        result["recent_changes"] = self._scan_git_log()

        # ── 6. KnowledgeStore Geçmişi ─────────────────────────────────
        result["knowledge_context"] = self._scan_knowledge_store()

        # ── 7. Sistem Açıklaması Üret ─────────────────────────────────
        result["description"] = self._build_description(result, hint)

        # ── 8. Regülasyon Tahmini ─────────────────────────────────────
        result["regulations"] = self._infer_regulations(result)

        total_info = sum([
            bool(result["db_schema"]),
            bool(result["api_docs"]),
            bool(result["existing_features"]),
            bool(result["recent_changes"]),
        ])

        logger.info("ProjectScanner: %d veri kaynağı tarandı", total_info)

        return AgentResult(
            agent_name=self.name,
            success=True,
            data=result,
        )

    # ── Tarama Metodları ─────────────────────────────────────────────────────

    def _scan_db_schema(self) -> str:
        """SQLAlchemy models.py dosyalarından tablo şemasını çıkar."""
        lines = []
        model_files = list(REPO_ROOT.rglob("models.py"))[:5]

        for mf in model_files:
            try:
                content = mf.read_text(encoding="utf-8", errors="ignore")
                # class tanımlarını bul
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        # Column tanımlarını çıkar
                        cols = []
                        for item in ast.walk(node):
                            if isinstance(item, ast.Assign):
                                for target in item.targets:
                                    if isinstance(target, ast.Name):
                                        cols.append(target.id)
                        if cols:
                            lines.append(f"Tablo: {node.name} | Kolonlar: {', '.join(cols[:10])}")
            except Exception:
                # AST parse edilemezse regex ile dene
                import re
                for match in re.finditer(r"class\s+(\w+)\s*\(", content):
                    lines.append(f"Model: {match.group(1)}")

        # Alembic migration'lardan da tablo isimlerini al
        for migration in sorted(REPO_ROOT.rglob("versions/*.py"))[-3:]:
            try:
                content = migration.read_text(encoding="utf-8", errors="ignore")
                import re
                for match in re.finditer(r"create_table\s*\(\s*['\"](\w+)['\"]", content):
                    lines.append(f"Tablo: {match.group(1)}")
            except Exception:
                pass

        return "\n".join(lines[:50]) if lines else ""

    def _scan_api_endpoints(self) -> str:
        """FastAPI router dosyalarından endpoint listesi çıkar."""
        import re
        lines = []
        router_files = list(REPO_ROOT.rglob("router.py"))[:10]

        for rf in router_files:
            try:
                content = rf.read_text(encoding="utf-8", errors="ignore")
                # @router.get/post/put/delete/patch
                for match in re.finditer(
                    r'@router\.(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']',
                    content,
                ):
                    method = match.group(1).upper()
                    path = match.group(2)
                    # prefix'i bul
                    prefix_match = re.search(r'prefix\s*=\s*["\']([^"\']+)["\']', content)
                    prefix = prefix_match.group(1) if prefix_match else ""
                    lines.append(f"{method} {prefix}{path}")
            except Exception:
                pass

        return "\n".join(lines[:60]) if lines else ""

    def _scan_feature_files(self) -> str:
        """engine/features klasöründeki .feature dosyalarını özetle."""
        lines = []
        features_dir = REPO_ROOT / "engine" / "features"
        if not features_dir.exists():
            return ""

        for fp in sorted(features_dir.rglob("*.feature"))[:20]:
            try:
                content = fp.read_text(encoding="utf-8", errors="ignore")
                # Feature ve Scenario başlıklarını al
                for line in content.splitlines():
                    line = line.strip()
                    if line.startswith("Feature:") or line.startswith("Scenario:"):
                        lines.append(line)
            except Exception:
                pass

        return "\n".join(lines[:40]) if lines else ""

    def _scan_e2e_specs(self) -> str:
        """e2e klasöründeki .spec.ts dosyalarından test başlıklarını al."""
        import re
        lines = []
        e2e_dir = REPO_ROOT / "e2e"
        if not e2e_dir.exists():
            return ""

        for sp in sorted(e2e_dir.rglob("*.spec.ts"))[:15]:
            try:
                content = sp.read_text(encoding="utf-8", errors="ignore")
                for match in re.finditer(
                    r"(?:describe|test|it)\s*\(\s*['\"`](.+?)['\"`]", content
                ):
                    lines.append(f"Test: {match.group(1)}")
            except Exception:
                pass

        return "\n".join(lines[:40]) if lines else ""

    def _scan_git_log(self) -> str:
        """Son 20 commit mesajını al."""
        try:
            result = subprocess.run(
                ["git", "log", "--oneline", "-20", "--no-merges"],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.stdout.strip()
        except Exception:
            return ""

    def _scan_knowledge_store(self) -> str:
        """KnowledgeStore'dan proje hakkında geçmiş bilgi çek."""
        try:
            from app.domains.ai.knowledge_store import KnowledgeStore
            project_id = getattr(self, "_project_id", None)
            store = KnowledgeStore(project_id=project_id)
            chunks = store.retrieve(
                "bankacılık test senaryoları hata analizi",
                top_k=5,
                sources=["insight", "error_pattern", "execution"],
                project_id=project_id,
            )
            if chunks:
                return "\n".join([c.content for c in chunks])
        except Exception:
            pass
        return ""

    def _build_description(self, data: dict, hint: str) -> str:
        """Taranan verilerden otomatik sistem açıklaması üret."""
        parts = ["TestwrightAI Test Otomasyon Platformu"]

        # DB'den modül isimlerini çıkar
        db = data.get("db_schema", "")
        if "transfer" in db.lower() or "payment" in db.lower():
            parts.append("Para transferi ve ödeme modülleri")
        if "user" in db.lower() or "auth" in db.lower():
            parts.append("Kullanıcı yönetimi ve kimlik doğrulama")
        if "account" in db.lower() or "hesap" in db.lower():
            parts.append("Hesap yönetimi")
        if "loan" in db.lower() or "kredi" in db.lower():
            parts.append("Kredi modülü")

        if hint:
            parts.append(f"Odak: {hint}")

        return " | ".join(parts)

    def _infer_regulations(self, data: dict) -> list[str]:
        """Taranan verilerden hangi regülasyonların geçerli olduğunu tahmin et."""
        regs = ["BDDK", "KVKK"]  # Her bankacılık uygulamasında geçerli

        db = (data.get("db_schema", "") + data.get("api_docs", "")).lower()
        features = data.get("existing_features", "").lower()
        all_text = db + features

        if any(w in all_text for w in ["card", "kart", "pci", "cvv", "pan"]):
            regs.append("PCI-DSS")
        if any(w in all_text for w in ["transfer", "havale", "eft", "swift"]):
            regs.append("MASAK")
            regs.append("TCMB")
        if any(w in all_text for w in ["kyc", "müşteri", "customer", "kimlik"]):
            regs.append("KYC")
        if any(w in all_text for w in ["aml", "kara para", "şüpheli"]):
            regs.append("AML")

        return list(dict.fromkeys(regs))  # Sıra koruyarak tekrarları kaldır
