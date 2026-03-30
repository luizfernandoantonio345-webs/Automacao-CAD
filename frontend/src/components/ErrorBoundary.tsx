import React, { Component, ErrorInfo, PropsWithChildren } from "react";

interface EBState {
  hasError: boolean;
  errorMessage: string;
}

/**
 * Captura erros de renderização React e exibe uma tela amigável
 * em vez de uma página em branco.
 */
export class ErrorBoundary extends Component<PropsWithChildren<{}>, EBState> {
  state: EBState = { hasError: false, errorMessage: "" };

  static getDerivedStateFromError(error: Error): Partial<EBState> {
    return { hasError: true, errorMessage: error.message };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("[ErrorBoundary]", error, info);
  }

  handleReload = () => {
    window.location.reload();
  };

  handleGoHome = () => {
    window.location.href = "/";
  };

  render() {
    if (!this.state.hasError) {
      // @ts-ignore - Component.props exists at runtime
      return this.props.children;
    }

    return (
      <div style={s.container}>
        <div style={s.card}>
          <div style={s.iconCircle}>!</div>
          <h1 style={s.title}>Algo deu errado</h1>
          <p style={s.message}>
            Um erro inesperado ocorreu na interface. Seus dados estão seguros.
          </p>
          <p style={s.detail}>{this.state.errorMessage}</p>
          <div style={s.actions}>
            <button onClick={this.handleReload} style={s.btnPrimary}>
              Recarregar Página
            </button>
            <button onClick={this.handleGoHome} style={s.btnSecondary}>
              Voltar ao Início
            </button>
          </div>
        </div>
      </div>
    );
  }
}

const s: Record<string, React.CSSProperties> = {
  container: {
    height: "100vh",
    backgroundColor: "#0A0A0B",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontFamily: "'Segoe UI', Roboto, sans-serif",
    padding: "20px",
  },
  card: {
    maxWidth: "460px",
    textAlign: "center",
    padding: "48px 40px",
    backgroundColor: "#0D0D0F",
    border: "1px solid #1a1c22",
    borderRadius: "8px",
  },
  iconCircle: {
    width: "56px",
    height: "56px",
    borderRadius: "50%",
    backgroundColor: "rgba(255, 77, 77, 0.1)",
    border: "2px solid #FF4D4D",
    color: "#FF4D4D",
    fontSize: "28px",
    fontWeight: 900,
    display: "inline-flex",
    alignItems: "center",
    justifyContent: "center",
    marginBottom: "20px",
  },
  title: {
    color: "#FFF",
    fontSize: "20px",
    fontWeight: 700,
    margin: "0 0 12px",
  },
  message: {
    color: "#889",
    fontSize: "14px",
    lineHeight: "1.6",
    margin: "0 0 8px",
  },
  detail: {
    color: "#556",
    fontSize: "12px",
    fontFamily: "monospace",
    margin: "0 0 28px",
    wordBreak: "break-word",
  },
  actions: {
    display: "flex",
    gap: "12px",
    justifyContent: "center",
  },
  btnPrimary: {
    padding: "12px 24px",
    backgroundColor: "#00A1FF",
    border: "none",
    color: "#FFF",
    borderRadius: "4px",
    cursor: "pointer",
    fontWeight: 700,
    fontSize: "13px",
  },
  btnSecondary: {
    padding: "12px 24px",
    backgroundColor: "transparent",
    border: "1px solid #333",
    color: "#888",
    borderRadius: "4px",
    cursor: "pointer",
    fontWeight: 600,
    fontSize: "13px",
  },
};
