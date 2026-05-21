export type ProvenanceKind = "real" | "simulated" | "fallback" | "stub";
export type ArtifactTarget = "shared" | "playwright" | "maviyaka";
export type ValidationStatus = "pending" | "validated" | "failed" | "not_applicable";

type ProvenanceInput = {
  provenance?: string | null;
  simulated?: boolean | number | null;
  fallback?: boolean | number | null;
  stub?: boolean | number | null;
  mock_mode?: boolean | number | null;
};

function isTruthy(value: unknown): boolean {
  if (typeof value === "string") return value === "true" || value === "1";
  return Boolean(value);
}

export function normalizeProvenance(input?: ProvenanceInput | null): ProvenanceKind {
  const raw = input?.provenance;
  if (raw === "real" || raw === "simulated" || raw === "fallback" || raw === "stub") {
    return raw;
  }
  if (isTruthy(input?.stub)) return "stub";
  if (isTruthy(input?.fallback)) return "fallback";
  if (isTruthy(input?.simulated) || isTruthy(input?.mock_mode)) return "simulated";
  return "real";
}

export function isRealProvenance(provenance: ProvenanceKind): boolean {
  return provenance === "real";
}

export function provenanceLabel(provenance: ProvenanceKind): string {
  switch (provenance) {
    case "real":
      return "Gerçek";
    case "simulated":
      return "Simüle";
    case "fallback":
      return "Fallback";
    case "stub":
      return "Stub";
  }
  return "Gerçek";
}

export function provenanceBadgeClass(provenance: ProvenanceKind): string {
  switch (provenance) {
    case "real":
      return "border-emerald-500/20 bg-emerald-500/10 text-emerald-300";
    case "simulated":
      return "border-amber-500/20 bg-amber-500/10 text-amber-300";
    case "fallback":
      return "border-orange-500/20 bg-orange-500/10 text-orange-300";
    case "stub":
      return "border-slate-500/20 bg-slate-500/10 text-slate-300";
  }
  return "border-emerald-500/20 bg-emerald-500/10 text-emerald-300";
}

export function artifactTargetLabel(target: ArtifactTarget): string {
  switch (target) {
    case "playwright":
      return "Playwright";
    case "maviyaka":
      return "MaviYaka";
    case "shared":
      return "Ortak";
  }
  return "Ortak";
}

export function artifactTargetBadgeClass(target: ArtifactTarget): string {
  switch (target) {
    case "playwright":
      return "border-violet-500/20 bg-violet-500/10 text-violet-300";
    case "maviyaka":
      return "border-sky-500/20 bg-sky-500/10 text-sky-300";
    case "shared":
      return "border-slate-500/20 bg-slate-500/10 text-slate-300";
  }
  return "border-slate-500/20 bg-slate-500/10 text-slate-300";
}

export function validationStatusLabel(status: ValidationStatus): string {
  switch (status) {
    case "validated":
      return "Doğrulandı";
    case "failed":
      return "Doğrulama Hatası";
    case "pending":
      return "Bekliyor";
    case "not_applicable":
      return "Uygulanmaz";
  }
  return "Bekliyor";
}

export function validationStatusBadgeClass(status: ValidationStatus): string {
  switch (status) {
    case "validated":
      return "border-emerald-500/20 bg-emerald-500/10 text-emerald-300";
    case "failed":
      return "border-red-500/20 bg-red-500/10 text-red-300";
    case "pending":
      return "border-amber-500/20 bg-amber-500/10 text-amber-300";
    case "not_applicable":
      return "border-slate-500/20 bg-slate-500/10 text-slate-300";
  }
  return "border-amber-500/20 bg-amber-500/10 text-amber-300";
}
