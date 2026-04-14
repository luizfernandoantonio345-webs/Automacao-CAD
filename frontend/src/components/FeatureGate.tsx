import React from "react";
import { useNavigate } from "react-router-dom";
import { useLicense } from "../context/LicenseContext";
import { useTheme } from "../context/ThemeContext";
import { FaCrown, FaLock } from "react-icons/fa";

/**
 * Tier hierarchy for feature gating.
 * Higher index = more permissions.
 */
const TIER_LEVEL: Record<string, number> = {
  demo: 0,
  starter: 1,
  professional: 2,
  enterprise: 3,
};

interface FeatureGateProps {
  /** Minimum tier required to access this feature */
  requiredTier: "starter" | "professional" | "enterprise";
  children: React.ReactNode;
}

/**
 * Wraps a page/section and shows an upgrade prompt if the user's tier
 * is below the required level.
 */
export const FeatureGate: React.FC<FeatureGateProps> = ({
  requiredTier,
  children,
}) => {
  const { license } = useLicense();
  const { theme } = useTheme();
  const navigate = useNavigate();

  const userLevel = TIER_LEVEL[license.tier ?? "demo"] ?? 0;
  const requiredLevel = TIER_LEVEL[requiredTier] ?? 1;

  if (userLevel >= requiredLevel) {
    return <>{children}</>;
  }

  const tierNames: Record<string, string> = {
    starter: "Starter",
    professional: "Professional",
    enterprise: "Enterprise",
  };

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        minHeight: "60vh",
        padding: "48px 24px",
        textAlign: "center",
        background: theme.gradientPage || theme.background,
        color: theme.textPrimary,
      }}
    >
      <div
        style={{
          width: 72,
          height: 72,
          borderRadius: 20,
          background: `${theme.warning}20`,
          border: `2px solid ${theme.warning}40`,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          marginBottom: 24,
        }}
      >
        <FaLock size={28} color={theme.warning} />
      </div>

      <h2
        style={{
          fontSize: 22,
          fontWeight: 700,
          marginBottom: 12,
          color: theme.textPrimary,
        }}
      >
        Funcionalidade {tierNames[requiredTier]}
      </h2>

      <p
        style={{
          fontSize: 15,
          color: theme.textSecondary,
          maxWidth: 440,
          lineHeight: 1.7,
          marginBottom: 32,
        }}
      >
        Este recurso requer o plano <strong>{tierNames[requiredTier]}</strong>{" "}
        ou superior. Faça upgrade para desbloquear todas as funcionalidades e
        aumentar sua produtividade.
      </p>

      <button
        onClick={() => navigate(`/pricing?upgrade_to=${requiredTier}`)}
        style={{
          padding: "14px 32px",
          background: "linear-gradient(135deg, #00A1FF 0%, #0077CC 100%)",
          border: "none",
          borderRadius: 12,
          color: "#FFF",
          fontSize: 14,
          fontWeight: 700,
          letterSpacing: "1px",
          cursor: "pointer",
          display: "flex",
          alignItems: "center",
          gap: 10,
          boxShadow: "0 8px 32px rgba(0,161,255,0.3)",
        }}
      >
        <FaCrown size={16} />
        Ver Planos & Fazer Upgrade
      </button>

      <button
        onClick={() => navigate("/dashboard")}
        style={{
          marginTop: 16,
          padding: "10px 24px",
          background: "transparent",
          border: `1px solid ${theme.border}`,
          borderRadius: 8,
          color: theme.textSecondary,
          fontSize: 13,
          cursor: "pointer",
        }}
      >
        Voltar ao Dashboard
      </button>
    </div>
  );
};
