/**
 * Login v3.0 — AutomAção CAD Enterprise
 *
 * 10x Upgrade:
 * - Animated stats counters on left panel
 * - "Esqueceu a senha?" link
 * - empresa field in register mode
 * - Mobile branding above form
 * - Logo pulsing glow
 * - Blueprint SVG overlay
 * - Improved form entrance animation
 * - Animated mode-switch heading
 * - "Lembre-me" checkbox
 * - Styled trust badge chips
 */

import React, { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import {
  AlertCircle,
  ArrowRight,
  Building,
  Eye,
  EyeOff,
  Layers,
  Lock,
  Mail,
  Shield,
  Sparkles,
  Zap,
} from "lucide-react";

import {
  blur,
  breakpoints,
  colors,
  radius,
  shadows,
  spacing,
} from "../design/tokens";
import { textStyles } from "../design/typography";
import {
  fadeIn,
  slideRight,
  staggerContainer,
  staggerItem,
} from "../design/animations";
import { Button } from "../components/ui/Button";
import { Input } from "../components/ui/Input";
import { ApiService } from "../services/api";
import { useLicense } from "../context/LicenseContext";

const AnimatedBackground: React.FC = () => (
  <div style={{ position: "fixed", inset: 0, zIndex: 0, overflow: "hidden" }}>
    <div
      style={{ position: "absolute", inset: 0, background: colors.dark.base }}
    />
    <motion.div
      animate={{ backgroundPosition: ["0% 0%", "100% 100%", "0% 0%"] }}
      transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
      style={{
        position: "absolute",
        inset: 0,
        background: `
          radial-gradient(at 0% 0%, ${colors.primary.DEFAULT}15 0px, transparent 50%),
          radial-gradient(at 100% 0%, ${colors.secondary.DEFAULT}12 0px, transparent 50%),
          radial-gradient(at 100% 100%, ${colors.primary.DEFAULT}10 0px, transparent 50%),
          radial-gradient(at 0% 100%, ${colors.secondary.DEFAULT}08 0px, transparent 50%)
        `,
        backgroundSize: "200% 200%",
      }}
    />

    <motion.div
      animate={{ x: [0, 100, 0], y: [0, -50, 0], scale: [1, 1.2, 1] }}
      transition={{ duration: 20, repeat: Infinity, ease: "easeInOut" }}
      style={{
        position: "absolute",
        top: "15%",
        left: "5%",
        width: "500px",
        height: "500px",
        borderRadius: "50%",
        background: `radial-gradient(circle, ${colors.primary.DEFAULT}12 0%, transparent 70%)`,
        filter: "blur(60px)",
      }}
    />

    <motion.div
      animate={{ x: [0, -80, 0], y: [0, 80, 0], scale: [1, 1.3, 1] }}
      transition={{ duration: 25, repeat: Infinity, ease: "easeInOut" }}
      style={{
        position: "absolute",
        bottom: "10%",
        right: "0%",
        width: "600px",
        height: "600px",
        borderRadius: "50%",
        background: `radial-gradient(circle, ${colors.secondary.DEFAULT}10 0%, transparent 70%)`,
        filter: "blur(80px)",
      }}
    />

    <div
      style={{
        position: "absolute",
        inset: 0,
        backgroundImage: `
          linear-gradient(${colors.primary.DEFAULT}04 1px, transparent 1px),
          linear-gradient(90deg, ${colors.primary.DEFAULT}04 1px, transparent 1px)
        `,
        backgroundSize: "80px 80px",
        opacity: 0.5,
      }}
    />
  </div>
);

const BlueprintOverlay: React.FC = () => (
  <svg
    width="320"
    height="320"
    viewBox="0 0 320 320"
    style={{
      position: "absolute",
      bottom: 0,
      right: 0,
      opacity: 0.05,
      pointerEvents: "none",
    }}
  >
    {Array.from({ length: 9 }).map((_, i) => (
      <line
        key={`d1-${i}`}
        x1={0}
        y1={i * 40}
        x2={320}
        y2={i * 40 + 320}
        stroke={colors.primary.DEFAULT}
        strokeWidth="1"
      />
    ))}
    {Array.from({ length: 9 }).map((_, i) => (
      <line
        key={`d2-${i}`}
        x1={i * 40}
        y1={0}
        x2={i * 40 + 320}
        y2={320}
        stroke={colors.primary.DEFAULT}
        strokeWidth="1"
      />
    ))}
    <circle
      cx="160"
      cy="160"
      r="80"
      stroke={colors.primary.DEFAULT}
      strokeWidth="1"
      fill="none"
    />
    <circle
      cx="160"
      cy="160"
      r="40"
      stroke={colors.primary.DEFAULT}
      strokeWidth="1"
      fill="none"
    />
    <line
      x1="80"
      y1="160"
      x2="240"
      y2="160"
      stroke={colors.primary.DEFAULT}
      strokeWidth="1"
    />
    <line
      x1="160"
      y1="80"
      x2="160"
      y2="240"
      stroke={colors.primary.DEFAULT}
      strokeWidth="1"
    />
  </svg>
);

const STATS = [
  { target: 1200, label: "Engenheiros", suffix: "+" },
  { target: 50000, label: "Projetos CAD", suffix: "+" },
  { target: 99.9, label: "Uptime", suffix: "%" },
];

const features = [
  {
    icon: <Shield size={20} />,
    title: "Segurança Enterprise",
    description: "Criptografia AES-256 e autenticação multifator",
  },
  {
    icon: <Layers size={20} />,
    title: "AutoCAD Integration",
    description: "Conexão direta com AutoCAD via plugin dedicado",
  },
  {
    icon: <Zap size={20} />,
    title: "IA Generativa",
    description: "Geração automática de desenhos e validação de normas",
  },
];

const AnimatedCounter: React.FC<{
  target: number;
  suffix: string;
  label: string;
}> = ({ target, suffix, label }) => {
  const [value, setValue] = useState(0);

  useEffect(() => {
    const durationMs = 1500;
    const steps = 60;
    const increment = target / steps;
    let current = 0;

    const timer = window.setInterval(() => {
      current += increment;
      if (current >= target) {
        setValue(target);
        window.clearInterval(timer);
      } else {
        setValue(Math.floor(current * 10) / 10);
      }
    }, durationMs / steps);

    return () => window.clearInterval(timer);
  }, [target]);

  const displayValue =
    target === 99.9
      ? value.toFixed(1)
      : Math.floor(value).toLocaleString("pt-BR");

  return (
    <div style={{ textAlign: "center" }}>
      <div
        style={{
          ...textStyles.heading.h2,
          color: colors.primary.DEFAULT,
          fontVariantNumeric: "tabular-nums",
          lineHeight: 1,
        }}
      >
        {displayValue}
        {suffix}
      </div>
      <div
        style={{
          ...textStyles.caption,
          color: colors.text.tertiary,
          marginTop: spacing[1],
        }}
      >
        {label}
      </div>
    </div>
  );
};

const Login: React.FC = () => {
  const navigate = useNavigate();
  const { refreshTier } = useLicense();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [empresa, setEmpresa] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [mode, setMode] = useState<"login" | "register">("login");

  useEffect(() => {
    setError("");
  }, [mode]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setIsLoading(true);

    try {
      if (mode === "register") {
        await ApiService.register({
          email,
          senha: password,
          empresa: empresa || undefined,
        });
      }

      const response = await ApiService.login({ email, senha: password });

      if (response.access_token) {
        localStorage.setItem("access_token", response.access_token);
        refreshTier();
        navigate("/dashboard");
      }
    } catch (err: any) {
      setError(err.message || "Erro ao conectar. Tente novamente.");
    } finally {
      setIsLoading(false);
    }
  };

  const enterDemoMode = async () => {
    try {
      await ApiService.demoLogin();
      refreshTier();
      navigate("/dashboard");
    } catch {
      localStorage.setItem("access_token", "demo_token");
      refreshTier();
      navigate("/dashboard");
    }
  };

  return (
    <div style={{ minHeight: "100vh", display: "flex", position: "relative" }}>
      <AnimatedBackground />

      <motion.div
        variants={staggerContainer}
        initial="hidden"
        animate="visible"
        className="login-left"
        style={{
          flex: 1,
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          padding: spacing[12],
          position: "relative",
          zIndex: 1,
          overflow: "hidden",
        }}
      >
        <BlueprintOverlay />

        <motion.div variants={slideRight} style={{ marginBottom: spacing[12] }}>
          <div
            style={{ display: "flex", alignItems: "center", gap: spacing[3] }}
          >
            <motion.div
              animate={{ scale: [1, 1.05, 1], opacity: [1, 0.85, 1] }}
              transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
              style={{
                width: "48px",
                height: "48px",
                borderRadius: radius.lg,
                background: colors.gradient.primary,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                boxShadow: shadows.glowPrimary,
              }}
            >
              <Layers size={24} color="#FFF" />
            </motion.div>
            <div>
              <h1
                style={{
                  margin: 0,
                  ...textStyles.heading.h2,
                  color: colors.text.primary,
                }}
              >
                AutomAção CAD
              </h1>
              <p
                style={{
                  margin: 0,
                  ...textStyles.body.sm,
                  color: colors.text.tertiary,
                }}
              >
                Enterprise Engineering Platform
              </p>
            </div>
          </div>
        </motion.div>

        <motion.div variants={slideRight} style={{ marginBottom: spacing[8] }}>
          <h2
            style={{
              margin: 0,
              ...textStyles.display.lg,
              color: colors.text.primary,
              maxWidth: "500px",
            }}
          >
            Automação{" "}
            <span
              style={{
                background: colors.gradient.primary,
                WebkitBackgroundClip: "text",
                WebkitTextFillColor: "transparent",
                backgroundClip: "text",
              }}
            >
              inteligente
            </span>
            <br />
            para engenharia.
          </h2>
          <p
            style={{
              margin: `${spacing[4]} 0 0`,
              ...textStyles.body.lg,
              color: colors.text.secondary,
              maxWidth: "450px",
            }}
          >
            Transforme seus fluxos de trabalho com IA, integração AutoCAD e
            geração automática de documentação técnica.
          </p>
        </motion.div>

        <motion.div
          variants={fadeIn}
          style={{
            display: "flex",
            gap: spacing[8],
            marginBottom: spacing[10],
            padding: `${spacing[5]} ${spacing[6]}`,
            borderRadius: radius.lg,
            background: "rgba(255,255,255,0.03)",
            border: `1px solid ${colors.border.subtle}`,
            width: "fit-content",
          }}
        >
          {STATS.map((stat) => (
            <AnimatedCounter
              key={stat.label}
              target={stat.target}
              suffix={stat.suffix}
              label={stat.label}
            />
          ))}
        </motion.div>

        <motion.div
          variants={staggerContainer}
          style={{ display: "flex", flexDirection: "column", gap: spacing[4] }}
        >
          {features.map((feature, index) => (
            <motion.div
              key={index}
              variants={staggerItem}
              style={{
                display: "flex",
                alignItems: "flex-start",
                gap: spacing[4],
                padding: spacing[4],
                borderRadius: radius.lg,
                background: "rgba(255, 255, 255, 0.02)",
                border: `1px solid ${colors.border.subtle}`,
              }}
            >
              <div
                style={{
                  width: "40px",
                  height: "40px",
                  borderRadius: radius.md,
                  background: colors.primary.soft,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  color: colors.primary.DEFAULT,
                  flexShrink: 0,
                }}
              >
                {feature.icon}
              </div>
              <div>
                <h4
                  style={{
                    margin: 0,
                    ...textStyles.label.lg,
                    color: colors.text.primary,
                  }}
                >
                  {feature.title}
                </h4>
                <p
                  style={{
                    margin: `${spacing[1]} 0 0`,
                    ...textStyles.body.sm,
                    color: colors.text.tertiary,
                  }}
                >
                  {feature.description}
                </p>
              </div>
            </motion.div>
          ))}
        </motion.div>

        <motion.div
          variants={fadeIn}
          style={{
            display: "flex",
            alignItems: "center",
            gap: spacing[3],
            marginTop: "auto",
            paddingTop: spacing[12],
          }}
        >
          {["Petrobras", "Vale", "Braskem"].map((company, i) => (
            <span
              key={i}
              style={{
                ...textStyles.caption,
                color: colors.text.tertiary,
                textTransform: "uppercase",
                letterSpacing: "0.1em",
                padding: `${spacing[2]} ${spacing[4]}`,
                border: `1px solid ${colors.border.subtle}`,
                borderRadius: radius.lg,
                background: "rgba(255,255,255,0.03)",
              }}
            >
              {company}
            </span>
          ))}
        </motion.div>
      </motion.div>

      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.3 }}
        className="login-right"
        style={{
          flex: 1,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          padding: spacing[8],
          position: "relative",
          zIndex: 1,
          flexDirection: "column",
        }}
      >
        <div
          className="login-mobile-brand"
          style={{
            display: "none",
            marginBottom: spacing[8],
            textAlign: "center",
          }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: spacing[3],
              marginBottom: spacing[2],
            }}
          >
            <div
              style={{
                width: "40px",
                height: "40px",
                borderRadius: radius.lg,
                background: colors.gradient.primary,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                boxShadow: shadows.glowPrimary,
              }}
            >
              <Layers size={20} color="#FFF" />
            </div>
            <span
              style={{ ...textStyles.heading.h3, color: colors.text.primary }}
            >
              AutomAção CAD
            </span>
          </div>
          <p
            style={{
              ...textStyles.body.sm,
              color: colors.text.tertiary,
              margin: 0,
            }}
          >
            Enterprise Engineering Platform
          </p>
        </div>

        <motion.div
          initial={{ opacity: 0, scale: 0.96, filter: "blur(10px)" }}
          animate={{ opacity: 1, scale: 1, filter: "blur(0px)" }}
          transition={{ duration: 0.5, ease: "easeOut" }}
          style={{
            width: "100%",
            maxWidth: "420px",
            padding: spacing[10],
            borderRadius: radius["2xl"],
            background: "rgba(255, 255, 255, 0.03)",
            backdropFilter: `blur(${blur.xl})`,
            WebkitBackdropFilter: `blur(${blur.xl})`,
            border: `1px solid ${colors.border.subtle}`,
            boxShadow: shadows.modal,
          }}
        >
          <AnimatePresence mode="wait">
            <motion.div
              key={mode}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.2 }}
              style={{ marginBottom: spacing[6], textAlign: "center" }}
            >
              <h2
                style={{
                  margin: 0,
                  ...textStyles.heading.h3,
                  color: colors.text.primary,
                }}
              >
                {mode === "login" ? "Bem-vindo de volta" : "Crie sua conta"}
              </h2>
              <p
                style={{
                  margin: `${spacing[1]} 0 0`,
                  ...textStyles.body.sm,
                  color: colors.text.tertiary,
                }}
              >
                {mode === "login"
                  ? "Entre para continuar na plataforma"
                  : "Comece gratuitamente hoje"}
              </p>
            </motion.div>
          </AnimatePresence>

          <div
            style={{
              display: "flex",
              marginBottom: spacing[8],
              padding: spacing[1],
              borderRadius: radius.lg,
              background: colors.dark.elevated,
            }}
          >
            {(["login", "register"] as const).map((m) => (
              <button
                key={m}
                onClick={() => setMode(m)}
                style={{
                  flex: 1,
                  padding: `${spacing[2]} ${spacing[4]}`,
                  borderRadius: radius.md,
                  border: "none",
                  background:
                    mode === m ? colors.primary.DEFAULT : "transparent",
                  color: mode === m ? "#FFF" : colors.text.tertiary,
                  ...textStyles.label.md,
                  cursor: "pointer",
                  transition: "all 200ms ease-out",
                }}
              >
                {m === "login" ? "Entrar" : "Criar Conta"}
              </button>
            ))}
          </div>

          <form onSubmit={handleSubmit}>
            <div
              style={{
                display: "flex",
                flexDirection: "column",
                gap: spacing[5],
              }}
            >
              <Input
                type="email"
                label="Email"
                placeholder="seu@email.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                leftIcon={<Mail size={18} />}
                variant="filled"
                required
                autoComplete="email"
              />

              <Input
                type={showPassword ? "text" : "password"}
                label="Senha"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                leftIcon={<Lock size={18} />}
                rightIcon={
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    style={{
                      background: "none",
                      border: "none",
                      cursor: "pointer",
                      padding: 0,
                      color: colors.text.tertiary,
                    }}
                    aria-label={
                      showPassword ? "Ocultar senha" : "Mostrar senha"
                    }
                  >
                    {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                  </button>
                }
                variant="filled"
                required
                minLength={6}
                autoComplete={
                  mode === "login" ? "current-password" : "new-password"
                }
              />

              {mode === "login" && (
                <div
                  style={{ textAlign: "right", marginTop: `-${spacing[3]}` }}
                >
                  <Link
                    to="/forgot-password"
                    style={{
                      ...textStyles.body.sm,
                      color: colors.text.tertiary,
                      textDecoration: "none",
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.color = colors.primary.DEFAULT;
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.color = colors.text.tertiary;
                    }}
                  >
                    Esqueceu a senha?
                  </Link>
                </div>
              )}

              {mode === "register" && (
                <Input
                  type="text"
                  label="Empresa (opcional)"
                  placeholder="Nome da sua empresa"
                  value={empresa}
                  onChange={(e) => setEmpresa(e.target.value)}
                  leftIcon={<Building size={18} />}
                  variant="filled"
                  autoComplete="organization"
                />
              )}

              {mode === "login" && (
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: spacing[2],
                  }}
                >
                  <input
                    type="checkbox"
                    id="rememberMe"
                    style={{
                      accentColor: colors.primary.DEFAULT,
                      cursor: "pointer",
                    }}
                  />
                  <label
                    htmlFor="rememberMe"
                    style={{
                      ...textStyles.body.sm,
                      color: colors.text.tertiary,
                      cursor: "pointer",
                    }}
                  >
                    Lembre-me
                  </label>
                </div>
              )}

              <AnimatePresence mode="wait">
                {error && (
                  <motion.div
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -10 }}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: spacing[2],
                      padding: spacing[3],
                      borderRadius: radius.md,
                      background: colors.danger.soft,
                      color: colors.danger.DEFAULT,
                      ...textStyles.body.sm,
                    }}
                  >
                    <AlertCircle size={16} />
                    {error}
                  </motion.div>
                )}
              </AnimatePresence>

              <Button
                type="submit"
                variant="primary"
                size="lg"
                fullWidth
                glow
                isLoading={isLoading}
                rightIcon={<ArrowRight size={18} />}
              >
                {mode === "login" ? "Entrar" : "Criar Conta"}
              </Button>
            </div>
          </form>

          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: spacing[4],
              margin: `${spacing[6]} 0`,
            }}
          >
            <div
              style={{
                flex: 1,
                height: "1px",
                background: colors.border.subtle,
              }}
            />
            <span
              style={{ ...textStyles.caption, color: colors.text.tertiary }}
            >
              ou
            </span>
            <div
              style={{
                flex: 1,
                height: "1px",
                background: colors.border.subtle,
              }}
            />
          </div>

          <Button
            variant="outline"
            size="lg"
            fullWidth
            leftIcon={<Sparkles size={18} />}
            onClick={enterDemoMode}
          >
            Explorar Demonstração
          </Button>

          <div
            style={{
              display: "flex",
              justifyContent: "center",
              gap: spacing[4],
              marginTop: spacing[6],
            }}
          >
            {["Termos", "Privacidade", "Suporte"].map((link, i) => (
              <a
                key={i}
                href={`/${link.toLowerCase()}`}
                style={{
                  ...textStyles.caption,
                  color: colors.text.tertiary,
                  textDecoration: "none",
                }}
              >
                {link}
              </a>
            ))}
          </div>
        </motion.div>
      </motion.div>

      <style>{`
        @media (max-width: ${breakpoints.lg}px) {
          .login-left {
            display: none !important;
          }
          .login-right {
            flex: 1 !important;
            padding: ${spacing[4]} !important;
            align-items: flex-start !important;
            padding-top: ${spacing[8]} !important;
          }
          .login-mobile-brand {
            display: block !important;
          }
        }
      `}</style>
    </div>
  );
};

export default Login;
