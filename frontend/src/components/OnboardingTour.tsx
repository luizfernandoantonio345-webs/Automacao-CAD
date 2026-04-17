/**
 * OnboardingTour.tsx — AutomAção CAD Enterprise
 *
 * Tour guiado de 5 passos usando framer-motion (sem dependências externas).
 * Destaca elementos do DOM via spotlight + popover posicionado.
 *
 * @usage
 * <OnboardingTour
 *   steps={ONBOARDING_STEPS}
 *   active={showTour}
 *   onFinish={() => setShowTour(false)}
 * />
 */

import React, { useCallback, useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { ChevronRight, ChevronLeft, X } from "lucide-react";
import { colors, radius, shadows, spacing, zIndex } from "../design/tokens";

// ─────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────

export interface TourStep {
  /** data-tour attribute value of the target element */
  target: string;
  title: string;
  description: string;
  /** Preferred popover placement (auto-adjusts if out of viewport) */
  placement?: "top" | "bottom" | "left" | "right";
}

export interface OnboardingTourProps {
  steps: TourStep[];
  active: boolean;
  onFinish: () => void;
  /** LocalStorage key to remember completion (default: "engcad_tour_done") */
  storageKey?: string;
}

// ─────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────

function getTargetRect(target: string): DOMRect | null {
  const el = document.querySelector(`[data-tour="${target}"]`);
  return el ? el.getBoundingClientRect() : null;
}

const PADDING = 8; // px around highlighted element

interface PopoverPos {
  top: number;
  left: number;
  transformOrigin: string;
}

function calcPopoverPos(
  rect: DOMRect,
  placement: TourStep["placement"],
  popW = 320,
  popH = 180,
): PopoverPos {
  const vw = window.innerWidth;
  const vh = window.innerHeight;
  const cx = rect.left + rect.width / 2;
  const cy = rect.top + rect.height / 2;

  let top: number;
  let left: number;
  let transformOrigin = "top center";

  const tryBottom = rect.bottom + PADDING + 16 + popH < vh;
  const tryTop = rect.top - PADDING - 16 - popH > 0;
  const tryRight = rect.right + PADDING + 16 + popW < vw;

  const resolved =
    placement === "bottom" && tryBottom
      ? "bottom"
      : placement === "top" && tryTop
        ? "top"
        : placement === "right" && tryRight
          ? "right"
          : tryBottom
            ? "bottom"
            : tryTop
              ? "top"
              : "bottom";

  if (resolved === "bottom") {
    top = rect.bottom + PADDING + 16;
    left = Math.max(16, Math.min(cx - popW / 2, vw - popW - 16));
    transformOrigin = "top center";
  } else if (resolved === "top") {
    top = rect.top - PADDING - 16 - popH;
    left = Math.max(16, Math.min(cx - popW / 2, vw - popW - 16));
    transformOrigin = "bottom center";
  } else {
    top = Math.max(16, Math.min(cy - popH / 2, vh - popH - 16));
    left = rect.right + PADDING + 16;
    transformOrigin = "center left";
  }

  return { top, left, transformOrigin };
}

// ─────────────────────────────────────────────────────────────
// Spotlight overlay (SVG clip-path with animated hole)
// ─────────────────────────────────────────────────────────────

const Spotlight: React.FC<{ rect: DOMRect | null }> = ({ rect }) => {
  if (!rect) return null;

  const x = rect.left - PADDING;
  const y = rect.top - PADDING;
  const w = rect.width + PADDING * 2;
  const h = rect.height + PADDING * 2;
  const r = Number(radius.lg.replace("px", "")) || 12;

  const vw = window.innerWidth;
  const vh = window.innerHeight;

  // SVG path: full viewport minus a rounded rect cutout
  const path = `M0,0 H${vw} V${vh} H0 Z
    M${x + r},${y}
    H${x + w - r} Q${x + w},${y} ${x + w},${y + r}
    V${y + h - r} Q${x + w},${y + h} ${x + w - r},${y + h}
    H${x + r} Q${x},${y + h} ${x},${y + h - r}
    V${y + r} Q${x},${y} ${x + r},${y} Z`;

  return (
    <motion.svg
      style={{
        position: "fixed",
        inset: 0,
        width: "100vw",
        height: "100vh",
        pointerEvents: "none",
        zIndex: (zIndex?.overlay ?? 100) + 1,
      }}
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
    >
      <path d={path} fill="rgba(0,0,0,0.72)" fillRule="evenodd" />
      {/* subtle glow ring around highlight */}
      <rect
        x={x}
        y={y}
        width={w}
        height={h}
        rx={r}
        fill="none"
        stroke={colors.primary?.DEFAULT ?? "#00A1FF"}
        strokeWidth="2"
        opacity="0.7"
      />
    </motion.svg>
  );
};

// ─────────────────────────────────────────────────────────────
// Popover card
// ─────────────────────────────────────────────────────────────

const Popover: React.FC<{
  step: TourStep;
  idx: number;
  total: number;
  rect: DOMRect | null;
  onNext: () => void;
  onPrev: () => void;
  onClose: () => void;
}> = ({ step, idx, total, rect, onNext, onPrev, onClose }) => {
  const pos = rect
    ? calcPopoverPos(rect, step.placement)
    : {
        top: window.innerHeight / 2 - 90,
        left: window.innerWidth / 2 - 160,
        transformOrigin: "center",
      };

  return (
    <motion.div
      key={idx}
      initial={{ opacity: 0, scale: 0.88 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.88 }}
      transition={{ type: "spring", stiffness: 350, damping: 28 }}
      style={{
        position: "fixed",
        top: pos.top,
        left: pos.left,
        width: 320,
        zIndex: (zIndex?.overlay ?? 100) + 2,
        background: colors.dark?.elevated ?? "#141B2D",
        border: `1px solid ${colors.border?.subtle ?? "#1e2a3a"}`,
        borderRadius: radius.xl,
        boxShadow: shadows?.xl ?? "0 24px 64px rgba(0,0,0,0.5)",
        padding: `${spacing[5]} ${spacing[6]}`,
        transformOrigin: pos.transformOrigin,
      }}
    >
      {/* Close button */}
      <button
        onClick={onClose}
        aria-label="Fechar tour"
        style={{
          position: "absolute",
          top: spacing[3],
          right: spacing[3],
          background: "transparent",
          border: "none",
          cursor: "pointer",
          color: colors.text?.tertiary ?? "#6b7a99",
          lineHeight: 1,
          padding: 4,
        }}
      >
        <X size={14} />
      </button>

      {/* Progress dots */}
      <div style={{ display: "flex", gap: 6, marginBottom: spacing[4] }}>
        {Array.from({ length: total }).map((_, i) => (
          <motion.div
            key={i}
            animate={{ width: i === idx ? 20 : 6, opacity: i <= idx ? 1 : 0.3 }}
            transition={{ duration: 0.3 }}
            style={{
              height: 6,
              borderRadius: 9999,
              background:
                i === idx
                  ? (colors.primary?.DEFAULT ?? "#00A1FF")
                  : (colors.border?.subtle ?? "#1e2a3a"),
            }}
          />
        ))}
      </div>

      {/* Step label */}
      <p
        style={{
          margin: "0 0 4px",
          fontSize: 11,
          color: colors.primary?.DEFAULT ?? "#00A1FF",
          fontWeight: 600,
          letterSpacing: "0.08em",
          textTransform: "uppercase",
        }}
      >
        Passo {idx + 1} de {total}
      </p>

      {/* Title */}
      <h3
        style={{
          margin: "0 0 8px",
          fontSize: 16,
          fontWeight: 700,
          color: colors.text?.primary ?? "#e8f0fe",
          lineHeight: 1.3,
        }}
      >
        {step.title}
      </h3>

      {/* Description */}
      <p
        style={{
          margin: "0 0 20px",
          fontSize: 14,
          color: colors.text?.secondary ?? "#8896b3",
          lineHeight: 1.6,
        }}
      >
        {step.description}
      </p>

      {/* Navigation */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <button
          onClick={onPrev}
          disabled={idx === 0}
          style={{
            display: "flex",
            alignItems: "center",
            gap: 4,
            background: "transparent",
            border: `1px solid ${colors.border?.subtle ?? "#1e2a3a"}`,
            borderRadius: radius.md,
            padding: "6px 12px",
            cursor: idx === 0 ? "not-allowed" : "pointer",
            color:
              idx === 0
                ? (colors.text?.disabled ?? "#3a4560")
                : (colors.text?.secondary ?? "#8896b3"),
            fontSize: 13,
            fontWeight: 500,
          }}
        >
          <ChevronLeft size={14} /> Anterior
        </button>

        <button
          onClick={onNext}
          style={{
            display: "flex",
            alignItems: "center",
            gap: 4,
            background: colors.primary?.DEFAULT ?? "#00A1FF",
            border: "none",
            borderRadius: radius.md,
            padding: "6px 16px",
            cursor: "pointer",
            color: "#fff",
            fontSize: 13,
            fontWeight: 600,
          }}
        >
          {idx === total - 1 ? "Concluir" : "Próximo"}{" "}
          <ChevronRight size={14} />
        </button>
      </div>
    </motion.div>
  );
};

// ─────────────────────────────────────────────────────────────
// Main component
// ─────────────────────────────────────────────────────────────

export const OnboardingTour: React.FC<OnboardingTourProps> = ({
  steps,
  active,
  onFinish,
  storageKey = "engcad_tour_done",
}) => {
  const [idx, setIdx] = useState(0);
  const [rect, setRect] = useState<DOMRect | null>(null);
  const rafRef = useRef<number | null>(null);

  const updateRect = useCallback(() => {
    if (active && steps[idx]) {
      setRect(getTargetRect(steps[idx].target));
    }
  }, [active, idx, steps]);

  useEffect(() => {
    updateRect();
    const onResize = () => updateRect();
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, [updateRect]);

  // Scroll target into view when step changes
  useEffect(() => {
    if (!active || !steps[idx]) return;
    const el = document.querySelector(`[data-tour="${steps[idx].target}"]`);
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "center" });
      // Wait for scroll to finish before measuring
      rafRef.current = requestAnimationFrame(() => {
        rafRef.current = requestAnimationFrame(updateRect);
      });
    }
    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
  }, [active, idx, steps, updateRect]);

  const handleNext = () => {
    if (idx < steps.length - 1) {
      setIdx((i) => i + 1);
    } else {
      handleFinish();
    }
  };

  const handlePrev = () => setIdx((i) => Math.max(0, i - 1));

  const handleFinish = () => {
    try {
      localStorage.setItem(storageKey, "1");
    } catch {
      /* ignore */
    }
    onFinish();
    setIdx(0);
  };

  if (!active) return null;

  return (
    <AnimatePresence>
      {/* Backdrop: blocks pointer on rest of page */}
      <div
        key="backdrop"
        onClick={(e) => e.stopPropagation()}
        style={{
          position: "fixed",
          inset: 0,
          zIndex: zIndex?.overlay ?? 100,
          pointerEvents: "all",
          cursor: "default",
        }}
      />

      <Spotlight key={`spot-${idx}`} rect={rect} />

      <Popover
        key={`pop-${idx}`}
        step={steps[idx]}
        idx={idx}
        total={steps.length}
        rect={rect}
        onNext={handleNext}
        onPrev={handlePrev}
        onClose={handleFinish}
      />
    </AnimatePresence>
  );
};

// ─────────────────────────────────────────────────────────────
// Default 5-step tour for EngCAD Dashboard
// ─────────────────────────────────────────────────────────────

export const DEFAULT_TOUR_STEPS: TourStep[] = [
  {
    target: "tour-dashboard",
    title: "Bem-vindo ao EngCAD!",
    description:
      "Este é o seu painel central. Aqui você acompanha KPIs, projetos ativos e ações rápidas.",
    placement: "bottom",
  },
  {
    target: "tour-kpi-grid",
    title: "Métricas em tempo real",
    description:
      "Acompanhe projetos gerados, taxa de aprovação, uptime e comandos AutoCAD executados.",
    placement: "bottom",
  },
  {
    target: "tour-quick-actions",
    title: "Ações rápidas",
    description:
      "Crie novos projetos, envie planilhas Excel ou abra o gerador de tubulações com um clique.",
    placement: "top",
  },
  {
    target: "tour-autocad-connect",
    title: "Conexão AutoCAD",
    description:
      "Conecte-se ao seu AutoCAD local para enviar comandos e sincronizar desenhos automaticamente.",
    placement: "bottom",
  },
  {
    target: "tour-sidebar",
    title: "Navegação completa",
    description:
      "Acesse CAD, análise de qualidade, faturamento, configurações e suporte pelo menu lateral.",
    placement: "right",
  },
];

export default OnboardingTour;
