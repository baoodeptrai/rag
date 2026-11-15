import { getApiBaseUrl } from "./chatService";

async function adminRequest(path, token, options = {}) {
  const response = await fetch(`${getApiBaseUrl()}${path}`, {
    ...options,
    headers: {
      ...(options.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
      Authorization: `Bearer ${token}`,
      ...options.headers,
    },
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const message = payload.detail || payload.message || `Lỗi HTTP ${response.status}`;
    throw new Error(message);
  }
  return payload;
}

export function getAdminDocuments(token) {
  return adminRequest("/api/admin/documents", token);
}

export function uploadAdminDocument(token, formData) {
  return adminRequest("/api/admin/upload", token, { method: "POST", body: formData });
}

export function reindexAdminDocuments(token) {
  return adminRequest("/api/admin/reindex", token, { method: "POST" });
}

export function deleteAdminDocument(token, fileName) {
  const body = new FormData();
  body.append("file_name", fileName);
  return adminRequest("/api/admin/documents/delete", token, { method: "POST", body });
}
