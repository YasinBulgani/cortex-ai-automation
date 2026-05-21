"""
PageInspector - Sayfa DOM analizi
Playwright page üzerinden interaktif elementleri, formları, linkleri analiz eder
ve AI motoruna zengin bağlam sağlar.
"""
from playwright.sync_api import Page


class PageInspector:
    """Sayfa yapısını analiz eder ve AI için özet çıkarır."""

    def __init__(self, page: Page):
        self.page = page

    def get_page_summary(self) -> dict:
        """
        Sayfanın başlık, meta, butonlar, linkler, form alanları gibi
        temel bilgilerini döndürür.
        """
        return {
            "url": self.page.url,
            "title": self._get_title(),
            "heading": self._get_headings(),
            "buttons": self._get_buttons(),
            "links": self._get_links(),
            "inputs": self._get_inputs(),
            "text_sample": self._get_text_sample(),
        }

    def get_summary_text(self) -> str:
        """AI sistem mesajına eklenecek metin formatında özet."""
        data = self.get_page_summary()
        lines = [
            f"Sayfa URL: {data['url']}",
            f"Başlık: {data['title']}",
            f"H1/H2 başlıklar: {', '.join(data['heading'][:5]) or 'yok'}",
            f"Butonlar: {', '.join(data['buttons'][:10]) or 'yok'}",
            f"Linkler: {', '.join(data['links'][:10]) or 'yok'}",
            f"Input alanları: {', '.join(data['inputs'][:10]) or 'yok'}",
            f"Sayfa metni (ilk 500 karakter): {data['text_sample'][:500]}",
        ]
        return "\n".join(lines)

    # ── Özel Toplayıcılar ──────────────────────────────────────────────────────
    def _get_title(self) -> str:
        try:
            return self.page.title()
        except Exception:
            return ""

    def _get_headings(self) -> list[str]:
        try:
            return self.page.eval_on_selector_all(
                "h1, h2, h3",
                "els => els.map(e => e.innerText.trim()).filter(t => t.length > 0)",
            )
        except Exception:
            return []

    # ── XPath JS Yardımcısı ────────────────────────────────────────────────────
    _xpath_js = """
    (e) => {
        if (e.id) return '#' + e.id;
        if (e.name) return e.tagName.toLowerCase() + '[name="' + e.name + '"]';
        
        // CSS Path oluşturma
        var path = [];
        var node = e;
        while (node && node.nodeType === Node.ELEMENT_NODE) {
            var selector = node.nodeName.toLowerCase();
            if (node.id) {
                selector += '#' + node.id;
                path.unshift(selector);
                break;
            } else {
                var sib = node, nth = 1;
                while (sib = sib.previousElementSibling) {
                    if (sib.nodeName.toLowerCase() == selector) nth++;
                }
                if (nth != 1) selector += ":nth-of-type("+nth+")";
            }
            path.unshift(selector);
            node = node.parentNode;
        }
        return path.join(' > ');
    }
    """

    def _get_buttons(self) -> list[str]:
        try:
            return self.page.eval_on_selector_all(
                "button, [role='button'], input[type='submit'], input[type='button'], a.btn, a[role='button']",
                f"""els => els.map(e => {{
                    const text = (e.innerText || e.value || e.getAttribute('aria-label') || '').trim();
                    const getPath = {_xpath_js};
                    const path = getPath(e);
                    return text.length > 0 ? text + " => XPath: " + path : "";
                }}).filter(t => t.length > 0)"""
            )
        except Exception:
            return []

    def _get_links(self) -> list[str]:
        try:
            return self.page.eval_on_selector_all(
                "a[href]:not([role='button'])",
                f"""els => els.map(e => {{
                    const text = e.innerText.trim();
                    const getPath = {_xpath_js};
                    const path = getPath(e);
                    return (text.length > 0 && text.length < 60) ? text + " => XPath: " + path : "";
                }}).filter(t => t.length > 0)"""
            )
        except Exception:
            return []

    def _get_inputs(self) -> list[str]:
        try:
            return self.page.eval_on_selector_all(
                "input:not([type='hidden']):not([type='submit']):not([type='button']), textarea, select",
                f"""els => els.map(e => {{
                    const label = e.getAttribute('placeholder') || e.getAttribute('name') ||
                                  e.getAttribute('id') || e.getAttribute('aria-label') || e.tagName;
                    const getPath = {_xpath_js};
                    const path = getPath(e);
                    return label.trim().length > 0 ? label.trim() + " => XPath: " + path : "";
                }}).filter(t => t.length > 0)"""
            )
        except Exception:
            return []

    def _get_text_sample(self) -> str:
        try:
            return self.page.evaluate("() => document.body.innerText") or ""
        except Exception:
            return ""
