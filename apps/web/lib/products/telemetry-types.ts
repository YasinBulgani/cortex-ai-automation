export interface ProductLiveStat {
  key: string;
  label: string;
  value: string | number;
  unit?: string;
  delta?: number;
  deltaLabel?: string;
  trend: "up" | "down" | "stable";
  target?: number;
  sparkline: number[];
  severity?: "ok" | "warn" | "critical";
}

export interface AiInsight {
  id: string;
  title: string;
  description: string;
  severity: "info" | "warning" | "critical" | "success";
  category: string;
  ctaLabel?: string;
  ctaHref?: string;
  createdAt: string;
  confidence?: number;
  dismissed?: boolean;
}

export interface ActivityEvent {
  id: string;
  ts: string;
  actor: string;
  actorAvatar?: string;
  verb: string;
  object: string;
  objectName: string;
  href?: string;
  meta?: string;
}

export interface BrowserStat {
  name: string;
  icon: string;
  version: string;
  passRate: number;
  runs: number;
  status: "passing" | "warning" | "failing";
}

export interface OnboardingStep {
  id: string;
  title: string;
  description: string;
  done: boolean;
  href?: string;
  ctaLabel: string;
}

export interface ProductTelemetry {
  productId: string;
  stats: ProductLiveStat[];
  aiInsights: AiInsight[];
  recentActivity: ActivityEvent[];
  onboarding: OnboardingStep[];
  browsers?: BrowserStat[];
  lastUpdated: string;
  isDemo?: boolean;
}
