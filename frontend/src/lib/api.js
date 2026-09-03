export class ApiError extends Error {
  constructor(message, status, detail) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

export const API_BASE = "";

function buildUrl(path, params) {
  if (!params) return `${API_BASE}${path}`;
  const qs = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== "") {
      qs.set(key, value);
    }
  }
  const q = qs.toString();
  return `${API_BASE}${path}${q ? `?${q}` : ""}`;
}

async function extractDetail(response) {
  const contentType = response.headers.get("content-type") || "";
  let detail = "";
  let body = null;
  try {
    if (contentType.includes("application/json")) {
      body = await response.json();
      const d = body?.detail;
      if (typeof d === "string") detail = d;
      else if (Array.isArray(d)) {
        detail = d
          .map((item) =>
            typeof item === "string" ? item : item?.msg ? `${item.msg}` : JSON.stringify(item)
          )
          .join("; ");
      } else if (d && typeof d === "object") {
        detail = JSON.stringify(d);
      }
    } else {
      detail = await response.text();
    }
  } catch {
    detail = response.statusText;
  }
  return { detail, body };
}

export async function apiFetch(path, { method = "GET", body, token, params, isFormData = false } = {}) {
  const headers = {};
  if (token) headers["Authorization"] = `Bearer ${token}`;
  if (body && !isFormData) headers["Content-Type"] = "application/json";

  let payload;
  if (body && isFormData) {
    payload = body;
  } else if (body !== undefined) {
    payload = JSON.stringify(body);
  }

  const response = await fetch(buildUrl(path, params), {
    method,
    headers,
    body: payload,
  });

  if (!response.ok) {
    const { detail, body: errBody } = await extractDetail(response);
    throw new ApiError(detail || `Request failed with status ${response.status}`, response.status, errBody);
  }

  if (response.status === 204) return null;
  const contentType = response.headers.get("content-type") || "";
  if (contentType.includes("application/json")) return response.json();
  return response;
}

export function streamUrl(path) {
  return `${API_BASE}${path}`;
}