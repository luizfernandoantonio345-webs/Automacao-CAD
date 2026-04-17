/**
 * Billing Dashboard - Gerenciamento de Assinatura e Pagamentos
 *
 * Features:
 * - Visão geral da assinatura atual
 * - Histórico de faturas
 * - Métodos de pagamento
 * - Alteração de plano
 */

import React, { useState, useEffect, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  FaCreditCard,
  FaFileInvoiceDollar,
  FaChartLine,
  FaCheckCircle,
  FaClock,
  FaExclamationTriangle,
  FaDownload,
  FaTrash,
  FaStar,
  FaRocket,
  FaCrown,
  FaBuilding,
  FaBolt,
} from "react-icons/fa";
import { api, ApiService, SessionUser } from "../services/api";
import { useToast } from "../context/ToastContext";

interface Subscription {
  status: string;
  tier: string;
  tier_name: string;
  current_period_end: string;
  cancel_at_period_end: boolean;
  features: Record<string, any>;
  usage: {
    cam_jobs_used: number;
    cam_jobs_limit: number;
    api_calls_used: number;
  };
}

interface Invoice {
  id: string;
  number: string;
  status: string;
  amount: number;
  currency: string;
  description: string;
  created_at: string;
  paid_at: string | null;
  pdf_url: string | null;
  period_start: string;
  period_end: string;
}

interface PaymentMethod {
  id: string;
  type: string;
  brand: string | null;
  last4: string | null;
  exp_month: number | null;
  exp_year: number | null;
  is_default: boolean;
  created_at: string;
}

interface Plan {
  tier: string;
  name: string;
  price_monthly: number;
  price_yearly: number;
  currency: string;
  features: Record<string, any>;
  is_current: boolean;
  is_upgrade: boolean;
  is_downgrade: boolean;
  savings_yearly: number;
}

const Billing: React.FC = () => {
  const { addToast } = useToast();
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<
    "overview" | "invoices" | "payment" | "plans"
  >("overview");

  const [subscription, setSubscription] = useState<Subscription | null>(null);
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [paymentMethods, setPaymentMethods] = useState<PaymentMethod[]>([]);
  const [plans, setPlans] = useState<Plan[]>([]);
  const [billingCycle, setBillingCycle] = useState<"monthly" | "yearly">(
    "monthly",
  );
  const [sessionUser, setSessionUser] = useState<SessionUser | null>(null);
  const [resolvedUserEmail, setResolvedUserEmail] = useState(
    localStorage.getItem("userEmail") || "user@example.com",
  );

  useEffect(() => {
    loadBillingData();
  }, []);

  const loadBillingData = async () => {
    setLoading(true);
    try {
      let activeUser: SessionUser | null = null;
      try {
        activeUser = await ApiService.getCurrentUser();
        setSessionUser(activeUser);
      } catch {
        activeUser = null;
      }

      const userEmail =
        activeUser?.email ||
        localStorage.getItem("userEmail") ||
        "user@example.com";
      setResolvedUserEmail(userEmail);

      const [subRes, invRes, pmRes, plansRes] = await Promise.all([
        api.get(`/api/billing/subscription/${encodeURIComponent(userEmail)}`),
        api.get(`/api/billing/invoices?email=${encodeURIComponent(userEmail)}`),
        api.get(
          `/api/billing/payment-methods?email=${encodeURIComponent(userEmail)}`,
        ),
        api.get(
          `/api/billing/subscription/plans?email=${encodeURIComponent(userEmail)}`,
        ),
      ]);

      setSubscription(subRes.data);
      setInvoices(invRes.data.invoices || []);
      setPaymentMethods(pmRes.data.payment_methods || []);
      setPlans(plansRes.data.plans || []);
    } catch (err) {
      console.error("Error loading billing data:", err);
      // Use demo data if API fails
      setSubscription({
        status: "active",
        tier: "professional",
        tier_name: "Professional",
        current_period_end: new Date(
          Date.now() + 30 * 24 * 60 * 60 * 1000,
        ).toISOString(),
        cancel_at_period_end: false,
        features: {
          cam_jobs_per_month: 2500,
          max_users: 5,
          max_machines: 2,
          ai_queries_per_month: 500,
        },
        usage: {
          cam_jobs_used: 847,
          cam_jobs_limit: 2500,
          api_calls_used: 1234,
        },
      });
    } finally {
      setLoading(false);
    }
  };

  const handleSetDefaultPaymentMethod = async (methodId: string) => {
    try {
      await api.put(
        `/api/billing/payment-methods/${methodId}/default?email=${encodeURIComponent(resolvedUserEmail)}`,
      );
      addToast("success", "Sucesso", "Método de pagamento padrão atualizado");
      loadBillingData();
    } catch (err) {
      addToast("error", "Erro", "Erro ao atualizar método de pagamento");
    }
  };

  const handleRemovePaymentMethod = async (methodId: string) => {
    if (
      !window.confirm(
        "Tem certeza que deseja remover este método de pagamento?",
      )
    )
      return;

    try {
      await api.delete(
        `/api/billing/payment-methods/${methodId}?email=${encodeURIComponent(resolvedUserEmail)}`,
      );
      addToast("success", "Sucesso", "Método de pagamento removido");
      loadBillingData();
    } catch (err: any) {
      addToast(
        "error",
        "Erro",
        err.response?.data?.detail || "Erro ao remover método de pagamento",
      );
    }
  };

  const handleChangePlan = async (newTier: string) => {
    const plan = plans.find((p) => p.tier === newTier);
    if (!plan) return;

    const confirmMsg = plan.is_upgrade
      ? `Deseja fazer upgrade para ${plan.name}? A cobrança será proporcional.`
      : `Deseja fazer downgrade para ${plan.name}? A alteração será aplicada no próximo período.`;

    if (!window.confirm(confirmMsg)) return;

    try {
      const res = await api.put(
        `/api/billing/subscription/plan?email=${encodeURIComponent(resolvedUserEmail)}`,
        {
          new_tier: newTier,
          billing_cycle: billingCycle,
          prorate: true,
        },
      );
      addToast("success", "Sucesso", res.data.message);
      loadBillingData();
    } catch (err: any) {
      addToast(
        "error",
        "Erro",
        err.response?.data?.detail || "Erro ao alterar plano",
      );
    }
  };

  const formatCurrency = (amount: number, currency: string = "BRL") => {
    return new Intl.NumberFormat("pt-BR", {
      style: "currency",
      currency: currency,
    }).format(amount / 100);
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString("pt-BR", {
      day: "2-digit",
      month: "short",
      year: "numeric",
    });
  };

  const getStatusBadge = (status: string) => {
    const styles: Record<
      string,
      { bg: string; color: string; icon: React.ReactNode }
    > = {
      paid: {
        bg: "rgba(16, 185, 129, 0.15)",
        color: "#10B981",
        icon: <FaCheckCircle />,
      },
      active: {
        bg: "rgba(16, 185, 129, 0.15)",
        color: "#10B981",
        icon: <FaCheckCircle />,
      },
      pending: {
        bg: "rgba(245, 158, 11, 0.15)",
        color: "#f59e0b",
        icon: <FaClock />,
      },
      failed: {
        bg: "rgba(239, 68, 68, 0.15)",
        color: "#ef4444",
        icon: <FaExclamationTriangle />,
      },
      canceled: {
        bg: "rgba(107, 114, 128, 0.15)",
        color: "#6b7280",
        icon: <FaClock />,
      },
    };
    const style = styles[status] || styles.pending;
    return (
      <span
        style={{
          display: "inline-flex",
          alignItems: "center",
          gap: "6px",
          padding: "4px 12px",
          background: style.bg,
          borderRadius: "20px",
          color: style.color,
          fontSize: "12px",
          fontWeight: 600,
        }}
      >
        {style.icon}
        {status.charAt(0).toUpperCase() + status.slice(1)}
      </span>
    );
  };

  const getTierIcon = (tier: string) => {
    const icons: Record<string, React.ReactNode> = {
      starter: <FaStar color="#00A1FF" />,
      professional: <FaRocket color="#8B5CF6" />,
      enterprise: <FaCrown color="#F59E0B" />,
    };
    return icons[tier] || icons.starter;
  };

  const camUsagePercent = Math.min(
    100,
    ((subscription?.usage?.cam_jobs_used || 0) /
      Math.max(subscription?.usage?.cam_jobs_limit || 1, 1)) *
      100,
  );
  const activeUsers = Math.max(1, subscription?.features?.max_users ? 1 : 1);
  const monthlySavings = useMemo(
    () => (subscription?.usage?.cam_jobs_used || 0) * 48,
    [subscription],
  );
  const savedHours = useMemo(
    () => Math.max(1, Math.round((subscription?.usage?.cam_jobs_used || 0) * 1.5)),
    [subscription],
  );
  const usageLabel =
    camUsagePercent >= 80
      ? "Uso intenso"
      : camUsagePercent >= 40
        ? "Uso consistente"
        : "Adoção em crescimento";

  if (loading) {
    return (
      <div
        style={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          height: "60vh",
        }}
      >
        <div
          className="animate-spin"
          style={{
            width: "40px",
            height: "40px",
            border: "3px solid #1e3a5f",
            borderTopColor: "#00A1FF",
            borderRadius: "50%",
          }}
        />
      </div>
    );
  }

  return (
    <div style={{ padding: "32px", maxWidth: "1200px", margin: "0 auto" }}>
      {/* Header */}
      <div
        style={{
          marginBottom: "32px",
          padding: "28px",
          borderRadius: "20px",
          background:
            "radial-gradient(circle at top left, rgba(0,161,255,0.16), transparent 34%), linear-gradient(135deg, #07111f 0%, #0f2035 48%, #101827 100%)",
          border: "1px solid rgba(120, 161, 255, 0.18)",
          boxShadow: "0 24px 80px rgba(0,0,0,0.28)",
        }}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            gap: "16px",
            alignItems: "flex-start",
            flexWrap: "wrap",
          }}
        >
          <div>
            <div
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "8px",
                padding: "6px 12px",
                borderRadius: "999px",
                background: "rgba(255,255,255,0.06)",
                color: "#9cc9ff",
                fontSize: "12px",
                fontWeight: 700,
                letterSpacing: "0.08em",
                textTransform: "uppercase",
                marginBottom: "14px",
              }}
            >
              <FaBolt /> Receita e assinatura
            </div>
            <h1
              style={{
                color: "#fff",
                fontSize: "30px",
                fontWeight: 800,
                marginBottom: "10px",
              }}
            >
              Billing & Assinatura
            </h1>
            <p style={{ color: "#94a3b8", fontSize: "14px", margin: 0 }}>
              Gestão executiva de plano, cobrança e capacidade operacional
            </p>
          </div>
          {getStatusBadge(subscription?.status || "active")}
        </div>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
            gap: "14px",
            marginTop: "24px",
          }}
        >
          <div
            style={{
              padding: "16px 18px",
              borderRadius: "14px",
              background: "rgba(255,255,255,0.04)",
              border: "1px solid rgba(255,255,255,0.08)",
            }}
          >
            <div
              style={{
                color: "#64748b",
                fontSize: "11px",
                textTransform: "uppercase",
                letterSpacing: "0.08em",
              }}
            >
              Conta faturada
            </div>
            <div
              style={{
                color: "#fff",
                fontSize: "15px",
                fontWeight: 700,
                marginTop: "8px",
              }}
            >
              {resolvedUserEmail}
            </div>
            <div
              style={{
                color: "#8da3bf",
                fontSize: "12px",
                marginTop: "6px",
                display: "flex",
                alignItems: "center",
                gap: "8px",
              }}
            >
              <FaBuilding /> {sessionUser?.empresa || "Organização principal"}
            </div>
          </div>

          <div
            style={{
              padding: "16px 18px",
              borderRadius: "14px",
              background: "rgba(255,255,255,0.04)",
              border: "1px solid rgba(255,255,255,0.08)",
            }}
          >
            <div
              style={{
                color: "#64748b",
                fontSize: "11px",
                textTransform: "uppercase",
                letterSpacing: "0.08em",
              }}
            >
              Plano atual
            </div>
            <div
              style={{
                color: "#fff",
                fontSize: "15px",
                fontWeight: 700,
                marginTop: "8px",
                display: "flex",
                alignItems: "center",
                gap: "10px",
              }}
            >
              {getTierIcon(subscription?.tier || "starter")}
              {subscription?.tier_name || "Professional"}
            </div>
            <div
              style={{ color: "#8da3bf", fontSize: "12px", marginTop: "6px" }}
            >
              Renovação{" "}
              {subscription?.current_period_end
                ? formatDate(subscription.current_period_end)
                : "N/A"}
            </div>
          </div>

          <div
            style={{
              padding: "16px 18px",
              borderRadius: "14px",
              background: "rgba(255,255,255,0.04)",
              border: "1px solid rgba(255,255,255,0.08)",
            }}
          >
            <div
              style={{
                color: "#64748b",
                fontSize: "11px",
                textTransform: "uppercase",
                letterSpacing: "0.08em",
              }}
            >
              Capacidade CAM
            </div>
            <div
              style={{
                color: "#fff",
                fontSize: "15px",
                fontWeight: 700,
                marginTop: "8px",
              }}
            >
              {subscription?.usage?.cam_jobs_used || 0}/
              {subscription?.usage?.cam_jobs_limit || 0}
            </div>
            <div
              style={{
                color: camUsagePercent > 80 ? "#f59e0b" : "#8da3bf",
                fontSize: "12px",
                marginTop: "6px",
              }}
            >
              {camUsagePercent.toFixed(0)}% da capacidade do ciclo
            </div>
          </div>

          <div
            style={{
              padding: "16px 18px",
              borderRadius: "14px",
              background: "rgba(255,255,255,0.04)",
              border: "1px solid rgba(255,255,255,0.08)",
            }}
          >
            <div
              style={{
                color: "#64748b",
                fontSize: "11px",
                textTransform: "uppercase",
                letterSpacing: "0.08em",
              }}
            >
              Usuários ativos
            </div>
            <div
              style={{
                color: "#fff",
                fontSize: "15px",
                fontWeight: 700,
                marginTop: "8px",
              }}
            >
              {activeUsers}/{subscription?.features?.max_users || 1}
            </div>
            <div
              style={{ color: "#8da3bf", fontSize: "12px", marginTop: "6px" }}
            >
              Escala atual da operação
            </div>
          </div>
        </div>
      </div>

      <div style={{ marginBottom: "32px" }}>
        <h1
          style={{
            color: "#fff",
            fontSize: "28px",
            fontWeight: 700,
            marginBottom: "8px",
            display: "none",
          }}
        >
          Billing & Assinatura
        </h1>
        <p style={{ color: "#64748b", fontSize: "14px", display: "none" }}>
          Gerencie sua assinatura, faturas e métodos de pagamento
        </p>
      </div>

      {/* Tabs */}
      <div
        style={{
          display: "flex",
          gap: "8px",
          marginBottom: "32px",
          borderBottom: "1px solid #1e3a5f",
          paddingBottom: "16px",
        }}
      >
        {[
          { id: "overview", label: "Visão Geral", icon: <FaChartLine /> },
          { id: "invoices", label: "Faturas", icon: <FaFileInvoiceDollar /> },
          { id: "payment", label: "Pagamento", icon: <FaCreditCard /> },
          { id: "plans", label: "Planos", icon: <FaRocket /> },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as any)}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "8px",
              padding: "10px 20px",
              background:
                activeTab === tab.id
                  ? "rgba(0, 161, 255, 0.15)"
                  : "transparent",
              border: "1px solid",
              borderColor: activeTab === tab.id ? "#00A1FF" : "transparent",
              borderRadius: "8px",
              color: activeTab === tab.id ? "#00A1FF" : "#94a3b8",
              fontSize: "14px",
              fontWeight: 500,
              cursor: "pointer",
              transition: "all 0.2s",
            }}
          >
            {tab.icon}
            {tab.label}
          </button>
        ))}
      </div>

      <AnimatePresence mode="wait">
        {/* Overview Tab */}
        {activeTab === "overview" && (
          <motion.div
            key="overview"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
          >
            {/* ── Métricas de Valor ── */}
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
                gap: "14px",
                marginBottom: "24px",
              }}
            >
              {[
                {
                  label: "Economia Mensal",
                  value: `R$ ${monthlySavings.toLocaleString("pt-BR")}`,
                  sub: "economia estimada vs. processo manual",
                  icon: "📉",
                  color: "#10B981",
                },
                {
                  label: "Tempo Economizado",
                  value: `${savedHours}h/mês`,
                  sub: "horas técnicas liberadas para produção",
                  icon: "⏱",
                  color: "#00A1FF",
                },
                {
                  label: "Uso do Sistema",
                  value: `${camUsagePercent.toFixed(0)}%`,
                  sub: `${usageLabel} • ${subscription?.usage?.cam_jobs_used || 0} de ${subscription?.usage?.cam_jobs_limit || 0} jobs`,
                  icon: "⚡",
                  color: camUsagePercent > 80 ? "#f59e0b" : "#8B5CF6",
                },
              ].map((m) => (
                <div
                  key={m.label}
                  style={{
                    padding: "18px 20px",
                    borderRadius: "14px",
                    background: "linear-gradient(135deg, #0a1628, #0f2035)",
                    border: `1px solid ${m.color}33`,
                    boxShadow: `0 0 18px ${m.color}14`,
                  }}
                >
                  <div style={{ fontSize: "22px", marginBottom: "6px" }}>{m.icon}</div>
                  <div style={{ color: "#64748b", fontSize: "11px", textTransform: "uppercase", letterSpacing: "0.08em" }}>
                    {m.label}
                  </div>
                  <div style={{ color: m.color, fontSize: "24px", fontWeight: 800, margin: "6px 0 4px" }}>
                    {m.value}
                  </div>
                  <div style={{ color: "#64748b", fontSize: "12px" }}>{m.sub}</div>
                </div>
              ))}
            </div>

            {/* Subscription Card */}
            <div
              style={{
                background: "linear-gradient(135deg, #0a1628 0%, #1a2942 100%)",
                border: "1px solid #1e3a5f",
                borderRadius: "16px",
                padding: "32px",
                marginBottom: "24px",
              }}
            >
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "flex-start",
                  marginBottom: "24px",
                }}
              >
                <div>
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "12px",
                      marginBottom: "8px",
                    }}
                  >
                    {getTierIcon(subscription?.tier || "starter")}
                    <h2
                      style={{
                        color: "#fff",
                        fontSize: "24px",
                        fontWeight: 700,
                        margin: 0,
                      }}
                    >
                      Plano {subscription?.tier_name}
                    </h2>
                  </div>
                  <p style={{ color: "#64748b", fontSize: "14px" }}>
                    Próxima cobrança:{" "}
                    {subscription?.current_period_end
                      ? formatDate(subscription.current_period_end)
                      : "N/A"}
                  </p>
                </div>
                {getStatusBadge(subscription?.status || "active")}
              </div>

              {/* Usage Stats */}
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(3, 1fr)",
                  gap: "24px",
                }}
              >
                <div
                  style={{
                    background: "rgba(0, 161, 255, 0.05)",
                    borderRadius: "12px",
                    padding: "20px",
                  }}
                >
                  <p
                    style={{
                      color: "#64748b",
                      fontSize: "12px",
                      marginBottom: "8px",
                    }}
                  >
                    Jobs CAM
                  </p>
                  <p
                    style={{
                      color: "#fff",
                      fontSize: "24px",
                      fontWeight: 700,
                    }}
                  >
                    {subscription?.usage?.cam_jobs_used || 0}
                    <span
                      style={{
                        color: "#64748b",
                        fontSize: "14px",
                        fontWeight: 400,
                      }}
                    >
                      /{subscription?.usage?.cam_jobs_limit || 0}
                    </span>
                  </p>
                  <div
                    style={{
                      marginTop: "8px",
                      height: "4px",
                      background: "#1e3a5f",
                      borderRadius: "2px",
                      overflow: "hidden",
                    }}
                  >
                    <div
                      style={{
                        width: `${Math.min(100, ((subscription?.usage?.cam_jobs_used || 0) / (subscription?.usage?.cam_jobs_limit || 1)) * 100)}%`,
                        height: "100%",
                        background: "linear-gradient(90deg, #00A1FF, #0066CC)",
                      }}
                    />
                  </div>
                </div>

                <div
                  style={{
                    background: "rgba(139, 92, 246, 0.05)",
                    borderRadius: "12px",
                    padding: "20px",
                  }}
                >
                  <p
                    style={{
                      color: "#64748b",
                      fontSize: "12px",
                      marginBottom: "8px",
                    }}
                  >
                    Consultas IA
                  </p>
                  <p
                    style={{
                      color: "#fff",
                      fontSize: "24px",
                      fontWeight: 700,
                    }}
                  >
                    {subscription?.usage?.api_calls_used || 0}
                  </p>
                  <p
                    style={{
                      color: "#64748b",
                      fontSize: "12px",
                      marginTop: "8px",
                    }}
                  >
                    {usageLabel}
                  </p>
                </div>

                <div
                  style={{
                    background: "rgba(245, 158, 11, 0.05)",
                    borderRadius: "12px",
                    padding: "20px",
                  }}
                >
                  <p
                    style={{
                      color: "#64748b",
                      fontSize: "12px",
                      marginBottom: "8px",
                    }}
                  >
                    Usuários
                  </p>
                  <p
                    style={{
                      color: "#fff",
                      fontSize: "24px",
                      fontWeight: 700,
                    }}
                  >
                    1
                    <span
                      style={{
                        color: "#64748b",
                        fontSize: "14px",
                        fontWeight: 400,
                      }}
                    >
                      /{subscription?.features?.max_users || 1}
                    </span>
                  </p>
                  <p
                    style={{
                      color: "#64748b",
                      fontSize: "12px",
                      marginTop: "8px",
                    }}
                  >
                    Ativos
                  </p>
                </div>
              </div>
            </div>

            {/* Recent Invoices Preview */}
            <div
              style={{
                background: "#0a1628",
                border: "1px solid #1e3a5f",
                borderRadius: "16px",
                padding: "24px",
              }}
            >
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  marginBottom: "20px",
                }}
              >
                <h3
                  style={{
                    color: "#fff",
                    fontSize: "16px",
                    fontWeight: 600,
                    margin: 0,
                  }}
                >
                  Faturas Recentes
                </h3>
                <button
                  onClick={() => setActiveTab("invoices")}
                  style={{
                    background: "transparent",
                    border: "none",
                    color: "#00A1FF",
                    fontSize: "13px",
                    cursor: "pointer",
                  }}
                >
                  Ver todas →
                </button>
              </div>

              {invoices.slice(0, 3).map((invoice) => (
                <div
                  key={invoice.id}
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    padding: "16px 0",
                    borderBottom: "1px solid #1e3a5f",
                  }}
                >
                  <div>
                    <p
                      style={{
                        color: "#fff",
                        fontSize: "14px",
                        fontWeight: 500,
                      }}
                    >
                      {invoice.number}
                    </p>
                    <p style={{ color: "#64748b", fontSize: "12px" }}>
                      {formatDate(invoice.created_at)}
                    </p>
                  </div>
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "16px",
                    }}
                  >
                    {getStatusBadge(invoice.status)}
                    <span
                      style={{
                        color: "#fff",
                        fontSize: "14px",
                        fontWeight: 600,
                      }}
                    >
                      {formatCurrency(invoice.amount, invoice.currency)}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </motion.div>
        )}

        {/* Invoices Tab */}
        {activeTab === "invoices" && (
          <motion.div
            key="invoices"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
          >
            <div
              style={{
                background: "#0a1628",
                border: "1px solid #1e3a5f",
                borderRadius: "16px",
                overflow: "hidden",
              }}
            >
              <table style={{ width: "100%", borderCollapse: "collapse" }}>
                <thead>
                  <tr style={{ background: "#0d1f35" }}>
                    <th
                      style={{
                        padding: "16px 24px",
                        textAlign: "left",
                        color: "#64748b",
                        fontSize: "12px",
                        fontWeight: 600,
                        textTransform: "uppercase",
                      }}
                    >
                      Número
                    </th>
                    <th
                      style={{
                        padding: "16px 24px",
                        textAlign: "left",
                        color: "#64748b",
                        fontSize: "12px",
                        fontWeight: 600,
                        textTransform: "uppercase",
                      }}
                    >
                      Data
                    </th>
                    <th
                      style={{
                        padding: "16px 24px",
                        textAlign: "left",
                        color: "#64748b",
                        fontSize: "12px",
                        fontWeight: 600,
                        textTransform: "uppercase",
                      }}
                    >
                      Descrição
                    </th>
                    <th
                      style={{
                        padding: "16px 24px",
                        textAlign: "left",
                        color: "#64748b",
                        fontSize: "12px",
                        fontWeight: 600,
                        textTransform: "uppercase",
                      }}
                    >
                      Status
                    </th>
                    <th
                      style={{
                        padding: "16px 24px",
                        textAlign: "right",
                        color: "#64748b",
                        fontSize: "12px",
                        fontWeight: 600,
                        textTransform: "uppercase",
                      }}
                    >
                      Valor
                    </th>
                    <th
                      style={{
                        padding: "16px 24px",
                        textAlign: "center",
                        color: "#64748b",
                        fontSize: "12px",
                        fontWeight: 600,
                        textTransform: "uppercase",
                      }}
                    >
                      Ações
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {invoices.map((invoice) => (
                    <tr
                      key={invoice.id}
                      style={{ borderBottom: "1px solid #1e3a5f" }}
                    >
                      <td
                        style={{
                          padding: "16px 24px",
                          color: "#fff",
                          fontSize: "14px",
                        }}
                      >
                        {invoice.number}
                      </td>
                      <td
                        style={{
                          padding: "16px 24px",
                          color: "#94a3b8",
                          fontSize: "14px",
                        }}
                      >
                        {formatDate(invoice.created_at)}
                      </td>
                      <td
                        style={{
                          padding: "16px 24px",
                          color: "#94a3b8",
                          fontSize: "14px",
                        }}
                      >
                        {invoice.description}
                      </td>
                      <td style={{ padding: "16px 24px" }}>
                        {getStatusBadge(invoice.status)}
                      </td>
                      <td
                        style={{
                          padding: "16px 24px",
                          color: "#fff",
                          fontSize: "14px",
                          fontWeight: 600,
                          textAlign: "right",
                        }}
                      >
                        {formatCurrency(invoice.amount, invoice.currency)}
                      </td>
                      <td style={{ padding: "16px 24px", textAlign: "center" }}>
                        <button
                          onClick={() =>
                            window.open(invoice.pdf_url || "#", "_blank")
                          }
                          style={{
                            display: "inline-flex",
                            alignItems: "center",
                            gap: "6px",
                            padding: "8px 12px",
                            background: "rgba(0, 161, 255, 0.1)",
                            border: "none",
                            borderRadius: "6px",
                            color: "#00A1FF",
                            fontSize: "12px",
                            cursor: "pointer",
                          }}
                        >
                          <FaDownload size={12} />
                          PDF
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </motion.div>
        )}

        {/* Payment Methods Tab */}
        {activeTab === "payment" && (
          <motion.div
            key="payment"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
          >
            <div
              style={{
                background: "#0a1628",
                border: "1px solid #1e3a5f",
                borderRadius: "16px",
                padding: "24px",
              }}
            >
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  marginBottom: "24px",
                }}
              >
                <h3
                  style={{
                    color: "#fff",
                    fontSize: "18px",
                    fontWeight: 600,
                    margin: 0,
                  }}
                >
                  Métodos de Pagamento
                </h3>
                <button
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "8px",
                    padding: "10px 20px",
                    background:
                      "linear-gradient(135deg, #00A1FF 0%, #0066CC 100%)",
                    border: "none",
                    borderRadius: "8px",
                    color: "#fff",
                    fontSize: "14px",
                    fontWeight: 500,
                    cursor: "pointer",
                  }}
                >
                  <FaCreditCard />
                  Adicionar Cartão
                </button>
              </div>

              <div style={{ display: "grid", gap: "16px" }}>
                {paymentMethods.map((method) => (
                  <div
                    key={method.id}
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      padding: "20px",
                      background: method.is_default
                        ? "rgba(0, 161, 255, 0.05)"
                        : "#0d1f35",
                      border: "1px solid",
                      borderColor: method.is_default ? "#00A1FF" : "#1e3a5f",
                      borderRadius: "12px",
                    }}
                  >
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "16px",
                      }}
                    >
                      <div
                        style={{
                          width: "48px",
                          height: "32px",
                          background: "#1e3a5f",
                          borderRadius: "6px",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                        }}
                      >
                        <FaCreditCard size={18} color="#00A1FF" />
                      </div>
                      <div>
                        <p
                          style={{
                            color: "#fff",
                            fontSize: "14px",
                            fontWeight: 500,
                          }}
                        >
                          {method.brand?.toUpperCase()} •••• {method.last4}
                        </p>
                        <p style={{ color: "#64748b", fontSize: "12px" }}>
                          Expira {method.exp_month?.toString().padStart(2, "0")}
                          /{method.exp_year}
                        </p>
                      </div>
                      {method.is_default && (
                        <span
                          style={{
                            padding: "4px 10px",
                            background: "rgba(0, 161, 255, 0.15)",
                            borderRadius: "20px",
                            color: "#00A1FF",
                            fontSize: "11px",
                            fontWeight: 600,
                          }}
                        >
                          PADRÃO
                        </span>
                      )}
                    </div>
                    <div style={{ display: "flex", gap: "8px" }}>
                      {!method.is_default && (
                        <button
                          onClick={() =>
                            handleSetDefaultPaymentMethod(method.id)
                          }
                          style={{
                            padding: "8px 12px",
                            background: "transparent",
                            border: "1px solid #1e3a5f",
                            borderRadius: "6px",
                            color: "#94a3b8",
                            fontSize: "12px",
                            cursor: "pointer",
                          }}
                        >
                          Definir padrão
                        </button>
                      )}
                      <button
                        onClick={() => handleRemovePaymentMethod(method.id)}
                        style={{
                          padding: "8px 12px",
                          background: "transparent",
                          border: "1px solid rgba(239, 68, 68, 0.3)",
                          borderRadius: "6px",
                          color: "#ef4444",
                          fontSize: "12px",
                          cursor: "pointer",
                        }}
                      >
                        <FaTrash />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </motion.div>
        )}

        {/* Plans Tab */}
        {activeTab === "plans" && (
          <motion.div
            key="plans"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
          >
            {/* Billing Cycle Toggle */}
            <div
              style={{
                display: "flex",
                justifyContent: "center",
                marginBottom: "32px",
              }}
            >
              <div
                style={{
                  display: "flex",
                  background: "#0d1f35",
                  borderRadius: "30px",
                  padding: "4px",
                }}
              >
                <button
                  onClick={() => setBillingCycle("monthly")}
                  style={{
                    padding: "10px 24px",
                    background:
                      billingCycle === "monthly" ? "#00A1FF" : "transparent",
                    border: "none",
                    borderRadius: "26px",
                    color: billingCycle === "monthly" ? "#fff" : "#94a3b8",
                    fontSize: "14px",
                    fontWeight: 500,
                    cursor: "pointer",
                    transition: "all 0.2s",
                  }}
                >
                  Mensal
                </button>
                <button
                  onClick={() => setBillingCycle("yearly")}
                  style={{
                    padding: "10px 24px",
                    background:
                      billingCycle === "yearly" ? "#00A1FF" : "transparent",
                    border: "none",
                    borderRadius: "26px",
                    color: billingCycle === "yearly" ? "#fff" : "#94a3b8",
                    fontSize: "14px",
                    fontWeight: 500,
                    cursor: "pointer",
                    transition: "all 0.2s",
                  }}
                >
                  Anual
                  <span
                    style={{
                      marginLeft: "8px",
                      padding: "2px 8px",
                      background: "rgba(16, 185, 129, 0.2)",
                      borderRadius: "10px",
                      color: "#10B981",
                      fontSize: "11px",
                    }}
                  >
                    -17%
                  </span>
                </button>
              </div>
            </div>

            {/* Plans Grid */}
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(3, 1fr)",
                gap: "24px",
              }}
            >
              {plans.map((plan) => (
                <div
                  key={plan.tier}
                  style={{
                    background: plan.is_current
                      ? "linear-gradient(135deg, rgba(0, 161, 255, 0.1) 0%, rgba(0, 102, 204, 0.1) 100%)"
                      : "#0a1628",
                    border: "1px solid",
                    borderColor: plan.is_current ? "#00A1FF" : "#1e3a5f",
                    borderRadius: "16px",
                    padding: "32px",
                    position: "relative",
                    overflow: "hidden",
                  }}
                >
                  {plan.is_current && (
                    <div
                      style={{
                        position: "absolute",
                        top: "16px",
                        right: "16px",
                        padding: "4px 12px",
                        background: "#00A1FF",
                        borderRadius: "20px",
                        color: "#fff",
                        fontSize: "11px",
                        fontWeight: 600,
                      }}
                    >
                      ATUAL
                    </div>
                  )}

                  <div style={{ marginBottom: "24px" }}>
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "12px",
                        marginBottom: "8px",
                      }}
                    >
                      {getTierIcon(plan.tier)}
                      <h3
                        style={{
                          color: "#fff",
                          fontSize: "20px",
                          fontWeight: 700,
                          margin: 0,
                        }}
                      >
                        {plan.name}
                      </h3>
                    </div>
                    <div
                      style={{
                        display: "flex",
                        alignItems: "baseline",
                        gap: "4px",
                      }}
                    >
                      <span
                        style={{
                          color: "#fff",
                          fontSize: "36px",
                          fontWeight: 700,
                        }}
                      >
                        R${" "}
                        {billingCycle === "monthly"
                          ? plan.price_monthly
                          : Math.round(plan.price_yearly / 12)}
                      </span>
                      <span style={{ color: "#64748b", fontSize: "14px" }}>
                        /mês
                      </span>
                    </div>
                    {billingCycle === "yearly" && (
                      <p
                        style={{
                          color: "#10B981",
                          fontSize: "13px",
                          marginTop: "4px",
                        }}
                      >
                        Economize R$ {plan.savings_yearly}/ano
                      </p>
                    )}
                  </div>

                  <ul
                    style={{
                      listStyle: "none",
                      padding: 0,
                      margin: "0 0 24px 0",
                    }}
                  >
                    <li
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "10px",
                        color: "#94a3b8",
                        fontSize: "14px",
                        marginBottom: "12px",
                      }}
                    >
                      <FaCheckCircle color="#00A1FF" size={14} />
                      {plan.features.cam_jobs_per_month === -1
                        ? "Jobs CAM ilimitados"
                        : `${plan.features.cam_jobs_per_month} jobs CAM/mês`}
                    </li>
                    <li
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "10px",
                        color: "#94a3b8",
                        fontSize: "14px",
                        marginBottom: "12px",
                      }}
                    >
                      <FaCheckCircle color="#00A1FF" size={14} />
                      {plan.features.max_users}{" "}
                      {plan.features.max_users === 1 ? "usuário" : "usuários"}
                    </li>
                    <li
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "10px",
                        color: "#94a3b8",
                        fontSize: "14px",
                        marginBottom: "12px",
                      }}
                    >
                      <FaCheckCircle color="#00A1FF" size={14} />
                      {plan.features.ai_queries_per_month} consultas IA/mês
                    </li>
                    <li
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "10px",
                        color: "#94a3b8",
                        fontSize: "14px",
                        marginBottom: "12px",
                      }}
                    >
                      <FaCheckCircle color="#00A1FF" size={14} />
                      Suporte {plan.features.support}
                    </li>
                    <li
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "10px",
                        color: "#94a3b8",
                        fontSize: "14px",
                      }}
                    >
                      <FaCheckCircle color="#00A1FF" size={14} />
                      SLA {plan.features.sla}
                    </li>
                  </ul>

                  <button
                    onClick={() =>
                      !plan.is_current && handleChangePlan(plan.tier)
                    }
                    disabled={plan.is_current}
                    style={{
                      width: "100%",
                      padding: "14px",
                      background: plan.is_current
                        ? "#1e3a5f"
                        : plan.is_upgrade
                          ? "linear-gradient(135deg, #00A1FF 0%, #0066CC 100%)"
                          : "transparent",
                      border:
                        plan.is_current || plan.is_upgrade
                          ? "none"
                          : "1px solid #1e3a5f",
                      borderRadius: "10px",
                      color: plan.is_current ? "#64748b" : "#fff",
                      fontSize: "14px",
                      fontWeight: 600,
                      cursor: plan.is_current ? "not-allowed" : "pointer",
                    }}
                  >
                    {plan.is_current
                      ? "Plano Atual"
                      : plan.is_upgrade
                        ? "Fazer Upgrade"
                        : "Fazer Downgrade"}
                  </button>
                </div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default Billing;
