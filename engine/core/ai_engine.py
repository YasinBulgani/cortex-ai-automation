"""
AIEngine - LLM ile AI destekli test üretimi ve aksiyon yürütme

Desteklenen sağlayıcılar merkezi LLMGateway üzerinden yönetilir.
"""
import json
import re
from playwright.sync_api import Page
from rich.console import Console

from config.settings import settings
from core.page_inspector import PageInspector
from services import get_llm_gateway

console = Console()

# Desteklenen Playwright aksiyon şeması
ACTION_SCHEMA = """
Aşağıdaki JSON formatında bir aksiyonlar listesi döndür:
[
  {"action": "navigate",      "url": "https://..."},
  {"action": "click",         "selector": "CSS ya da metin", "by": "text|css|role"},
  {"action": "fill",          "selector": "...", "value": "yazılacak metin"},
  {"action": "select",        "selector": "...", "value": "seçenek"},
  {"action": "wait",          "ms": 1000},
  {"action": "assert_text",   "selector": "...", "expected": "beklenen metin"},
  {"action": "assert_visible","selector": "..."},
  {"action": "assert_url",    "contains": "..."},
  {"action": "screenshot",    "name": "dosya_adi"}
]
Sadece JSON listesi döndür. Açıklama veya markdown kullanma.
"""

SYSTEM_PROMPT = """Sen bir web otomasyon test uzmanısın.
Kullanıcının görevini yerine getirmek için Playwright aksiyonları üretirsin.
Sayfa yapısını dikkate alarak doğru selector'lar kullan.
Tercih sırası: aria-label > placeholder > metin içeriği > CSS class/ID.
{page_context}
"""


class AIEngine:
    """LLM destekli test üretici ve aksiyon yürütücüsü."""

    def __init__(self):
        self._gateway = None

    @property
    def gateway(self):
        if self._gateway is None:
            self._gateway = get_llm_gateway()
        return self._gateway

    @property
    def execute_model_name(self) -> str:
        model = settings.OPENAI_MODEL
        if model.startswith("g4f-"):
            return model.replace("g4f-", "")
        return model

    def _call_llm(self, messages: list[dict], temperature: float = 0.7) -> str:
        """Evrensel LLM çağırıcı: merkezi LLMGateway'e delege eder."""
        model = self.execute_model_name
        res = self.gateway.complete(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=4096,
        )
        return res.content.strip()

    # ── Test Üretimi ───────────────────────────────────────────────────────────
    def generate_actions(self, task: str, page: Page = None) -> list[dict]:
        """
        Verilen görev tanımından Playwright aksiyonları listesi üretir.

        Args:
            task: "Giriş formunu doldur ve gönder" gibi Türkçe/İngilizce görev açıklaması
            page: Mevcut Playwright page (sayfa bağlamı için analiz edilir)

        Returns:
            Aksiyon sözlükleri listesi
        """
        page_context = ""
        if page:
            inspector = PageInspector(page)
            page_context = f"\n\nSayfa Bağlamı:\n{inspector.get_summary_text()}"

        system = SYSTEM_PROMPT.format(page_context=page_context)
        user_message = f"Görev: {task}\n\n{ACTION_SCHEMA}"

        console.print(f"[bold blue]🤖 AI'ya soruyorum:[/bold blue] {task}")

        raw = self._call_llm([
            {"role": "system", "content": system},
            {"role": "user", "content": user_message},
        ], temperature=0.1)
        
        return self._parse_actions(raw)

    def generate_test_file(self, url: str, task: str, test_name: str = None) -> str:
        """
        Verilen URL ve görev için pytest test dosyasının Python kodunu üretir.

        Returns:
            Python kaynak kodu (string)
        """
        name = test_name or "generated_test"
        prompt = f"""
Aşağıdaki bilgiler için bir pytest test dosyası yaz:
- Test edilecek URL: {url}
- Görev: {task}
- Test fonksiyon adı: test_{name}

Playwright sync API kullan. conftest.py'den gelen `page` fixture'ını kullan.
page.goto(...) ile URL'ye git. Assertions ekle.
Sadece Python kodu döndür.
"""
        code = self._call_llm([
            {"role": "system", "content": "Sen bir pytest + Playwright test yazarısın. Sadece Python kodu üret."},
            {"role": "user", "content": prompt},
        ], temperature=0.1)
        
        # Markdown kod bloğunu temizle
        if code.startswith("```"):
            lines = code.split("\n")
            code = "\n".join(lines[1:-1])
        return code

    def generate_gherkin(self, requirements: str, target_url: str = None, tech: str = None) -> str:
        """
        Verilen iş kuralları/gereksinim (requirements) metninden
        standartlara uygun bir Gherkin (.feature) veya seçilmiş teknoloji formatında dosya üretir.
        """
        
        dom_context = ""
        if target_url:
            console.print(f"[bold cyan]🔍 Hedef URL analiz ediliyor: {target_url}[/bold cyan]")
            try:
                from core.browser import BrowserEngine
                from core.page_inspector import PageInspector
                engine = BrowserEngine()
                engine.start()
                engine.page.goto(target_url, wait_until="domcontentloaded")
                inspector = PageInspector(engine.page)
                dom_context = "\nSAYFADAKİ GERÇEK ELEMENTLER VE XPATH/CSS SELECTORLERİ:\n" + inspector.get_summary_text()
                engine.stop()
            except Exception as e:
                console.print(f"[bold red]Hedef URL analizi başarısız: {e}[/bold red]")
                
        target_tech_prompt = f"{tech} teknolojisine uygun BDD/Gherkin formatında" if tech else "Gherkin (.feature) formatında"
                
        prompt = f"""
Sen bir BDD / QA Test dâhisin.
Aşağıdaki gereksinimleri okuyup {target_tech_prompt} bir test senaryosu yaz.

GEREKSİNİMLER:
{requirements}

KURALLAR:
1. SADECE aşağidaki desteklenen adımları kullan:
  Given kullanıcı ana sayfadadır
  Given kullanıcı "<path>" sayfasındadır
  When kullanıcı "<metin>" metnine tıklar
  When kullanıcı "<selector>" kutusuna "<değer>" yazar
  When kullanıcı arama kutusuna "<değer>" yazar
  When kullanıcı Enter tuşuna basar
  When kullanıcı "<ms>" milisaniye bekler
  When AI "<görev>" görevini gerçekleştirir
  Then sayfa başlığı "<metin>" içermelidir
  Then URL "<metin>" içermelidir
  Then "<selector>" elementi görünür olmalıdır
  Then en az 1 adım başarılı olmalıdır
  
2. Senaryolara uygun etiketler (örneğin @smoke, @P1, @ai) bekle.
3. SADECE feature text içeriği döndür. Markdown '```gherkin' gibi taglar KULLANMA.
4. EĞER SANA SAYFA ELEMENTLERİ VERİLMİŞSE, uydurma selectorler kullanmak yerine kesinlikle sana verilen XPath veya CSS Selector'leri kullan ("Element => XPath: ...").
{dom_context}
        """
        console.print("[bold purple]🤖 AI Test Case üretiyor...[/bold purple]")
        content = self._call_llm([
            {"role": "system", "content": "You are a specialized Gherkin test generator."},
            {"role": "user", "content": prompt},
        ], temperature=0.2)
        
        if content.startswith("```"):
            lines = content.split("\n")
            if lines[-1].strip() == "```":
                content = "\n".join(lines[1:-1])
        return content

    # ── Aksiyon Yürütme ────────────────────────────────────────────────────────
    def execute_actions(self, actions: list[dict], page: Page) -> list[dict]:
        """
        Aksiyonlar listesini Playwright ile sırayla yürütür.

        Returns:
            Her aksiyon için sonuç bilgisi içeren liste
        """
        results = []
        for i, action in enumerate(actions, 1):
            act = action.get("action", "")
            console.print(f"  [cyan]▶ [{i}/{len(actions)}] {act}[/cyan]", end=" ")
            try:
                result = self._run_action(action, page)
                results.append({"action": action, "status": "passed", "detail": result})
                console.print("[green]✓[/green]")
            except Exception as e:
                results.append({"action": action, "status": "failed", "error": str(e)})
                console.print(f"[red]✗ {e}[/red]")
        return results

    def _run_action(self, action: dict, page: Page) -> str:
        act = action["action"]

        if act == "navigate":
            page.goto(action["url"], wait_until="domcontentloaded")
            return f"Navigated to {action['url']}"

        elif act == "click":
            sel = action["selector"]
            by = action.get("by", "css")
            if by == "text":
                page.get_by_text(sel, exact=False).first.click()
            elif by == "role":
                page.get_by_role(sel).click()
            else:
                page.locator(sel).first.click()
            return f"Clicked: {sel}"

        elif act == "fill":
            page.locator(action["selector"]).fill(action["value"])
            return f"Filled '{action['selector']}' with '{action['value']}'"

        elif act == "select":
            page.locator(action["selector"]).select_option(action["value"])
            return f"Selected '{action['value']}'"

        elif act == "wait":
            page.wait_for_timeout(action.get("ms", 1000))
            return f"Waited {action.get('ms', 1000)}ms"

        elif act == "assert_text":
            element = page.locator(action["selector"])
            actual = element.inner_text()
            expected = action["expected"]
            assert expected in actual, f"Beklenen: '{expected}', Bulunan: '{actual}'"
            return f"Text assertion passed: '{expected}'"

        elif act == "assert_visible":
            page.locator(action["selector"]).wait_for(state="visible")
            return f"Element visible: {action['selector']}"

        elif act == "assert_url":
            current = page.url
            assert action["contains"] in current, \
                f"URL beklenen değeri içermiyor. Beklenen: '{action['contains']}', Mevcut: '{current}'"
            return f"URL assertion passed"

        elif act == "screenshot":
            from core.browser import BrowserEngine
            from config.settings import settings
            from datetime import datetime
            settings.SCREENSHOTS_DIR.mkdir(exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = settings.SCREENSHOTS_DIR / f"{action.get('name', 'screenshot')}_{ts}.png"
            page.screenshot(path=str(path), full_page=True)
            return f"Screenshot saved: {path}"

        else:
            raise ValueError(f"Bilinmeyen aksiyon: {act}")

    # ── Yardımcı ──────────────────────────────────────────────────────────────
    def _parse_actions(self, raw: str) -> list[dict]:
        """LLM çıktısından JSON aksiyon listesini ayrıştırır."""
        try:
            data = json.loads(raw)
            if isinstance(data, list):
                return data
            if isinstance(data, dict) and "actions" in data:
                return data["actions"]
        except json.JSONDecodeError:
            # Markdown bloğu varsa temizle
            if "```" in raw:
                lines = raw.split("\n")
                cleaned = [l for l in lines if not l.strip().startswith("```")]
                try:
                    return json.loads("\n".join(cleaned))
                except Exception:
                    pass
        console.print(f"[yellow]⚠ JSON ayrıştırılamadı. Ham çıktı:[/yellow]\n{raw}")
        return []

    # ── API Analizi ───────────────────────────────────────────────────────────
    def analyze_api_response(self, request_info: dict, response_info: dict) -> str:
        """
        API isteği ve dönen JSON yanıtını analiz edip hataları,
        güvenlik açıklarını veya test edilebilir edge-caseleri raporlar.
        """
        sys_prompt = "Sen kıdemli bir yazılım test otomasyon ve siber güvenlik uzmanısın. BDD testçisinden daha çok bir backend dedektifi gibi düşün."
        
        req_str = json.dumps(request_info, indent=2, ensure_ascii=False)
        res_str = json.dumps(response_info, indent=2, ensure_ascii=False)
        
        user_msg = f"""Aşağıdaki HTTP Servis isteğini ve yanıtını analiz et:

GİDEN İSTEK:
{req_str}

GELEN YANIT (STATUS: {response_info.get('status', 'Bilinmiyor')}):
{res_str}

Lütfen yukarıdaki verilere bakarak şu formatta markdown bir analiz ver:
1. **Durum Değerlendirmesi:** İstek başarılı mı? Kod ile body eşleşiyor mu?
2. **Anomaliler / Hatalar:** Body içinde null, beklenmeyen tip, stack trace vb. absürtlük var mı? Güvenlik problemi var mı?
3. **Önerilen BDD (Gherkin) Adımları:** QA test mühendisi bu API'yi test ederken nelere assert koymalı? (Örn: Then response kodu 200 olmalı, Then "id" alanı boş olmamalı vb.)
"""
        return self._call_llm([
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_msg},
        ], temperature=0.3)

    # ── Playwright Codegen Çevirici ───────────────────────────────────────────
    def convert_code_to_gherkin(self, python_code: str) -> str:
        """Playwright pytest kodunu Türkçe BDD (Gherkin) senaryosuna dönüştürür."""
        prompt = f"""Sen uzman bir Test Otomasyon Mühendisisin.
Aşağıda, kullanıcının tarayıcı üzerinde gerçekleştirdiği işlemleri izleyerek otomatik üretilmiş 'playwright-pytest' kodları bulunmaktadır.
Görevin, bu koddaki tıklama, metin girme, bekleme gibi aksiyonları analiz edip, Gherkin (BDD) formatında temiz, anlaşılır ve Türkçe 'Feature' ve 'Scenario' dökümanı üretmektir.

Kod:
```python
{python_code}
```

KURALLAR:
1. Senaryo adını ve Feature adını koddaki işlemlere bakarak mantıklı bir şekilde Türkçe olarak belirle.
2. Sadece BDD (Gherkin) formatında çıktı ver. Başka hiçbir açıklama, kod bloğu disi vs. ekleme.
3. Feature dili '# language: tr' olsun.
4. Çıktı kesinlikle 'Feature: ...' ile başlamalıdır.
5. SADECE AŞAĞIDAKİ GEÇERLİ ADIMLARI KULLAN (Uydurma adım yazma! Gerekirse bunları arka arkaya kullan):
  Given kullanıcı ana sayfadadır
  Given kullanıcı "<path>" sayfasındadır
  When kullanıcı "<metin>" metnine tıklar
  When kullanıcı "<selector>" kutusuna "<değer>" yazar
  When kullanıcı arama kutusuna "<değer>" yazar
  When kullanıcı Enter tuşuna basar
  When kullanıcı "<ms>" milisaniye bekler
  Then sayfa başlığı "<metin>" içermelidir
  Then URL "<metin>" içermelidir
  Then "<selector>" elementi görünür olmalıdır
  Then en az 1 adım başarılı olmalıdır

Çıktıyı kod bloğu (```gherkin) içerisinde verme, doğrudan ham BDD metni olarak yaz.
"""
        try:
            content = self._call_llm([
                {"role": "system", "content": "Sen kıdemli bir yazılım test QA mühendisisin."},
                {"role": "user", "content": prompt}
            ], temperature=0.2)
            
            # Markdown block cleanup
            if content.startswith("```gherkin"):
                content = content.replace("```gherkin", "", 1).strip()
            if content.startswith("```"):
                content = content.replace("```", "", 1).strip()
            if content.endswith("```"):
                content = content[:-3].strip()
            return content
        except Exception as e:
            return f"Feature: AI Hata\n  Scenario: Hata\n    Given AI motoru '{e}' hatasını verdi"

    # ── AI Security Scanner ───────────────────────────────────────────────────
    def run_security_audit(self, target_url: str) -> str:
        """Hedef URL'i analiz ederek AI destekli güvenlik (Sızma/Zafiyet) taraması yapar."""
        console.print(f"[bold cyan]🔐 Güvenlik Testi Başlatılıyor: {target_url}[/bold cyan]")
        import requests
        from bs4 import BeautifulSoup
        
        headers_info = {}
        forms_info = []
        scripts_info = []
        
        try:
            # 1. HTTP İstek ve Headerları Analiz Et
            res = requests.get(target_url, timeout=15, verify=False)
            headers_info = dict(res.headers)
            
            # 2. BeautifulSoup ile Statik Zafiyet (Form & Script) Yüzeyini Çıkar
            soup = BeautifulSoup(res.text, 'html.parser')
            
            for form in soup.find_all('form'):
                action = form.get('action', '')
                method = form.get('method', 'get').upper()
                inputs = [{"name": inp.get('name', ''), "type": inp.get('type', '')} for inp in form.find_all('input')]
                forms_info.append({"action": action, "method": method, "inputs": inputs})
                
            for script in soup.find_all('script'):
                src = script.get('src')
                if src:
                    scripts_info.append(f"External: {src}")
                elif script.string:
                    inline = script.string.strip()
                    if len(inline) > 200:
                        inline = inline[:200] + "...(truncated)"
                    scripts_info.append(f"Inline: {inline}")
                    
        except Exception as e:
            return f"❌ Hedef adrese ulaşılamadı veya bir hata oluştu: {str(e)}"
            
        sys_prompt = "Sen kıdemli bir Siber Güvenlik Uzmanı (Pen-tester) ve Web Güvenlik Mimarı'sın. Sana verilen sistem verilerini analiz et."
        user_msg = f"""
Lütfen aşağıdaki web hedefi için güvenlik açıklarını analiz et ve profesyonel bir zafiyet raporu çıkar.

Hedef URL: {target_url}

=== HTTP HEADERS (CORS, CSP, X-Frame, HSTS kontrolleri için): ===
{json.dumps(headers_info, indent=2)}

=== HTML FORMLARI (CSRF, XSS, SQLi potansiyeli için): ===
{json.dumps(forms_info, indent=2)}

=== JAVASCRIPT & HARİCİ KAYNAKLAR (XSS, Outdated lib riskleri için): ===
{json.dumps(scripts_info[:20], indent=2)} # Sadece ilk 20 script

Lütfen analizi Markdown formatında yap. Açıkları kritiklik seviyesine göre (Kritik, Yüksek, Orta, Düşük) kategorize et. Sadece teknik ve net bir döküman üret. Tavsiyeler sun.
"""
        return self._call_llm([
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_msg}
        ], temperature=0.2)
        
    def extract_manual_tests_from_text(self, text: str) -> list[dict]:
        """
        Analiz dokümanından manuel test senaryolarını ve adımlarını ayıklar.
        """
        prompt = f"""
Sana bir yazılım analiz/gereksinim dokümanı veriyorum. 
Bu dokümandan çıkarılabilecek tüm mantıklı manuel test caselerini ayıkla.
Her test case için bir başlık (title) ve sıralı adımlar (steps) belirle.
Her adımda bir aksiyon (action) ve bir beklenen sonuç (expected) olmalı.

DOKÜMAN:
{text}

Lütfen sonucunu aşağıdaki JSON formatında döndür:
[
  {{
    "title": "Test Başlığı",
    "steps": [
      {{"action": "Adım aksiyonu", "expected": "Beklenen sonuç"}},
      ...
    ]
  }},
  ...
]
Sadece JSON döndür, açıklama yapma.
"""
        raw = self._call_llm([
            {"role": "system", "content": "Sen bir QA Test Analiz uzmanısın. Dokümanlardan manuel test senaryosu üretirsin."},
            {"role": "user", "content": prompt},
        ], temperature=0.2)
        
        try:
            # Markdown temizliği (eğer varsa)
            if "```" in raw:
                raw = re.sub(r"```json|```", "", raw).strip()
            data = json.loads(raw)
            return data if isinstance(data, list) else []
        except Exception as e:
            console.print(f"[red]AI Manuel Test Ayrıştırma Hatası: {e}[/red]")
            return []


    def extract_test_cases_from_document(self, text: str) -> list[dict]:
        """
        Analiz/gereksinim dokümanından zengin test case'leri çıkarır.
        Öncelik, etiket, ön koşul ve adım bilgilerini içerir.
        """
        prompt = f"""
Sana bir yazılım analiz veya gereksinim dokümanı veriyorum.
Bu dokümandan çıkarılabilecek tüm mantıklı test caselerini üret.

Her test case için şu bilgileri belirle:
- title: Kısa ve açıklayıcı başlık
- description: Test amacını anlatan bir cümle
- preconditions: Testin çalışması için gerekli ön koşullar (boş olabilir)
- priority: P1 (kritik), P2 (yüksek), P3 (normal)
- tags: Virgülle ayrılmış etiketler (örn: smoke, login, ödeme)
- steps: Her biri action ve expected içeren adımlar listesi

DOKÜMAN:
{text[:6000]}

Sonucu SADECE aşağıdaki JSON formatında döndür:
[
  {{
    "title": "Test başlığı",
    "description": "Test amacı",
    "preconditions": "Ön koşullar",
    "priority": "P1|P2|P3",
    "tags": "smoke, login",
    "steps": [
      {{"action": "Kullanıcı login sayfasına gider", "expected": "Login formu görünür"}},
      ...
    ]
  }}
]
Sadece JSON döndür.
"""
        raw = self._call_llm([
            {"role": "system", "content": "Sen kıdemli bir QA mühendisisin. Gereksinim dokümanlarından kapsamlı test case'leri üretirsin."},
            {"role": "user", "content": prompt},
        ], temperature=0.3)

        try:
            if "```" in raw:
                raw = re.sub(r"```json|```", "", raw).strip()
            data = json.loads(raw)
            return data if isinstance(data, list) else []
        except Exception as e:
            console.print(f"[red]Test Case Ayrıştırma Hatası: {e}[/red]")
            return []

    def generate_test_cases_with_explanations(
        self, url: str, page_context: str,
        goals: str = "General testing", count: int = 5,
    ) -> list:
        """Generate test cases with detailed explanations for each step."""
        messages = [
            {
                "role": "system",
                "content": (
                    f"Sen bir QA test uzmanısın. Verilen sayfa için {count} adet "
                    f"test senaryosu oluştur. Her test için adımları ve her adımın "
                    f"neden önemli olduğunun açıklamasını sağla.\n\n"
                    f"Sayfa yapısı:\n{page_context}\n\n"
                    f"Test Hedefleri: {goals}\n\n"
                    "Her test case için JSON format:\n"
                    "{\n"
                    '  "title": "Test başlığı",\n'
                    '  "description": "Test açıklaması",\n'
                    '  "risk_level": "low|medium|high",\n'
                    '  "tags": ["tag1", "tag2"],\n'
                    '  "steps": [\n'
                    '    {"action": "click|fill|select|assert", "selector": "...", "value": "..."},\n'
                    "  ],\n"
                    '  "explanations": [\n'
                    '    "Adım 1 neden önemli: ...",\n'
                    "  ]\n"
                    "}"
                ),
            },
            {
                "role": "user",
                "content": f"URL: {url}\n\nBu sayfa için {count} adet test case oluştur.",
            },
        ]

        response = self._call_llm(messages, temperature=0.5)

        try:
            json_match = response.find("[")
            if json_match >= 0:
                json_str = response[json_match:]
                test_cases = json.loads(json_str)
                return test_cases if isinstance(test_cases, list) else [test_cases]
        except Exception:
            pass

        return [
            {
                "title": f"Test Case {i + 1}",
                "description": f"Basic test case for {url}",
                "risk_level": "medium",
                "tags": ["generated"],
                "steps": [
                    {"action": "navigate", "url": url},
                    {"action": "screenshot", "name": f"test_{i + 1}_screenshot"},
                ],
                "explanations": [
                    "Navigate to the application page",
                    "Capture initial state",
                ],
            }
            for i in range(min(count, 3))
        ]

    def analyze_page_for_test_strategy(self, url: str, page_context: str) -> dict:
        """Analyze a page and recommend optimal testing strategy."""
        messages = [
            {
                "role": "system",
                "content": (
                    f"Sayfa türünü ve test stratejisini analiz et.\n\n"
                    f"Sayfa yapısı:\n{page_context}\n\n"
                    "JSON response:\n"
                    "{\n"
                    '  "page_type": "login|checkout|dashboard|search|form|other",\n'
                    '  "complexity_score": 0-10,\n'
                    '  "critical_elements": ["element1", "element2"],\n'
                    '  "recommendations": ["test critical flows", "test edge cases"],\n'
                    '  "best_practices": ["best practice 1", "best practice 2"]\n'
                    "}"
                ),
            },
            {
                "role": "user",
                "content": f"Analyze page at {url} and recommend testing strategy.",
            },
        ]

        response = self._call_llm(messages, temperature=0.3)

        try:
            json_match = response.find("{")
            if json_match >= 0:
                json_str = response[json_match:]
                return json.loads(json_str)
        except Exception:
            pass

        return {
            "page_type": "unknown",
            "complexity_score": 5.0,
            "critical_elements": ["button", "input"],
            "recommendations": ["Test main functionality"],
            "best_practices": ["Test with valid and invalid inputs"],
        }

    def extract_service_tests_from_spec(self, spec_text: str, spec_type: str = "openapi") -> list[dict]:
        """
        Swagger/OpenAPI spec, kaynak kod veya Postman koleksiyonundan
        servis test senaryoları üretir.
        """
        prompt = f"""
Sana bir {spec_type} servis spesifikasyonu veriyorum.
Bu spesifikasyondan kapsamlı API test senaryoları üret.

Her endpoint için şu senaryoları üret:
- Happy path (başarılı senaryo)
- Negatif senaryo (hata kodları, validation)
- Edge case (boş veri, sınır değer)
- Security (auth eksik, yetkisiz erişim)

Her test için şu alanları doldur:
- title: Test başlığı
- endpoint: HTTP method + path (örn: POST /api/users)
- scenario_type: happy_path | negative | edge_case | security
- priority: P1|P2|P3
- tags: virgülle ayrılmış etiketler
- request: {{ method, path, headers, body, params }}
- expected_response: {{ status_code, body_contains }}
- description: Test amacı

SPESİFİKASYON:
{spec_text[:6000]}

Sonucu SADECE aşağıdaki JSON formatında döndür:
[
  {{
    "title": "POST /api/login - Başarılı giriş",
    "endpoint": "POST /api/login",
    "scenario_type": "happy_path",
    "priority": "P1",
    "tags": "auth, login, smoke",
    "request": {{
      "method": "POST",
      "path": "/api/login",
      "headers": {{"Content-Type": "application/json"}},
      "body": {{"email": "test@test.com", "password": "pass123"}}
    }},
    "expected_response": {{
      "status_code": 200,
      "body_contains": ["token"]
    }},
    "description": "Geçerli kimlik bilgileriyle başarılı giriş"
  }}
]
Sadece JSON döndür.
"""
        raw = self._call_llm([
            {"role": "system", "content": "Sen kıdemli bir API test mühendisisin. Servis spesifikasyonlarından kapsamlı test senaryoları üretirsin."},
            {"role": "user", "content": prompt},
        ], temperature=0.3)

        try:
            if "```" in raw:
                raw = re.sub(r"```json|```", "", raw).strip()
            data = json.loads(raw)
            return data if isinstance(data, list) else []
        except Exception as e:
            console.print(f"[red]Servis Test Ayrıştırma Hatası: {e}[/red]")
            return []
