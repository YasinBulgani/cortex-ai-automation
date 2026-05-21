export interface TestResult {
  testId: string;
  testName: string;
  status: 'passed' | 'failed' | 'skipped' | 'flaky';
  duration: number;
  timestamp: Date;
  errorMessage?: string;
  retryCount: number;
}

export interface AnomalyReport {
  type: 'flaky' | 'slow' | 'sudden_failure' | 'pattern_change';
  severity: 'critical' | 'warning' | 'info';
  testId: string;
  description: string;
  evidence: string[];
  suggestedAction: string;
}

export class TestAnomalyDetector {
  private history = new Map<string, TestResult[]>();
  private maxHistory = 100;

  constructor(private windowSize = 20) {}

  addResult(result: TestResult) {
    const list = this.history.get(result.testId) ?? [];
    list.push(result);
    if (list.length > this.maxHistory) list.shift();
    this.history.set(result.testId, list);
  }

  addBatch(results: TestResult[]) {
    for (const r of results) this.addResult(r);
  }

  analyze(): AnomalyReport[] {
    const anomalies: AnomalyReport[] = [];

    for (const [testId, results] of this.history) {
      anomalies.push(
        ...this.detectFlaky(testId, results),
        ...this.detectSlowdown(testId, results),
        ...this.detectSuddenFailure(testId, results),
      );
    }

    const order: Record<string, number> = { critical: 0, warning: 1, info: 2 };
    return anomalies.sort((a, b) => order[a.severity] - order[b.severity]);
  }

  private detectFlaky(testId: string, results: TestResult[]): AnomalyReport[] {
    const recent = results.slice(-this.windowSize);
    if (recent.length < 5) return [];

    const statuses = recent.map(r => r.status);
    let transitions = 0;
    for (let i = 1; i < statuses.length; i++) {
      if (statuses[i] !== statuses[i - 1]) transitions++;
    }

    const score = transitions / (recent.length - 1);
    if (score <= 0.4) return [];

    return [{
      type: 'flaky',
      severity: score > 0.6 ? 'critical' : 'warning',
      testId,
      description: `Son ${this.windowSize} çalıştırmada %${(score * 100).toFixed(0)} tutarsızlık`,
      evidence: [
        `Geçiş: ${transitions}/${recent.length - 1}`,
        `Son 5: ${statuses.slice(-5).join(' → ')}`,
      ],
      suggestedAction: 'Wait koşullarını, veri izolasyonunu ve ortam bağımlılıklarını kontrol edin',
    }];
  }

  private detectSlowdown(testId: string, results: TestResult[]): AnomalyReport[] {
    const passed = results.slice(-this.windowSize).filter(r => r.status === 'passed');
    if (passed.length < 5) return [];

    const durations = passed.map(r => r.duration);
    const avg = durations.reduce((a, b) => a + b, 0) / durations.length;
    const stdDev = Math.sqrt(
      durations.map(d => (d - avg) ** 2).reduce((a, b) => a + b, 0) / durations.length,
    );
    const last = durations.at(-1)!;

    if (last <= avg + 2 * stdDev) return [];

    return [{
      type: 'slow',
      severity: last > avg * 3 ? 'critical' : 'warning',
      testId,
      description: `Süre anormal: ${last}ms (ort: ${avg.toFixed(0)}ms)`,
      evidence: [`Ortalama: ${avg.toFixed(0)}ms`, `StdDev: ${stdDev.toFixed(0)}ms`, `Son: ${last}ms`],
      suggestedAction: 'API latency, DB sorguları ve environment sağlığını kontrol edin',
    }];
  }

  private detectSuddenFailure(testId: string, results: TestResult[]): AnomalyReport[] {
    const recent = results.slice(-5);
    if (recent.length < 3) return [];

    const prevAllPass = recent.slice(0, -1).every(r => r.status === 'passed');
    const lastFailed = recent.at(-1)!.status === 'failed';

    if (!prevAllPass || !lastFailed) return [];

    return [{
      type: 'sudden_failure',
      severity: 'critical',
      testId,
      description: 'Stabil test aniden başarısız oldu',
      evidence: [
        `Hata: ${recent.at(-1)!.errorMessage ?? 'Bilinmiyor'}`,
        `Önceki ${recent.length - 1} çalıştırma başarılıydı`,
      ],
      suggestedAction: 'Son deployment veya kod değişikliğini kontrol edin — muhtemelen gerçek bug',
    }];
  }

  getSummary(): { total: number; flaky: number; slow: number; failures: number } {
    const anomalies = this.analyze();
    return {
      total: anomalies.length,
      flaky: anomalies.filter(a => a.type === 'flaky').length,
      slow: anomalies.filter(a => a.type === 'slow').length,
      failures: anomalies.filter(a => a.type === 'sudden_failure').length,
    };
  }
}
