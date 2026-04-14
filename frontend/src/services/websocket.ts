/**
 * ═══════════════════════════════════════════════════════════════════════════
 * WebSocket Service — Comunicação em tempo real com o servidor
 * Reconexão automática, heartbeat e gestão de canais
 * ═══════════════════════════════════════════════════════════════════════════
 */

import { API_BASE_URL } from "./api";

export type WSChannel =
  | "system"
  | "cad"
  | "cam"
  | "ai"
  | "notifications"
  | "chat"
  | "telemetry"
  | "collaboration";

export interface WSMessage {
  type: string;
  [key: string]: any;
}

type MessageHandler = (message: WSMessage) => void;

interface WSConfig {
  channels?: WSChannel[];
  autoReconnect?: boolean;
  maxReconnectAttempts?: number;
  reconnectIntervalMs?: number;
  heartbeatIntervalMs?: number;
}

const DEFAULT_CONFIG: Required<WSConfig> = {
  channels: ["system", "notifications"],
  autoReconnect: true,
  maxReconnectAttempts: 10,
  reconnectIntervalMs: 3000,
  heartbeatIntervalMs: 30000,
};

class WebSocketService {
  private ws: WebSocket | null = null;
  private config: Required<WSConfig>;
  private handlers: Map<string, Set<MessageHandler>> = new Map();
  private globalHandlers: Set<MessageHandler> = new Set();
  private reconnectAttempts = 0;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private heartbeatTimer: ReturnType<typeof setInterval> | null = null;
  private isIntentionalClose = false;
  private _clientId: string | null = null;

  constructor(config?: WSConfig) {
    this.config = { ...DEFAULT_CONFIG, ...config };
  }

  get connected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  get clientId(): string | null {
    return this._clientId;
  }

  connect(token?: string): void {
    if (this.ws?.readyState === WebSocket.OPEN) return;

    this.isIntentionalClose = false;

    const wsBase = API_BASE_URL.replace(/^http/, "ws");
    const params = new URLSearchParams();
    if (token) params.set("token", token);
    if (this.config.channels.length > 0) {
      params.set("channels", this.config.channels.join(","));
    }

    const url = `${wsBase}/ws?${params.toString()}`;

    try {
      this.ws = new WebSocket(url);
    } catch (err) {
      console.error("[WS] Falha ao criar WebSocket:", err);
      this.scheduleReconnect(token);
      return;
    }

    this.ws.onopen = () => {
      console.log("[WS] Conectado");
      this.reconnectAttempts = 0;
      this.startHeartbeat();
    };

    this.ws.onmessage = (event) => {
      try {
        const message: WSMessage = JSON.parse(event.data);
        this.dispatch(message);
      } catch {
        console.warn("[WS] Mensagem inválida:", event.data);
      }
    };

    this.ws.onclose = (event) => {
      console.log(`[WS] Desconectado (code=${event.code})`);
      this._clientId = null;
      this.stopHeartbeat();
      if (!this.isIntentionalClose && this.config.autoReconnect) {
        this.scheduleReconnect(token);
      }
    };

    this.ws.onerror = (event) => {
      console.error("[WS] Erro:", event);
    };
  }

  disconnect(): void {
    this.isIntentionalClose = true;
    this.stopHeartbeat();
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.ws) {
      this.ws.close(1000, "Client disconnect");
      this.ws = null;
    }
  }

  send(message: WSMessage): boolean {
    if (!this.connected || !this.ws) return false;
    try {
      this.ws.send(JSON.stringify(message));
      return true;
    } catch {
      return false;
    }
  }

  subscribe(channels: WSChannel[]): void {
    this.send({ type: "subscribe", channels });
    channels.forEach((ch) => {
      if (!this.config.channels.includes(ch)) {
        this.config.channels.push(ch);
      }
    });
  }

  unsubscribe(channels: WSChannel[]): void {
    this.send({ type: "unsubscribe", channels });
    this.config.channels = this.config.channels.filter(
      (c) => !channels.includes(c),
    );
  }

  on(type: string, handler: MessageHandler): () => void {
    if (!this.handlers.has(type)) {
      this.handlers.set(type, new Set());
    }
    this.handlers.get(type)!.add(handler);
    return () => this.handlers.get(type)?.delete(handler);
  }

  onAny(handler: MessageHandler): () => void {
    this.globalHandlers.add(handler);
    return () => this.globalHandlers.delete(handler);
  }

  private dispatch(message: WSMessage): void {
    if (message.type === "connected") {
      this._clientId = message.client_id;
    }

    const typeHandlers = this.handlers.get(message.type);
    if (typeHandlers) {
      typeHandlers.forEach((h) => {
        try {
          h(message);
        } catch (err) {
          console.error(`[WS] Handler error for '${message.type}':`, err);
        }
      });
    }

    this.globalHandlers.forEach((h) => {
      try {
        h(message);
      } catch (err) {
        console.error("[WS] Global handler error:", err);
      }
    });
  }

  private startHeartbeat(): void {
    this.stopHeartbeat();
    this.heartbeatTimer = setInterval(() => {
      this.send({ type: "ping" });
    }, this.config.heartbeatIntervalMs);
  }

  private stopHeartbeat(): void {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
  }

  private scheduleReconnect(token?: string): void {
    if (this.reconnectAttempts >= this.config.maxReconnectAttempts) {
      console.warn("[WS] Máximo de tentativas de reconexão atingido");
      return;
    }

    const delay = Math.min(
      this.config.reconnectIntervalMs * Math.pow(1.5, this.reconnectAttempts),
      30000,
    );

    console.log(
      `[WS] Reconectando em ${Math.round(delay / 1000)}s (tentativa ${this.reconnectAttempts + 1}/${this.config.maxReconnectAttempts})`,
    );

    this.reconnectTimer = setTimeout(() => {
      this.reconnectAttempts++;
      this.connect(token);
    }, delay);
  }
}

// Singleton
export const wsService = new WebSocketService();
export default WebSocketService;
