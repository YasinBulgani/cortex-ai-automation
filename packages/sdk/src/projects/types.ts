/**
 * Core project types (tspm domain).
 */

import type { UUID, ISODateTime } from "../common/types";

export interface Project {
  id: UUID;
  tenant_id: UUID;
  name: string;
  slug: string;
  description?: string | null;
  repo_url?: string | null;
  tech_stack?: string | null;
  created_at: ISODateTime;
  updated_at: ISODateTime;
}

export interface CreateProjectInput {
  name: string;
  slug: string;
  description?: string | null;
  repo_url?: string | null;
  tech_stack?: string | null;
}

export interface ProjectStats {
  total_cases: number;
  active_cases: number;
  pass_rate_pct: number;
  blocked: number;
}
