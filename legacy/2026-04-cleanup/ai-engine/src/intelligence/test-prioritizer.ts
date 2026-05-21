import { execSync } from 'node:child_process';

export interface TestPriority {
  testFile: string;
  priority: number;
  reason: string;
  riskLevel: 'critical' | 'high' | 'medium' | 'low';
  estimatedDuration: number;
}

export interface ChangeImpact {
  changedFiles: string[];
  impactedModules: string[];
  impactedTests: TestPriority[];
}

export class AITestPrioritizer {
  private testCodeMap: Map<string, string[]>;
  private historicalData: Map<string, { failRate: number; avgDuration: number }>;

  constructor(
    testCodeMap?: Map<string, string[]>,
    historicalData?: Map<string, { failRate: number; avgDuration: number }>,
  ) {
    this.testCodeMap = testCodeMap ?? new Map();
    this.historicalData = historicalData ?? new Map();
  }

  analyzeChanges(baseBranch = 'main'): ChangeImpact {
    const raw = execSync(`git diff ${baseBranch}...HEAD --name-only`, { encoding: 'utf-8' });
    const changedFiles = raw.trim().split('\n').filter(Boolean);

    const impactedModules = this.extractModules(changedFiles);
    const impactedTests = this.prioritize(changedFiles, impactedModules);

    return { changedFiles, impactedModules, impactedTests };
  }

  selectForCI(impact: ChangeImpact, maxDuration = 300): string[] {
    let total = 0;
    const selected: string[] = [];

    for (const t of impact.impactedTests) {
      if (t.riskLevel === 'critical' || total + t.estimatedDuration <= maxDuration) {
        selected.push(t.testFile);
        total += t.estimatedDuration;
      }
    }

    return selected;
  }

  private prioritize(changedFiles: string[], modules: string[]): TestPriority[] {
    const tests: TestPriority[] = [];

    for (const [testFile, sources] of this.testCodeMap) {
      const directHit = sources.some(s => changedFiles.includes(s));
      const moduleHit = modules.some(m => testFile.includes(m));
      if (!directHit && !moduleHit) continue;

      const hist = this.historicalData.get(testFile);
      let score = 0;
      const reasons: string[] = [];

      if (directHit) { score += 50; reasons.push('Kaynak dosya değişti'); }
      if (moduleHit) { score += 30; reasons.push('Modül etkilendi'); }
      if (hist && hist.failRate > 0.1) {
        score += 20;
        reasons.push(`Fail oranı %${(hist.failRate * 100).toFixed(0)}`);
      }

      tests.push({
        testFile,
        priority: Math.min(score, 100),
        reason: reasons.join('. '),
        riskLevel: score >= 80 ? 'critical' : score >= 50 ? 'high' : score >= 30 ? 'medium' : 'low',
        estimatedDuration: hist?.avgDuration ?? 30,
      });
    }

    return tests.sort((a, b) => b.priority - a.priority);
  }

  private extractModules(files: string[]): string[] {
    const modules = new Set<string>();
    for (const f of files) {
      const parts = f.split('/');
      if (parts.length >= 2) modules.add(parts.slice(0, 2).join('/'));
    }
    return [...modules];
  }
}
