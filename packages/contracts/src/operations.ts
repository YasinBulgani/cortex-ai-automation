/**
 * Operations — OpenAPI path & schema'lardan extracted utility types.
 *
 * Kullanım:
 *   import type { Project, Scenario, LoginRequest } from "@neurex/contracts";
 *   import type { paths } from "@neurex/contracts";
 */

import type { components, paths } from "./openapi";

// ─── Schema aliases (sık kullanılan tipler) ──────────────────────────────
type S = components["schemas"];

// Auth
export type LoginRequest    = S["LoginRequest"];
export type TokenResponse   = S["TokenResponse"];
export type UserMeResponse  = S["UserMeResponse"];
export type RegisterRequest = S["RegisterRequest"];
export type RefreshRequest  = S["RefreshRequest"];

// Project — en sık kullanılan
export type ProjectOut       = S["ProjectOut"] extends never ? unknown : S["ProjectOut"];
export type ProjectCreate    = S["ProjectCreate"] extends never ? unknown : S["ProjectCreate"];

// ─── Path helpers ─────────────────────────────────────────────────────────
// Sık erişilen endpoint'lere TypeScript helper'ları
export type Paths       = paths;
export type Schemas     = components["schemas"];

// Bir endpoint'in response shape'ini almak için yardımcı:
export type GetResponse<P extends keyof paths, M extends keyof paths[P]> =
  paths[P][M] extends { responses: { 200: { content: { "application/json": infer R } } } }
    ? R
    : never;

// Örnek kullanım:
//   type Projects = GetResponse<"/api/v1/tspm/projects", "get">;
