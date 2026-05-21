const DEFAULT_ADMIN_EMAIL = "admin@example.com";
const DEFAULT_ADMIN_PASSWORD = "admin123";

export const ADMIN_EMAIL =
  process.env.E2E_ADMIN_EMAIL ||
  process.env.ADMIN_EMAIL ||
  DEFAULT_ADMIN_EMAIL;

export const ADMIN_PASSWORD =
  process.env.E2E_ADMIN_PASSWORD ||
  process.env.ADMIN_PASSWORD ||
  DEFAULT_ADMIN_PASSWORD;

export function getAdminCredentials() {
  return { email: ADMIN_EMAIL, password: ADMIN_PASSWORD };
}
