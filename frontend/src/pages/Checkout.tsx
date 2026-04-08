/**
 * ENGENHARIA CAD – Checkout Page
 * Fluxo completo de monetização: seleção do plano → dados → pagamento
 */
import React, { useState, useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import {
  FaCheck,
  FaCrown,
  FaRocket,
  FaArrowLeft,
  FaArrowRight,
  FaWhatsapp,
  FaEnvelope,
  FaShieldAlt,
  FaLock,
  FaCopy,
  FaBolt,
  FaUser,
  FaBuilding,
  FaPhone,
  FaCheckCircle,
  FaStar,
} from "react-icons/fa";
import { COLORS, SHADOWS } from "../styles/premium";

// ─────────────────── Plan data ───────────────────
const PLAN_DATA: Record<string, any> = {
  starter: {
    name: "Starter",
    price: 297,
    color: "#10B981",
    icon: <FaRocket />,
    features: [
      "Automação CAD básica (5 projetos)",
      "IA Assistente (100 consultas/mês)",
      "Exportação DXF/DWG",
      "Validação ASME básica",
      "Suporte por email (48h)",
    ],
  },
  professional: {
    name: "Professional",
    price: 697,
    color: "#00A1FF",
    icon: <FaCrown />,
    popular: true,
    features: [
      "Tudo do Starter",
      "Controle CNC/Plasma completo",
      "Nesting inteligente",
      "IA Assistente (500 consultas/mês)",
      "20 projetos simultâneos",
      "Suporte prioritário (24h)",
    ],
  },
};

type Step = "summary" | "contact" | "payment" | "success";

const PIX_KEY = "pagamentos@engenharia-cad.com.br";
const WHATSAPP_NUMBER = "5531999999999";

// ─────────────────── Animated BG ───────────────────
const AnimatedBg: React.FC = () => (
  <div style={{ position: "fixed", inset: 0, zIndex: 0, overflow: "hidden" }}>
    <div
      style={{
        position: "absolute",
        inset: 0,
        background:
          "linear-gradient(135deg, #030508 0%, #0a1628 40%, #071020 70%, #030508 100%)",
      }}
    />
    <div
      style={{
        position: "absolute",
        inset: 0,
        backgroundImage: `
          linear-gradient(rgba(0,161,255,0.03) 1px, transparent 1px),
          linear-gradient(90deg, rgba(0,161,255,0.03) 1px, transparent 1px)`,
        backgroundSize: "60px 60px",
      }}
    />
  </div>
);

// ─────────────────── Steps indicator ───────────────────
const STEPS: { key: Step; label: string }[] = [
  { key: "summary", label: "Plano" },
  { key: "contact", label: "Dados" },
  { key: "payment", label: "Pagamento" },
  { key: "success", label: "Ativação" },
];

const StepIndicator: React.FC<{ current: Step }> = ({ current }) => {
  const idx = STEPS.findIndex((s) => s.key === current);
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 0,
        marginBottom: "40px",
      }}
    >
      {STEPS.map((step, i) => (
        <React.Fragment key={step.key}>
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              gap: "6px",
            }}
          >
            <div
              style={{
                width: "32px",
                height: "32px",
                borderRadius: "50%",
                background:
                  i < idx
                    ? COLORS.success
                    : i === idx
                      ? COLORS.primary
                      : COLORS.bgCard,
                border: `2px solid ${i <= idx ? (i < idx ? COLORS.success : COLORS.primary) : COLORS.border}`,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "#FFF",
                fontSize: "12px",
                fontWeight: 700,
                transition: "all 0.3s",
              }}
            >
              {i < idx ? <FaCheck size={11} /> : i + 1}
            </div>
            <span
              style={{
                fontSize: "10px",
                color: i === idx ? COLORS.primary : COLORS.textTertiary,
                fontWeight: i === idx ? 600 : 400,
                letterSpacing: "0.05em",
                whiteSpace: "nowrap",
              }}
            >
              {step.label}
            </span>
          </div>
          {i < STEPS.length - 1 && (
            <div
              style={{
                flex: 1,
                height: "2px",
                background: i < idx ? COLORS.success : COLORS.border,
                transition: "all 0.3s",
                marginBottom: "20px",
                minWidth: "20px",
              }}
            />
          )}
        </React.Fragment>
      ))}
    </div>
  );
};

// ─────────────────── Main Component ───────────────────
const Checkout: React.FC = () => {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const planId = params.get("plan") || "professional";
  const billing = params.get("billing") || "monthly";
  const plan = PLAN_DATA[planId] || PLAN_DATA.professional;

  const [step, setStep] = useState<Step>("summary");
  const [copied, setCopied] = useState(false);

  // Contact form
  const [form, setForm] = useState({
    name: "",
    email: "",
    company: "",
    phone: "",
    cnpj: "",
  });
  const [formError, setFormError] = useState("");

  const finalPrice =
    billing === "annual" ? Math.round(plan.price * 0.8) : plan.price;
  const annualTotal = finalPrice * 12;

  const handleCopyPix = () => {
    navigator.clipboard.writeText(PIX_KEY).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 3000);
    });
  };

  const handleFormChange = (field: string, value: string) => {
    setForm((p) => ({ ...p, [field]: value }));
    setFormError("");
  };

  const handleContactSubmit = () => {
    if (!form.name || !form.email || !form.phone) {
      setFormError("Preencha Nome, E-mail e Telefone para continuar.");
      return;
    }
    if (!form.email.includes("@")) {
      setFormError("E-mail inválido.");
      return;
    }
    setStep("payment");
  };

  const handleWhatsAppOrder = () => {
    const text = encodeURIComponent(
      `Olá! Gostaria de contratar o plano *${plan.name}* do Engenharia CAD.\n\n` +
        `👤 Nome: ${form.name}\n` +
        `🏢 Empresa: ${form.company || "Não informado"}\n` +
        `📧 E-mail: ${form.email}\n` +
        `📱 Telefone: ${form.phone}\n` +
        `💰 Plano: ${plan.name} – R$ ${finalPrice}/mês (${billing === "annual" ? "anual" : "mensal"})\n\n` +
        `Por favor, envie as instruções de pagamento e ativação.`,
    );
    window.open(`https://wa.me/${WHATSAPP_NUMBER}?text=${text}`, "_blank");
    setStep("success");
  };

  const handleEmailOrder = () => {
    const subject = encodeURIComponent(
      `Contratação Plano ${plan.name} – Engenharia CAD`,
    );
    const body = encodeURIComponent(
      `Olá,\n\nGostaria de contratar o plano ${plan.name} do Engenharia CAD.\n\n` +
        `Nome: ${form.name}\nEmpresa: ${form.company}\nE-mail: ${form.email}\nTelefone: ${form.phone}\n\n` +
        `Plano: ${plan.name} – R$ ${finalPrice}/mês\n\nAguardo instruções de pagamento e ativação.\n\nAtenciosamente,\n${form.name}`,
    );
    window.location.href = `mailto:comercial@engenharia-cad.com?subject=${subject}&body=${body}`;
    setStep("success");
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        position: "relative",
        fontFamily: "'Inter','Segoe UI',Roboto,sans-serif",
        padding: "24px 16px",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      <AnimatedBg />

      <div
        style={{
          position: "relative",
          zIndex: 10,
          width: "100%",
          maxWidth: "560px",
        }}
      >
        {/* Back */}
        <motion.button
          whileHover={{ x: -4 }}
          onClick={() =>
            step === "summary"
              ? navigate("/pricing")
              : setStep(STEPS[STEPS.findIndex((s) => s.key === step) - 1].key)
          }
          style={{
            display: "flex",
            alignItems: "center",
            gap: "8px",
            background: "transparent",
            border: "none",
            color: COLORS.textSecondary,
            cursor: "pointer",
            fontSize: "14px",
            marginBottom: "28px",
            padding: "4px 0",
          }}
        >
          <FaArrowLeft size={13} />
          Voltar
        </motion.button>

        {/* Brand */}
        <div style={{ textAlign: "center", marginBottom: "32px" }}>
          <h1
            style={{
              color: "#FFF",
              fontSize: "22px",
              fontWeight: 800,
              letterSpacing: "4px",
              margin: 0,
            }}
          >
            ENGENHARIA <span style={{ color: COLORS.primary }}>CAD</span>
          </h1>
          <p
            style={{
              color: COLORS.textTertiary,
              fontSize: "11px",
              letterSpacing: "2px",
              margin: "4px 0 0",
            }}
          >
            CHECKOUT SEGURO
          </p>
        </div>

        {/* Steps */}
        <StepIndicator current={step} />

        {/* Card */}
        <motion.div
          key={step}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.35 }}
          style={{
            background: COLORS.bgCard,
            border: `1px solid ${COLORS.border}`,
            borderRadius: "18px",
            overflow: "hidden",
            boxShadow: SHADOWS.lg,
          }}
        >
          {/* Accent top */}
          <div
            style={{
              height: "3px",
              background: `linear-gradient(90deg, transparent, ${plan.color}, transparent)`,
            }}
          />

          <div style={{ padding: "32px" }}>
            {/* ──────── STEP: SUMMARY ──────── */}
            {step === "summary" && (
              <>
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "14px",
                    marginBottom: "24px",
                  }}
                >
                  <div
                    style={{
                      width: "52px",
                      height: "52px",
                      borderRadius: "14px",
                      background: `${plan.color}20`,
                      border: `1px solid ${plan.color}40`,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      color: plan.color,
                      fontSize: "22px",
                    }}
                  >
                    {plan.icon}
                  </div>
                  <div>
                    <h2
                      style={{
                        color: "#FFF",
                        fontSize: "20px",
                        fontWeight: 700,
                        margin: 0,
                      }}
                    >
                      Plano {plan.name}
                    </h2>
                    {plan.popular && (
                      <span
                        style={{
                          fontSize: "10px",
                          background: plan.color,
                          color: "#FFF",
                          padding: "2px 10px",
                          borderRadius: "20px",
                          fontWeight: 700,
                        }}
                      >
                        MAIS POPULAR
                      </span>
                    )}
                  </div>
                </div>

                {/* Price display */}
                <div
                  style={{
                    background: `${plan.color}10`,
                    border: `1px solid ${plan.color}30`,
                    borderRadius: "12px",
                    padding: "20px",
                    marginBottom: "24px",
                    textAlign: "center",
                  }}
                >
                  <div
                    style={{
                      display: "flex",
                      alignItems: "baseline",
                      justifyContent: "center",
                      gap: "4px",
                    }}
                  >
                    <span
                      style={{ color: COLORS.textSecondary, fontSize: "16px" }}
                    >
                      R$
                    </span>
                    <span
                      style={{
                        color: plan.color,
                        fontSize: "48px",
                        fontWeight: 900,
                        lineHeight: 1,
                      }}
                    >
                      {finalPrice.toLocaleString()}
                    </span>
                    <span
                      style={{ color: COLORS.textSecondary, fontSize: "14px" }}
                    >
                      /mês
                    </span>
                  </div>
                  {billing === "annual" && (
                    <p
                      style={{
                        color: COLORS.textTertiary,
                        fontSize: "13px",
                        margin: "8px 0 0",
                      }}
                    >
                      Cobrado anualmente: R$ {annualTotal.toLocaleString()}/ano
                      <span
                        style={{
                          background: COLORS.success,
                          color: "#FFF",
                          fontSize: "10px",
                          padding: "2px 8px",
                          borderRadius: "10px",
                          marginLeft: "8px",
                          fontWeight: 600,
                        }}
                      >
                        20% OFF
                      </span>
                    </p>
                  )}
                </div>

                {/* Features */}
                <div style={{ marginBottom: "28px" }}>
                  {plan.features.map((f: string, i: number) => (
                    <div
                      key={i}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "10px",
                        marginBottom: "10px",
                      }}
                    >
                      <FaCheck size={12} color={COLORS.success} />
                      <span
                        style={{
                          color: COLORS.textSecondary,
                          fontSize: "14px",
                        }}
                      >
                        {f}
                      </span>
                    </div>
                  ))}
                </div>

                {/* Urgency */}
                <motion.div
                  animate={{ opacity: [1, 0.7, 1] }}
                  transition={{ duration: 1.5, repeat: Infinity }}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "8px",
                    background: "rgba(245,158,11,0.1)",
                    border: "1px solid rgba(245,158,11,0.3)",
                    borderRadius: "8px",
                    padding: "10px 14px",
                    marginBottom: "24px",
                    color: "#F59E0B",
                    fontSize: "13px",
                    fontWeight: 600,
                  }}
                >
                  <FaBolt size={12} />
                  Oferta exclusiva: Ativação imediata após confirmação
                </motion.div>

                <button
                  onClick={() => setStep("contact")}
                  style={{
                    width: "100%",
                    padding: "16px",
                    background: `linear-gradient(135deg, ${plan.color}, ${plan.color}cc)`,
                    border: "none",
                    borderRadius: "10px",
                    color: "#FFF",
                    fontSize: "16px",
                    fontWeight: 700,
                    cursor: "pointer",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    gap: "10px",
                  }}
                >
                  Continuar
                  <FaArrowRight size={14} />
                </button>
              </>
            )}

            {/* ──────── STEP: CONTACT ──────── */}
            {step === "contact" && (
              <>
                <h2
                  style={{
                    color: "#FFF",
                    fontSize: "20px",
                    fontWeight: 700,
                    margin: "0 0 8px",
                  }}
                >
                  Seus dados
                </h2>
                <p
                  style={{
                    color: COLORS.textSecondary,
                    fontSize: "14px",
                    margin: "0 0 24px",
                  }}
                >
                  Preencha para receber sua licença pelo WhatsApp ou e-mail.
                </p>

                {[
                  {
                    field: "name",
                    label: "NOME COMPLETO *",
                    icon: <FaUser />,
                    type: "text",
                    placeholder: "João da Silva",
                  },
                  {
                    field: "email",
                    label: "E-MAIL *",
                    icon: <FaEnvelope />,
                    type: "email",
                    placeholder: "joao@empresa.com.br",
                  },
                  {
                    field: "phone",
                    label: "TELEFONE/WHATSAPP *",
                    icon: <FaPhone />,
                    type: "tel",
                    placeholder: "(11) 99999-9999",
                  },
                  {
                    field: "company",
                    label: "EMPRESA",
                    icon: <FaBuilding />,
                    type: "text",
                    placeholder: "Engenharia Santos Ltda",
                  },
                ].map(({ field, label, icon, type, placeholder }) => (
                  <div key={field} style={{ marginBottom: "16px" }}>
                    <label
                      style={{
                        color: COLORS.textTertiary,
                        fontSize: "10px",
                        letterSpacing: "1px",
                        fontWeight: 600,
                        display: "block",
                        marginBottom: "6px",
                      }}
                    >
                      {label}
                    </label>
                    <div style={{ position: "relative" }}>
                      <span
                        style={{
                          position: "absolute",
                          left: "12px",
                          top: "50%",
                          transform: "translateY(-50%)",
                          color: COLORS.textTertiary,
                          fontSize: "13px",
                        }}
                      >
                        {icon}
                      </span>
                      <input
                        type={type}
                        placeholder={placeholder}
                        value={(form as any)[field]}
                        onChange={(e) =>
                          handleFormChange(field, e.target.value)
                        }
                        style={{
                          width: "100%",
                          padding: "12px 12px 12px 36px",
                          background: COLORS.bgPanel,
                          border: `1px solid ${COLORS.border}`,
                          borderRadius: "8px",
                          color: "#FFF",
                          fontSize: "14px",
                          outline: "none",
                          boxSizing: "border-box",
                        }}
                      />
                    </div>
                  </div>
                ))}

                {formError && (
                  <p
                    style={{
                      color: COLORS.danger,
                      fontSize: "13px",
                      marginBottom: "12px",
                    }}
                  >
                    {formError}
                  </p>
                )}

                <button
                  onClick={handleContactSubmit}
                  style={{
                    width: "100%",
                    padding: "16px",
                    background: `linear-gradient(135deg, ${plan.color}, ${plan.color}cc)`,
                    border: "none",
                    borderRadius: "10px",
                    color: "#FFF",
                    fontSize: "16px",
                    fontWeight: 700,
                    cursor: "pointer",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    gap: "10px",
                  }}
                >
                  Ir para Pagamento
                  <FaArrowRight size={14} />
                </button>
              </>
            )}

            {/* ──────── STEP: PAYMENT ──────── */}
            {step === "payment" && (
              <>
                <h2
                  style={{
                    color: "#FFF",
                    fontSize: "20px",
                    fontWeight: 700,
                    margin: "0 0 8px",
                  }}
                >
                  Método de Pagamento
                </h2>
                <p
                  style={{
                    color: COLORS.textSecondary,
                    fontSize: "14px",
                    margin: "0 0 24px",
                  }}
                >
                  Escolha a forma mais conveniente para você:
                </p>

                {/* Option 1: WhatsApp */}
                <motion.button
                  whileHover={{
                    scale: 1.02,
                    boxShadow: "0 4px 20px rgba(37,211,102,0.3)",
                  }}
                  whileTap={{ scale: 0.98 }}
                  onClick={handleWhatsAppOrder}
                  style={{
                    width: "100%",
                    padding: "18px 20px",
                    background: "rgba(37,211,102,0.08)",
                    border: "1px solid rgba(37,211,102,0.4)",
                    borderRadius: "12px",
                    cursor: "pointer",
                    display: "flex",
                    alignItems: "center",
                    gap: "16px",
                    marginBottom: "12px",
                    textAlign: "left",
                  }}
                >
                  <FaWhatsapp size={28} color="#25D366" />
                  <div>
                    <div
                      style={{
                        color: "#FFF",
                        fontWeight: 700,
                        fontSize: "15px",
                        marginBottom: "2px",
                      }}
                    >
                      Contratar via WhatsApp
                    </div>
                    <div style={{ color: "#8899aa", fontSize: "12px" }}>
                      Nossa equipe envia PIX/boleto e ativa sua licença em
                      minutos
                    </div>
                  </div>
                  <span
                    style={{
                      marginLeft: "auto",
                      background: "#25D366",
                      color: "#FFF",
                      fontSize: "10px",
                      padding: "3px 10px",
                      borderRadius: "20px",
                      fontWeight: 700,
                      whiteSpace: "nowrap",
                    }}
                  >
                    RECOMENDADO
                  </span>
                </motion.button>

                {/* Option 2: Email */}
                <motion.button
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  onClick={handleEmailOrder}
                  style={{
                    width: "100%",
                    padding: "18px 20px",
                    background: "rgba(0,161,255,0.05)",
                    border: `1px solid ${COLORS.border}`,
                    borderRadius: "12px",
                    cursor: "pointer",
                    display: "flex",
                    alignItems: "center",
                    gap: "16px",
                    marginBottom: "12px",
                    textAlign: "left",
                  }}
                >
                  <FaEnvelope size={24} color={COLORS.primary} />
                  <div>
                    <div
                      style={{
                        color: "#FFF",
                        fontWeight: 700,
                        fontSize: "15px",
                        marginBottom: "2px",
                      }}
                    >
                      Solicitar por E-mail
                    </div>
                    <div style={{ color: "#8899aa", fontSize: "12px" }}>
                      Enviaremos proposta formal com NF-e para sua empresa
                    </div>
                  </div>
                </motion.button>

                {/* Option 3: PIX direct */}
                <div
                  style={{
                    padding: "18px 20px",
                    background: "rgba(139,92,246,0.05)",
                    border: `1px solid ${COLORS.border}`,
                    borderRadius: "12px",
                    marginBottom: "24px",
                  }}
                >
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "12px",
                      marginBottom: "12px",
                    }}
                  >
                    <span style={{ fontSize: "24px" }}>🏦</span>
                    <div>
                      <div
                        style={{
                          color: "#FFF",
                          fontWeight: 700,
                          fontSize: "15px",
                        }}
                      >
                        PIX Direto
                      </div>
                      <div style={{ color: "#8899aa", fontSize: "12px" }}>
                        Chave PIX (e-mail)
                      </div>
                    </div>
                  </div>
                  <div
                    style={{
                      background: COLORS.bgPanel,
                      border: `1px solid ${COLORS.border}`,
                      borderRadius: "8px",
                      padding: "12px",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      gap: "12px",
                    }}
                  >
                    <span
                      style={{
                        color: COLORS.primary,
                        fontSize: "13px",
                        fontFamily: "monospace",
                      }}
                    >
                      {PIX_KEY}
                    </span>
                    <button
                      onClick={handleCopyPix}
                      style={{
                        background: copied ? COLORS.success : COLORS.primary,
                        border: "none",
                        borderRadius: "6px",
                        color: "#FFF",
                        padding: "6px 12px",
                        cursor: "pointer",
                        fontSize: "12px",
                        display: "flex",
                        alignItems: "center",
                        gap: "6px",
                        fontWeight: 600,
                        flexShrink: 0,
                        transition: "background 0.2s",
                      }}
                    >
                      {copied ? <FaCheck size={11} /> : <FaCopy size={11} />}
                      {copied ? "Copiado!" : "Copiar"}
                    </button>
                  </div>
                  <p
                    style={{
                      color: COLORS.textTertiary,
                      fontSize: "11px",
                      margin: "10px 0 0",
                    }}
                  >
                    Valor: R$ {finalPrice.toLocaleString()}/mês • Após
                    pagamento, envie comprovante via WhatsApp para ativação
                    imediata.
                  </p>
                </div>

                {/* Trust */}
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    gap: "6px",
                  }}
                >
                  <FaShieldAlt size={12} color={COLORS.textTertiary} />
                  <span
                    style={{ color: COLORS.textTertiary, fontSize: "11px" }}
                  >
                    30 dias de garantia • CNPJ 00.000.000/0001-00 • NF-e
                    disponível
                  </span>
                </div>
              </>
            )}

            {/* ──────── STEP: SUCCESS ──────── */}
            {step === "success" && (
              <div style={{ textAlign: "center", padding: "20px 0" }}>
                <motion.div
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  transition={{ type: "spring", damping: 12, stiffness: 200 }}
                  style={{
                    width: "80px",
                    height: "80px",
                    borderRadius: "50%",
                    background: `${COLORS.success}20`,
                    border: `2px solid ${COLORS.success}`,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    margin: "0 auto 24px",
                  }}
                >
                  <FaCheckCircle size={36} color={COLORS.success} />
                </motion.div>

                <h2
                  style={{
                    color: "#FFF",
                    fontSize: "22px",
                    fontWeight: 800,
                    margin: "0 0 12px",
                  }}
                >
                  Solicitação Enviada!
                </h2>
                <p
                  style={{
                    color: COLORS.textSecondary,
                    fontSize: "15px",
                    lineHeight: "1.6",
                    margin: "0 0 24px",
                  }}
                >
                  Nossa equipe entrará em contato em até{" "}
                  <strong style={{ color: COLORS.primary }}>30 minutos</strong>{" "}
                  para confirmar pagamento e enviar sua chave de ativação.
                </p>

                <div
                  style={{
                    background: "rgba(0,161,255,0.05)",
                    border: `1px solid ${COLORS.border}`,
                    borderRadius: "12px",
                    padding: "16px",
                    marginBottom: "24px",
                    textAlign: "left",
                  }}
                >
                  <p
                    style={{
                      color: COLORS.textTertiary,
                      fontSize: "12px",
                      fontWeight: 600,
                      letterSpacing: "0.05em",
                      margin: "0 0 12px",
                    }}
                  >
                    PRÓXIMOS PASSOS:
                  </p>
                  {[
                    "1. Confirme o pagamento conforme orientação recebida",
                    "2. Envie o comprovante via WhatsApp",
                    `3. Receba sua chave de licença em até 30 minutos`,
                    "4. Ative no sistema: Painel → Configurações → Ativar Licença",
                  ].map((step, i) => (
                    <div
                      key={i}
                      style={{
                        display: "flex",
                        gap: "8px",
                        marginBottom: "8px",
                      }}
                    >
                      <span
                        style={{
                          marginTop: "3px",
                          flexShrink: 0,
                          display: "flex",
                        }}
                      >
                        <FaCheck size={11} color={COLORS.success} />
                      </span>
                      <span
                        style={{
                          color: COLORS.textSecondary,
                          fontSize: "13px",
                        }}
                      >
                        {step}
                      </span>
                    </div>
                  ))}
                </div>

                {/* Stars */}
                <div
                  style={{
                    display: "flex",
                    justifyContent: "center",
                    gap: "4px",
                    marginBottom: "8px",
                  }}
                >
                  {[...Array(5)].map((_, i) => (
                    <span key={i}>
                      <FaStar size={14} color="#F59E0B" />
                    </span>
                  ))}
                </div>
                <p
                  style={{
                    color: COLORS.textTertiary,
                    fontSize: "12px",
                    margin: "0 0 24px",
                  }}
                >
                  "Reduziu em 80% o tempo de geração de P&IDs" — Eng. Carlos M.,
                  Petrobras
                </p>

                <button
                  onClick={() => navigate("/dashboard")}
                  style={{
                    width: "100%",
                    padding: "14px",
                    background: COLORS.gradientPrimary,
                    border: "none",
                    borderRadius: "10px",
                    color: "#FFF",
                    fontSize: "15px",
                    fontWeight: 700,
                    cursor: "pointer",
                  }}
                >
                  Voltar ao Dashboard
                </button>
              </div>
            )}
          </div>
        </motion.div>

        {/* Security footer */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: "6px",
            marginTop: "20px",
          }}
        >
          <FaLock size={11} color={COLORS.textTertiary} />
          <span style={{ color: COLORS.textTertiary, fontSize: "11px" }}>
            Conexão 100% segura (AES-256) — seus dados estão protegidos
          </span>
        </div>
      </div>
    </div>
  );
};

export default Checkout;
