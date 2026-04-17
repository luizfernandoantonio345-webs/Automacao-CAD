/**
 * ENGENHARIA CAD — Forgot Password Page
 * Página de solicitação de recuperação de senha
 */
import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import {
  FaArrowLeft,
  FaCheckCircle,
  FaEnvelope,
  FaLifeRing,
  FaShieldAlt,
} from "react-icons/fa";
import { api } from "../services/api";

const ForgotPassword: React.FC = () => {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      await api.post("/auth/forgot-password", { email });
      setSent(true);
    } catch {
      // Resposta intencionalmente neutra para não expor existência do email
      setSent(true);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        background:
          "radial-gradient(circle at 0% 0%, rgba(0,161,255,0.25) 0%, rgba(0,161,255,0) 35%), radial-gradient(circle at 100% 100%, rgba(0,102,204,0.18) 0%, rgba(0,102,204,0) 40%), linear-gradient(135deg, #030508 0%, #0a1628 40%, #071020 70%, #030508 100%)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "20px",
      }}
    >
      <motion.div
        initial={{ opacity: 0, y: 20, scale: 0.98 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ duration: 0.45 }}
        style={{
          background: "rgba(15, 23, 42, 0.88)",
          border: "1px solid rgba(0, 161, 255, 0.24)",
          borderRadius: "18px",
          padding: "40px",
          maxWidth: "460px",
          width: "100%",
          boxShadow: "0 24px 64px rgba(0, 0, 0, 0.45)",
          backdropFilter: "blur(10px)",
          WebkitBackdropFilter: "blur(10px)",
        }}
      >
        <Link
          to="/login"
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: "8px",
            color: "#94a3b8",
            textDecoration: "none",
            fontSize: "14px",
            marginBottom: "20px",
            fontWeight: 600,
          }}
        >
          <FaArrowLeft /> Voltar ao login
        </Link>

        {!sent ? (
          <>
            <div
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 8,
                padding: "6px 12px",
                borderRadius: 999,
                border: "1px solid rgba(0,161,255,0.32)",
                background: "rgba(0,161,255,0.1)",
                color: "#8ad4ff",
                fontSize: 11,
                fontWeight: 700,
                letterSpacing: "0.08em",
                textTransform: "uppercase",
                marginBottom: "18px",
              }}
            >
              <FaShieldAlt /> Segurança de conta
            </div>

            <div style={{ textAlign: "center", marginBottom: "30px" }}>
              <div
                style={{
                  width: "68px",
                  height: "68px",
                  borderRadius: "16px",
                  background:
                    "linear-gradient(135deg, #00A1FF 0%, #0066CC 100%)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  margin: "0 auto 16px",
                  boxShadow: "0 10px 24px rgba(0,161,255,0.35)",
                }}
              >
                <FaEnvelope size={28} color="white" />
              </div>
              <h1
                style={{
                  color: "#fff",
                  fontSize: "26px",
                  fontWeight: 800,
                  margin: 0,
                }}
              >
                Recuperar Senha
              </h1>
              <p
                style={{
                  color: "#94a3b8",
                  fontSize: "14px",
                  marginTop: "10px",
                  lineHeight: 1.6,
                }}
              >
                Informe seu email corporativo para receber um link seguro de
                redefinição.
              </p>
            </div>

            <form onSubmit={handleSubmit}>
              {error && (
                <div
                  style={{
                    background: "rgba(239, 68, 68, 0.1)",
                    border: "1px solid rgba(239, 68, 68, 0.3)",
                    borderRadius: "10px",
                    padding: "12px",
                    marginBottom: "16px",
                    color: "#ef4444",
                    fontSize: "14px",
                  }}
                >
                  {error}
                </div>
              )}

              <div style={{ marginBottom: "24px" }}>
                <label
                  style={{
                    display: "block",
                    color: "#b7c3d6",
                    fontSize: "14px",
                    marginBottom: "8px",
                    fontWeight: 600,
                  }}
                >
                  Email
                </label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="seu@email.com"
                  required
                  style={{
                    width: "100%",
                    padding: "14px 16px",
                    background: "rgba(30, 41, 59, 0.8)",
                    border: "1px solid rgba(100, 116, 139, 0.35)",
                    borderRadius: "12px",
                    color: "#fff",
                    fontSize: "15px",
                    outline: "none",
                  }}
                />
              </div>

              <motion.button
                type="submit"
                disabled={loading}
                whileHover={{ scale: 1.01 }}
                whileTap={{ scale: 0.99 }}
                style={{
                  width: "100%",
                  padding: "14px",
                  background: loading
                    ? "rgba(0, 161, 255, 0.45)"
                    : "linear-gradient(135deg, #00A1FF 0%, #0066CC 100%)",
                  border: "none",
                  borderRadius: "12px",
                  color: "#fff",
                  fontSize: "16px",
                  fontWeight: 700,
                  cursor: loading ? "not-allowed" : "pointer",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: "8px",
                  boxShadow: "0 10px 24px rgba(0,161,255,0.28)",
                }}
              >
                {loading ? (
                  "Enviando link seguro..."
                ) : (
                  <>
                    <FaEnvelope /> Enviar link de recuperação
                  </>
                )}
              </motion.button>
            </form>

            <div
              style={{
                marginTop: "16px",
                display: "flex",
                alignItems: "center",
                gap: 8,
                color: "#6f819a",
                fontSize: 12,
              }}
            >
              <FaLifeRing /> Precisa de ajuda? Contate o suporte corporativo.
            </div>
          </>
        ) : (
          <motion.div
            initial={{ opacity: 0, scale: 0.94 }}
            animate={{ opacity: 1, scale: 1 }}
            style={{ textAlign: "center" }}
          >
            <div
              style={{
                width: "84px",
                height: "84px",
                borderRadius: "50%",
                background: "rgba(16, 185, 129, 0.12)",
                border: "2px solid #10B981",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                margin: "0 auto 24px",
              }}
            >
              <FaCheckCircle size={36} color="#10B981" />
            </div>
            <h2
              style={{
                color: "#fff",
                fontSize: "24px",
                fontWeight: 800,
                margin: 0,
              }}
            >
              Solicitação registrada
            </h2>
            <p
              style={{
                color: "#94a3b8",
                fontSize: "14px",
                marginTop: "12px",
                lineHeight: 1.7,
              }}
            >
              Se existir uma conta para{" "}
              <strong style={{ color: "#00A1FF" }}>{email}</strong>, você
              receberá um link para redefinir sua senha.
            </p>
            <p
              style={{ color: "#64748b", fontSize: "13px", marginTop: "14px" }}
            >
              Confira também spam e promoções.
            </p>
            <motion.button
              onClick={() => navigate("/login")}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              style={{
                marginTop: "24px",
                padding: "12px 26px",
                background: "rgba(0, 161, 255, 0.12)",
                border: "1px solid rgba(0, 161, 255, 0.35)",
                borderRadius: "12px",
                color: "#00A1FF",
                fontSize: "15px",
                fontWeight: 700,
                cursor: "pointer",
              }}
            >
              Voltar para login
            </motion.button>
          </motion.div>
        )}
      </motion.div>
    </div>
  );
};

export default ForgotPassword;
