import { AITestPrioritizer, type ChangeImpact } from '../intelligence/test-prioritizer.js';
import { TestAnomalyDetector, type AnomalyReport } from '../intelligence/anomaly-detector.js';

export interface CIRunConfig {
  baseBranch: string;
  maxDuration: number;
  shardCount: number;
  healingEnabled: boolean;
  anomalyCheckEnabled: boolean;
}

export interface CIRunPlan {
  selectedTests: string[];
  shardAssignments: Map<number, string[]>;
  estimatedDuration: number;
  riskSummary: { critical: number; high: number; medium: number; low: number };
  anomalies: AnomalyReport[];
}

const DEFAULT_CI: CIRunConfig = {
  baseBranch: 'main',
  maxDuration: 600,
  shardCount: 4,
  healingEnabled: true,
  anomalyCheckEnabled: true,
};

export class CIIntegrator {
  private prioritizer: AITestPrioritizer;
  private anomalyDetector: TestAnomalyDetector;

  constructor(
    prioritizer?: AITestPrioritizer,
    anomalyDetector?: TestAnomalyDetector,
  ) {
    this.prioritizer = prioritizer ?? new AITestPrioritizer();
    this.anomalyDetector = anomalyDetector ?? new TestAnomalyDetector();
  }

  plan(config: Partial<CIRunConfig> = {}): CIRunPlan {
    const cfg = { ...DEFAULT_CI, ...config };

    const impact = this.prioritizer.analyzeChanges(cfg.baseBranch);
    const selected = this.prioritizer.selectForCI(impact, cfg.maxDuration);
    const anomalies = cfg.anomalyCheckEnabled ? this.anomalyDetector.analyze() : [];

    const shards = this.assignShards(selected, cfg.shardCount);
    const risk = this.summarizeRisk(impact);

    const estimated = Math.max(
      ...Array.from(shards.values()).map(tests =>
        tests.reduce((sum, t) => {
          const test = impact.impactedTests.find(it => it.testFile === t);
          return sum + (test?.estimatedDuration ?? 30);
        }, 0),
      ),
    );

    return {
      selectedTests: selected,
      shardAssignments: shards,
      estimatedDuration: estimated,
      riskSummary: risk,
      anomalies,
    };
  }

  private assignShards(tests: string[], count: number): Map<number, string[]> {
    const shards = new Map<number, string[]>();
    for (let i = 0; i < count; i++) shards.set(i, []);

    tests.forEach((test, idx) => {
      shards.get(idx % count)!.push(test);
    });

    return shards;
  }

  private summarizeRisk(impact: ChangeImpact) {
    const counts = { critical: 0, high: 0, medium: 0, low: 0 };
    for (const t of impact.impactedTests) counts[t.riskLevel]++;
    return counts;
  }

  generateMarkdownReport(plan: CIRunPlan): string {
    const lines = [
      '# AI Test Seçim Raporu',
      '',
      `**Seçilen test sayısı:** ${plan.selectedTests.length}`,
      `**Tahmini süre:** ${plan.estimatedDuration}s`,
      `**Shard sayısı:** ${plan.shardAssignments.size}`,
      '',
      '## Risk Özeti',
      `- 🔴 Critical: ${plan.riskSummary.critical}`,
      `- 🟠 High: ${plan.riskSummary.high}`,
      `- 🟡 Medium: ${plan.riskSummary.medium}`,
      `- 🟢 Low: ${plan.riskSummary.low}`,
      '',
    ];

    if (plan.anomalies.length > 0) {
      lines.push('## Anomaliler', '');
      for (const a of plan.anomalies) {
        lines.push(`- **[${a.severity}]** ${a.testId}: ${a.description}`);
      }
      lines.push('');
    }

    lines.push('## Shard Dağılımı', '');
    for (const [shard, tests] of plan.shardAssignments) {
      lines.push(`### Shard ${shard + 1}`);
      for (const t of tests) lines.push(`- ${t}`);
      lines.push('');
    }

    return lines.join('\n');
  }
}
