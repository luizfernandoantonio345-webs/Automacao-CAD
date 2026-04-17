/**
 * ENGENHARIA CAD — Reset Password Page
 * Página para redefinir a senha usando o token do email
 */
import React, { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { motion } from "framer-motion";
import {
  FaCheckCircle,
  FaEye,
  FaEyeSlash,
  FaLock,
  FaShieldAlt,
  FaTimesCircle,
} from "react-icons/fa";
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
      setError(
        err.response?.data?.detail ||
          "Erro ao redefinir senha. O link pode ter expirado.",
      );
    } finally {
      setLoading(false);
    }
  };

  if (!token) {
    return (
      <div
        style={{
          minHeight: "100vh",
          background:
            "radial-gradient(circle at 0% 0%, rgba(239,68,68,0.2) 0%, rgba(239,68,68,0) 32%), linear-gradient(135deg, #030508 0%, #0a1628 40%, #071020 70%, #030508 100%)",
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
            border: "1px solid rgba(239, 68, 68, 0.32)",
            borderRadius: "18px",
            padding: "42px",
            maxWidth: "460px",
            textAlign: "center",
            boxShadow: "0 24px 64px rgba(0,0,0,0.45)",
          }}
        >
          <div style={{ marginBottom: "14px" }}>
            <FaTimesCircle size={52} color="#ef4444" />
          </div>
          <h2
            style={{
              color: "#fff",
              fontSize: "24px",
              marginBottom: "12px",
              fontWeight: 800,
            }}
          >
            Link inválido ou expirado
          </h2>
          <p
            style={{
              color: "#94a3b8",
              fontSize: "14px",
              marginBottom: "24px",
              lineHeight: 1.6,
            }}
          >
            Solicite um novo link para redefinir sua senha com segurança.
          </p>
          <Link
            to="/forgot-password"
            style={{
              color: "#00A1FF",
              textDecoration: "none",
              fontWeight: 700,
              border: "1px solid rgba(0,161,255,0.35)",
              padding: "10px 14px",
              borderRadius: "10px",
              display: "inline-block",
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
        background:
          "radial-gradient(circle at 0% 0%, rgba(0,161,255,0.25) 0%, rgba(0,161,255,0) 35%), radial-gradient(circle at 100% 100%, rgba(0,102,204,0.16) 0%, rgba(0,102,204,0) 40%), linear-gradient(135deg, #030508 0%, #0a1628 40%, #071020 70%, #030508 100%)",
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
          background: "rgba(15, 23, 42, 0.9)",
          border: "1px solid rgba(0, 161, 255, 0.22)",
          borderRadius: "18px",
          padding: "40px",
          maxWidth: "460px",
          width: "100%",
          boxShadow: "0 24px 64px rgba(0, 0, 0, 0.45)",
          backdropFilter: "blur(10px)",
          WebkitBackdropFilter: "blur(10px)",
        }}
      >
        {!success ? (
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
              <FaShieldAlt /> Nova credencial segura
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
                <FaLock size={28} color="white" />
              </div>
              <h1
                style={{
                  color: "#fff",
                  fontSize: "26px",
                  fontWeight: 800,
                  margin: 0,
                }}
              >
                Definir nova senha
              </h1>
              <p
                style={{
                  color: "#94a3b8",
                  fontSize: "14px",
                  marginTop: "10px",
                  lineHeight: 1.6,
                }}
              >
                Crie uma senha forte para concluir a recuperação da sua conta.
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

              <div style={{ marginBottom: "16px" }}>
                <label
                  style={{
                    display: "block",
                    color: "#b7c3d6",
                    fontSize: "14px",
                    marginBottom: "8px",
                    fontWeight: 600,
                  }}
                >
                  Nova senha
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
                      border: "1px solid rgba(100, 116, 139, 0.35)",
                      borderRadius: "12px",
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
                      color: "#7f92ad",
                      cursor: "pointer",
                    }}
                  >
                    {showPassword ? <FaEyeSlash /> : <FaEye />}
                  </button>
                </div>

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
                    <div
                      style={{
                        display: "flex",
                        flexWrap: "wrap",
                        gap: "8px",
                        fontSize: "12px",
                      }}
                    >
                      <span
                        style={{
                          color: passwordChecks.length ? "#10B981" : "#64748b",
                        }}
                      >
                        {passwordChecks.length ? "✓" : "○"} 8+ caracteres
                      </span>
                      <span
                        style={{
                          color: passwordChecks.uppercase
                            ? "#10B981"
                            : "#64748b",
                        }}
                      >
                        {passwordChecks.uppercase ? "✓" : "○"} Maiúscula
                      </span>
                      <span
                        style={{
                          color: passwordChecks.number ? "#10B981" : "#64748b",
                        }}
                      >
                        {passwordChecks.number ? "✓" : "○"} Número
                      </span>
                      <span
                        style={{
                          color: passwordChecks.special ? "#10B981" : "#64748b",
                        }}
                      >
                        {passwordChecks.special ? "✓" : "○"} Especial
                      </span>
                    </div>
                  </div>
                )}
              </div>

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
                  Confirmar senha
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
                        : "rgba(100, 116, 139, 0.35)"
                    }`,
                    borderRadius: "12px",
                    color: "#fff",
                    fontSize: "15px",
                    outline: "none",
                  }}
                />
                {confirmPassword && confirmPassword !== password && (
                  <p
                    style={{
                      color: "#ef4444",
                      fontSize: "12px",
                      marginTop: "6px",
                    }}
                  >
                    As senhas não coincidem.
                  </p>
                )}
              </div>

              <motion.button
                type="submit"
                disabled={
                  loading ||
                  passwordStrength < 3 ||
                  password !== confirmPassword
                }
                whileHover={{ scale: 1.01 }}
                whileTap={{ scale: 0.99 }}
                style={{
                  width: "100%",
                  padding: "14px",
                  background:
                    loading ||
                    passwordStrength < 3 ||
                    password !== confirmPassword
                      ? "rgba(0, 161, 255, 0.35)"
                      : "linear-gradient(135deg, #00A1FF 0%, #0066CC 100%)",
                  border: "none",
                  borderRadius: "12px",
                  color: "#fff",
                  fontSize: "16px",
                  fontWeight: 700,
                  cursor:
                    loading ||
                    passwordStrength < 3 ||
                    password !== confirmPassword
                      ? "not-allowed"
                      : "pointer",
                  boxShadow: "0 10px 24px rgba(0,161,255,0.28)",
                }}
              >
                {loading ? "Redefinindo senha..." : "Redefinir senha"}
              </motion.button>
            </form>
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
              Senha atualizada com sucesso
            </h2>
            <p
              style={{
                color: "#94a3b8",
                fontSize: "14px",
                marginTop: "12px",
                lineHeight: 1.7,
              }}
            >
              Sua conta já pode ser acessada com a nova senha.
            </p>
            <motion.button
              onClick={() => navigate("/login")}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              style={{
                marginTop: "24px",
                padding: "14px 30px",
                background: "linear-gradient(135deg, #00A1FF 0%, #0066CC 100%)",
                border: "none",
                borderRadius: "12px",
                color: "#fff",
                fontSize: "15px",
                fontWeight: 700,
                cursor: "pointer",
              }}
            >
              Ir para login
            </motion.button>
          </motion.div>
        )}
      </motion.div>
    </div>
  );
};

export default ResetPassword;
