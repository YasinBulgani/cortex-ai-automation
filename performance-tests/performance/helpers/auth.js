import http from "k6/http";

const BASE = __ENV.API_BASE || "http://127.0.0.1:8765";

export function login(email = "admin@example.com", password = "admin123") {
  const res = http.post(
    `${BASE}/api/v1/auth/login`,
    JSON.stringify({ email, password }),
    { headers: { "Content-Type": "application/json" } }
  );
  if (res.status !== 200) {
    throw new Error(`Login failed: ${res.status}`);
  }
  return res.json("access_token");
}

export function authHeaders(token) {
  return {
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
  };
}

export { BASE };
