// ─── @neurex/contracts ──────────────────────────────────────────────────
// Backend OpenAPI spec'inden otomatik üretilen TypeScript tipler.
//
// Yenileme:
//   npm run -w @neurex/contracts generate
//
// Kullanım:
//   import type { LoginRequest, TokenResponse, paths } from "@neurex/contracts";

export type { paths, components, operations } from "./openapi";
export * from "./operations";
