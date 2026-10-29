"use client";

/** Cliente para el navegador: habla con /api/v1 (mismo origen) y envía el token CSRF en las escrituras. */

let csrf: string | null = null;

export function resetCsrf() {
  csrf = null;
}

async function csrfToken(): Promise<string> {
  if (!csrf) {
    const res = await fetch("/api/v1/auth/csrf/", { credentials: "same-origin" });
    csrf = ((await res.json()) as { csrfToken: string }).csrfToken;
  }
  return csrf;
}

export class ApiError extends Error {
  constructor(
    public status: number,
    public data: Record<string, unknown>,
  ) {
    super(messageFrom(data) || `Error ${status}`);
  }
}

/** Extrae un mensaje legible de las respuestas de error de DRF. */
export function messageFrom(data: unknown): string {
  if (!data || typeof data !== "object") return "";
  const d = data as Record<string, unknown>;
  if (typeof d.detail === "string") return d.detail;
  const parts: string[] = [];
  for (const [key, value] of Object.entries(d)) {
    const text = Array.isArray(value) ? value.join(" ") : typeof value === "string" ? value : "";
    if (text) parts.push(key === "non_field_errors" ? text : text);
  }
  return parts.join(" ");
}

export async function api<T = unknown>(path: string, init: { method?: string; json?: unknown; form?: FormData } = {}): Promise<T> {
  const method = init.method ?? (init.json || init.form ? "POST" : "GET");
  const headers: Record<string, string> = {};
  let body: BodyInit | undefined;
  if (method !== "GET") headers["X-CSRFToken"] = await csrfToken();
  if (init.json !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(init.json);
  } else if (init.form) {
    body = init.form;
  }
  const res = await fetch(`/api/v1${path}`, { method, headers, body, credentials: "same-origin", cache: "no-store" });
  if (res.status === 204) return undefined as T;
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new ApiError(res.status, data);
  return data as T;
}
