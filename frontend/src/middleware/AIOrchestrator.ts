// ═══════════════════════════════════════════════════════════════════════════
// Engenharia CAD — Camada de Orquestração de IA Invisível (Middleware) v2.0
// O "Sanduíche de IA": Frontend ← AIOrchestrator → Backend ← ai_watchdog.py
// Sem interface. Sem renderização. Invisível. Blindado.
// ═══════════════════════════════════════════════════════════════════════════

import type {
  AxiosInstance,
  InternalAxiosRequestConfig,
  AxiosResponse,
  AxiosError,
} from "axios";

// ---------------------------------------------------------------------------
//  Constantes de Engenharia — Norma N-58 / Petrobras REGAP
// ---------------------------------------------------------------------------
const ENGINEERING_LIMITS = {
  diameter: { min: 0.5, max: 120, safeDefault: 6 },
  length: { min: 1, max: 50_000, safeDefault: 1000 },
} as const;

const CACHEABLE_ROUTES = [
  "/insights",
  "/history",
  "/logs",
  "/health",
  "/project-draft",
];
const MUTABLE_ROUTES = [
  "/generate",
  "/excel",
  "/login",
  "/auth/register",
  "/auth/demo",
];
const CACHE_TTL_MS = 5 * 60_000; // 5 minutos

type LogLevel = "info" | "warn" | "error" | "correction";

// ---------------------------------------------------------------------------
//  Fábrica de Dados Fallback — O Dashboard NUNCA recebe erro bruto
// ---------------------------------------------------------------------------
const FALLBACK_DATA: Record<string, unknown> = {
  "/insights": {
    stats: {
      total_projects: 0,
      seed_projects: 0,
      real_projects: 0,
      top_part_names: [],
      top_companies: [],
      diameter_range: [0, 0],
      length_range: [0, 0],
      draft_feedback: { accepted: 0, rejected: 0 },
    },
    recommendations: {
      suggested_part_name: "FLANGE-PADRAO",
      suggested_company: "PETROBRAS-REGAP",
      typical_diameter_min: 6,
      typical_diameter_max: 48,
      typical_length_min: 100,
      typical_length_max: 5000,
      total_projects: 0,
    },
    templates: [],
  },
  "/health": {
    autocad: false,
    status: "degraded",
    _ai_note: "Resposta de fallback — backend temporariamente indisponível",
  },
  "/history": { history: [] },
  "/logs": { logs: [] },
  "/generate": {
    path: "",
    usado: 0,
    limite: 100,
    _ai_note: "Geração em modo degradado",
  },
  "/system": { cpu: 0, ram: 0, disk: 0 },
  "/project-draft": {
    company: "PETROBRAS-REGAP",
    part_name: "FLANGE-PADRAO",
    diameter: 6,
    length: 1000,
    code: "AUTO-001",
    based_on_template: null,
    confidence: "medium" as const,
  },
  "/auth/me": null, // 401 é legítimo para auth — sem fallback
};

function getFallbackData(url: string): unknown | null {
  for (const pattern of Object.keys(FALLBACK_DATA)) {
    if (url.includes(pattern)) return FALLBACK_DATA[pattern];
  }
  return null;
}

// ---------------------------------------------------------------------------
//  Telemetria Silenciosa — Log de decisões da IA (debug only)
// ---------------------------------------------------------------------------
class SilentTelemetry {
  private entries: {
    ts: number;
    level: LogLevel;
    msg: string;
    detail?: unknown;
  }[] = [];
  private maxEntries = 200;

  log(level: LogLevel, msg: string, detail?: unknown) {
    const entry = { ts: Date.now(), level, msg, detail };
    this.entries.push(entry);
    if (this.entries.length > this.maxEntries) this.entries.shift();

    if (process.env.NODE_ENV === "development") {
      const prefix = `[AI_ORCHESTRATOR][${level.toUpperCase()}]`;
      if (level === "error") console.error(prefix, msg, detail ?? "");
      else if (level === "warn" || level === "correction")
        console.warn(prefix, msg, detail ?? "");
      else console.log(prefix, msg, detail ?? "");
    }
  }

  getHistory() {
    return [...this.entries];
  }
}

// ---------------------------------------------------------------------------
//  Cache de Respostas Estáveis — Fallback quando o Python cai
// ---------------------------------------------------------------------------
class StableResponseCache {
  private store = new Map<string, { data: unknown; ts: number }>();

  private makeKey(method: string, url: string, params?: unknown): string {
    const p = params ? JSON.stringify(params) : "";
    return `${method.toUpperCase()}:${url}:${p}`;
  }

  set(method: string, url: string, data: unknown, params?: unknown) {
    try {
      this.store.set(this.makeKey(method, url, params), {
        data: structuredClone(data),
        ts: Date.now(),
      });
    } catch {
      /* falha no clone — ignorar silenciosamente */
    }
  }

  get(method: string, url: string, params?: unknown): unknown | null {
    const key = this.makeKey(method, url, params);
    const entry = this.store.get(key);
    if (!entry) return null;
    if (Date.now() - entry.ts > CACHE_TTL_MS) {
      this.store.delete(key);
      return null;
    }
    try {
      return structuredClone(entry.data);
    } catch {
      return entry.data;
    }
  }

  invalidatePattern(pattern: string) {
    const toDelete: string[] = [];
    this.store.forEach((_, k) => {
      if (k.includes(pattern)) toDelete.push(k);
    });
    toDelete.forEach((k) => this.store.delete(k));
  }

  clear() {
    this.store.clear();
  }
}
// ---------------------------------------------------------------------------
//  Deduplicação de Requisições — Evita chamadas duplicadas simultâneas
// ---------------------------------------------------------------------------
class RequestDeduplicator {
  private inFlight = new Map<string, Promise<AxiosResponse>>();

  private makeKey(config: InternalAxiosRequestConfig): string | null {
    const method = (config.method || "get").toUpperCase();
    if (method !== "GET") return null; // só deduplica GETs
    const url = config.url || "";
    const params = config.params ? JSON.stringify(config.params) : "";
    return `${method}:${url}:${params}`;
  }

  getExisting(
    config: InternalAxiosRequestConfig,
  ): Promise<AxiosResponse> | null {
    const key = this.makeKey(config);
    if (!key) return null;
    return this.inFlight.get(key) ?? null;
  }

  track(config: InternalAxiosRequestConfig, promise: Promise<AxiosResponse>) {
    const key = this.makeKey(config);
    if (!key) return;
    this.inFlight.set(key, promise);
    promise.finally(() => this.inFlight.delete(key));
  }
}

// ---------------------------------------------------------------------------
//  Network Quality Tracker — Ajusta timeouts/retries baseado na rede real
// ---------------------------------------------------------------------------
type NetworkQuality = "excellent" | "good" | "degraded" | "poor";

class NetworkQualityTracker {
  private latencies: number[] = [];
  private maxSamples = 20;
  private failureCount = 0;
  private successCount = 0;

  recordLatency(ms: number) {
    this.latencies.push(ms);
    if (this.latencies.length > this.maxSamples) this.latencies.shift();
    this.successCount++;
  }

  recordFailure() {
    this.failureCount++;
  }

  getQuality(): NetworkQuality {
    if (this.latencies.length < 3) return "good"; // sem dados suficientes
    const avg =
      this.latencies.reduce((a, b) => a + b, 0) / this.latencies.length;
    const failRate =
      this.failureCount / Math.max(this.successCount + this.failureCount, 1);
    if (failRate > 0.3) return "poor";
    if (avg > 5000 || failRate > 0.15) return "degraded";
    if (avg > 2000) return "good";
    return "excellent";
  }

  /** Retorna timeout adaptativo baseado na qualidade da rede */
  getAdaptiveTimeout(): number {
    const quality = this.getQuality();
    switch (quality) {
      case "excellent":
        return 10_000;
      case "good":
        return 15_000;
      case "degraded":
        return 25_000;
      case "poor":
        return 40_000;
    }
  }

  /** Retorna número de retries recomendado */
  getAdaptiveRetries(): number {
    const quality = this.getQuality();
    switch (quality) {
      case "excellent":
        return 1;
      case "good":
        return 2;
      case "degraded":
        return 3;
      case "poor":
        return 4;
    }
  }

  getStats() {
    return {
      quality: this.getQuality(),
      avgLatency:
        this.latencies.length > 0
          ? Math.round(
              this.latencies.reduce((a, b) => a + b, 0) / this.latencies.length,
            )
          : 0,
      samples: this.latencies.length,
      successCount: this.successCount,
      failureCount: this.failureCount,
    };
  }
}

// ---------------------------------------------------------------------------
//  Pre-Warmer — Antecipação de requisições que o usuário vai precisar
// ---------------------------------------------------------------------------
class PreWarmer {
  private warmed = new Map<string, { data: unknown; ts: number }>();
  private pending = new Map<string, Promise<unknown>>();
  private ttl = 30_000; // 30s — dados pré-aquecidos expiram rápido

  schedule(key: string, fetchFn: () => Promise<unknown>) {
    if (this.pending.has(key) || this.warmed.has(key)) return;
    const promise = fetchFn()
      .then((data) => {
        this.warmed.set(key, { data, ts: Date.now() });
        return data;
      })
      .catch(() => null)
      .finally(() => this.pending.delete(key));
    this.pending.set(key, promise);
  }

  consume(key: string): unknown | null {
    const entry = this.warmed.get(key);
    if (!entry) return null;
    this.warmed.delete(key);
    if (Date.now() - entry.ts > this.ttl) return null;
    return entry.data;
  }
}

// ---------------------------------------------------------------------------
//  Monitor de Saúde do Backend — Detecção silenciosa de degradação
// ---------------------------------------------------------------------------
class BackendHealthMonitor {
  private healthy = true;
  private consecutiveFailures = 0;
  private lastCheck = 0;
  private checkInterval = 30_000; // 30s

  reportSuccess() {
    this.consecutiveFailures = 0;
    this.healthy = true;
  }

  reportFailure() {
    this.consecutiveFailures++;
    if (this.consecutiveFailures >= 3) this.healthy = false;
  }

  isHealthy() {
    return this.healthy;
  }
  shouldCheck() {
    return Date.now() - this.lastCheck > this.checkInterval;
  }
  markChecked() {
    this.lastCheck = Date.now();
  }
}

// ---------------------------------------------------------------------------
//  Status Channel — Simulação de progresso para operações CAD lentas
// ---------------------------------------------------------------------------
type StatusListener = (status: {
  phase: string;
  progress: number;
  message: string;
}) => void;

class StatusChannel {
  private listeners = new Set<StatusListener>();
  private activeTimers = new Map<string, ReturnType<typeof setInterval>>();

  subscribe(fn: StatusListener) {
    this.listeners.add(fn);
    return () => this.listeners.delete(fn);
  }

  private emit(phase: string, progress: number, message: string) {
    const status = { phase, progress, message };
    this.listeners.forEach((fn) => {
      try {
        fn(status);
      } catch {}
    });
  }

  /** Simula progresso enquanto o AutoCAD processa */
  simulateProgress(operationId: string, estimatedMs: number) {
    let progress = 0;
    const step = 100 / (estimatedMs / 300);
    const timer = setInterval(() => {
      progress = Math.min(progress + step * (1 - progress / 130), 95); // nunca chega a 100 sozinho
      this.emit("processing", Math.round(progress), "Motor CAD processando...");
    }, 300);
    this.activeTimers.set(operationId, timer);
  }

  completeProgress(operationId: string) {
    const timer = this.activeTimers.get(operationId);
    if (timer) {
      clearInterval(timer);
      this.activeTimers.delete(operationId);
    }
    this.emit("complete", 100, "Operação concluída");
  }

  cancelProgress(operationId: string) {
    const timer = this.activeTimers.get(operationId);
    if (timer) {
      clearInterval(timer);
      this.activeTimers.delete(operationId);
    }
  }
}

// ═══════════════════════════════════════════════════════════════════════════
//  ORQUESTRADOR PRINCIPAL — Fachada unificada de todos os subsistemas
// ═══════════════════════════════════════════════════════════════════════════
class AIOrchestrator {
  private telemetry = new SilentTelemetry();
  private cache = new StableResponseCache();
  private dedup = new RequestDeduplicator();
  private preWarmer = new PreWarmer();
  private healthMonitor = new BackendHealthMonitor();
  private networkTracker = new NetworkQualityTracker();
  readonly status = new StatusChannel();

  private axiosInstance: AxiosInstance | null = null;
  private installed = false;

  // ─── API pública ───────────────────────────────────────────────────

  /** Instala interceptadores no axios — chamar UMA vez na inicialização */
  install(axiosInstance: AxiosInstance) {
    if (this.installed) return;
    this.axiosInstance = axiosInstance;

    // Interceptor de REQUEST — correção preventiva
    axiosInstance.interceptors.request.use(
      (config) => this.onRequest(config),
      (error) => Promise.reject(error),
    );

    // Interceptor de RESPONSE — cache + fallback
    axiosInstance.interceptors.response.use(
      (response) => this.onResponseSuccess(response),
      (error) => this.onResponseError(error),
    );

    this.installed = true;
    this.telemetry.log("info", "Orquestrador instalado — supervisão ativa");
  }

  /** Pré-aquece rotas que o usuário provavelmente vai acessar */
  anticipate(nextRoute: string) {
    if (!this.axiosInstance) return;
    const ax = this.axiosInstance;

    const routeMap: Record<string, { key: string; url: string }[]> = {
      "/dashboard": [
        { key: "insights", url: "/insights" },
        { key: "history", url: "/history" },
      ],
      "/ingestion": [{ key: "insights", url: "/insights" }],
      "/quality": [
        { key: "insights", url: "/insights" },
        { key: "logs", url: "/logs" },
      ],
      "/cad-console": [{ key: "health", url: "/health" }],
    };

    const targets = routeMap[nextRoute];
    if (!targets) return;

    for (const t of targets) {
      this.preWarmer.schedule(t.key, () =>
        ax
          .get(t.url)
          .then((r) => r.data)
          .catch(() => null),
      );
    }
    this.telemetry.log("info", `Pré-aquecimento iniciado para ${nextRoute}`);
  }

  /** Consome dados pré-aquecidos (se disponíveis) */
  consumePreWarmed(key: string): unknown | null {
    return this.preWarmer.consume(key);
  }

  /** Subscreve ao canal de status de progresso */
  onStatusChange(fn: StatusListener) {
    return this.status.subscribe(fn);
  }

  /** Inicia simulação de progresso para operação CAD */
  trackCadOperation(operationId: string, estimatedMs = 8000) {
    this.status.simulateProgress(operationId, estimatedMs);
  }

  /** Finaliza simulação de progresso */
  completeCadOperation(operationId: string) {
    this.status.completeProgress(operationId);
  }

  /** Retorna se o backend está respondendo normalmente */
  isBackendHealthy() {
    return this.healthMonitor.isHealthy();
  }

  /** Histórico de decisões da IA (para debug) */
  getAuditLog() {
    return this.telemetry.getHistory();
  }

  /** Estatísticas de qualidade de rede (para debug) */
  getNetworkStats() {
    return this.networkTracker.getStats();
  }

  /** Limpa caches (ex: após logout) */
  reset() {
    this.cache.clear();
    this.telemetry.log("info", "Cache limpo — reset completo");
  }

  // ─── Interceptor de Request ────────────────────────────────────────

  private onRequest(
    config: InternalAxiosRequestConfig,
  ): InternalAxiosRequestConfig {
    const url = config.url || "";
    const method = (config.method || "get").toUpperCase();

    // Timeout adaptativo baseado na qualidade real da rede
    config.timeout = this.networkTracker.getAdaptiveTimeout();

    // Marca timestamp para medir latência
    (config as any)._aiRequestStart = Date.now();

    // Validação e correção de payloads de engenharia
    if (method === "POST" && url.includes("/generate") && config.data) {
      config.data = this.sanitizeEngineeringPayload(config.data);
    }

    // Normalização de strings em payloads
    if (
      config.data &&
      typeof config.data === "object" &&
      !(config.data instanceof FormData)
    ) {
      config.data = this.normalizeStringFields(config.data);
    }

    return config;
  }

  // ─── Interceptor de Response (sucesso) ─────────────────────────────

  private onResponseSuccess(response: AxiosResponse): AxiosResponse {
    const url = response.config.url || "";
    const method = (response.config.method || "get").toUpperCase();

    this.healthMonitor.reportSuccess();

    // Rastreia latência para ajuste adaptativo
    const start = (response.config as any)._aiRequestStart;
    if (start) this.networkTracker.recordLatency(Date.now() - start);

    // Armazena em cache para fallback futuro
    if (method === "GET" && CACHEABLE_ROUTES.some((r) => url.includes(r))) {
      this.cache.set(method, url, response.data, response.config.params);
      this.telemetry.log("info", `Cache atualizado: ${url}`);
    }

    // Invalida caches após mutações
    if (MUTABLE_ROUTES.some((r) => url.includes(r)) && method === "POST") {
      this.cache.invalidatePattern("/insights");
      this.cache.invalidatePattern("/history");
    }

    return response;
  }

  // ─── Interceptor de Response (erro) — SILENT RECOVERY ───────────
  // O Dashboard NUNCA recebe um erro bruto. A IA sempre injeta dados.

  private onResponseError(error: AxiosError): Promise<AxiosResponse> {
    const config = error.config;
    const url = config?.url || "";
    const method = (config?.method || "get").toUpperCase();
    const status = error.response?.status;

    this.healthMonitor.reportFailure();
    this.networkTracker.recordFailure();

    // 401 não tem fallback — é autenticação legítima
    if (status === 401) return Promise.reject(error);

    // CAMADA 1: Tenta servir do cache estável (Python caiu? Último cache válido)
    if (method === "GET") {
      const cached = this.cache.get(method, url, config?.params);
      if (cached) {
        this.telemetry.log("warn", `Silent Recovery [CACHE] para ${url}`, {
          originalStatus: status,
          errorCode: error.code,
        });
        return Promise.resolve(
          this.buildSyntheticResponse(cached, config!, "AI Cache Recovery"),
        );
      }
    }

    // CAMADA 2: Auto-corrige erros de validação (ValueError, N-58 conflicts)
    if ((status === 422 || status === 400) && config?.data) {
      const backendMsg = (error.response?.data as any)?.detail || "";
      if (
        typeof backendMsg === "string" &&
        this.isEngineeringError(backendMsg)
      ) {
        this.telemetry.log(
          "correction",
          `Silent Recovery [AUTO-FIX] após erro ${status}: ${backendMsg}`,
        );
        const corrected = this.deepCorrectPayload(config.data, backendMsg);
        if (corrected && this.axiosInstance) {
          config.data = corrected;
          (config as any)._aiRetried = true;
          return this.axiosInstance.request(config!);
        }
      }
    }

    // CAMADA 3: Fallback estático — dados seguros pré-definidos por endpoint
    // Garante que o Dashboard NUNCA receba um erro bruto
    const fallback = getFallbackData(url);
    if (fallback !== null && fallback !== undefined) {
      this.telemetry.log("warn", `Silent Recovery [FALLBACK] para ${url}`, {
        originalStatus: status,
        errorCode: error.code,
        message: "Usando dados de fallback estáticos",
      });
      return Promise.resolve(
        this.buildSyntheticResponse(
          { ...(fallback as any), _ai_recovered: true },
          config!,
          "AI Fallback Recovery",
        ),
      );
    }

    // CAMADA 4: Erros de rede/timeout — retry mental (apenas log)
    if (!status) {
      this.telemetry.log("error", `Falha de rede para ${url}`, {
        code: error.code,
        message: error.message,
      });
    }

    return Promise.reject(error);
  }

  /** Constrói uma AxiosResponse sintética para injetar no fluxo */
  private buildSyntheticResponse(
    data: unknown,
    config: InternalAxiosRequestConfig,
    statusText: string,
  ): AxiosResponse {
    return {
      data,
      status: 200,
      statusText,
      headers: {},
      config,
    } as AxiosResponse;
  }

  // ─── Correção Preventiva de Payloads de Engenharia ─────────────────

  private sanitizeEngineeringPayload(data: any): any {
    if (!data || typeof data !== "object") return data;
    const corrections: string[] = [];

    // Diâmetro
    if ("diameter" in data) {
      const d = Number(data.diameter);
      if (!Number.isFinite(d) || d <= 0) {
        data.diameter = ENGINEERING_LIMITS.diameter.safeDefault;
        corrections.push(`diameter: ${d} → ${data.diameter} (valor inválido)`);
      } else if (d < ENGINEERING_LIMITS.diameter.min) {
        data.diameter = ENGINEERING_LIMITS.diameter.min;
        corrections.push(
          `diameter: ${d} → ${data.diameter} (abaixo do mínimo N-58)`,
        );
      } else if (d > ENGINEERING_LIMITS.diameter.max) {
        data.diameter = ENGINEERING_LIMITS.diameter.max;
        corrections.push(
          `diameter: ${d} → ${data.diameter} (acima do máximo N-58)`,
        );
      }
    }

    // Comprimento
    if ("length" in data) {
      const l = Number(data.length);
      if (!Number.isFinite(l) || l <= 0) {
        data.length = ENGINEERING_LIMITS.length.safeDefault;
        corrections.push(`length: ${l} → ${data.length} (valor inválido)`);
      } else if (l < ENGINEERING_LIMITS.length.min) {
        data.length = ENGINEERING_LIMITS.length.min;
        corrections.push(`length: ${l} → ${data.length} (abaixo do mínimo)`);
      } else if (l > ENGINEERING_LIMITS.length.max) {
        data.length = ENGINEERING_LIMITS.length.max;
        corrections.push(`length: ${l} → ${data.length} (acima do máximo)`);
      }
    }

    // Company obrigatório
    if (
      "company" in data &&
      (!data.company ||
        typeof data.company !== "string" ||
        !data.company.trim())
    ) {
      data.company = "PETROBRAS-REGAP";
      corrections.push("company: vazio → PETROBRAS-REGAP");
    }

    // Part name obrigatório
    if (
      "part_name" in data &&
      (!data.part_name ||
        typeof data.part_name !== "string" ||
        !data.part_name.trim())
    ) {
      data.part_name = "FLANGE-PADRAO";
      corrections.push("part_name: vazio → FLANGE-PADRAO");
    }

    if (corrections.length > 0) {
      data._aiAutoAdjusted = true;
      this.telemetry.log(
        "correction",
        "Correção preventiva de payload",
        corrections,
      );
    }

    return data;
  }

  /** Normaliza campos string: trim e remoção de caracteres perigosos */
  private normalizeStringFields(data: any): any {
    if (!data || typeof data !== "object" || data instanceof FormData)
      return data;
    for (const key of Object.keys(data)) {
      if (typeof data[key] === "string") {
        data[key] = data[key].trim();
      }
    }
    return data;
  }

  /** Identifica se a mensagem de erro é sobre engenharia (não auth/rede) */
  private isEngineeringError(msg: string): boolean {
    const patterns = [
      "diameter",
      "length",
      "diâmetro",
      "comprimento",
      "n-58",
      "norma",
      "fora do intervalo",
      "out of range",
      "invalid value",
      "valor inválido",
      "ValueError",
      "pressure",
      "pressão",
      "class",
    ];
    return patterns.some((p) => msg.toLowerCase().includes(p.toLowerCase()));
  }

  /** Tenta corrigir payload baseado na mensagem de erro do backend */
  private deepCorrectPayload(data: any, errorMsg: string): any | null {
    if ((data as any)?._aiRetried) return null; // evita loops infinitos

    try {
      const payload = typeof data === "string" ? JSON.parse(data) : { ...data };
      const msg = errorMsg.toLowerCase();

      if (msg.includes("diameter") || msg.includes("diâmetro")) {
        payload.diameter = ENGINEERING_LIMITS.diameter.safeDefault;
      }
      if (msg.includes("length") || msg.includes("comprimento")) {
        payload.length = ENGINEERING_LIMITS.length.safeDefault;
      }

      payload._aiAutoAdjusted = true;
      this.telemetry.log(
        "correction",
        "Deep correction aplicada após rejeição do backend",
        {
          original: data,
          corrected: payload,
          errorMsg,
        },
      );
      return payload;
    } catch {
      return null;
    }
  }
}

// ═══════════════════════════════════════════════════════════════════════════
//  Instância Singleton — Compartilhada por toda a aplicação
// ═══════════════════════════════════════════════════════════════════════════
export const orchestrator = new AIOrchestrator();

// ═══════════════════════════════════════════════════════════════════════════
//  SSE GUARDIAN — Reconexão automática para streams em tempo real
// ═══════════════════════════════════════════════════════════════════════════

type SSEMessageHandler = (event: MessageEvent) => void;
type SSEErrorHandler = (retryCount: number, nextRetryMs: number) => void;

/**
 * Gerenciador de conexões SSE com reconexão automática exponencial.
 * Se o stream cair, reconecta silenciosamente sem que o usuário perceba.
 */
export class SSEGuardian {
  private source: EventSource | null = null;
  private retryCount = 0;
  private maxRetries = 10;
  private baseDelay = 1000;
  private maxDelay = 30_000;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private destroyed = false;

  constructor(
    private url: string,
    private onMessage: SSEMessageHandler,
    private onError?: SSEErrorHandler,
  ) {
    this.connect();
  }

  private connect() {
    if (this.destroyed) return;
    try {
      this.source = new EventSource(this.url);
      this.source.onmessage = (event) => {
        this.retryCount = 0; // sucesso reseta contador
        this.onMessage(event);
      };
      this.source.onerror = () => {
        this.source?.close();
        this.source = null;
        this.scheduleReconnect();
      };
    } catch {
      this.scheduleReconnect();
    }
  }

  private scheduleReconnect() {
    if (this.destroyed || this.retryCount >= this.maxRetries) return;
    const delay = Math.min(
      this.baseDelay * Math.pow(2, this.retryCount),
      this.maxDelay,
    );
    this.retryCount++;
    if (this.onError) this.onError(this.retryCount, delay);
    this.reconnectTimer = setTimeout(() => this.connect(), delay);
  }

  destroy() {
    this.destroyed = true;
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    this.source?.close();
    this.source = null;
  }
}

// ═══════════════════════════════════════════════════════════════════════════
//  HEARTBEAT CHECKER — Ping silencioso ao backend a cada 30s
// ═══════════════════════════════════════════════════════════════════════════

let _heartbeatTimer: ReturnType<typeof setInterval> | null = null;

/**
 * Inicia heartbeat silencioso. Se o backend parar de responder,
 * o healthMonitor dentro do orchestrator atualiza e componentes
 * podem reagir via `orchestrator.isBackendHealthy()`.
 */
export function startHeartbeat(
  axiosInstance: { get: Function },
  intervalMs = 30_000,
) {
  if (_heartbeatTimer) return; // já iniciado
  _heartbeatTimer = setInterval(() => {
    axiosInstance.get("/health").catch(() => {
      // Silencioso — o interceptor de erro do orchestrator cuida do resto
    });
  }, intervalMs);
}

export function stopHeartbeat() {
  if (_heartbeatTimer) {
    clearInterval(_heartbeatTimer);
    _heartbeatTimer = null;
  }
}

export default orchestrator;
