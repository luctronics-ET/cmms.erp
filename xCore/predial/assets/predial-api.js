const API_BASE = window.PREDIAL_API_BASE || "http://127.0.0.1:8002";

async function http(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const payload = await response.json();
      detail = payload.detail || detail;
    } catch (_) {
      // Keep fallback status text.
    }
    throw new Error(detail);
  }
  if (response.status === 204) return null;
  return response.json();
}

const predialAPI = {
  health: () => http("/health"),
  listUsuarios: () => http("/api/v1/usuarios"),
  listLocais: () => http("/api/v1/locais"),
  createLocal: (payload) => http("/api/v1/locais", { method: "POST", body: JSON.stringify(payload) }),
  listTemplates: (tipoLocal) => http(`/api/v1/templates${tipoLocal ? `?tipo_local=${encodeURIComponent(tipoLocal)}` : ""}`),
  listInspecoes: (params = {}) => {
    const query = new URLSearchParams();
    if (params.status) query.set("status", params.status);
    if (params.local_id) query.set("local_id", params.local_id);
    const suffix = query.toString() ? `?${query}` : "";
    return http(`/api/v1/inspecoes${suffix}`);
  },
  createInspecao: (payload) => http("/api/v1/inspecoes", { method: "POST", body: JSON.stringify(payload) }),
  getInspecao: (id) => http(`/api/v1/inspecoes/${id}`),
  upsertItem: (id, payload) => http(`/api/v1/inspecoes/${id}/itens`, { method: "PUT", body: JSON.stringify(payload) }),
  transition: (id, payload) => http(`/api/v1/inspecoes/${id}/status`, { method: "PUT", body: JSON.stringify(payload) }),
  historico: (params = {}) => {
    const query = new URLSearchParams();
    if (params.status) query.set("status", params.status);
    if (params.local_id) query.set("local_id", params.local_id);
    const suffix = query.toString() ? `?${query}` : "";
    return http(`/api/v1/historico${suffix}`);
  },
  resumo: () => http("/api/v1/relatorio/resumo"),
  listNormas: () => http("/api/v1/normas"),
  createNorma: (payload) => http("/api/v1/normas", { method: "POST", body: JSON.stringify(payload) }),
  listLaudos: (localId) => http(`/api/v1/laudos${localId ? `?local_id=${localId}` : ""}`),
  createLaudo: (payload) => http("/api/v1/laudos", { method: "POST", body: JSON.stringify(payload) }),
};
