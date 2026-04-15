import axios, { AxiosError, AxiosRequestConfig } from "axios";
import { orchestrator } from "../middleware/AIOrchestrator";

const CLIENT_CACHE_VERSION_KEY = "engcad_client_cache_version";
const CLIENT_CACHE_VERSION = "2026-04-07-api-unified";

const normalizeBaseUrl = (value: string): string => value.replace(/\/$/, "");

// Resolução única de base URL por ambiente.
const getDefaultApiBase = (): string => {
  if (typeof window === "undefined") {
    return "http://localhost:8000";
  }

  const host = window.location.hostname;
  if (host === "localhost" || host === "127.0.0.1" || host === "0.0.0.0") {
    return `${window.location.protocol}//${host}:8000`;
  }

  // Vercel: frontend e backend são domínios separados
  if (host.includes("vercel.app") || host.includes("automacao-cad")) {
    return "https://automacao-cad-backend.vercel.app";
  }

  // Produção genérica: usa origem atual (reverse proxy / edge rewrite).
  return window.location.origin;
};

const configuredApiBase =
  (typeof window !== "undefined" && (window as any).__ENGCAD_API_URL__) ||
  process.env.REACT_APP_API_URL ||
  getDefaultApiBase();

const normalizeCanonicalBackend = (value: string): string => {
  const normalized = normalizeBaseUrl(value);
  if (typeof window === "undefined") return normalized;

  const frontendHost = window.location.hostname;
  const isDeployedFrontend =
    frontendHost.includes("vercel.app") || frontendHost.includes("automacao-cad");

  // If a preview backend URL was injected (e.g. automacao-cad-backend-xyz.vercel.app),
  // pin to canonical production backend to avoid stale preview environments.
  if (
    isDeployedFrontend &&
    /https?:\/\/automacao-cad-backend-[^.]+\.vercel\.app/i.test(normalized)
  ) {
    return "https://automacao-cad-backend.vercel.app";
  }

  return normalized;
};

export const API_BASE_URL = normalizeCanonicalBackend(configuredApiBase);

// Runtime fallback base captured at initialization
const runtimeDefaultApiBase = normalizeBaseUrl(getDefaultApiBase());

export const SSE_BASE_URL =
  (typeof window !== "undefined" && (window as any).__ENGCAD_SSE_URL__) ||
  process.env.REACT_APP_SSE_URL ||
  API_BASE_URL;

const baseURL = API_BASE_URL;
export const api = axios.create({ baseURL, timeout: 15_000 });

const clearStaleClientCache = () => {
  if (typeof window === "undefined") return;
  try {
    const appliedVersion = window.localStorage.getItem(
      CLIENT_CACHE_VERSION_KEY,
    );
    if (appliedVersion === CLIENT_CACHE_VERSION) return;

    window.sessionStorage.removeItem("auth_token");
    window.localStorage.removeItem("token");
    window.localStorage.removeItem("selected-refinery");
    window.localStorage.removeItem("refinery-config");
    window.localStorage.setItem(CLIENT_CACHE_VERSION_KEY, CLIENT_CACHE_VERSION);

    if ("serviceWorker" in navigator) {
      navigator.serviceWorker
        .getRegistrations()
        .then((regs) => Promise.all(regs.map((reg) => reg.unregister())))
        .catch(() => {
          // noop
        });
    }

    if ("caches" in window) {
      caches
        .keys()
        .then((keys) => Promise.all(keys.map((k) => caches.delete(k))))
        .catch(() => {
          // noop
        });
    }
  } catch {
    // noop
  }
};

clearStaleClientCache();

// ── AI Orchestrator — interceptadores invisíveis de validação e cache ──
orchestrator.install(api);

// Expõe instância para o BackendHeartbeat (invisível ao usuário)
if (typeof window !== "undefined") {
  (window as any).__ENGCAD_AXIOS__ = api;
}

const TOKEN_KEY = "token";
const LEGACY_TOKEN_KEYS = ["auth_token"];
let memoryToken = "";

const migrateLegacyToken = (): void => {
  if (typeof window === "undefined") return;
  try {
    const current = window.localStorage.getItem(TOKEN_KEY);
    if (current) {
      for (const legacyKey of LEGACY_TOKEN_KEYS) {
        window.sessionStorage.removeItem(legacyKey);
      }
      return;
    }

    for (const legacyKey of LEGACY_TOKEN_KEYS) {
      const legacy = window.sessionStorage.getItem(legacyKey);
      if (legacy) {
        window.localStorage.setItem(TOKEN_KEY, legacy);
        window.sessionStorage.removeItem(legacyKey);
        break;
      }
    }
  } catch {
    // noop
  }
};

migrateLegacyToken();

const safeStorage = {
  getToken: (): string => {
    if (memoryToken) return memoryToken;
    try {
      memoryToken = window.localStorage.getItem(TOKEN_KEY) || "";
      return memoryToken;
    } catch {
      return "";
    }
  },
  setToken: (token: string) => {
    memoryToken = token;
    try {
      window.localStorage.setItem(TOKEN_KEY, token);
      for (const legacyKey of LEGACY_TOKEN_KEYS) {
        window.sessionStorage.removeItem(legacyKey);
      }
    } catch {
      // noop
    }
  },
  clearToken: () => {
    memoryToken = "";
    try {
      window.localStorage.removeItem(TOKEN_KEY);
      for (const legacyKey of LEGACY_TOKEN_KEYS) {
        window.sessionStorage.removeItem(legacyKey);
      }
    } catch {
      // noop
    }
  },
};

api.interceptors.request.use((config) => {
  const token = safeStorage.getToken();
  if (token) {
    config.headers = {
      ...(config.headers || {}),
      Authorization: `Bearer ${token}`,
    } as any;
  }
  return config;
});

// Auto-refresh expired tokens (401) before forcing re-login
let _refreshing: Promise<string | null> | null = null;

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    if (
      error.response?.status === 401 &&
      error.response?.data?.detail === "Token expirado" &&
      !originalRequest._retry &&
      originalRequest.url !== "/auth/refresh"
    ) {
      originalRequest._retry = true;
      if (!_refreshing) {
        _refreshing = (async () => {
          try {
            const token = safeStorage.getToken();
            if (!token) return null;
            const res = await api.post<{ access_token: string }>(
              "/auth/refresh",
              null,
              {
                headers: { Authorization: `Bearer ${token}` },
              },
            );
            const newToken = res.data.access_token;
            safeStorage.setToken(newToken);
            return newToken;
          } catch {
            return null;
          } finally {
            _refreshing = null;
          }
        })();
      }
      const newToken = await _refreshing;
      if (newToken) {
        originalRequest.headers.Authorization = `Bearer ${newToken}`;
        return api.request(originalRequest);
      }
    }
    return Promise.reject(error);
  },
);

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

const shouldRetry = (error: AxiosError) => {
  const status = error.response?.status;
  return !status || status >= 500 || error.code === "ECONNABORTED";
};

const shouldFailoverToRuntimeBase = (error: AxiosError) => {
  const status = error.response?.status;
  return (
    !status || error.code === "ERR_NETWORK" || error.code === "ECONNABORTED"
  );
};

const runtimeBaseDiffers = () => {
  const currentBase = (api.defaults.baseURL || "").replace(/\/$/, "");
  const runtimeBase = runtimeDefaultApiBase.replace(/\/$/, "");
  return currentBase !== runtimeBase;
};

async function requestWithRetry<T>(
  config: AxiosRequestConfig,
  retries = 1,
): Promise<T> {
  for (let attempt = 0; ; attempt += 1) {
    try {
      const response = await api.request<T>(config);
      return response.data;
    } catch (error) {
      const axiosError = error as AxiosError;

      // Fallback automático quando a base configurada está stale (ex.: porta errada em cache/build).
      if (runtimeBaseDiffers() && shouldFailoverToRuntimeBase(axiosError)) {
        try {
          const response = await axios.request<T>({
            ...config,
            baseURL: runtimeDefaultApiBase,
            timeout: 15_000,
            headers: {
              ...(config.headers || {}),
              ...(safeStorage.getToken()
                ? { Authorization: `Bearer ${safeStorage.getToken()}` }
                : {}),
            },
          });
          api.defaults.baseURL = runtimeDefaultApiBase;
          return response.data;
        } catch {
          // mantém fluxo normal abaixo para preservar tratamento de erro existente
        }
      }

      if (attempt >= retries || !shouldRetry(axiosError)) {
        if (axiosError.response?.status === 401) {
          safeStorage.clearToken();
        }
        throw error;
      }
      await sleep(250 * (attempt + 1));
    }
  }
}

export type LoginPayload = { email: string; senha: string };
export type RegisterPayload = {
  email: string;
  senha: string;
  empresa?: string;
};

/** Resposta padronizada de API envelope */
export interface ApiEnvelope<T> {
  data: T;
  status: "success" | "error";
}

/** Configuração de uma refinaria */
export interface RefineryItem {
  id: string;
  name: string;
  location: string;
  norms: string[];
  material_database: string;
  default_pressure_class: string;
  clash_detection_tolerance_mm: number;
}

export type GeneratePayload = {
  diameter: number;
  length: number;
  company: string;
  part_name: string;
  code: string;
  executar?: boolean;
  fluid?: string;
  temperature_c?: number;
  operating_pressure_bar?: number;
};

export type PipingSpec = {
  pressure_class: string;
  material: string;
  flange_face: string;
  selected_schedule: string;
  wall_thickness_mm: number;
  hydrotest_pressure_bar: number;
  corrosion_allowance_mm: number;
};

export type QualityCheck = {
  id: number;
  project_id: number;
  check_type: string;
  check_name: string;
  passed: number;
  details: string;
  created_at: number;
};

export type ProjectRecord = {
  id: number;
  user_email: string;
  code: string;
  company: string;
  part_name: string;
  diameter: number;
  length: number;
  fluid: string;
  temperature_c: number;
  operating_pressure_bar: number;
  status: string;
  lsp_path: string | null;
  dxf_path: string | null;
  csv_path: string | null;
  clash_count: number;
  norms_checked: string;
  norms_passed: string;
  piping_spec: string;
  created_at: number;
  completed_at: number | null;
};

export type GenerateResponse = {
  id: number;
  path: string;
  csv_path: string | null;
  piping_spec: PipingSpec;
  quality_checks: QualityCheck[];
  usado: number;
  limite: number;
};

export type QualityCheckResult = {
  project_id: number;
  checks: { name: string; passed: boolean; detail: string }[];
  passed: number;
  total: number;
  all_passed: boolean;
  verdict: "APROVADO" | "REPROVADO" | "PARCIAL";
};

export type ProjectStats = {
  stats: {
    total_projects: number;
    completed_projects: number;
    top_companies: [string, number][];
    top_parts: [string, number][];
    diameter_range: [number, number];
    length_range: [number, number];
  };
  recent_uploads: {
    id: number;
    filename: string;
    row_count: number;
    projects_generated: number;
    status: string;
    created_at: number;
  }[];
};

export type LoginResponse = {
  access_token: string;
  token_type: string;
  email: string;
  empresa: string;
  tier?: string;
  limite: number;
  usado: number;
};

export type SessionUser = {
  email: string;
  empresa: string;
  tier?: string;
  limite: number;
  usado: number;
};

export type InsightsResponse = {
  stats: {
    total_projects: number;
    seed_projects: number;
    real_projects: number;
    top_part_names: [string, number][];
    top_companies: [string, number][];
    diameter_range: [number, number];
    length_range: [number, number];
    draft_feedback: {
      accepted: number;
      rejected: number;
    };
  };
  recommendations: {
    suggested_part_name: string;
    suggested_company: string;
    typical_diameter_min: number;
    typical_diameter_max: number;
    typical_length_min: number;
    typical_length_max: number;
    total_projects: number;
  };
  templates: {
    id: string;
    company: string;
    part_name: string;
    diameter: number;
    length: number;
    count: number;
    score: number;
  }[];
};

export type ProjectDraftResponse = {
  company: string;
  part_name: string;
  diameter: number;
  length: number;
  code: string;
  based_on_template: string | null;
  confidence: "high" | "medium";
};

export type ProjectDraftFromTextResponse = ProjectDraftResponse & {
  parsed_fields: string[];
  prompt: string;
  explanation: string;
  field_confidence: {
    company: "high" | "medium";
    part_name: "high" | "medium";
    diameter: "high" | "medium";
    length: "high" | "medium";
    code: "medium";
  };
};

// ═══════════════════════════════════════════════════════════════════════════
// AutoCAD COM Driver (Nível 4) — Tipos
// ═══════════════════════════════════════════════════════════════════════════

export type AutoCADDriverStatus = {
  status: string;
  engine: string;
  operations_total: number;
  operations_success: number;
  operations_failed: number;
  reconnections: number;
  last_error: string | null;
};

export type AutoCADHealthResponse = {
  driver_status: string;
  engine: string;
  com_available: boolean;
  cloud_mode?: boolean;
  healthy?: boolean;
  mode?: string;
  stats: AutoCADDriverStatus;
  document: { name: string; path: string; saved: boolean } | null;
};

export type DriverResult = {
  success: boolean;
  operation: string;
  status: string;
  message: string;
  entity_handle: string | null;
  details: Record<string, unknown>;
};

export type DrawPipePayload = {
  points: number[][];
  diameter?: number;
  layer?: string;
};

export type InsertComponentPayload = {
  block_name: string;
  coordinate: number[];
  rotation?: number;
  scale?: number;
  layer?: string;
};

export type BatchDrawPayload = {
  pipes: DrawPipePayload[];
  components?: InsertComponentPayload[];
  finalize?: boolean;
};

export type BatchDrawResponse = {
  layers: DriverResult;
  pipes: DriverResult[];
  components: DriverResult[];
  finalize: DriverResult | null;
  summary: { total: number; success: number; failed: number };
};

export type Stress50DispatchResponse = {
  status: string;
  queue: string;
  jobs_submitted: number;
  job_ids: string[];
  health: {
    dispatch_elapsed_ms: number;
    dispatch_memory_current_mb: number;
    dispatch_memory_peak_mb: number;
  };
  cad_envelope: {
    projeto: string;
    norma: string;
    precisao: string;
    gerar_cotas_auto: boolean;
  };
  message: string;
};

export const ApiService = {
  login: async (payload: LoginPayload) => {
    const data = await requestWithRetry<LoginResponse>(
      { method: "POST", url: "/login", data: payload, timeout: 30_000 },
      2,
    );
    safeStorage.setToken(data.access_token);
    // Store tier in license so LicenseContext picks it up
    if (data.tier) {
      window.localStorage.setItem(
        "license",
        JSON.stringify({ tier: data.tier, validated: true }),
      );
    }
    return data;
  },
  register: async (payload: RegisterPayload) => {
    const data = await requestWithRetry<LoginResponse>(
      { method: "POST", url: "/auth/register", data: payload },
      0,
    );
    safeStorage.setToken(data.access_token);
    if (data.tier) {
      window.localStorage.setItem(
        "license",
        JSON.stringify({ tier: data.tier, validated: true }),
      );
    }
    return data;
  },
  demoLogin: async () => {
    const data = await requestWithRetry<LoginResponse>(
      { method: "POST", url: "/auth/demo" },
      2,
    );
    safeStorage.setToken(data.access_token);
    window.localStorage.setItem(
      "license",
      JSON.stringify({ tier: "demo", validated: true }),
    );
    return data;
  },
  logout: () => {
    safeStorage.clearToken();
    window.localStorage.removeItem("license");
  },
  getCurrentUser: () =>
    requestWithRetry<SessionUser>({ method: "GET", url: "/auth/me" }, 1),
  gerarProjeto: (payload: GeneratePayload) =>
    requestWithRetry<{ path: string; usado: number; limite: number }>(
      {
        method: "POST",
        url: "/generate",
        data: payload,
      },
      0,
    ),
  executarProjeto: (payload: GeneratePayload) =>
    requestWithRetry<{ path: string; usado: number; limite: number }>(
      {
        method: "POST",
        url: "/generate",
        data: { ...payload, executar: true },
      },
      0,
    ),
  uploadExcel: (formData: FormData) =>
    requestWithRetry<{
      files: string[];
      count: number;
      usado: number;
      limite: number;
    }>(
      {
        method: "POST",
        url: "/excel",
        data: formData,
        headers: { "Content-Type": "multipart/form-data" },
      },
      0,
    ),
  gerarRascunhoProjeto: (params?: { company?: string; part_name?: string }) =>
    requestWithRetry<ProjectDraftResponse>(
      {
        method: "GET",
        url: "/project-draft",
        params,
      },
      1,
    ),
  gerarRascunhoProjetoPorTexto: (prompt: string) =>
    requestWithRetry<ProjectDraftFromTextResponse>(
      {
        method: "GET",
        url: "/project-draft-from-text",
        params: { prompt },
      },
      1,
    ),
  enviarFeedbackRascunho: (payload: {
    prompt: string;
    feedback: "accepted" | "rejected";
    company: string;
    part_name: string;
    code: string;
  }) =>
    requestWithRetry<{ status: string }>(
      {
        method: "POST",
        url: "/project-draft-feedback",
        data: payload,
      },
      0,
    ),
  getRefineries: () =>
    requestWithRetry<ApiEnvelope<RefineryItem[]>>(
      { method: "GET", url: "/api/refineries" },
      1,
    ),
  obterInsights: () =>
    requestWithRetry<InsightsResponse>({ method: "GET", url: "/insights" }, 1),
  obterHistorico: () =>
    requestWithRetry<{ history: string[] }>(
      { method: "GET", url: "/history" },
      1,
    ),
  obterLogs: () =>
    requestWithRetry<{ logs: string[] }>({ method: "GET", url: "/logs" }, 1),
  health: () =>
    requestWithRetry<{ autocad: boolean }>(
      { method: "GET", url: "/health" },
      1,
    ),
  dispararTesteStress50Porticos: () =>
    requestWithRetry<Stress50DispatchResponse>(
      {
        method: "POST",
        url: "/jobs/stress/porticos-50",
      },
      0,
    ),
  obterStatusJob: (jobId: string) =>
    requestWithRetry<{ id: string; status: string; result?: unknown }>(
      {
        method: "GET",
        url: `/jobs/${jobId}`,
      },
      1,
    ),

  // ═══════════════════════════════════════════════════════════════════════
  // AutoCAD COM Driver (Nível 4)
  // ═══════════════════════════════════════════════════════════════════════

  autocadConnect: () =>
    requestWithRetry<DriverResult>(
      { method: "POST", url: "/api/autocad/connect" },
      1,
    ),

  autocadDisconnect: () =>
    requestWithRetry<DriverResult>(
      { method: "POST", url: "/api/autocad/disconnect" },
      0,
    ),

  autocadStatus: () =>
    requestWithRetry<AutoCADDriverStatus>(
      { method: "GET", url: "/api/autocad/status" },
      1,
    ),

  autocadHealth: () =>
    requestWithRetry<AutoCADHealthResponse>(
      { method: "GET", url: "/api/autocad/health" },
      1,
    ),

  autocadDrawPipe: (payload: DrawPipePayload) =>
    requestWithRetry<DriverResult>(
      { method: "POST", url: "/api/autocad/draw-pipe", data: payload },
      0,
    ),

  autocadInsertComponent: (payload: InsertComponentPayload) =>
    requestWithRetry<DriverResult>(
      { method: "POST", url: "/api/autocad/insert-component", data: payload },
      0,
    ),

  autocadCreateLayers: () =>
    requestWithRetry<DriverResult>(
      { method: "POST", url: "/api/autocad/create-layers" },
      0,
    ),

  autocadFinalize: () =>
    requestWithRetry<DriverResult>(
      { method: "POST", url: "/api/autocad/finalize" },
      0,
    ),

  autocadBatchDraw: (payload: BatchDrawPayload) =>
    requestWithRetry<BatchDrawResponse>(
      { method: "POST", url: "/api/autocad/batch-draw", data: payload },
      0,
    ),

  autocadSave: () =>
    requestWithRetry<DriverResult>(
      { method: "POST", url: "/api/autocad/save" },
      0,
    ),

  autocadDrawLine: (payload: {
    start: number[];
    end: number[];
    layer?: string;
  }) =>
    requestWithRetry<DriverResult>(
      { method: "POST", url: "/api/autocad/draw-line", data: payload },
      0,
    ),

  autocadAddText: (payload: {
    text: string;
    position: number[];
    height?: number;
    layer?: string;
  }) =>
    requestWithRetry<DriverResult>(
      { method: "POST", url: "/api/autocad/add-text", data: payload },
      0,
    ),

  autocadSendCommand: (command: string) =>
    requestWithRetry<DriverResult>(
      { method: "POST", url: "/api/autocad/send-command", data: { command } },
      0,
    ),

  autocadSetBridgePath: (path: string) =>
    requestWithRetry<DriverResult>(
      { method: "POST", url: "/api/autocad/config/bridge", data: { path } },
      0,
    ),

  autocadSetMode: (use_bridge: boolean) =>
    requestWithRetry<DriverResult>(
      { method: "POST", url: "/api/autocad/config/mode", data: { use_bridge } },
      0,
    ),

  autocadCommit: () =>
    requestWithRetry<DriverResult>(
      { method: "POST", url: "/api/autocad/commit" },
      0,
    ),

  autocadBufferStatus: () =>
    requestWithRetry<{
      mode: string;
      bridge_path: string;
      buffer_size: number;
      bridge_accessible: boolean;
    }>({ method: "GET", url: "/api/autocad/buffer" }, 1),

  /** Teste Ponta a Ponta — desenha quadrado + válvula no AutoCAD */
  autocadDrawSample: () =>
    requestWithRetry<BatchDrawResponse>(
      { method: "POST", url: "/api/v1/debug/draw-sample" },
      0,
    ),

  // ═══════════════════════════════════════════════════════════════════════
  // Projetos — CRUD real com banco de dados
  // ═══════════════════════════════════════════════════════════════════════

  getProjects: () =>
    requestWithRetry<{ projects: ProjectRecord[]; total: number }>(
      { method: "GET", url: "/projects" },
      1,
    ),

  getProject: (id: number) =>
    requestWithRetry<{
      project: ProjectRecord;
      quality_checks: QualityCheck[];
    }>({ method: "GET", url: `/projects/${id}` }, 1),

  getProjectStats: () =>
    requestWithRetry<ProjectStats>({ method: "GET", url: "/project-stats" }, 1),

  downloadProjectFile: (projectId: number, fileType: "lsp" | "dxf" | "csv") =>
    api
      .get(`/projects/${projectId}/download/${fileType}`, {
        responseType: "blob",
      })
      .then((res) => {
        const url = window.URL.createObjectURL(new Blob([res.data]));
        const a = document.createElement("a");
        a.href = url;
        a.download = `project_${projectId}.${fileType}`;
        a.click();
        window.URL.revokeObjectURL(url);
      }),

  runQualityCheck: (projectId: number) =>
    requestWithRetry<QualityCheckResult>(
      { method: "POST", url: `/quality-check/${projectId}` },
      0,
    ),
};
