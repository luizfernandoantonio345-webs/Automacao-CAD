/**
 * ENGENHARIA CAD — Forgot Password Page
 * Página de solicitação de recuperação de senha
 */
import React, { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { motion } from "framer-motion";
import { FaEnvelope, FaArrowLeft, FaCheckCircle } from "react-icons/fa";
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
    } catch (err: any) {
      // Sempre mostrar sucesso para não expor se email existe
      setSent(true);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "linear-gradient(135deg, #030508 0%, #0a1628 40%, #071020 70%, #030508 100%)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "20px",
      }}
    >
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        style={{
          background: "rgba(15, 23, 42, 0.9)",
          border: "1px solid rgba(0, 161, 255, 0.2)",
          borderRadius: "16px",
          padding: "40px",
          maxWidth: "440px",
          width: "100%",
          boxShadow: "0 25px 50px -12px rgba(0, 0, 0, 0.5)",
        }}
      >
        {/* Back link */}
        <Link
          to="/login"
          style={{
            display: "flex",
            alignItems: "center",
            gap: "8px",
            color: "#64748b",
            textDecoration: "none",
            fontSize: "14px",
            marginBottom: "24px",
          }}
        >
          <FaArrowLeft /> Voltar ao login
        </Link>

        {!sent ? (
          <>
            {/* Header */}
            <div style={{ textAlign: "center", marginBottom: "32px" }}>
              <div
                style={{
                  width: "64px",
                  height: "64px",
                  borderRadius: "50%",
                  background: "linear-gradient(135deg, #00A1FF 0%, #0066CC 100%)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  margin: "0 auto 16px",
                }}
              >
                <FaEnvelope style={{ fontSize: "28px", color: "white" }} />
              </div>
              <h1 style={{ color: "#fff", fontSize: "24px", fontWeight: 700, margin: 0 }}>
                Esqueceu a Senha?
              </h1>
              <p style={{ color: "#64748b", fontSize: "14px", marginTop: "8px" }}>
                Digite seu email e enviaremos instruções para recuperar sua senha.
              </p>
            </div>

            {/* Form */}
            <form onSubmit={handleSubmit}>
              {error && (
                <div
                  style={{
                    background: "rgba(239, 68, 68, 0.1)",
                    border: "1px solid rgba(239, 68, 68, 0.3)",
                    borderRadius: "8px",
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
                    color: "#94a3b8",
                    fontSize: "14px",
                    marginBottom: "8px",
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
                    border: "1px solid rgba(100, 116, 139, 0.3)",
                    borderRadius: "10px",
                    color: "#fff",
                    fontSize: "15px",
                    outline: "none",
                    transition: "border-color 0.2s",
                  }}
                />
              </div>

              <motion.button
                type="submit"
                disabled={loading}
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                style={{
                  width: "100%",
                  padding: "14px",
                  background: loading
                    ? "rgba(0, 161, 255, 0.5)"
                    : "linear-gradient(135deg, #00A1FF 0%, #0066CC 100%)",
                  border: "none",
                  borderRadius: "10px",
                  color: "#fff",
                  fontSize: "16px",
                  fontWeight: 600,
                  cursor: loading ? "not-allowed" : "pointer",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: "8px",
                }}
              >
                {loading ? (
                  <span>Enviando...</span>
                ) : (
                  <>
                    <FaEnvelope /> Enviar Link de Recuperação
                  </>
                )}
              </motion.button>
            </form>
          </>
        ) : (
          /* Success State */
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            style={{ textAlign: "center" }}
          >
            <div
              style={{
                width: "80px",
                height: "80px",
                borderRadius: "50%",
                background: "rgba(16, 185, 129, 0.1)",
                border: "2px solid #10B981",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                margin: "0 auto 24px",
              }}
            >
              <FaCheckCircle style={{ fontSize: "36px", color: "#10B981" }} />
            </div>
            <h2 style={{ color: "#fff", fontSize: "22px", fontWeight: 700, margin: 0 }}>
              Email Enviado!
            </h2>
            <p style={{ color: "#94a3b8", fontSize: "14px", marginTop: "12px", lineHeight: 1.6 }}>
              Se existe uma conta com o email <strong style={{ color: "#00A1FF" }}>{email}</strong>,
              você receberá um link para redefinir sua senha.
            </p>
            <p style={{ color: "#64748b", fontSize: "13px", marginTop: "16px" }}>
              Verifique também a pasta de spam.
            </p>
            <motion.button
              onClick={() => navigate("/login")}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              style={{
                marginTop: "24px",
                padding: "12px 24px",
                background: "rgba(0, 161, 255, 0.1)",
                border: "1px solid rgba(0, 161, 255, 0.3)",
                borderRadius: "10px",
                color: "#00A1FF",
                fontSize: "15px",
                fontWeight: 600,
                cursor: "pointer",
              }}
            >
              Voltar ao Login
            </motion.button>
          </motion.div>
        )}
      </motion.div>
    </div>
  );
};

export default ForgotPassword;
