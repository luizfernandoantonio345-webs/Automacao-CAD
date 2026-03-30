import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  FaFingerprint,
  FaShieldAlt,
  FaMicrochip,
  FaRocket,
  FaDraftingCompass,
  FaBolt,
  FaChartLine,
} from "react-icons/fa";
import { API_BASE_URL, ApiService } from "../services/api";

const FEATURES = [
  {
    icon: <FaDraftingCompass />,
    title: "AutoCAD Automation",
    desc: "Geração automatizada de desenhos de piping, P&ID e isométricos direto no AutoCAD.",
  },
  {
    icon: <FaBolt />,
    title: "IA Integrada",
    desc: "Inteligência artificial para validação de normas (ASME, Petrobras N-series) em tempo real.",
  },
  {
    icon: <FaChartLine />,
    title: "Quality Gate",
    desc: "Controle de qualidade com rastreabilidade completa e relatórios certificáveis.",
  },
];

const Login = () => {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [demoLoading, setDemoLoading] = useState(false);
  const navigate = useNavigate();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) {
      setError("Preencha e-mail e senha para entrar.");
      return;
    }
    setError("");
    setLoading(true);
    try {
      await ApiService.login({ email, senha: password });
      navigate("/global-setup");
    } catch (err: any) {
      const status = err?.response?.status;
      if (status === 401) {
        setError("Credenciais inválidas. Verifique e-mail e senha.");
      } else if (status === 429) {
        setError("Muitas tentativas. Aguarde um momento.");
      } else if (!status) {
        setError(
          `Servidor indisponível em ${API_BASE_URL}. Recarregue com Ctrl+F5 e tente novamente.`,
        );
      } else {
        setError(`Erro no servidor (${status}). Tente novamente.`);
      }
      setLoading(false);
    }
  };

  const handleDemo = async () => {
    setError("");
    setDemoLoading(true);
    try {
      await ApiService.demoLogin();
      navigate("/global-setup");
    } catch (err: any) {
      const status = err?.response?.status;
      if (status === 429) {
        setError("Muitas tentativas. Aguarde um momento e tente novamente.");
      } else if (status && status >= 500) {
        setError(
          "Servidor temporariamente indisponível. Tente novamente em instantes.",
        );
      } else {
        setError(
          `Não foi possível conectar ao servidor em ${API_BASE_URL}. Recarregue com Ctrl+F5 e tente novamente.`,
        );
      }
      setDemoLoading(false);
    }
  };

  return (
    <div style={s.container}>
      <div style={s.overlay} />

      {/* Left panel — Product identity & features */}
      <div style={s.leftPanel}>
        <div style={s.heroContent}>
          <div style={s.heroLogoRow}>
            <span style={s.heroIcon}>
              <FaMicrochip />
            </span>
            <h1 style={s.heroBrand}>
              ENGENHARIA <span style={s.brandHighlight}>CAD</span>
            </h1>
          </div>
          <p style={s.heroTagline}>
            Plataforma de Automação CAD Industrial com Inteligência Artificial
          </p>
          <div style={s.featureList}>
            {FEATURES.map((f, i) => (
              <div key={i} style={s.featureItem}>
                <span style={s.featureIcon}>{f.icon}</span>
                <div>
                  <div style={s.featureTitle}>{f.title}</div>
                  <div style={s.featureDesc}>{f.desc}</div>
                </div>
              </div>
            ))}
          </div>
          <div style={s.heroStats}>
            <div style={s.stat}>
              <span style={s.statVal}>50+</span>
              <span style={s.statLabel}>Normas Suportadas</span>
            </div>
            <div style={s.stat}>
              <span style={s.statVal}>10x</span>
              <span style={s.statLabel}>Mais Rápido</span>
            </div>
            <div style={s.stat}>
              <span style={s.statVal}>99.9%</span>
              <span style={s.statLabel}>Precisão</span>
            </div>
          </div>
        </div>
      </div>

      {/* Right panel — Login form */}
      <div style={s.rightPanel}>
        <div style={s.loginBox}>
          <div style={s.topLine} />

          <div style={s.header}>
            <h2 style={s.loginTitle}>Acesso ao Sistema</h2>
            <div style={s.versionBadge}>V1.0 GOLD</div>
          </div>

          <form onSubmit={handleLogin} style={s.form}>
            <div style={s.inputWrapper}>
              <label style={s.label}>E-MAIL</label>
              <input
                type="email"
                placeholder="operador@empresa.com.br"
                style={s.input}
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>

            <div style={s.inputWrapper}>
              <label style={s.label}>SENHA</label>
              <input
                type="password"
                placeholder="••••••••••••"
                style={s.input}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>

            {error && <div style={s.errorMsg}>{error}</div>}

            <button
              type="submit"
              style={{ ...s.submitBtn, opacity: loading ? 0.6 : 1 }}
              disabled={loading || demoLoading}
            >
              <span style={s.btnText}>
                {loading ? "AUTENTICANDO..." : "ENTRAR"}
              </span>
              <span style={s.btnIcon}>
                <FaFingerprint />
              </span>
            </button>
          </form>

          <div style={s.divider}>
            <span style={s.dividerLine} />
            <span style={s.dividerText}>ou</span>
            <span style={s.dividerLine} />
          </div>

          <button
            onClick={handleDemo}
            style={{ ...s.demoBtn, opacity: demoLoading ? 0.6 : 1 }}
            disabled={loading || demoLoading}
          >
            <span style={{ marginRight: 10, display: "inline-flex" }}>
              <FaRocket />
            </span>
            {demoLoading ? "CARREGANDO DEMO..." : "EXPLORAR MODO DEMONSTRAÇÃO"}
          </button>
          <p style={s.demoHint}>
            Acesso completo sem cadastro — veja o sistema em ação em 1 minuto
          </p>

          <div style={s.footer}>
            <div style={s.statusDot} />
            <span style={s.statusText}>CONEXÃO SEGURA AES-256</span>
          </div>
        </div>
      </div>
    </div>
  );
};

const s: Record<string, React.CSSProperties> = {
  container: {
    height: "100vh",
    backgroundColor: "#050507",
    display: "flex",
    position: "relative",
    overflow: "hidden",
    fontFamily: "'Segoe UI', Roboto, sans-serif",
  },
  overlay: {
    position: "absolute",
    width: "100%",
    height: "100%",
    background:
      "linear-gradient(135deg, #050507 0%, #0a1628 50%, #050507 100%)",
    opacity: 0.9,
    zIndex: 0,
  },

  /* ── Left Panel ── */
  leftPanel: {
    flex: 1,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    position: "relative",
    zIndex: 10,
    padding: "60px",
  },
  heroContent: { maxWidth: 520 },
  heroLogoRow: {
    display: "flex",
    alignItems: "center",
    gap: "14px",
    marginBottom: "16px",
  },
  heroIcon: {
    fontSize: "38px",
    color: "#00A1FF",
    filter: "drop-shadow(0 0 10px rgba(0,161,255,0.5))",
    display: "inline-flex",
  },
  heroBrand: {
    color: "#FFF",
    fontSize: "36px",
    letterSpacing: "8px",
    margin: 0,
    fontWeight: 900,
  },
  brandHighlight: { color: "#00A1FF" },
  heroTagline: {
    color: "#8899aa",
    fontSize: "16px",
    lineHeight: "1.6",
    marginBottom: "40px",
  },
  featureList: {
    display: "flex",
    flexDirection: "column",
    gap: "20px",
    marginBottom: "40px",
  },
  featureItem: {
    display: "flex",
    gap: "14px",
    alignItems: "flex-start",
  },
  featureIcon: {
    color: "#00A1FF",
    fontSize: "20px",
    marginTop: "2px",
    flexShrink: 0,
    display: "inline-flex",
  },
  featureTitle: {
    color: "#e0e0e0",
    fontWeight: 700,
    fontSize: "14px",
    marginBottom: "4px",
  },
  featureDesc: {
    color: "#667788",
    fontSize: "13px",
    lineHeight: "1.5",
  },
  heroStats: {
    display: "flex",
    gap: "30px",
    borderTop: "1px solid #1a2030",
    paddingTop: "24px",
  },
  stat: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
  },
  statVal: {
    color: "#00A1FF",
    fontSize: "22px",
    fontWeight: 900,
    letterSpacing: "1px",
  },
  statLabel: {
    color: "#556677",
    fontSize: "11px",
    marginTop: "4px",
    letterSpacing: "0.5px",
  },

  /* ── Right Panel ── */
  rightPanel: {
    width: "480px",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    position: "relative",
    zIndex: 10,
    borderLeft: "1px solid #111827",
    backgroundColor: "rgba(8,10,15,0.6)",
    flexShrink: 0,
  },
  loginBox: {
    width: "380px",
    position: "relative",
  },
  topLine: {
    position: "absolute",
    top: "-1px",
    left: 0,
    width: "100%",
    height: "3px",
    background: "linear-gradient(90deg, transparent, #00A1FF, transparent)",
  },
  header: { textAlign: "center", marginBottom: "32px" },
  loginTitle: {
    color: "#FFF",
    fontSize: "18px",
    fontWeight: 700,
    letterSpacing: "3px",
    margin: 0,
  },
  versionBadge: {
    display: "inline-block",
    padding: "3px 10px",
    backgroundColor: "#002d4a",
    color: "#00A1FF",
    fontSize: "9px",
    borderRadius: "10px",
    marginTop: "10px",
    letterSpacing: "1px",
  },
  form: { display: "flex", flexDirection: "column" },
  inputWrapper: { marginBottom: "20px" },
  label: {
    color: "#555",
    fontSize: "10px",
    fontWeight: "bold",
    marginBottom: "8px",
    display: "block",
    letterSpacing: "1px",
  },
  input: {
    width: "100%",
    padding: "14px",
    backgroundColor: "#0A0B0E",
    border: "1px solid #222",
    color: "#FFF",
    borderRadius: "4px",
    outline: "none",
    transition: "border 0.3s",
    fontSize: "14px",
    boxSizing: "border-box",
  },
  errorMsg: {
    color: "#ff3c66",
    fontSize: "0.85rem",
    marginBottom: "0.75rem",
    textAlign: "center",
    backgroundColor: "rgba(255,60,102,0.08)",
    padding: "8px",
    borderRadius: "4px",
  },
  submitBtn: {
    padding: "14px",
    backgroundColor: "#00A1FF",
    border: "none",
    color: "#FFF",
    borderRadius: "4px",
    cursor: "pointer",
    display: "flex",
    justifyContent: "center",
    alignItems: "center",
    transition: "all 0.3s",
    fontWeight: 700,
    fontSize: "13px",
    letterSpacing: "2px",
  },
  btnText: { marginRight: "10px" },
  btnIcon: { fontSize: "18px", display: "inline-flex" },
  divider: {
    display: "flex",
    alignItems: "center",
    margin: "20px 0",
    gap: "12px",
  },
  dividerLine: {
    flex: 1,
    height: "1px",
    backgroundColor: "#222",
  },
  dividerText: {
    color: "#555",
    fontSize: "12px",
    letterSpacing: "1px",
  },
  demoBtn: {
    width: "100%",
    padding: "14px",
    backgroundColor: "transparent",
    border: "1px solid #00A1FF",
    color: "#00A1FF",
    borderRadius: "4px",
    cursor: "pointer",
    fontWeight: 700,
    fontSize: "12px",
    letterSpacing: "1.5px",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    transition: "all 0.3s",
  },
  demoHint: {
    color: "#445566",
    fontSize: "11px",
    textAlign: "center",
    marginTop: "10px",
    lineHeight: "1.5",
  },
  footer: {
    marginTop: "30px",
    display: "flex",
    justifyContent: "center",
    alignItems: "center",
    opacity: 0.6,
  },
  statusDot: {
    width: "6px",
    height: "6px",
    backgroundColor: "#32CD32",
    borderRadius: "50%",
    marginRight: "10px",
    boxShadow: "0 0 5px #32CD32",
  },
  statusText: { color: "#AAA", fontSize: "9px", letterSpacing: "1px" },
};

export default Login;
