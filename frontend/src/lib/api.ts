/**
 * OTT Content Aggregator - Frontend API Client Foundation
 *
 * Provides a configurable backend API base URL, reusable request helpers,
 * typed error handling, and support for JSON and FormData payloads.
 */

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export class ApiError extends Error {
  public readonly status: number;
  public readonly data: unknown;

  constructor(status: number, message: string, data?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.data = data;
  }
}

export interface RequestOptions extends Omit<RequestInit, "body"> {
  body?: unknown;
  params?: Record<string, string | number | boolean | undefined | null>;
  token?: string | null;
  timeoutMs?: number;
}

/**
 * Build URL with query parameters safely.
 */
function buildUrl(
  path: string,
  params?: Record<string, string | number | boolean | undefined | null>
): string {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  const url = new URL(`${API_BASE_URL}${normalizedPath}`);

  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        url.searchParams.append(key, String(value));
      }
    });
  }

  return url.toString();
}

/**
 * Reusable API request helper with sensible defaults and typed error handling.
 */
export async function apiRequest<T>(
  endpoint: string,
  options: RequestOptions = {}
): Promise<T> {
  const { body, params, token, headers = {}, ...customConfig } = options;

  const url = buildUrl(endpoint, params);

  const requestHeaders: Record<string, string> = {
    Accept: "application/json",
    ...(headers as Record<string, string>),
  };

  if (token) {
    requestHeaders.Authorization = `Bearer ${token}`;
  }

  let requestBody: BodyInit | undefined = undefined;

  if (body !== undefined && body !== null) {
    if (body instanceof FormData) {
      requestBody = body;
      // When body is FormData, browser sets multipart/form-data with proper boundary
    } else if (body instanceof URLSearchParams) {
      requestHeaders["Content-Type"] = "application/x-www-form-urlencoded";
      requestBody = body.toString();
    } else if (typeof body === "string") {
      requestBody = body;
      if (!requestHeaders["Content-Type"]) {
        requestHeaders["Content-Type"] = "text/plain";
      }
    } else {
      if (!requestHeaders["Content-Type"]) {
        requestHeaders["Content-Type"] = "application/json";
      }
      requestBody = JSON.stringify(body);
    }
  }

  const timeoutMs = options.timeoutMs ?? 10000;
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  let response: Response;
  try {
    response = await fetch(url, {
      ...customConfig,
      signal: customConfig.signal || controller.signal,
      headers: requestHeaders,
      body: requestBody,
    });
  } finally {
    clearTimeout(timeoutId);
  }

  if (!response.ok) {
    let errorDetail = `Request failed with status ${response.status}`;
    let errorData: unknown = null;

    try {
      errorData = await response.json();
      if (
        errorData &&
        typeof errorData === "object" &&
        "detail" in errorData
      ) {
        const detail = (errorData as { detail: unknown }).detail;
        if (typeof detail === "string") {
          errorDetail = detail;
        } else if (Array.isArray(detail)) {
          errorDetail = detail
            .map((item) => (typeof item === "object" && item && "msg" in item ? String(item.msg) : JSON.stringify(item)))
            .join(", ");
        }
      }
    } catch {
      try {
        const text = await response.text();
        if (text) errorDetail = text;
      } catch {
        // Fall back to default errorDetail
      }
    }

    throw new ApiError(response.status, errorDetail, errorData);
  }

  if (response.status === 204) {
    return null as T;
  }

  return response.json() as Promise<T>;
}

export const api = {
  get: <T>(endpoint: string, options?: RequestOptions) =>
    apiRequest<T>(endpoint, { ...options, method: "GET" }),

  post: <T>(endpoint: string, body?: unknown, options?: RequestOptions) =>
    apiRequest<T>(endpoint, { ...options, method: "POST", body }),

  put: <T>(endpoint: string, body?: unknown, options?: RequestOptions) =>
    apiRequest<T>(endpoint, { ...options, method: "PUT", body }),

  patch: <T>(endpoint: string, body?: unknown, options?: RequestOptions) =>
    apiRequest<T>(endpoint, { ...options, method: "PATCH", body }),

  delete: <T>(endpoint: string, options?: RequestOptions) =>
    apiRequest<T>(endpoint, { ...options, method: "DELETE" }),

  getBaseUrl: () => API_BASE_URL,
};

