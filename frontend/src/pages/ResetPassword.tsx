/**
 * ENGENHARIA CAD — Reset Password Page
 * Página para redefinir a senha usando o token do email
 */
import React, { useState, useEffect } from "react";
import { useNavigate, useSearchParams, Link } from "react-router-dom";
import { motion } from "framer-motion";
import { FaLock, FaCheckCircle, FaTimesCircle, FaEye, FaEyeSlash } from "react-icons/fa";
import { api } from "../services/api";

const ResetPassword: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token");

  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState("");

  // Password strength indicators
  const passwordChecks = {
    length: password.length >= 8,
    uppercase: /[A-Z]/.test(password),
    lowercase: /[a-z]/.test(password),
    number: /[0-9]/.test(password),
    special: /[!@#$%^&*(),.?":{}|<>]/.test(password),
  };

  const passwordStrength = Object.values(passwordChecks).filter(Boolean).length;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    if (password !== confirmPassword) {
      setError("As senhas não coincidem");
      return;
    }

    if (passwordStrength < 3) {
      setError("A senha precisa ser mais forte");
      return;
    }

    if (!token) {
      setError("Token inválido");
      return;
    }

    setLoading(true);

    try {
      await api.post("/auth/reset-password", {
        token,
        new_password: password,
      });
      setSuccess(true);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Erro ao redefinir senha. O link pode ter expirado.");
    } finally {
      setLoading(false);
    }
  };

  if (!token) {
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
          style={{
            background: "rgba(15, 23, 42, 0.9)",
            border: "1px solid rgba(239, 68, 68, 0.3)",
            borderRadius: "16px",
            padding: "40px",
            maxWidth: "440px",
            textAlign: "center",
          }}
        >
          <div style={{ marginBottom: "16px" }}>
            <FaTimesCircle size={48} color="#ef4444" />
          </div>
          <h2 style={{ color: "#fff", fontSize: "20px", marginBottom: "12px" }}>
            Link Inválido
          </h2>
          <p style={{ color: "#94a3b8", fontSize: "14px", marginBottom: "24px" }}>
            Este link de recuperação é inválido ou expirou.
          </p>
          <Link
            to="/forgot-password"
            style={{
              color: "#00A1FF",
              textDecoration: "none",
              fontWeight: 600,
            }}
          >
            Solicitar novo link
          </Link>
        </motion.div>
      </div>
    );
  }

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
        {!success ? (
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
                <FaLock size={28} color="white" />
              </div>
              <h1 style={{ color: "#fff", fontSize: "24px", fontWeight: 700, margin: 0 }}>
                Nova Senha
              </h1>
              <p style={{ color: "#64748b", fontSize: "14px", marginTop: "8px" }}>
                Crie uma nova senha segura para sua conta
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

              {/* Password Field */}
              <div style={{ marginBottom: "16px" }}>
                <label style={{ display: "block", color: "#94a3b8", fontSize: "14px", marginBottom: "8px" }}>
                  Nova Senha
                </label>
                <div style={{ position: "relative" }}>
                  <input
                    type={showPassword ? "text" : "password"}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    required
                    style={{
                      width: "100%",
                      padding: "14px 48px 14px 16px",
                      background: "rgba(30, 41, 59, 0.8)",
                      border: "1px solid rgba(100, 116, 139, 0.3)",
                      borderRadius: "10px",
                      color: "#fff",
                      fontSize: "15px",
                      outline: "none",
                    }}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    style={{
                      position: "absolute",
                      right: "14px",
                      top: "50%",
                      transform: "translateY(-50%)",
                      background: "none",
                      border: "none",
                      color: "#64748b",
                      cursor: "pointer",
                      padding: "4px",
                    }}
                  >
                    {showPassword ? <FaEyeSlash /> : <FaEye />}
                  </button>
                </div>

                {/* Password Strength */}
                {password && (
                  <div style={{ marginTop: "12px" }}>
                    <div
                      style={{
                        display: "flex",
                        gap: "4px",
                        marginBottom: "8px",
                      }}
                    >
                      {[1, 2, 3, 4, 5].map((level) => (
                        <div
                          key={level}
                          style={{
                            flex: 1,
                            height: "4px",
                            borderRadius: "2px",
                            background:
                              passwordStrength >= level
                                ? passwordStrength <= 2
                                  ? "#ef4444"
                                  : passwordStrength <= 3
                                  ? "#f59e0b"
                                  : "#10B981"
                                : "rgba(100, 116, 139, 0.3)",
                          }}
                        />
                      ))}
                    </div>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: "8px", fontSize: "12px" }}>
                      <span style={{ color: passwordChecks.length ? "#10B981" : "#64748b" }}>
                        {passwordChecks.length ? "✓" : "○"} 8+ caracteres
                      </span>
                      <span style={{ color: passwordChecks.uppercase ? "#10B981" : "#64748b" }}>
                        {passwordChecks.uppercase ? "✓" : "○"} Maiúscula
                      </span>
                      <span style={{ color: passwordChecks.number ? "#10B981" : "#64748b" }}>
                        {passwordChecks.number ? "✓" : "○"} Número
                      </span>
                      <span style={{ color: passwordChecks.special ? "#10B981" : "#64748b" }}>
                        {passwordChecks.special ? "✓" : "○"} Especial
                      </span>
                    </div>
                  </div>
                )}
              </div>

              {/* Confirm Password Field */}
              <div style={{ marginBottom: "24px" }}>
                <label style={{ display: "block", color: "#94a3b8", fontSize: "14px", marginBottom: "8px" }}>
                  Confirmar Senha
                </label>
                <input
                  type={showPassword ? "text" : "password"}
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="••••••••"
                  required
                  style={{
                    width: "100%",
                    padding: "14px 16px",
                    background: "rgba(30, 41, 59, 0.8)",
                    border: `1px solid ${
                      confirmPassword && confirmPassword !== password
                        ? "rgba(239, 68, 68, 0.5)"
                        : "rgba(100, 116, 139, 0.3)"
                    }`,
                    borderRadius: "10px",
                    color: "#fff",
                    fontSize: "15px",
                    outline: "none",
                  }}
                />
                {confirmPassword && confirmPassword !== password && (
                  <p style={{ color: "#ef4444", fontSize: "12px", marginTop: "6px" }}>
                    As senhas não coincidem
                  </p>
                )}
              </div>

              <motion.button
                type="submit"
                disabled={loading || passwordStrength < 3 || password !== confirmPassword}
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                style={{
                  width: "100%",
                  padding: "14px",
                  background:
                    loading || passwordStrength < 3 || password !== confirmPassword
                      ? "rgba(0, 161, 255, 0.3)"
                      : "linear-gradient(135deg, #00A1FF 0%, #0066CC 100%)",
                  border: "none",
                  borderRadius: "10px",
                  color: "#fff",
                  fontSize: "16px",
                  fontWeight: 600,
                  cursor:
                    loading || passwordStrength < 3 || password !== confirmPassword
                      ? "not-allowed"
                      : "pointer",
                }}
              >
                {loading ? "Redefinindo..." : "Redefinir Senha"}
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
              <FaCheckCircle size={36} color="#10B981" />
            </div>
            <h2 style={{ color: "#fff", fontSize: "22px", fontWeight: 700, margin: 0 }}>
              Senha Atualizada!
            </h2>
            <p style={{ color: "#94a3b8", fontSize: "14px", marginTop: "12px", lineHeight: 1.6 }}>
              Sua senha foi redefinida com sucesso. Você já pode fazer login com a nova senha.
            </p>
            <motion.button
              onClick={() => navigate("/login")}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              style={{
                marginTop: "24px",
                padding: "14px 32px",
                background: "linear-gradient(135deg, #00A1FF 0%, #0066CC 100%)",
                border: "none",
                borderRadius: "10px",
                color: "#fff",
                fontSize: "15px",
                fontWeight: 600,
                cursor: "pointer",
              }}
            >
              Ir para Login
            </motion.button>
          </motion.div>
        )}
      </motion.div>
    </div>
  );
};

export default ResetPassword;
