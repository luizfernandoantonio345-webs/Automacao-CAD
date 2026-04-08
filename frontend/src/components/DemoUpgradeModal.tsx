/**
 * ENGENHARIA CAD – DemoUpgradeModal
 * Modal de persuasão exibido quando usuário demo atinge limites.
 * Otimizado para conversão: urgência, social proof, benefícios claros.
 */
import React from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  FaLock,
  FaRocket,
  FaTimes,
  FaCrown,
  FaCheck,
  FaWhatsapp,
  FaStar,
  FaBolt,
  FaShieldAlt,
} from "react-icons/fa";
import { useLicense } from "../context/LicenseContext";

const PERSUASION_STATS = [
  { value: "85%", label: "redução no tempo de projeto" },
  { value: "3x", label: "mais projetos entregues" },
  { value: "50+", label: "normas validadas automaticamente" },
];

const DemoUpgradeModal: React.FC = () => {
  const { showUpgradeModal, upgradeReason, dismissUpgrade, license } =
    useLicense();

  if (!showUpgradeModal) return null;

  const isDemo = license.isDemo;

  return (
    <AnimatePresence>
      {showUpgradeModal && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          style={overlay}
          onClick={dismissUpgrade}
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.85, y: 40 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.85, y: 40 }}
            transition={{ type: "spring", damping: 20, stiffness: 300 }}
            style={modal}
            onClick={(e) => e.stopPropagation()}
          >
            {/* Close */}
            <button style={closeBtn} onClick={dismissUpgrade}>
              <FaTimes size={14} />
            </button>

            {/* Top accent */}
            <div style={accentBar} />

            {/* Icon */}
            <div style={iconWrapper}>
              <motion.div
                animate={{ rotate: [0, -10, 10, -10, 0] }}
                transition={{ duration: 0.6, delay: 0.3 }}
              >
                <FaLock size={32} color="#00A1FF" />
              </motion.div>
            </div>

            {/* Title */}
            <h2 style={title}>
              {isDemo ? "Limite do Demo Atingido" : "Limite do Plano Atingido"}
            </h2>
            <p style={subtitle}>{upgradeReason}</p>

            {/* Social proof */}
            <div style={statsRow}>
              {PERSUASION_STATS.map((s, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.2 + i * 0.1 }}
                  style={statCard}
                >
                  <span style={statValue}>{s.value}</span>
                  <span style={statLabel}>{s.label}</span>
                </motion.div>
              ))}
            </div>

            {/* Benefits teaser */}
            <div style={benefitsList}>
              {[
                "IA ilimitada para projetos CAD",
                "Controle CNC e nesting inteligente",
                "Validação automática de normas ASME",
                "Relatórios certificáveis PDF/DXF",
                "Suporte técnico especializado",
              ].map((b, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.3 + i * 0.07 }}
                  style={benefitRow}
                >
                  <FaCheck size={11} color="#10B981" />
                  <span style={benefitText}>{b}</span>
                </motion.div>
              ))}
            </div>

            {/* Urgency badge */}
            <motion.div
              animate={{ opacity: [1, 0.7, 1] }}
              transition={{ duration: 1.5, repeat: Infinity }}
              style={urgencyBadge}
            >
              <FaBolt size={11} />
              Oferta de boas-vindas: 20% OFF no primeiro mês
            </motion.div>

            {/* CTAs */}
            <div style={ctaGroup}>
              <motion.button
                whileHover={{
                  scale: 1.03,
                  boxShadow: "0 8px 30px rgba(0,161,255,0.4)",
                }}
                whileTap={{ scale: 0.97 }}
                onClick={() => {
                  dismissUpgrade();
                  window.location.href = "/pricing";
                }}
                style={primaryCta}
              >
                <FaRocket size={16} />
                Ver Planos e Preços
              </motion.button>

              <motion.button
                whileHover={{ scale: 1.03 }}
                whileTap={{ scale: 0.97 }}
                onClick={() => {
                  dismissUpgrade();
                  window.open(
                    "https://wa.me/5511999999999?text=Olá!%20Tenho%20interesse%20no%20plano%20Professional%20do%20Engenharia%20CAD.",
                    "_blank",
                  );
                }}
                style={whatsappCta}
              >
                <FaWhatsapp size={16} />
                Falar com Consultor
              </motion.button>
            </div>

            {/* Trust signals */}
            <div style={trustRow}>
              <FaShieldAlt size={11} color="#556677" />
              <span style={trustText}>
                30 dias de garantia • Cancelamento fácil • Sem fidelidade
              </span>
            </div>

            {/* Social proof count */}
            <p style={socialProof}>
              <FaStar size={11} color="#F59E0B" />
              <FaStar size={11} color="#F59E0B" />
              <FaStar size={11} color="#F59E0B" />
              <FaStar size={11} color="#F59E0B" />
              <FaStar size={11} color="#F59E0B" />
              &nbsp; Mais de 120 engenheiros já utilizam
            </p>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};

// ── Styles ──────────────────────────────────────────────────
const overlay: React.CSSProperties = {
  position: "fixed",
  inset: 0,
  background: "rgba(0,0,0,0.75)",
  backdropFilter: "blur(8px)",
  zIndex: 99999,
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  padding: "16px",
};

const modal: React.CSSProperties = {
  position: "relative",
  background: "linear-gradient(180deg, #0d1117 0%, #111620 100%)",
  border: "1px solid #1a2030",
  borderRadius: "20px",
  padding: "36px 32px 28px",
  maxWidth: "420px",
  width: "100%",
  textAlign: "center",
  fontFamily: "'Inter','Segoe UI',Roboto,sans-serif",
  overflow: "hidden",
  boxShadow: "0 20px 60px rgba(0,0,0,0.6), 0 0 40px rgba(0,161,255,0.1)",
};

const accentBar: React.CSSProperties = {
  position: "absolute",
  top: 0,
  left: 0,
  right: 0,
  height: "3px",
  background:
    "linear-gradient(90deg, transparent, #00A1FF, #10B981, transparent)",
};

const closeBtn: React.CSSProperties = {
  position: "absolute",
  top: "16px",
  right: "16px",
  background: "#1a2030",
  border: "none",
  borderRadius: "6px",
  color: "#8899aa",
  cursor: "pointer",
  padding: "6px",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
};

const iconWrapper: React.CSSProperties = {
  width: "72px",
  height: "72px",
  borderRadius: "18px",
  background: "rgba(0,161,255,0.1)",
  border: "1px solid rgba(0,161,255,0.3)",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  margin: "0 auto 20px",
};

const title: React.CSSProperties = {
  color: "#FFFFFF",
  fontSize: "22px",
  fontWeight: 800,
  margin: "0 0 8px",
  letterSpacing: "-0.02em",
};

const subtitle: React.CSSProperties = {
  color: "#8899aa",
  fontSize: "14px",
  margin: "0 0 24px",
  lineHeight: "1.5",
};

const statsRow: React.CSSProperties = {
  display: "flex",
  gap: "10px",
  justifyContent: "center",
  marginBottom: "20px",
};

const statCard: React.CSSProperties = {
  background: "rgba(0,161,255,0.07)",
  border: "1px solid rgba(0,161,255,0.15)",
  borderRadius: "10px",
  padding: "10px 14px",
  display: "flex",
  flexDirection: "column",
  alignItems: "center",
  flex: 1,
};

const statValue: React.CSSProperties = {
  color: "#00A1FF",
  fontSize: "20px",
  fontWeight: 900,
  lineHeight: 1,
  marginBottom: "4px",
};

const statLabel: React.CSSProperties = {
  color: "#8899aa",
  fontSize: "10px",
  lineHeight: 1.3,
  textAlign: "center",
};

const benefitsList: React.CSSProperties = {
  textAlign: "left",
  marginBottom: "18px",
  display: "flex",
  flexDirection: "column",
  gap: "8px",
};

const benefitRow: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: "10px",
};

const benefitText: React.CSSProperties = {
  color: "#aabbcc",
  fontSize: "13px",
};

const urgencyBadge: React.CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  gap: "6px",
  background: "rgba(245,158,11,0.15)",
  border: "1px solid rgba(245,158,11,0.4)",
  borderRadius: "20px",
  padding: "6px 14px",
  color: "#F59E0B",
  fontSize: "12px",
  fontWeight: 600,
  marginBottom: "20px",
};

const ctaGroup: React.CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: "10px",
  marginBottom: "16px",
};

const primaryCta: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  gap: "10px",
  padding: "14px 24px",
  background: "linear-gradient(135deg, #00A1FF, #0077CC)",
  border: "none",
  borderRadius: "10px",
  color: "#FFF",
  fontSize: "15px",
  fontWeight: 700,
  cursor: "pointer",
  letterSpacing: "0.02em",
  transition: "all 0.2s",
};

const whatsappCta: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  gap: "10px",
  padding: "12px 24px",
  background: "rgba(37,211,102,0.1)",
  border: "1px solid rgba(37,211,102,0.4)",
  borderRadius: "10px",
  color: "#25D366",
  fontSize: "14px",
  fontWeight: 600,
  cursor: "pointer",
  transition: "all 0.2s",
};

const trustRow: React.CSSProperties = {
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  gap: "6px",
  marginBottom: "10px",
};

const trustText: React.CSSProperties = {
  color: "#556677",
  fontSize: "11px",
};

const socialProof: React.CSSProperties = {
  color: "#667788",
  fontSize: "12px",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  gap: "3px",
  margin: 0,
};

export default DemoUpgradeModal;
