import React, {
  createContext,
  useCallback,
  useContext,
  useRef,
  useState,
} from "react";

// ═══════════════════════════════════════════════════════════════════════
// Engenharia CAD — Toast Notification System
// Captura erros do circuit_breaker e exibe feedback visual ao usuário.
// ═══════════════════════════════════════════════════════════════════════

export type ToastLevel = "info" | "success" | "warning" | "error";

export interface Toast {
  id: number;
  level: ToastLevel;
  title: string;
  message: string;
  ts: number;
}

interface ToastContextValue {
  toasts: Toast[];
  addToast: (level: ToastLevel, title: string, message: string) => void;
  removeToast: (id: number) => void;
  /** Verifica resposta HTTP e dispara toast se for circuit breaker */
  handleApiError: (error: unknown) => void;
}

const ToastCtx = createContext<ToastContextValue | null>(null);

const TOAST_DURATION_MS = 6000;
const MAX_TOASTS = 5;

export const ToastProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const nextId = useRef(1);

  const removeToast = useCallback((id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const addToast = useCallback(
    (level: ToastLevel, title: string, message: string) => {
      const id = nextId.current++;
      setToasts((prev) => {
        const next = [...prev, { id, level, title, message, ts: Date.now() }];
        return next.length > MAX_TOASTS ? next.slice(-MAX_TOASTS) : next;
      });
      setTimeout(() => removeToast(id), TOAST_DURATION_MS);
    },
    [removeToast],
  );

  const handleApiError = useCallback(
    (error: unknown) => {
      const err = error as any;
      const status = err?.response?.status;
      const detail = err?.response?.data?.detail;
      const message =
        typeof detail === "string"
          ? detail
          : err?.message || "Erro desconhecido";

      // Circuit Breaker detectado (503 + padrão do CircuitBreakerOpen)
      if (
        status === 503 ||
        (typeof message === "string" &&
          /circuit.?breaker|service.*unavailable/i.test(message))
      ) {
        addToast(
          "error",
          "Sistema em Recuperação",
          "Modo Offline Ativado — o serviço está se recuperando automaticamente. Tente novamente em instantes.",
        );
        return;
      }

      // Erro genérico do backend
      if (status && status >= 500) {
        addToast("error", "Erro do Servidor", message);
        return;
      }

      if (status === 400 || status === 422) {
        addToast("warning", "Dados Inválidos", message);
        return;
      }

      // Rede / timeout
      if (err?.code === "ERR_NETWORK" || err?.code === "ECONNABORTED") {
        addToast(
          "error",
          "Sem Conexão",
          "Servidor Engenharia CAD inacessível — verifique a rede.",
        );
        return;
      }
    },
    [addToast],
  );

  return (
    <ToastCtx.Provider
      value={{ toasts, addToast, removeToast, handleApiError }}
    >
      {children}
      <ToastContainer toasts={toasts} onClose={removeToast} />
    </ToastCtx.Provider>
  );
};

export const useToast = (): ToastContextValue => {
  const ctx = useContext(ToastCtx);
  if (!ctx) throw new Error("useToast must be used within <ToastProvider>");
  return ctx;
};

// ═══════════════════════════════════════════════════════════════════════
// Toast Container — renderiza no canto superior direito
// ═══════════════════════════════════════════════════════════════════════

const LEVEL_COLORS: Record<
  ToastLevel,
  { bg: string; border: string; icon: string }
> = {
  info: { bg: "#0c1929", border: "#00A1FF", icon: "ℹ" },
  success: { bg: "#0c2918", border: "#00FF87", icon: "✓" },
  warning: { bg: "#2a2200", border: "#FFD700", icon: "⚠" },
  error: { bg: "#2a0000", border: "#FF4444", icon: "✕" },
};

const ToastContainer: React.FC<{
  toasts: Toast[];
  onClose: (id: number) => void;
}> = ({ toasts, onClose }) => {
  if (toasts.length === 0) return null;

  return (
    <div
      style={{
        position: "fixed",
        top: "1rem",
        right: "1rem",
        zIndex: 99999,
        display: "flex",
        flexDirection: "column",
        gap: "0.5rem",
        maxWidth: "420px",
        width: "100%",
        pointerEvents: "none",
      }}
    >
      {toasts.map((t) => {
        const colors = LEVEL_COLORS[t.level];
        return (
          <div
            key={t.id}
            style={{
              pointerEvents: "auto",
              backgroundColor: colors.bg,
              border: `1px solid ${colors.border}`,
              borderLeft: `4px solid ${colors.border}`,
              borderRadius: "6px",
              padding: "0.75rem 1rem",
              boxShadow: "0 4px 20px rgba(0,0,0,0.5)",
              animation: "fadeIn 0.3s ease-out",
            }}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "flex-start",
              }}
            >
              <div
                style={{
                  display: "flex",
                  gap: "0.5rem",
                  alignItems: "flex-start",
                  flex: 1,
                }}
              >
                <span
                  style={{
                    color: colors.border,
                    fontSize: "1rem",
                    fontWeight: 700,
                  }}
                >
                  {colors.icon}
                </span>
                <div>
                  <div
                    style={{
                      color: colors.border,
                      fontWeight: 700,
                      fontSize: "0.85rem",
                      marginBottom: "0.2rem",
                    }}
                  >
                    {t.title}
                  </div>
                  <div
                    style={{
                      color: "#ccc",
                      fontSize: "0.8rem",
                      lineHeight: 1.4,
                    }}
                  >
                    {t.message}
                  </div>
                </div>
              </div>
              <button
                onClick={() => onClose(t.id)}
                style={{
                  background: "none",
                  border: "none",
                  color: "#666",
                  cursor: "pointer",
                  fontSize: "1rem",
                  padding: "0 0.25rem",
                  lineHeight: 1,
                }}
              >
                ×
              </button>
            </div>
          </div>
        );
      })}
    </div>
  );
};
