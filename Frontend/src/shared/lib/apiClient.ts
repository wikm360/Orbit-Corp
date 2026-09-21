import type { TokenResponse } from "@/features/auth/types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export const AUTH_UNAUTHORIZED_EVENT = "auth:unauthorized";
export const AUTH_REFRESHED_EVENT = "auth:refreshed";

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

function storedToken(key: string): string | null {
  return typeof window === "undefined" ? null : localStorage.getItem(key);
}

export async function parseErrorMessage(response: Response): Promise<string> {
  try {
    const body = await response.json();
    if (typeof body.detail === "string") return body.detail;
    if (Array.isArray(body.detail)) return body.detail.map((item: { msg?: string }) => item.msg ?? "").filter(Boolean).join("؛ ");
  } catch {
    // The response has no JSON error body.
  }
  return response.statusText;
}

export function notifyUnauthorized(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem("auth_token");
  localStorage.removeItem("refresh_token");
  window.dispatchEvent(new Event(AUTH_UNAUTHORIZED_EVENT));
}

let refreshInFlight: Promise<TokenResponse | null> | null = null;

async function refreshSession(): Promise<TokenResponse | null> {
  if (refreshInFlight) return refreshInFlight;
  const refreshToken = storedToken("refresh_token");
  if (!refreshToken) return null;
  refreshInFlight = (async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
      if (!response.ok) return null;
      const session = (await response.json()) as TokenResponse;
      if (storedToken("refresh_token") !== refreshToken) return null;
      localStorage.setItem("auth_token", session.access_token);
      localStorage.setItem("refresh_token", session.refresh_token);
      window.dispatchEvent(new CustomEvent(AUTH_REFRESHED_EVENT, { detail: session }));
      return session;
    } catch {
      return null;
    }
  })();
  try {
    return await refreshInFlight;
  } finally {
    refreshInFlight = null;
  }
}

export async function revokeSession(): Promise<void> {
  const refreshToken = storedToken("refresh_token");
  if (!refreshToken) return;
  try {
    await fetch(`${API_BASE_URL}/auth/logout`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
  } catch {
    // Local sign-out still proceeds if the server is unavailable.
  }
}

export async function authorizedFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const makeRequest = (token: string | null) => {
    const headers = new Headers(init.headers);
    if (token) headers.set("Authorization", `Bearer ${token}`);
    return fetch(`${API_BASE_URL}${path}`, { ...init, headers });
  };
  const initialToken = storedToken("auth_token");
  let response = await makeRequest(initialToken);
  if (response.status === 401 && !["/auth/login", "/auth/register", "/auth/refresh", "/auth/logout"].includes(path)) {
    const currentToken = storedToken("auth_token");
    if (currentToken && currentToken !== initialToken) response = await makeRequest(currentToken);
    else {
      const session = await refreshSession();
      if (session) response = await makeRequest(session.access_token);
    }
    if (response.status === 401) notifyUnauthorized();
  }
  return response;
}

interface RequestOptions {
  method?: string;
  body?: unknown;
  formData?: FormData;
  headers?: Record<string, string>;
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers: Record<string, string> = { ...options.headers };
  let body: BodyInit | undefined;
  if (options.formData) body = options.formData;
  else if (options.body !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(options.body);
  }
  const response = await authorizedFetch(path, { method: options.method ?? "GET", headers, body });
  if (!response.ok) throw new ApiError(response.status, await parseErrorMessage(response));
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export { API_BASE_URL };
