// ── Monkey Test AI Prompt Builders ──────────────────────────────────────────
// Pure functions — no React dependencies. Safe to import in server or client.

type EngineAction = {
  step: number;
  type: string;
  url: string;
  timestamp: string;
  target?: string;
  value?: string;
  result?: string;
  triggered_error?: boolean;
  load_time_ms?: number;
  direction?: string;
  key?: string;
  viewport?: string;
};

type EngineConsoleError = { type: string; text: string; url: string; timestamp: string; category: string };
type EngineNetworkError = { url: string; status: number; page_url: string; timestamp: string; category: string };
type EngineBug = { category: string; severity: string; count: number; sample: string; affected_pages: string[] };
type EngineRecommendation = { priority: string; text: string };

type EngineResult = {
  test_url: string;
  actions_performed: number;
  error_count: number;
  stability_score: number;
  pages_visited_count: number;
  total_time_seconds: number;
  actions_log: EngineAction[];
  console_errors: EngineConsoleError[];
  network_errors: EngineNetworkError[];
  analysis: {
    bugs: EngineBug[];
    recommendations: EngineRecommendation[];
    risk_level: string;
  };
};

// ── Helpers ──────────────────────────────────────────────────────────────────

export function groupActionsIntoFlows(
  actions: EngineAction[],
): { url: string; actions: EngineAction[] }[] {
  if (!actions.length) return [];
  const flows: { url: string; actions: EngineAction[] }[] = [];
  let currentFlow: { url: string; actions: EngineAction[] } = {
    url: actions[0].url,
    actions: [],
  };
  for (const a of actions) {
    if (a.url !== currentFlow.url && currentFlow.actions.length > 0) {
      flows.push(currentFlow);
      currentFlow = { url: a.url, actions: [] };
    }
    currentFlow.actions.push(a);
  }
  if (currentFlow.actions.length > 0) flows.push(currentFlow);
  return flows;
}

// ── Prompt Builders ──────────────────────────────────────────────────────────

export function buildDetailedAnalysisPrompt(res: EngineResult): string {
  const flows = groupActionsIntoFlows(res.actions_log);

  const flowSummary = flows
    .slice(0, 12)
    .map((f, i) => {
      const actLines = f.actions
        .slice(0, 15)
        .map((a) => {
          const target = a.target ?? a.value ?? a.key ?? a.direction ?? a.viewport ?? "";
          const result = a.result ?? "ok";
          const err = a.triggered_error ? " ⚡HATA" : "";
          return `  ${a.step}. [${a.type}] ${target.slice(0, 60)} → ${result.slice(0, 80)}${err}`;
        })
        .join("\n");
      const more =
        f.actions.length > 15 ? `  ... +${f.actions.length - 15} eylem daha` : "";
      return `── Akış ${i + 1}: ${f.url}\n${actLines}${more ? "\n" + more : ""}`;
    })
    .join("\n\n");

  const bugLines = res.analysis.bugs
    .slice(0, 8)
    .map((b) => `- [${b.severity.toUpperCase()}] ${b.category} × ${b.count}: ${b.sample}`)
    .join("\n");

  const consoleLines = res.console_errors
    .slice(0, 6)
    .map((c) => `- ${c.category}: ${c.text.slice(0, 120)}`)
    .join("\n");

  const netLines = res.network_errors
    .slice(0, 6)
    .map((n) => `- HTTP ${n.status} ${n.category}: ${n.url.slice(0, 100)}`)
    .join("\n");

  return `Sen kıdemli bir QA mühendisisin. Aşağıda bir Monkey Test oturumunun tam verisi var.
Bu oturumda uygulamada denenen her kullanıcı senaryosunu detaylıca belgele.

═══ OTURUM ÖZETİ ═══
URL: ${res.test_url}
Süre: ${res.total_time_seconds}s | Eylem: ${res.actions_performed} | Hata: ${res.error_count}
Stabilite: %${res.stability_score} | Risk: ${res.analysis.risk_level}
Ziyaret edilen sayfa: ${res.pages_visited_count}

═══ EYLEM AKIŞLARI ═══
${flowSummary}

═══ BUG TESPİTLERİ ═══
${bugLines || "Tespit edilen bug yok"}

═══ CONSOLE HATALARI ═══
${consoleLines || "Yok"}

═══ NETWORK HATALARI ═══
${netLines || "Yok"}

═══ ENGINE ANALİZİ ═══
${res.analysis.recommendations.slice(0, 5).map((r) => `- [${r.priority}] ${r.text}`).join("\n") || "Öneri yok"}

───────────────────────────────────────────────────────────
GÖREV:
Yukarıdaki monkey test verisinden hareketle, oturumda denenen TÜM kullanıcı akışlarını ve senaryolarını ayrıntılı olarak belgele.

Her senaryo için MUTLAKA şu formatı kullan:

### Senaryo N: [Kısa açıklayıcı başlık]
**Sayfa / Özellik**: [URL veya özellik adı]
**Amaç**: [Bu akışın ne test ettiği]
**Adımlar**:
1. [Yapılan eylem ve hedef eleman]
2. ...
**Gözlemlenen Davranış**: [Ne oldu, nasıl tepki verdi]
**Durum**: ✅ Başarılı / ❌ Hata Tespit Edildi / ⚠️ Anormal Davranış
**Önem Derecesi**: Kritik / Yüksek / Orta / Düşük
**Otomasyon Önerisi**: [Bu senaryoyu nasıl otomatize ederiz]

─
Kurallar:
- Sadece GERÇEKTEN GERÇEKLEŞTİRİLEN eylemleri belgele (uydurmak yasak)
- Her sayfa/özellik için en az 1 senaryo üret
- Bug tespit edildiyse o senaryo ayrı bir başlık altında detaylandır
- Türkçe yaz; teknik terimler İngilizce kalabilir
- Minimum 5, maksimum 15 senaryo üret
- Sadece senaryoları yaz, giriş/kapanış metni ekleme`;
}

export function buildScenariosPromptFromEngine(res: EngineResult): string {
  const bugLines = res.analysis.bugs
    .slice(0, 10)
    .map((b) => `- [${b.severity}] ${b.category} (${b.count}x): ${b.sample}`)
    .join("\n");

  const consoleLines = res.console_errors
    .slice(0, 6)
    .map((c) => `- ${c.category}: ${c.text}`)
    .join("\n");

  const netLines = res.network_errors
    .slice(0, 6)
    .map((n) => `- ${n.status} ${n.category}: ${n.url}`)
    .join("\n");

  return `Canlı Tarayıcı Monkey Test Sonuçları
Hedef: ${res.test_url}
Eylem: ${res.actions_performed} | Hata: ${res.error_count} | Stabilite: %${res.stability_score}
Sayfalar: ${res.pages_visited_count} | Süre: ${res.total_time_seconds}s

== BUG ÖZETİ ==
${bugLines || "Bug yok"}

== CONSOLE HATALARI ==
${consoleLines || "Yok"}

== NETWORK HATALARI ==
${netLines || "Yok"}

---
Yukarıdaki gerçek tarayıcı monkey test sonuçlarına dayanarak en az 5 kapsamlı test senaryosu üret.
Her bug için en az bir test senaryosu yaz; bug yoksa pozitif, negatif, sınır değer, edge case ve güvenlik senaryoları üret.

ÇIKTI KESİNLİKLE MARKDOWN TABLO FORMATINDA OLMALI. JSON, kod bloğu, açıklama YASAK.

Tam olarak şu format:

| Test ID | Alan | Açıklama | Ön Koşul | Adımlar | Beklenen Sonuç | Öncelik |
|---------|------|----------|----------|---------|----------------|---------|
| TC_MT_001 | Login | Geçerli kullanıcı girişi | Kullanıcı kayıtlı | 1. Login sayfası aç<br>2. Kullanıcı adı gir<br>3. Şifre gir<br>4. Gönder | Ana sayfaya yönlendirilir | high |

Türkçe yaz. Test ID: TC_MT_001..TC_MT_NNN. Önceliği: critical / high / medium / low.
SADECE TABLO YAZ, BAŞKA HİÇBİR ŞEY YAZMA.`;
}

export function buildKaratePrompt(scenariosText: string, targetUrl: string): string {
  const url = targetUrl || "https://cortex-test.bgtsai.com";
  return `Aşağıdaki test senaryolarından Karate DSL feature dosyası üret.
Hedef URL: ${url}

Test Senaryoları:
${scenariosText}

---
ÇIKTI KESİNLİKLE GHERKIN BDD FORMATINDA KARATE DSL FEATURE DOSYASI OLMALI.
JSON, açıklama metin, markdown ek YASAK. Sadece .feature içeriği.

Yapı:

Feature: MonkeyTest - Otomatik Senaryolar

Background:
  * url '${url}'
  * configure driver = { type: 'chrome', headless: true }

Scenario: <senaryo başlığı>
  Given driver '${url}'
  When driver.click('<selector>')
  And input('<selector>', '<value>')
  Then match driver.title == '<expected>'

Kurallar:
- Her senaryo için ayrı Scenario bloğu (Scenario Outline yok)
- BDD: Given / When / Then / And anahtar kelimeleri zorunlu
- Sadece UI komutları: driver.get, driver.click, input, match driver.title, match driver.location
- Türkçe scenario başlıkları, İngilizce Karate komutları
- En az 3 Scenario yaz.

SADECE .feature içeriğini yaz, başka metin yok.`;
}
