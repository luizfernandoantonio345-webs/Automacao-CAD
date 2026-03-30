// ═══════════════════════════════════════════════════════════════════════════
// Engenharia CAD — UI Guard (Error Boundary Invisível)
// Captura crashes de renderização React e executa soft-reload automático.
// Jamais mostra tela branca — sempre mantém a fluidez visual.
// ═══════════════════════════════════════════════════════════════════════════

import React from "react";

interface UIGuardProps {
  children?: React.ReactNode;
  /** Componente fallback exibido durante recuperação (opcional) */
  fallback?: React.ReactNode;
}

interface UIGuardState {
  hasError: boolean;
  retryCount: number;
  recovering: boolean;
}

const MAX_RETRIES = 3;
const RECOVERY_DELAY_MS = 1500;

/** Fallback padrão — mínimo visual no tema dark do Engenharia CAD */
const DefaultFallback: React.FC<{
  onRetry: () => void;
  retryCount: number;
}> = ({ onRetry, retryCount }) => (
  <div
    style={{
      minHeight: "100vh",
      backgroundColor: "#0f172a",
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      justifyContent: "center",
      color: "#e0e0e0",
      fontFamily: "Inter, system-ui, sans-serif",
    }}
  >
    <div
      style={{
        padding: "2rem",
        borderRadius: "12px",
        backgroundColor: "#1e293b",
        border: "1px solid #334155",
        textAlign: "center",
        maxWidth: "400px",
      }}
    >
      <div
        style={{ fontSize: "1.5rem", marginBottom: "0.5rem", color: "#00A1FF" }}
      >
        ⟳
      </div>
      <div
        style={{ fontSize: "0.95rem", marginBottom: "1rem", color: "#94a3b8" }}
      >
        Recuperação automática em andamento...
      </div>
      <div
        style={{
          width: "100%",
          height: "3px",
          backgroundColor: "#334155",
          borderRadius: "2px",
          overflow: "hidden",
        }}
      >
        <div
          style={{
            height: "100%",
            backgroundColor: "#00A1FF",
            borderRadius: "2px",
            animation: "aiGuardPulse 1.5s ease-in-out infinite",
            width: "60%",
          }}
        />
      </div>
      {retryCount >= MAX_RETRIES && (
        <button
          onClick={onRetry}
          style={{
            marginTop: "1rem",
            padding: "0.5rem 1.5rem",
            backgroundColor: "#00A1FF",
            color: "#fff",
            border: "none",
            borderRadius: "6px",
            cursor: "pointer",
            fontSize: "0.85rem",
          }}
        >
          Recarregar
        </button>
      )}
    </div>
    <style>{`
      @keyframes aiGuardPulse {
        0%, 100% { transform: translateX(-100%); }
        50% { transform: translateX(200%); }
      }
    `}</style>
  </div>
);

/**
 * Error Boundary invisível que captura crashes de componentes React.
 * - Tenta soft-reload automático até MAX_RETRIES vezes
 * - Nunca mostra tela branca ao usuário
 * - Loga silenciosamente para telemetria
 */

// TS6 + ES5 target: class fields shadow inherited Component members (state, props, setState).
// We route all access through a self-cast to avoid the TS6 defineProperty semantics.
export class UIGuard extends React.Component<UIGuardProps, UIGuardState> {
  constructor(props: UIGuardProps) {
    super(props);
    const self = this as any;
    self.state = { hasError: false, retryCount: 0, recovering: false };
    self._recoveryTimer = null;
    self.handleManualRetry = () => {
      self.setState({ hasError: false, retryCount: 0, recovering: false });
    };
  }

  static getDerivedStateFromError(): Partial<UIGuardState> {
    return { hasError: true };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    if (process.env.NODE_ENV === "development") {
      console.error(
        "[AI_ORCHESTRATOR][UI_GUARD] Crash capturado:",
        error.message,
      );
      console.error("[AI_ORCHESTRATOR][UI_GUARD] Stack:", info.componentStack);
    }

    const self = this as any;
    const st: UIGuardState = self.state;
    if (st.retryCount < MAX_RETRIES) {
      self.setState({ recovering: true });
      self._recoveryTimer = setTimeout(() => {
        self.setState((prev: UIGuardState) => ({
          hasError: false,
          recovering: false,
          retryCount: prev.retryCount + 1,
        }));
      }, RECOVERY_DELAY_MS);
    }
  }

  componentWillUnmount() {
    const timer = (this as any)._recoveryTimer;
    if (timer) clearTimeout(timer);
  }

  render() {
    const self = this as any;
    const st: UIGuardState = self.state;
    const p: UIGuardProps = self.props;
    if (st.hasError || st.recovering) {
      if (p.fallback) return p.fallback;
      return (
        <DefaultFallback
          onRetry={self.handleManualRetry}
          retryCount={st.retryCount}
        />
      );
    }
    return p.children;
  }
}

export default UIGuard;
