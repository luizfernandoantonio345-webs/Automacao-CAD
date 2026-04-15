/**
 * ENGENHARIA CAD – Onboarding Walkthrough
 * Guided first-use experience shown during the first 7 days after signup.
 * Steps: Criar Projeto → Validar Norma → Exportar DXF
 */
import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  FaRocket,
  FaCheck,
  FaTimes,
  FaArrowRight,
  FaProjectDiagram,
  FaClipboardCheck,
  FaFileExport,
  FaStar,
} from "react-icons/fa";
import { COLORS, SHADOWS } from "../styles/premium";

interface WalkthroughStep {
  id: string;
  title: string;
  description: string;
  icon: React.ReactNode;
  action: string;
  path: string;
}

const WALKTHROUGH_STEPS: WalkthroughStep[] = [
  {
    id: "create",
    title: "Crie seu primeiro projeto",
    description:
      "Acesse o módulo CAD e crie um novo projeto P&ID. Nossa IA vai guiar você em cada etapa.",
    icon: <FaProjectDiagram size={24} />,
    action: "Ir para Projetos",
    path: "/dashboard",
  },
  {
    id: "validate",
    title: "Valide contra normas",
    description:
      "Rode a validação automática ASME/Petrobras N-series para garantir conformidade sem retrabalho.",
    icon: <FaClipboardCheck size={24} />,
    action: "Ir para Validação",
    path: "/dashboard",
  },
  {
    id: "export",
    title: "Exporte em DXF/DWG",
    description:
      "Gere arquivos prontos para fabricação com nesting otimizado e aproveitamento máximo de chapa.",
    icon: <FaFileExport size={24} />,
    action: "Ir para Exportação",
    path: "/cam",
  },
];

const STORAGE_KEY = "engcad_onboarding";

interface OnboardingState {
  dismissed: boolean;
  completedSteps: string[];
  startDate: string;
}

function getState(): OnboardingState {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) return JSON.parse(raw);
  } catch {}
  return {
    dismissed: false,
    completedSteps: [],
    startDate: new Date().toISOString(),
  };
}

function saveState(state: OnboardingState) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
}

interface Props {
  onNavigate: (path: string) => void;
}

const OnboardingWalkthrough: React.FC<Props> = ({ onNavigate }) => {
  const [state, setState] = useState<OnboardingState>(getState);
  const [currentStep, setCurrentStep] = useState(0);

  useEffect(() => {
    saveState(state);
  }, [state]);

  // Don't show if dismissed or if it's been more than 7 days
  const startDate = new Date(state.startDate);
  const daysSinceStart =
    (Date.now() - startDate.getTime()) / (1000 * 60 * 60 * 24);
  if (state.dismissed || daysSinceStart > 7) return null;

  // Don't show if all steps completed
  const allDone = WALKTHROUGH_STEPS.every((s) =>
    state.completedSteps.includes(s.id),
  );
  if (allDone) return null;

  const handleDismiss = () => {
    setState((prev) => ({ ...prev, dismissed: true }));
  };

  const handleCompleteStep = (stepId: string, path: string) => {
    setState((prev) => ({
      ...prev,
      completedSteps: prev.completedSteps.includes(stepId)
        ? prev.completedSteps
        : [...prev.completedSteps, stepId],
    }));
    onNavigate(path);
  };

  const completedCount = state.completedSteps.length;
  const progress = Math.round(
    (completedCount / WALKTHROUGH_STEPS.length) * 100,
  );

  return (
    <motion.div
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      style={{
        background: COLORS.bgCard,
        border: `1px solid ${COLORS.border}`,
        borderRadius: "16px",
        padding: "24px",
        marginBottom: "24px",
        position: "relative",
        overflow: "hidden",
      }}
    >
      {/* Accent line */}
      <div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          right: 0,
          height: "3px",
          background: COLORS.gradientPrimary,
        }}
      />

      {/* Close */}
      <button
        onClick={handleDismiss}
        style={{
          position: "absolute",
          top: "12px",
          right: "12px",
          background: "transparent",
          border: "none",
          color: COLORS.textTertiary,
          cursor: "pointer",
          padding: "4px",
        }}
        aria-label="Fechar onboarding"
      >
        <FaTimes size={14} />
      </button>

      {/* Header */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "12px",
          marginBottom: "16px",
        }}
      >
        <div
          style={{
            width: "40px",
            height: "40px",
            borderRadius: "10px",
            background: `${COLORS.primary}20`,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: COLORS.primary,
          }}
        >
          <FaRocket size={18} />
        </div>
        <div>
          <h3
            style={{
              color: "#FFF",
              fontSize: "16px",
              fontWeight: 700,
              margin: 0,
            }}
          >
            Primeiros Passos
          </h3>
          <p
            style={{ color: COLORS.textSecondary, fontSize: "12px", margin: 0 }}
          >
            Complete estas etapas para dominar a plataforma
          </p>
        </div>
      </div>

      {/* Progress bar */}
      <div
        style={{
          height: "6px",
          background: COLORS.bgSurface,
          borderRadius: "3px",
          marginBottom: "20px",
          overflow: "hidden",
        }}
      >
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${progress}%` }}
          transition={{ duration: 0.5 }}
          style={{
            height: "100%",
            background: COLORS.gradientPrimary,
            borderRadius: "3px",
          }}
        />
      </div>
      <p
        style={{
          color: COLORS.textTertiary,
          fontSize: "11px",
          marginBottom: "16px",
          marginTop: "-12px",
        }}
      >
        {completedCount}/{WALKTHROUGH_STEPS.length} concluídos
      </p>

      {/* Steps */}
      <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
        {WALKTHROUGH_STEPS.map((step, i) => {
          const done = state.completedSteps.includes(step.id);
          return (
            <motion.div
              key={step.id}
              whileHover={{ scale: done ? 1 : 1.01 }}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "14px",
                padding: "14px 16px",
                background: done ? `${COLORS.success}10` : COLORS.bgSurface,
                border: `1px solid ${done ? `${COLORS.success}30` : COLORS.border}`,
                borderRadius: "10px",
                cursor: done ? "default" : "pointer",
                opacity: done ? 0.7 : 1,
                transition: "all 0.2s",
              }}
              onClick={() => !done && handleCompleteStep(step.id, step.path)}
            >
              <div
                style={{
                  width: "44px",
                  height: "44px",
                  borderRadius: "10px",
                  background: done
                    ? `${COLORS.success}20`
                    : `${COLORS.primary}15`,
                  color: done ? COLORS.success : COLORS.primary,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  flexShrink: 0,
                }}
              >
                {done ? <FaCheck size={18} /> : step.icon}
              </div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <h4
                  style={{
                    color: done ? COLORS.success : "#FFF",
                    fontSize: "14px",
                    fontWeight: 600,
                    margin: "0 0 4px",
                    textDecoration: done ? "line-through" : "none",
                  }}
                >
                  {step.title}
                </h4>
                <p
                  style={{
                    color: COLORS.textSecondary,
                    fontSize: "12px",
                    margin: 0,
                    lineHeight: 1.4,
                  }}
                >
                  {step.description}
                </p>
              </div>
              {!done && (
                <div style={{ color: COLORS.primary, flexShrink: 0 }}>
                  <FaArrowRight size={14} />
                </div>
              )}
            </motion.div>
          );
        })}
      </div>

      {/* Celebration when all done */}
      {allDone && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          style={{
            textAlign: "center",
            padding: "16px 0 0",
          }}
        >
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
              color: COLORS.success,
              fontSize: "14px",
              fontWeight: 600,
              margin: 0,
            }}
          >
            Parabéns! Você completou o onboarding.
          </p>
        </motion.div>
      )}
    </motion.div>
  );
};

export default OnboardingWalkthrough;
