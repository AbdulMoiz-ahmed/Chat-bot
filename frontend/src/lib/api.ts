import { getToken, clearAuth } from "./auth";

const isBrowser = typeof window !== "undefined";

export const API_BASE = isBrowser && window.location.hostname.includes("codexiasolutions.it.com")
  ? "https://app.chatbot.codexiasolutions.it.com/api/v1"
  : "http://127.0.0.1:8000/api/v1";

export const WS_BASE = isBrowser && window.location.hostname.includes("codexiasolutions.it.com")
  ? "wss://app.chatbot.codexiasolutions.it.com/api/v1/portal/ws"
  : "ws://127.0.0.1:8000/api/v1/portal/ws";

export const apiFetch = async (endpoint: string, options: RequestInit = {}) => {
  const token = getToken();
  const headers = new Headers(options.headers || {});

  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  if (!headers.has("Content-Type") && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  const url = endpoint.startsWith("http") ? endpoint : `${API_BASE}${endpoint}`;

  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (response.status === 401) {
    clearAuth();
    if (typeof window !== "undefined" && window.location.pathname !== "/login") {
      window.location.href = "/login";
    }
  }

  return response;
};
