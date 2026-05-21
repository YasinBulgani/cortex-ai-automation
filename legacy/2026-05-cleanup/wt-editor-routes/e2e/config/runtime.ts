const DEFAULT_API_BASE = "http://127.0.0.1:8875";

export const API_BASE = (process.env.API_BASE || DEFAULT_API_BASE).replace(/\/$/, "");
