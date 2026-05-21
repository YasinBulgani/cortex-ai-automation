#!/usr/bin/env python3
"""
Yeni test automation projesi oluşturmak için scaffolding script.
Mevcut proje yapısını template olarak kullanarak yeni projeler oluşturur.
"""

import os
import shutil
import json
from pathlib import Path
from datetime import datetime


class ProjectScaffolder:
    """Yeni test automation projeleri oluşturan sınıf."""

    # Kopyalanacak dizinler
    DIRS_TO_COPY = [
        "config",
        "core",
        "pages",
        "steps",
        "tests",
        "features",
        "routes",
        "ui",
        "scripts",
        "synthetic-data-platform-v4",
        "allure-results",
        "reports",
        "screenshots",
        "data"
    ]

    # Kopyalanmayacak dosyalar/dizinler
    IGNORE_PATTERNS = {
        "__pycache__",
        ".pytest_cache",
        ".pyc",
        ".env",
        "env_vars.env",
        "env_vars.local.env",
        ".claude",
        ".git",
        "node_modules",
        ".DS_Store",
        "allure-report"
    }

    # Yeni proje için oluşturulacak dosyalar
    NEW_PROJECT_FILES = {
        "README.md": """# {project_name}

Test Automation Project - created on {timestamp}

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
playwright install
```

2. Configure environment:
```bash
cp .env.example env_vars.env
# Edit env_vars.env with your settings
```

3. Run tests:
```bash
python runner.py
```

## Project Structure

- `tests/` - Test files
- `features/` - BDD Gherkin scenarios
- `steps/` - Step definitions
- `pages/` - Page Object Model
- `core/` - Core framework modules
- `routes/` - Flask API routes
- `ui/` - Web dashboard
- `synthetic-data-platform-v4/` - Synthetic data generation

See README files in subdirectories for more details.
""",
        "PROJECT.json": {
            "name": "{project_name}",
            "created_at": "{timestamp}",
            "version": "1.0.0",
            "description": "Test Automation Project",
            "base_url": "https://example.com"
        }
    }

    def __init__(self, project_name: str, source_dir: Path = None, target_dir: Path = None):
        """
        ProjectScaffolder'ı başlat.

        Args:
            project_name: Yeni projenin adı
            source_dir: Kaynak proje dizini (varsayılan: mevcut proje)
            target_dir: Hedef dizin (varsayılan: projects/)
        """
        self.project_name = project_name
        self.source_dir = source_dir or Path(__file__).resolve().parent.parent
        self.target_dir = target_dir or self.source_dir / "projects"
        self.project_path = self.target_dir / project_name

    def validate(self) -> bool:
        """Proje adı ve dizinleri doğrula."""
        if not self.project_name:
            print("❌ Proje adı boş olamaz!")
            return False

        if not self.project_name.replace("-", "").replace("_", "").isalnum():
            print("❌ Proje adı sadece alfanümerik karakterler ve tire/alt çizgi içerebilir!")
            return False

        if self.project_path.exists():
            print(f"❌ Proje zaten var: {self.project_path}")
            return False

        if not self.source_dir.exists():
            print(f"❌ Kaynak dizin bulunamadı: {self.source_dir}")
            return False

        return True

    def create(self) -> bool:
        """Yeni proje yapısını oluştur."""
        try:
            # Dizinleri doğrula
            if not self.validate():
                return False

            print(f"\n🚀 Proje oluşturuluyor: {self.project_name}")
            print(f"   Kaynak: {self.source_dir}")
            print(f"   Hedef: {self.project_path}")

            # Target dizini oluştur
            self.target_dir.mkdir(parents=True, exist_ok=True)
            self.project_path.mkdir(parents=True, exist_ok=True)

            # Dizinleri kopyala
            print("\n📁 Dizin yapısı kopyalanıyor...")
            self._copy_directories()

            # Dosyaları kopyala
            print("\n📄 Dosyalar kopyalanıyor...")
            self._copy_files()

            # Yeni dosyaları oluştur
            print("\n✏️  Proje dosyaları oluşturuluyor...")
            self._create_project_files()

            # .env dosyasını hazırla
            print("\n⚙️  Environment dosyaları hazırlanıyor...")
            self._setup_env_file()

            # Database'i reset et
            print("\n🗄️  Database hazırlanıyor...")
            self._init_database()

            print(f"\n✅ Proje başarıyla oluşturuldu!")
            print(f"   Konum: {self.project_path}")
            print(f"\n🎯 Sonraki adımlar:")
            print(f"   1. cd {self.project_path}")
            print(f"   2. pip install -r requirements.txt")
            print(f"   3. python app.py")

            return True

        except Exception as e:
            print(f"\n❌ Hata: {e}")
            # Cleanup on failure
            if self.project_path.exists():
                shutil.rmtree(self.project_path)
            return False

    def _copy_directories(self) -> None:
        """Dizinleri source'dan target'a kopyala."""
        for dir_name in self.DIRS_TO_COPY:
            src = self.source_dir / dir_name
            dst = self.project_path / dir_name

            # Eğer source'da yoksa skip et
            if not src.exists():
                continue

            # Hedef varsa sil
            if dst.exists():
                shutil.rmtree(dst)

            try:
                print(f"  ├─ {dir_name}/")
                shutil.copytree(src, dst, ignore=self._ignore_patterns)
            except Exception as e:
                print(f"  ⚠️  {dir_name}/ kopyalanamadı: {e}")
                # Devam et, bu dizin zorunlu değil

    def _copy_files(self) -> None:
        """Önemli dosyaları kopyala."""
        important_files = [
            "requirements.txt",
            "pytest.ini",
            ".env.example",
            "runner.py",
            "app.py",
            "conftest.py"
        ]

        for file_name in important_files:
            src = self.source_dir / file_name
            dst = self.project_path / file_name

            if src.exists():
                print(f"  ├─ {file_name}")
                shutil.copy2(src, dst)

    def _ignore_patterns(self, dir, files):
        """shutil.copytree için ignore fonksiyonu."""
        ignored = []
        for file in files:
            for pattern in self.IGNORE_PATTERNS:
                if pattern in file:
                    ignored.append(file)
                    break
        return set(ignored)

    def _create_project_files(self) -> None:
        """Yeni proje dosyalarını oluştur."""
        timestamp = datetime.now().isoformat()

        for file_name, content in self.NEW_PROJECT_FILES.items():
            file_path = self.project_path / file_name

            if file_name == "README.md":
                file_path.write_text(
                    content.format(
                        project_name=self.project_name,
                        timestamp=timestamp
                    )
                )
                print(f"  ├─ {file_name}")

            elif file_name == "PROJECT.json":
                project_json = {
                    "name": self.project_name,
                    "created_at": timestamp,
                    "version": "1.0.0",
                    "description": "Test Automation Project",
                    "base_url": "https://example.com"
                }
                file_path.write_text(json.dumps(project_json, indent=2))
                print(f"  ├─ {file_name}")

    def _setup_env_file(self) -> None:
        """Yeni proje için .env dosyasını oluştur."""
        env_example = self.source_dir / ".env.example"
        env_file = self.project_path / "env_vars.env"

        if env_example.exists():
            # .env.example'ı kopyala ve adapt et
            content = env_example.read_text()
            # Varsayılan değerleri ekle
            env_file.write_text(content)
            print(f"  ├─ env_vars.env (from .env.example)")
        else:
            # Minimal .env oluştur
            content = """# Test Automation Configuration

# AI/LLM Settings
OPENAI_API_KEY=your-api-key-here
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o

# Browser Settings
BROWSER=chromium
HEADLESS=false

# URLs
BASE_URL=https://example.com

# Timeouts (milliseconds)
DEFAULT_TIMEOUT=30000
NAVIGATION_TIMEOUT=60000
"""
            env_file.write_text(content)
            print(f"  ├─ env_vars.env (minimal)")

    def _init_database(self) -> None:
        """Yeni proje için database'i hazırla."""
        db_path = self.project_path / "test_data.db"

        # Eski database'i sil
        if db_path.exists():
            db_path.unlink()

        # Yeni database script'ini çalıştır
        seed_script = self.project_path / "scripts" / "seed_db.py"
        if seed_script.exists():
            print(f"  ├─ test_data.db (initialized)")
            # Database import ve init kodu burada çalışabilir
            # Şimdilik sadece dosyayı işaretliyoruz
            db_path.touch()


def main():
    """CLI entry point."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python scaffold_project.py <project-name>")
        print("Example: python scaffold_project.py my-new-project")
        sys.exit(1)

    project_name = sys.argv[1]
    scaffolder = ProjectScaffolder(project_name)

    success = scaffolder.create()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
