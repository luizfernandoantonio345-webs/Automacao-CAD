import React, { useState, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import {
  FaCrown,
  FaRocket,
  FaBuilding,
  FaCheck,
  FaTimes,
  FaMicrochip,
  FaShieldAlt,
  FaBolt,
  FaHeadset,
  FaInfinity,
  FaStar,
  FaArrowRight,
  FaUsers,
  FaServer,
  FaBrain,
  FaChartLine,
  FaLock,
  FaCalculator,
  FaQuoteLeft,
  FaClock,
  FaMoneyBillWave,
} from "react-icons/fa";
import { COLORS, SHADOWS, premiumStyles, animations } from "../styles/premium";

// ═══════════════════════════════════════════════════════════════════════════
// ANIMATED BACKGROUND (mesmo da Login)
// ═══════════════════════════════════════════════════════════════════════════

const AnimatedBackground: React.FC = () => (
  <div
    style={{ position: "absolute", inset: 0, overflow: "hidden", zIndex: 0 }}
  >
    <div
      style={{
        position: "absolute",
        inset: 0,
        background: COLORS.gradientDark,
      }}
    />

    <motion.div
      animate={{ x: [0, 100, 0], y: [0, -50, 0], scale: [1, 1.2, 1] }}
      transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
      style={{
        position: "absolute",
        top: "10%",
        left: "5%",
        width: "600px",
        height: "600px",
        borderRadius: "50%",
        background: `radial-gradient(circle, ${COLORS.primaryGlow} 0%, transparent 70%)`,
        filter: "blur(80px)",
      }}
    />
    <motion.div
      animate={{ x: [0, -80, 0], y: [0, 80, 0], scale: [1, 1.3, 1] }}
      transition={{ duration: 25, repeat: Infinity, ease: "linear" }}
      style={{
        position: "absolute",
        bottom: "5%",
        right: "10%",
        width: "500px",
        height: "500px",
        borderRadius: "50%",
        background:
          "radial-gradient(circle, rgba(139,92,246,0.15) 0%, transparent 70%)",
        filter: "blur(60px)",
      }}
    />

    <div style={premiumStyles.gridOverlay} />
  </div>
);

// ═══════════════════════════════════════════════════════════════════════════
// PLANOS E PREÇOS
// ═══════════════════════════════════════════════════════════════════════════

interface PlanFeature {
  text: string;
  included: boolean;
  highlight?: boolean;
}

interface Plan {
  id: string;
  name: string;
  icon: React.ReactNode;
  price: number;
  period: string;
  description: string;
  color: string;
  popular?: boolean;
  features: PlanFeature[];
  limits: {
    machines: number;
    projects: number | "unlimited";
    aiQueries: number | "unlimited";
    support: string;
  };
}

const PLANS: Plan[] = [
  {
    id: "starter",
    name: "Starter",
    icon: <FaRocket />,
    price: 297,
    period: "/mês",
    description: "Ideal para profissionais autônomos e pequenos escritórios",
    color: "#10B981",
    features: [
      { text: "Automação CAD básica", included: true },
      { text: "Geração de desenhos P&ID", included: true },
      { text: "Validação ASME básica", included: true },
      { text: "Exportação DXF/DWG", included: true },
      { text: "5 projetos simultâneos", included: true },
      { text: "Suporte por email", included: true },
      { text: "IA Assistente (100 consultas/mês)", included: true },
      { text: "Controle CNC básico", included: false },
      { text: "Nesting inteligente", included: false },
      { text: "API de integração", included: false },
      { text: "Múltiplas licenças", included: false },
      { text: "Suporte prioritário", included: false },
    ],
    limits: {
      machines: 1,
      projects: 5,
      aiQueries: 100,
      support: "Email (48h)",
    },
  },
  {
    id: "professional",
    name: "Professional",
    icon: <FaCrown />,
    price: 697,
    period: "/mês",
    description: "Para empresas de engenharia em crescimento",
    color: "#00A1FF",
    popular: true,
    features: [
      { text: "Tudo do plano Starter", included: true, highlight: true },
      { text: "Automação CAD avançada", included: true },
      { text: "Validação completa (ASME, Petrobras N-series)", included: true },
      { text: "Controle CNC/Plasma completo", included: true },
      { text: "Nesting inteligente com otimização", included: true },
      { text: "IA Assistente (500 consultas/mês)", included: true },
      { text: "20 projetos simultâneos", included: true },
      { text: "Relatórios certificáveis", included: true },
      { text: "Integração AutoCAD automática", included: true },
      { text: "Suporte prioritário (24h)", included: true },
      { text: "API de integração", included: false },
      { text: "Múltiplas licenças", included: false },
    ],
    limits: {
      machines: 2,
      projects: 20,
      aiQueries: 500,
      support: "Prioritário (24h)",
    },
  },
  {
    id: "enterprise",
    name: "Enterprise",
    icon: <FaBuilding />,
    price: 1497,
    period: "/mês",
    description: "Solução completa para grandes operações industriais",
    color: "#8B5CF6",
    features: [
      { text: "Tudo do plano Professional", included: true, highlight: true },
      { text: "Projetos ilimitados", included: true },
      { text: "IA Assistente ilimitada", included: true },
      { text: "API completa de integração", included: true },
      { text: "Até 10 licenças incluídas", included: true },
      { text: "White-label opcional", included: true },
      { text: "Treinamento da equipe (8h)", included: true },
      { text: "Gerente de conta dedicado", included: true },
      { text: "SLA 99.9% garantido", included: true },
      { text: "Backup em nuvem dedicado", included: true },
      { text: "Customização de relatórios", included: true },
      { text: "Suporte 24/7 com telefone", included: true },
    ],
    limits: {
      machines: 10,
      projects: "unlimited",
      aiQueries: "unlimited",
      support: "24/7 Telefone + Chat",
    },
  },
];

// Benefícios gerais
const BENEFITS = [
  {
    icon: <FaShieldAlt />,
    title: "Segurança Máxima",
    desc: "Criptografia AES-256 e autenticação por hardware (HWID)",
  },
  {
    icon: <FaBrain />,
    title: "IA Integrada",
    desc: "Assistente inteligente treinado em normas industriais",
  },
  {
    icon: <FaBolt />,
    title: "Alta Performance",
    desc: "Processamento otimizado para projetos complexos",
  },
  {
    icon: <FaHeadset />,
    title: "Suporte Especializado",
    desc: "Equipe técnica de engenheiros disponível",
  },
];

// Depoimentos
const TESTIMONIALS = [
  {
    name: "Carlos M.",
    role: "Eng. Mecânico",
    company: "Petrobras",
    text: "Reduziu em 80% o tempo de geração de P&IDs. Antes levávamos 3 dias, agora são 4 horas.",
    stars: 5,
  },
  {
    name: "Ana L.",
    role: "Coord. de Projetos",
    company: "Vale S.A.",
    text: "A validação automática ASME nos poupou de 2 retrabalhos que custariam R$ 50 mil cada.",
    stars: 5,
  },
  {
    name: "Roberto S.",
    role: "Diretor Técnico",
    company: "Engevix Engenharia",
    text: "O nesting inteligente reduziu nosso desperdício de chapa em 32%. O ROI foi imediato.",
    stars: 5,
  },
];

// ═══════════════════════════════════════════════════════════════════════════
// COMPONENTE PRINCIPAL
// ═══════════════════════════════════════════════════════════════════════════

const Pricing: React.FC = () => {
  const navigate = useNavigate();
  const [billingPeriod, setBillingPeriod] = useState<"monthly" | "annual">(
    "monthly",
  );
  const [hoveredPlan, setHoveredPlan] = useState<string | null>(null);
  const [projectsPerMonth, setProjectsPerMonth] = useState(10);

  const getPrice = (basePrice: number) => {
    if (billingPeriod === "annual") {
      return Math.round(basePrice * 0.8); // 20% desconto anual
    }
    return basePrice;
  };

  const roi = useMemo(() => {
    const hoursPerProjectManual = 12;
    const hoursPerProjectAutomated = 3;
    const hoursSaved =
      (hoursPerProjectManual - hoursPerProjectAutomated) * projectsPerMonth;
    const hourlyRate = 120; // R$/hora engenheiro
    const moneySaved = hoursSaved * hourlyRate;
    const planCost = getPrice(697); // Professional como referência
    const netSaving = moneySaved - planCost;
    const paybackDays =
      moneySaved > 0
        ? Math.max(1, Math.round((planCost / moneySaved) * 30))
        : 30;
    return { hoursSaved, moneySaved, netSaving, paybackDays };
  }, [projectsPerMonth, billingPeriod]);

  const handleSelectPlan = (planId: string) => {
    navigate(`/checkout?plan=${planId}&billing=${billingPeriod}`);
  };

  return (
    <div style={styles.container}>
      <AnimatedBackground />

      <div style={styles.content}>
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          style={styles.header}
        >
          <div style={styles.logoRow}>
            <motion.div
              animate={{ rotate: [0, 360] }}
              transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
              style={styles.logoIcon}
            >
              <FaMicrochip size={28} />
            </motion.div>
            <div>
              <h1 style={styles.brand}>
                ENGENHARIA <span style={{ color: COLORS.primary }}>CAD</span>
              </h1>
              <p style={styles.tagline}>PLATAFORMA INDUSTRIAL v2.0</p>
            </div>
          </div>

          <h2 style={styles.title}>
            Escolha o plano ideal para sua{" "}
            <span style={{ color: COLORS.primary }}>operação</span>
          </h2>
          <p style={styles.subtitle}>
            Todos os planos incluem atualizações gratuitas, suporte técnico e
            garantia de satisfação de 30 dias
          </p>

          {/* Trial Banner */}
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.3 }}
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              gap: "12px",
              padding: "16px 32px",
              background:
                "linear-gradient(135deg, rgba(0,161,255,0.15) 0%, rgba(139,92,246,0.15) 100%)",
              border: "1px solid rgba(0,161,255,0.3)",
              borderRadius: "12px",
              marginBottom: "32px",
            }}
          >
            <span style={{ color: "#FFD700", fontSize: "20px" }}>⭐</span>
            <span style={{ color: "#FFF", fontSize: "16px", fontWeight: 600 }}>
              🎁 14 DIAS GRÁTIS para testar todas as funcionalidades!
            </span>
            <span style={{ color: "#FFD700", fontSize: "20px" }}>⭐</span>
          </motion.div>

          {/* Billing Toggle */}
          <div style={styles.billingToggle}>
            <button
              onClick={() => setBillingPeriod("monthly")}
              style={{
                ...styles.toggleBtn,
                ...(billingPeriod === "monthly" ? styles.toggleActive : {}),
              }}
            >
              Mensal
            </button>
            <button
              onClick={() => setBillingPeriod("annual")}
              style={{
                ...styles.toggleBtn,
                ...(billingPeriod === "annual" ? styles.toggleActive : {}),
              }}
            >
              Anual
              <span style={styles.discountBadge}>-20%</span>
            </button>
          </div>
        </motion.div>

        {/* ROI Calculator */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          style={{
            background: COLORS.bgCard,
            border: `1px solid ${COLORS.border}`,
            borderRadius: "16px",
            padding: "32px",
            marginBottom: "48px",
            position: "relative",
            overflow: "hidden",
          }}
        >
          <div
            style={{
              ...premiumStyles.accentLine,
              background: COLORS.gradientPrimary,
            }}
          />
          <div style={{ textAlign: "center", marginBottom: "24px" }}>
            <div
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "10px",
                marginBottom: "8px",
              }}
            >
              <FaCalculator size={20} color={COLORS.primary} />
              <h3
                style={{
                  fontSize: "20px",
                  fontWeight: 700,
                  color: "#FFF",
                  margin: 0,
                }}
              >
                Calculadora de ROI
              </h3>
            </div>
            <p
              style={{
                color: COLORS.textSecondary,
                fontSize: "14px",
                margin: 0,
              }}
            >
              Veja quanto você economiza automatizando seus projetos
            </p>
          </div>
          <div
            style={{
              maxWidth: "500px",
              margin: "0 auto 24px",
              textAlign: "center",
            }}
          >
            <label
              style={{
                color: COLORS.textSecondary,
                fontSize: "14px",
                display: "block",
                marginBottom: "12px",
              }}
            >
              Quantos projetos CAD sua equipe faz por mês?
            </label>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: "16px",
              }}
            >
              <input
                type="range"
                min={1}
                max={50}
                value={projectsPerMonth}
                onChange={(e) => setProjectsPerMonth(Number(e.target.value))}
                style={{ width: "260px", accentColor: COLORS.primary }}
              />
              <span
                style={{
                  color: COLORS.primary,
                  fontSize: "28px",
                  fontWeight: 800,
                  minWidth: "50px",
                  textAlign: "center",
                }}
              >
                {projectsPerMonth}
              </span>
            </div>
          </div>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
              gap: "16px",
            }}
          >
            <div
              style={{
                background: COLORS.bgSurface,
                borderRadius: "12px",
                padding: "20px",
                textAlign: "center",
                border: `1px solid ${COLORS.border}`,
              }}
            >
              <FaClock
                size={18}
                color="#10B981"
                style={{ marginBottom: "8px" }}
              />
              <div
                style={{ fontSize: "28px", fontWeight: 800, color: "#10B981" }}
              >
                {roi.hoursSaved}h
              </div>
              <div style={{ fontSize: "12px", color: COLORS.textSecondary }}>
                Horas economizadas/mês
              </div>
            </div>
            <div
              style={{
                background: COLORS.bgSurface,
                borderRadius: "12px",
                padding: "20px",
                textAlign: "center",
                border: `1px solid ${COLORS.border}`,
              }}
            >
              <FaMoneyBillWave
                size={18}
                color="#F59E0B"
                style={{ marginBottom: "8px" }}
              />
              <div
                style={{ fontSize: "28px", fontWeight: 800, color: "#F59E0B" }}
              >
                R$ {roi.moneySaved.toLocaleString()}
              </div>
              <div style={{ fontSize: "12px", color: COLORS.textSecondary }}>
                Economia mensal estimada
              </div>
            </div>
            <div
              style={{
                background: COLORS.bgSurface,
                borderRadius: "12px",
                padding: "20px",
                textAlign: "center",
                border: `1px solid ${COLORS.border}`,
              }}
            >
              <FaChartLine
                size={18}
                color={COLORS.primary}
                style={{ marginBottom: "8px" }}
              />
              <div
                style={{
                  fontSize: "28px",
                  fontWeight: 800,
                  color: COLORS.primary,
                }}
              >
                {roi.netSaving > 0
                  ? `${Math.round(roi.moneySaved / getPrice(697))}x`
                  : "—"}
              </div>
              <div style={{ fontSize: "12px", color: COLORS.textSecondary }}>
                Retorno sobre investimento
              </div>
            </div>
            <div
              style={{
                background: COLORS.bgSurface,
                borderRadius: "12px",
                padding: "20px",
                textAlign: "center",
                border: `1px solid ${COLORS.border}`,
              }}
            >
              <FaRocket
                size={18}
                color="#8B5CF6"
                style={{ marginBottom: "8px" }}
              />
              <div
                style={{ fontSize: "28px", fontWeight: 800, color: "#8B5CF6" }}
              >
                {roi.paybackDays} dias
              </div>
              <div style={{ fontSize: "12px", color: COLORS.textSecondary }}>
                Payback estimado
              </div>
            </div>
          </div>
          {roi.netSaving > 0 && (
            <p
              style={{
                textAlign: "center",
                color: COLORS.success,
                fontSize: "14px",
                fontWeight: 600,
                margin: "20px 0 0",
              }}
            >
              Com {projectsPerMonth} projetos/mês, você economiza R${" "}
              {roi.netSaving.toLocaleString()} além do custo da plataforma!
            </p>
          )}
        </motion.div>

        {/* Plans Grid */}
        <div style={styles.plansGrid}>
          {PLANS.map((plan, index) => (
            <motion.div
              key={plan.id}
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.1 + 0.3 }}
              onMouseEnter={() => setHoveredPlan(plan.id)}
              onMouseLeave={() => setHoveredPlan(null)}
              style={{
                ...styles.planCard,
                borderColor:
                  hoveredPlan === plan.id || plan.popular
                    ? `${plan.color}60`
                    : COLORS.border,
                boxShadow:
                  hoveredPlan === plan.id || plan.popular
                    ? `0 8px 40px ${plan.color}25, 0 0 30px ${plan.color}15`
                    : SHADOWS.card,
                transform:
                  hoveredPlan === plan.id ? "translateY(-8px)" : "none",
              }}
            >
              {plan.popular && (
                <div style={{ ...styles.popularBadge, background: plan.color }}>
                  <FaStar size={10} /> MAIS POPULAR
                </div>
              )}

              {/* Accent line */}
              <div
                style={{ ...premiumStyles.accentLine, background: plan.color }}
              />

              {/* Plan Header */}
              <div style={styles.planHeader}>
                <div
                  style={{
                    ...styles.planIcon,
                    background: `${plan.color}20`,
                    color: plan.color,
                  }}
                >
                  {plan.icon}
                </div>
                <h3 style={styles.planName}>{plan.name}</h3>
                <p style={styles.planDesc}>{plan.description}</p>
              </div>

              {/* Price */}
              <div style={styles.priceSection}>
                <span style={styles.currency}>R$</span>
                <span style={{ ...styles.price, color: plan.color }}>
                  {getPrice(plan.price).toLocaleString()}
                </span>
                <span style={styles.period}>{plan.period}</span>
                {billingPeriod === "annual" && (
                  <p style={styles.annualNote}>
                    Cobrado anualmente (R${" "}
                    {(getPrice(plan.price) * 12).toLocaleString()}/ano)
                  </p>
                )}
              </div>

              {/* Limits */}
              <div style={styles.limitsGrid}>
                <div style={styles.limitItem}>
                  <FaServer size={14} />
                  <span>
                    {plan.limits.machines} máquina
                    {plan.limits.machines > 1 ? "s" : ""}
                  </span>
                </div>
                <div style={styles.limitItem}>
                  <FaChartLine size={14} />
                  <span>
                    {plan.limits.projects === "unlimited"
                      ? "∞"
                      : plan.limits.projects}{" "}
                    projetos
                  </span>
                </div>
                <div style={styles.limitItem}>
                  <FaBrain size={14} />
                  <span>
                    {plan.limits.aiQueries === "unlimited"
                      ? "∞"
                      : plan.limits.aiQueries}{" "}
                    IA/mês
                  </span>
                </div>
                <div style={styles.limitItem}>
                  <FaHeadset size={14} />
                  <span style={{ fontSize: "11px" }}>
                    {plan.limits.support}
                  </span>
                </div>
              </div>

              {/* Features */}
              <div style={styles.features}>
                {plan.features.map((feature, i) => (
                  <div
                    key={i}
                    style={{
                      ...styles.featureItem,
                      opacity: feature.included ? 1 : 0.4,
                    }}
                  >
                    {feature.included ? (
                      <FaCheck size={12} color={COLORS.success} />
                    ) : (
                      <FaTimes size={12} color={COLORS.textTertiary} />
                    )}
                    <span
                      style={
                        feature.highlight
                          ? { color: plan.color, fontWeight: 600 }
                          : {}
                      }
                    >
                      {feature.text}
                    </span>
                  </div>
                ))}
              </div>

              {/* CTA Button */}
              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={() => handleSelectPlan(plan.id)}
                style={{
                  ...styles.ctaBtn,
                  background: plan.popular ? plan.color : "transparent",
                  borderColor: plan.color,
                  color: plan.popular ? "#FFF" : plan.color,
                }}
              >
                {plan.id === "enterprise"
                  ? "Solicitar Proposta"
                  : "Começar Agora"}
                <FaArrowRight size={14} />
              </motion.button>
            </motion.div>
          ))}
        </div>

        {/* Benefits Section */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.8 }}
          style={styles.benefitsSection}
        >
          <h3 style={styles.benefitsTitle}>Presente em todos os planos</h3>
          <div style={styles.benefitsGrid}>
            {BENEFITS.map((benefit, i) => (
              <motion.div
                key={i}
                whileHover={{ y: -4, boxShadow: SHADOWS.glow }}
                style={styles.benefitCard}
              >
                <div style={styles.benefitIcon}>{benefit.icon}</div>
                <h4 style={styles.benefitTitle}>{benefit.title}</h4>
                <p style={styles.benefitDesc}>{benefit.desc}</p>
              </motion.div>
            ))}
          </div>
        </motion.div>

        {/* Testimonials */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.9 }}
          style={{ textAlign: "center", marginBottom: "48px" }}
        >
          <h3
            style={{
              fontSize: "24px",
              fontWeight: 700,
              color: "#FFF",
              marginBottom: "32px",
            }}
          >
            O que nossos clientes dizem
          </h3>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
              gap: "20px",
            }}
          >
            {TESTIMONIALS.map((t, i) => (
              <motion.div
                key={i}
                whileHover={{ y: -4 }}
                style={{
                  background: COLORS.bgCard,
                  border: `1px solid ${COLORS.border}`,
                  borderRadius: "12px",
                  padding: "24px",
                  textAlign: "left",
                  position: "relative",
                }}
              >
                <FaQuoteLeft
                  size={16}
                  color={`${COLORS.primary}40`}
                  style={{ marginBottom: "12px" }}
                />
                <p
                  style={{
                    color: COLORS.textSecondary,
                    fontSize: "14px",
                    lineHeight: 1.7,
                    margin: "0 0 16px",
                    fontStyle: "italic",
                  }}
                >
                  "{t.text}"
                </p>
                <div
                  style={{ display: "flex", gap: "4px", marginBottom: "8px" }}
                >
                  {[...Array(t.stars)].map((_, j) => (
                    <FaStar key={j} size={12} color="#F59E0B" />
                  ))}
                </div>
                <div>
                  <span
                    style={{ color: "#FFF", fontSize: "14px", fontWeight: 600 }}
                  >
                    {t.name}
                  </span>
                  <span
                    style={{ color: COLORS.textTertiary, fontSize: "13px" }}
                  >
                    {" "}
                    — {t.role}, {t.company}
                  </span>
                </div>
              </motion.div>
            ))}
          </div>
        </motion.div>

        {/* Trust Badges */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1 }}
          style={styles.trustSection}
        >
          <p style={styles.trustText}>
            <FaLock size={14} /> Pagamento 100% seguro • Garantia de 30 dias •
            Cancelamento a qualquer momento
          </p>
        </motion.div>

        {/* Back to Login */}
        <motion.button
          whileHover={{ scale: 1.02 }}
          onClick={() => navigate("/")}
          style={styles.backBtn}
        >
          ← Voltar para Login
        </motion.button>
      </div>
    </div>
  );
};

// ═══════════════════════════════════════════════════════════════════════════
// STYLES
// ═══════════════════════════════════════════════════════════════════════════

const styles: Record<string, React.CSSProperties> = {
  container: {
    minHeight: "100vh",
    position: "relative",
    fontFamily: "'Inter', 'Segoe UI', Roboto, sans-serif",
  },
  content: {
    position: "relative",
    zIndex: 10,
    maxWidth: "1400px",
    margin: "0 auto",
    padding: "48px 32px 80px",
  },
  header: {
    textAlign: "center",
    marginBottom: "48px",
  },
  logoRow: {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    gap: "16px",
    marginBottom: "32px",
  },
  logoIcon: {
    width: "56px",
    height: "56px",
    borderRadius: "14px",
    background: COLORS.gradientPrimary,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    color: "#FFF",
    boxShadow: SHADOWS.glow,
  },
  brand: {
    color: "#FFF",
    fontSize: "24px",
    letterSpacing: "4px",
    margin: 0,
    fontWeight: 800,
  },
  tagline: {
    color: COLORS.textTertiary,
    fontSize: "10px",
    letterSpacing: "2px",
    margin: 0,
  },
  title: {
    fontSize: "42px",
    fontWeight: 800,
    color: "#FFF",
    marginBottom: "16px",
    letterSpacing: "-0.02em",
  },
  subtitle: {
    fontSize: "16px",
    color: COLORS.textSecondary,
    maxWidth: "600px",
    margin: "0 auto 32px",
    lineHeight: 1.6,
  },
  billingToggle: {
    display: "inline-flex",
    gap: "4px",
    background: COLORS.bgCard,
    padding: "4px",
    borderRadius: "10px",
    border: `1px solid ${COLORS.border}`,
  },
  toggleBtn: {
    padding: "12px 24px",
    border: "none",
    borderRadius: "8px",
    background: "transparent",
    color: COLORS.textSecondary,
    fontSize: "14px",
    fontWeight: 500,
    cursor: "pointer",
    display: "flex",
    alignItems: "center",
    gap: "8px",
    transition: "all 0.2s",
  },
  toggleActive: {
    background: COLORS.primary,
    color: "#FFF",
    fontWeight: 600,
  },
  discountBadge: {
    padding: "2px 8px",
    background: COLORS.success,
    borderRadius: "20px",
    fontSize: "10px",
    fontWeight: 700,
  },
  plansGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))",
    gap: "24px",
    marginBottom: "64px",
    maxWidth: "100%",
  },
  planCard: {
    background: COLORS.bgCard,
    border: `1px solid ${COLORS.border}`,
    borderRadius: "16px",
    padding: "32px 28px",
    position: "relative",
    overflow: "hidden",
    transition: "all 0.3s ease",
  },
  popularBadge: {
    position: "absolute",
    top: "16px",
    right: "16px",
    padding: "6px 12px",
    borderRadius: "20px",
    fontSize: "10px",
    fontWeight: 700,
    color: "#FFF",
    display: "flex",
    alignItems: "center",
    gap: "4px",
    letterSpacing: "0.5px",
  },
  planHeader: {
    textAlign: "center",
    marginBottom: "24px",
  },
  planIcon: {
    width: "56px",
    height: "56px",
    borderRadius: "14px",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontSize: "24px",
    margin: "0 auto 16px",
  },
  planName: {
    fontSize: "22px",
    fontWeight: 700,
    color: "#FFF",
    margin: "0 0 8px",
  },
  planDesc: {
    fontSize: "13px",
    color: COLORS.textSecondary,
    margin: 0,
    lineHeight: 1.5,
  },
  priceSection: {
    textAlign: "center",
    marginBottom: "24px",
    paddingBottom: "24px",
    borderBottom: `1px solid ${COLORS.border}`,
  },
  currency: {
    fontSize: "18px",
    color: COLORS.textSecondary,
    verticalAlign: "top",
    marginRight: "2px",
  },
  price: {
    fontSize: "48px",
    fontWeight: 800,
    letterSpacing: "-0.02em",
  },
  period: {
    fontSize: "14px",
    color: COLORS.textTertiary,
    marginLeft: "4px",
  },
  annualNote: {
    fontSize: "11px",
    color: COLORS.textTertiary,
    marginTop: "8px",
  },
  limitsGrid: {
    display: "grid",
    gridTemplateColumns: "1fr 1fr",
    gap: "12px",
    marginBottom: "24px",
  },
  limitItem: {
    display: "flex",
    alignItems: "center",
    gap: "8px",
    padding: "10px 12px",
    background: COLORS.bgSurface,
    borderRadius: "8px",
    fontSize: "12px",
    color: COLORS.textSecondary,
  },
  features: {
    marginBottom: "24px",
  },
  featureItem: {
    display: "flex",
    alignItems: "center",
    gap: "10px",
    padding: "8px 0",
    fontSize: "13px",
    color: COLORS.textSecondary,
  },
  ctaBtn: {
    width: "100%",
    padding: "16px 24px",
    border: "2px solid",
    borderRadius: "10px",
    fontSize: "14px",
    fontWeight: 600,
    cursor: "pointer",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    gap: "10px",
    transition: "all 0.2s",
  },
  benefitsSection: {
    textAlign: "center",
    marginBottom: "48px",
  },
  benefitsTitle: {
    fontSize: "24px",
    fontWeight: 700,
    color: "#FFF",
    marginBottom: "32px",
  },
  benefitsGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
    gap: "20px",
    maxWidth: "100%",
  },
  benefitCard: {
    background: COLORS.bgCard,
    border: `1px solid ${COLORS.border}`,
    borderRadius: "12px",
    padding: "24px",
    textAlign: "center",
    transition: "all 0.2s",
  },
  benefitIcon: {
    width: "48px",
    height: "48px",
    borderRadius: "12px",
    background: `${COLORS.primary}15`,
    color: COLORS.primary,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontSize: "20px",
    margin: "0 auto 16px",
  },
  benefitTitle: {
    fontSize: "15px",
    fontWeight: 600,
    color: "#FFF",
    marginBottom: "8px",
  },
  benefitDesc: {
    fontSize: "12px",
    color: COLORS.textSecondary,
    lineHeight: 1.5,
    margin: 0,
  },
  trustSection: {
    textAlign: "center",
    marginBottom: "32px",
  },
  trustText: {
    display: "inline-flex",
    alignItems: "center",
    gap: "8px",
    fontSize: "13px",
    color: COLORS.textTertiary,
    padding: "12px 24px",
    background: COLORS.bgCard,
    borderRadius: "30px",
    border: `1px solid ${COLORS.border}`,
  },
  backBtn: {
    display: "block",
    margin: "0 auto",
    padding: "12px 24px",
    background: "transparent",
    border: `1px solid ${COLORS.border}`,
    borderRadius: "8px",
    color: COLORS.textSecondary,
    fontSize: "14px",
    cursor: "pointer",
    transition: "all 0.2s",
  },
};

// Media queries inline não são possíveis, mas podemos usar max-width para mobile
// Em produção, usar CSS modules ou styled-components

export default Pricing;
