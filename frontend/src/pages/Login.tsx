import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import {
  FaFingerprint,
  FaShieldAlt,
  FaMicrochip,
  FaRocket,
  FaDraftingCompass,
  FaBolt,
  FaChartLine,
  FaIndustry,
  FaCogs,
  FaLayerGroup,
  FaCrown,
} from "react-icons/fa";
import { API_BASE_URL, ApiService } from "../services/api";

// ═══════════════════════════════════════════════════════════════════════════
// ANIMATED BACKGROUND
// ═══════════════════════════════════════════════════════════════════════════

const AnimatedBackground: React.FC = () => (
  <div
    style={{
      position: "absolute",
      inset: 0,
      overflow: "hidden",
      zIndex: 0,
    }}
  >
    {/* Gradient base */}
    <div
      style={{
        position: "absolute",
        inset: 0,
        background:
          "linear-gradient(135deg, #030508 0%, #0a1628 40%, #071020 70%, #030508 100%)",
      }}
    />

    {/* Animated orbs */}
    <motion.div
      animate={{
        x: [0, 100, 0],
        y: [0, -50, 0],
        scale: [1, 1.2, 1],
      }}
      transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
      style={{
        position: "absolute",
        top: "20%",
        left: "10%",
        width: "400px",
        height: "400px",
        borderRadius: "50%",
        background:
          "radial-gradient(circle, rgba(0,161,255,0.15) 0%, transparent 70%)",
        filter: "blur(40px)",
      }}
    />
    <motion.div
      animate={{
        x: [0, -80, 0],
        y: [0, 80, 0],
        scale: [1, 1.3, 1],
      }}
      transition={{ duration: 25, repeat: Infinity, ease: "linear" }}
      style={{
        position: "absolute",
        bottom: "10%",
        right: "5%",
        width: "500px",
        height: "500px",
        borderRadius: "50%",
        background:
          "radial-gradient(circle, rgba(0,161,255,0.1) 0%, transparent 70%)",
        filter: "blur(60px)",
      }}
    />

    {/* Grid overlay */}
    <div
      style={{
        position: "absolute",
        inset: 0,
        backgroundImage: `
        linear-gradient(rgba(0,161,255,0.03) 1px, transparent 1px),
        linear-gradient(90deg, rgba(0,161,255,0.03) 1px, transparent 1px)
      `,
        backgroundSize: "60px 60px",
        opacity: 0.5,
      }}
    />
  </div>
);

// ═══════════════════════════════════════════════════════════════════════════
// FEATURE CARDS
// ═══════════════════════════════════════════════════════════════════════════

const FEATURES = [
  {
    icon: <FaDraftingCompass />,
    title: "Automação CAD",
    desc: "Geração automatizada de desenhos de piping, P&ID e isométricos direto no AutoCAD.",
    color: "#00A1FF",
  },
  {
    icon: <FaBolt />,
    title: "IA Integrada",
    desc: "Inteligência artificial para validação de normas (ASME, Petrobras N-series) em tempo real.",
    color: "#10B981",
  },
  {
    icon: <FaChartLine />,
    title: "Quality Gate",
    desc: "Controle de qualidade com rastreabilidade completa e relatórios certificáveis.",
    color: "#8B5CF6",
  },
  {
    icon: <FaIndustry />,
    title: "CNC/Plasma",
    desc: "Geração de G-code otimizado para corte plasma com nesting inteligente.",
    color: "#F59E0B",
  },
];

const STATS = [
  { value: "50+", label: "Normas Suportadas" },
  { value: "10x", label: "Mais Rápido" },
  { value: "99.9%", label: "Precisão" },
  { value: "24/7", label: "Disponibilidade" },
];

// ═══════════════════════════════════════════════════════════════════════════
// LOGIN COMPONENT
// ═══════════════════════════════════════════════════════════════════════════

const Login = () => {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [demoLoading, setDemoLoading] = useState(false);
  const [focusedInput, setFocusedInput] = useState<string | null>(null);
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
      navigate("/dashboard");
    } catch (err: any) {
      const status = err?.response?.status;
      if (status === 401) {
        setError("Credenciais inválidas. Verifique e-mail e senha.");
      } else if (status === 429) {
        setError("Muitas tentativas. Aguarde um momento.");
      } else if (!status) {
        setError(`Servidor indisponível. Recarregue e tente novamente.`);
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
      navigate("/dashboard");
    } catch (err: any) {
      const status = err?.response?.status;
      if (status === 429) {
        setError("Muitas tentativas. Aguarde e tente novamente.");
      } else if (status && status >= 500) {
        setError("Servidor temporariamente indisponível.");
      } else {
        setError("Não foi possível conectar. Tente novamente.");
      }
      setDemoLoading(false);
    }
  };

  return (
    <>
      <div style={s.container}>
        <AnimatedBackground />

        {/* ═══════════════ LEFT PANEL - BRANDING ═══════════════ */}
        <motion.div
          initial={{ opacity: 0, x: -50 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.8 }}
          style={s.leftPanel}
        >
          <div style={s.heroContent}>
            {/* Logo */}
            <motion.div
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ delay: 0.2, type: "spring", stiffness: 200 }}
              style={s.logoRow}
            >
              <div style={s.logoIcon}>
                <FaMicrochip size={32} />
              </div>
              <div>
                <h1 style={s.brand}>
                  ENGENHARIA <span style={s.brandHighlight}>CAD</span>
                </h1>
                <p style={s.version}>PLATAFORMA INDUSTRIAL v2.0</p>
              </div>
            </motion.div>

            {/* Tagline */}
            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.4 }}
              style={s.tagline}
            >
              Plataforma de Automação CAD Industrial com{" "}
              <span style={{ color: "#00A1FF" }}>Inteligência Artificial</span>{" "}
              para engenharia de piping, validação de normas e controle de
              qualidade.
            </motion.p>

            {/* Features Grid */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.5 }}
              style={s.featuresGrid}
            >
              {FEATURES.map((f, i) => (
                <motion.div
                  key={i}
                  whileHover={{ scale: 1.02, y: -4 }}
                  style={{
                    ...s.featureCard,
                    borderColor: `${f.color}40`,
                    boxShadow: `0 4px 20px ${f.color}10`,
                  }}
                >
                  <div style={{ ...s.featureIcon, color: f.color }}>
                    {f.icon}
                  </div>
                  <div>
                    <div style={s.featureTitle}>{f.title}</div>
                    <div style={s.featureDesc}>{f.desc}</div>
                  </div>
                </motion.div>
              ))}
            </motion.div>

            {/* Stats */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.7 }}
              style={s.statsRow}
            >
              {STATS.map((stat, i) => (
                <div key={i} style={s.stat}>
                  <span style={s.statValue}>{stat.value}</span>
                  <span style={s.statLabel}>{stat.label}</span>
                </div>
              ))}
            </motion.div>
          </div>
        </motion.div>

        {/* ═══════════════ RIGHT PANEL - LOGIN FORM ═══════════════ */}
        <motion.div
          initial={{ opacity: 0, x: 50 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.8 }}
          style={s.rightPanel}
        >
          <div style={s.formContainer}>
            {/* Glow effect */}
            <div style={s.formGlow} />

            {/* Top accent line */}
            <motion.div
              initial={{ scaleX: 0 }}
              animate={{ scaleX: 1 }}
              transition={{ delay: 0.5, duration: 0.5 }}
              style={s.accentLine}
            />

            {/* Header */}
            <div style={s.formHeader}>
              <motion.div
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ delay: 0.3, type: "spring" }}
                style={s.lockIcon}
              >
                <FaShieldAlt size={24} />
              </motion.div>
              <h2 style={s.formTitle}>Acesso ao Sistema</h2>
              <p style={s.formSubtitle}>Faça login para acessar sua conta</p>
            </div>

            {/* Form */}
            <form onSubmit={handleLogin} style={s.form}>
              <div style={s.inputGroup}>
                <label style={s.label}>E-MAIL</label>
                <motion.input
                  type="email"
                  placeholder="operador@empresa.com.br"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  onFocus={() => setFocusedInput("email")}
                  onBlur={() => setFocusedInput(null)}
                  style={{
                    ...s.input,
                    borderColor:
                      focusedInput === "email" ? "#00A1FF" : "#1a2030",
                    boxShadow:
                      focusedInput === "email"
                        ? "0 0 20px rgba(0,161,255,0.2)"
                        : "none",
                  }}
                  whileFocus={{ scale: 1.01 }}
                />
              </div>

              <div style={s.inputGroup}>
                <label style={s.label}>SENHA</label>
                <motion.input
                  type="password"
                  placeholder="••••••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  onFocus={() => setFocusedInput("password")}
                  onBlur={() => setFocusedInput(null)}
                  style={{
                    ...s.input,
                    borderColor:
                      focusedInput === "password" ? "#00A1FF" : "#1a2030",
                    boxShadow:
                      focusedInput === "password"
                        ? "0 0 20px rgba(0,161,255,0.2)"
                        : "none",
                  }}
                  whileFocus={{ scale: 1.01 }}
                />
              </div>

              <AnimatePresence>
                {error && (
                  <motion.div
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -10 }}
                    style={s.errorBox}
                  >
                    {error}
                  </motion.div>
                )}
              </AnimatePresence>

              <motion.button
                type="submit"
                disabled={loading || demoLoading}
                whileHover={{ scale: loading ? 1 : 1.02 }}
                whileTap={{ scale: loading ? 1 : 0.98 }}
                style={{
                  ...s.submitBtn,
                  opacity: loading ? 0.7 : 1,
                }}
              >
                {loading ? (
                  <motion.div
                    animate={{ rotate: 360 }}
                    transition={{
                      duration: 1,
                      repeat: Infinity,
                      ease: "linear",
                    }}
                  >
                    <FaCogs size={18} />
                  </motion.div>
                ) : (
                  <>
                    <span>ENTRAR</span>
                    <FaFingerprint size={18} />
                  </>
                )}
              </motion.button>
            </form>

            {/* Divider */}
            <div style={s.divider}>
              <div style={s.dividerLine} />
              <span style={s.dividerText}>ou</span>
              <div style={s.dividerLine} />
            </div>

            {/* Demo Button */}
            <motion.button
              onClick={handleDemo}
              disabled={loading || demoLoading}
              whileHover={{ scale: demoLoading ? 1 : 1.02 }}
              whileTap={{ scale: demoLoading ? 1 : 0.98 }}
              style={{
                ...s.demoBtn,
                opacity: demoLoading ? 0.7 : 1,
              }}
            >
              {demoLoading ? (
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                >
                  <FaCogs size={16} />
                </motion.div>
              ) : (
                <>
                  <FaRocket size={16} />
                  <span>EXPLORAR DEMONSTRAÇÃO</span>
                </>
              )}
            </motion.button>
            <p style={s.demoHint}>
              Acesso completo sem cadastro — veja o sistema em ação
            </p>

            {/* Ver Planos */}
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => navigate("/pricing")}
              style={s.pricingBtn}
            >
              <FaCrown size={14} />
              <span>Ver Planos & Preços</span>
            </motion.button>

            {/* Footer */}
            <div style={s.footer}>
              <motion.div
                animate={{ scale: [1, 1.2, 1] }}
                transition={{ duration: 2, repeat: Infinity }}
                style={s.statusDot}
              />
              <span style={s.statusText}>CONEXÃO SEGURA AES-256</span>
            </div>
          </div>
        </motion.div>
      </div>
      {/* Mobile / Responsive CSS */}
      <style>{`
      @media (max-width: 900px) {
        .login-container { flex-direction: column !important; height: auto !important; min-height: 100vh !important; overflow-y: auto !important; }
        .login-left { display: none !important; }
        .login-right { width: 100% !important; min-height: 100vh !important; padding: 32px 20px !important; }
        .login-form-container { width: 100% !important; max-width: 420px !important; margin: 0 auto !important; }
      }
      @media (max-width: 480px) {
        .login-right { padding: 24px 16px !important; }
      }
    `}</style>
    </>
  );
};

// ═══════════════════════════════════════════════════════════════════════════
// STYLES
// ═══════════════════════════════════════════════════════════════════════════

const s: Record<string, React.CSSProperties> = {
  container: {
    minHeight: "100vh",
    display: "flex",
    position: "relative",
    overflow: "hidden",
    fontFamily: "'Inter', 'Segoe UI', Roboto, sans-serif",
  },

  // ═══════════ LEFT PANEL ═══════════
  leftPanel: {
    flex: 1,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    position: "relative",
    zIndex: 10,
    padding: "48px",
  },
  heroContent: {
    maxWidth: "560px",
  },
  logoRow: {
    display: "flex",
    alignItems: "center",
    gap: "16px",
    marginBottom: "32px",
  },
  logoIcon: {
    width: "64px",
    height: "64px",
    borderRadius: "16px",
    background: "linear-gradient(135deg, #00A1FF 0%, #0077CC 100%)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    color: "#FFF",
    boxShadow: "0 8px 32px rgba(0,161,255,0.4)",
  },
  brand: {
    color: "#FFF",
    fontSize: "32px",
    letterSpacing: "6px",
    margin: 0,
    fontWeight: 800,
  },
  brandHighlight: {
    color: "#00A1FF",
  },
  version: {
    color: "#556677",
    fontSize: "11px",
    letterSpacing: "3px",
    marginTop: "4px",
  },
  tagline: {
    color: "#8899aa",
    fontSize: "16px",
    lineHeight: "1.8",
    marginBottom: "40px",
  },
  featuresGrid: {
    display: "grid",
    gridTemplateColumns: "1fr 1fr",
    gap: "16px",
    marginBottom: "40px",
  },
  featureCard: {
    display: "flex",
    gap: "14px",
    padding: "16px",
    backgroundColor: "rgba(255,255,255,0.02)",
    border: "1px solid rgba(255,255,255,0.05)",
    borderRadius: "12px",
    cursor: "default",
    transition: "all 0.3s ease",
  },
  featureIcon: {
    fontSize: "22px",
    marginTop: "2px",
    flexShrink: 0,
  },
  featureTitle: {
    color: "#e0e0e0",
    fontWeight: 700,
    fontSize: "13px",
    marginBottom: "6px",
  },
  featureDesc: {
    color: "#667788",
    fontSize: "12px",
    lineHeight: "1.5",
  },
  statsRow: {
    display: "flex",
    gap: "32px",
    borderTop: "1px solid #1a2030",
    paddingTop: "28px",
  },
  stat: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
  },
  statValue: {
    color: "#00A1FF",
    fontSize: "24px",
    fontWeight: 900,
    letterSpacing: "1px",
  },
  statLabel: {
    color: "#556677",
    fontSize: "10px",
    marginTop: "6px",
    letterSpacing: "1px",
    textTransform: "uppercase",
  },

  // ═══════════ RIGHT PANEL ═══════════
  rightPanel: {
    width: "520px",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    position: "relative",
    zIndex: 10,
    borderLeft: "1px solid rgba(255,255,255,0.05)",
    backgroundColor: "rgba(5,8,12,0.8)",
    backdropFilter: "blur(20px)",
    flexShrink: 0,
  },
  formContainer: {
    width: "380px",
    position: "relative",
  },
  formGlow: {
    position: "absolute",
    top: "-50%",
    left: "50%",
    transform: "translateX(-50%)",
    width: "200px",
    height: "200px",
    background:
      "radial-gradient(circle, rgba(0,161,255,0.15) 0%, transparent 70%)",
    filter: "blur(40px)",
    pointerEvents: "none",
  },
  accentLine: {
    position: "absolute",
    top: 0,
    left: 0,
    right: 0,
    height: "3px",
    background: "linear-gradient(90deg, transparent, #00A1FF, transparent)",
    transformOrigin: "center",
  },
  formHeader: {
    textAlign: "center",
    marginBottom: "32px",
  },
  lockIcon: {
    width: "56px",
    height: "56px",
    borderRadius: "16px",
    background:
      "linear-gradient(135deg, rgba(0,161,255,0.2) 0%, rgba(0,161,255,0.05) 100%)",
    border: "1px solid rgba(0,161,255,0.3)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    color: "#00A1FF",
    margin: "0 auto 20px auto",
  },
  formTitle: {
    color: "#FFF",
    fontSize: "22px",
    fontWeight: 700,
    letterSpacing: "2px",
    margin: 0,
  },
  formSubtitle: {
    color: "#667788",
    fontSize: "13px",
    marginTop: "8px",
  },
  form: {
    display: "flex",
    flexDirection: "column",
  },
  inputGroup: {
    marginBottom: "20px",
  },
  label: {
    color: "#667788",
    fontSize: "11px",
    fontWeight: 600,
    marginBottom: "10px",
    display: "block",
    letterSpacing: "2px",
  },
  input: {
    width: "100%",
    padding: "16px 18px",
    backgroundColor: "rgba(10,15,25,0.8)",
    border: "1px solid #1a2030",
    color: "#FFF",
    borderRadius: "12px",
    outline: "none",
    transition: "all 0.3s ease",
    fontSize: "14px",
    boxSizing: "border-box",
  },
  errorBox: {
    color: "#ff4466",
    fontSize: "13px",
    marginBottom: "16px",
    textAlign: "center",
    backgroundColor: "rgba(255,68,102,0.1)",
    padding: "12px",
    borderRadius: "10px",
    border: "1px solid rgba(255,68,102,0.2)",
  },
  submitBtn: {
    padding: "16px",
    background: "linear-gradient(135deg, #00A1FF 0%, #0077CC 100%)",
    border: "none",
    color: "#FFF",
    borderRadius: "12px",
    cursor: "pointer",
    display: "flex",
    justifyContent: "center",
    alignItems: "center",
    gap: "12px",
    fontWeight: 700,
    fontSize: "14px",
    letterSpacing: "2px",
    boxShadow: "0 8px 32px rgba(0,161,255,0.3)",
    transition: "all 0.3s ease",
  },
  divider: {
    display: "flex",
    alignItems: "center",
    margin: "24px 0",
    gap: "16px",
  },
  dividerLine: {
    flex: 1,
    height: "1px",
    backgroundColor: "#1a2030",
  },
  dividerText: {
    color: "#556677",
    fontSize: "12px",
    letterSpacing: "2px",
  },
  demoBtn: {
    width: "100%",
    padding: "14px",
    backgroundColor: "transparent",
    border: "2px solid #00A1FF",
    color: "#00A1FF",
    borderRadius: "12px",
    cursor: "pointer",
    fontWeight: 600,
    fontSize: "13px",
    letterSpacing: "2px",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    gap: "12px",
    transition: "all 0.3s ease",
  },
  demoHint: {
    color: "#556677",
    fontSize: "12px",
    textAlign: "center",
    marginTop: "12px",
    lineHeight: "1.6",
  },
  pricingBtn: {
    width: "100%",
    padding: "12px",
    backgroundColor: "transparent",
    border: "1px solid #1a2030",
    color: "#8899aa",
    borderRadius: "10px",
    cursor: "pointer",
    fontWeight: 600,
    fontSize: "13px",
    letterSpacing: "1px",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    gap: "8px",
    transition: "all 0.2s ease",
    marginTop: "12px",
  },
  footer: {
    marginTop: "32px",
    display: "flex",
    justifyContent: "center",
    alignItems: "center",
    opacity: 0.7,
  },
  statusDot: {
    width: "8px",
    height: "8px",
    backgroundColor: "#10B981",
    borderRadius: "50%",
    marginRight: "10px",
    boxShadow: "0 0 10px #10B981",
  },
  statusText: {
    color: "#667788",
    fontSize: "10px",
    letterSpacing: "2px",
  },
};

export default Login;
