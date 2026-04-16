/**
 * ENGENHARIA CAD — Profile Page
 * Página de perfil do usuário com configurações de conta e segurança
 */
import React, { useState, useEffect } from "react";
import { motion } from "framer-motion";
import {
  FaUser,
  FaEnvelope,
  FaBuilding,
  FaPhone,
  FaShieldAlt,
  FaLock,
  FaKey,
  FaTrash,
  FaCheck,
  FaQrcode,
  FaCopy,
  FaCheckCircle,
  FaExclamationTriangle,
} from "react-icons/fa";
import { api } from "../services/api";
import { useToast } from "../context/ToastContext";
import SidebarLayout from "../components/SidebarLayout";

interface UserProfile {
  email: string;
  empresa?: string;
  nome?: string;
  telefone?: string;
  tier: string;
  email_verified?: boolean;
  two_factor_enabled?: boolean;
}

const Profile: React.FC = () => {
  const { showToast } = useToast();
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [activeTab, setActiveTab] = useState<"profile" | "security">("profile");

  // Profile form
  const [empresa, setEmpresa] = useState("");
  const [nome, setNome] = useState("");
  const [telefone, setTelefone] = useState("");

  // Password change form
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmNewPassword, setConfirmNewPassword] = useState("");

  // 2FA state
  const [show2FASetup, setShow2FASetup] = useState(false);
  const [qrCodeUrl, setQrCodeUrl] = useState("");
  const [secret, setSecret] = useState("");
  const [backupCodes, setBackupCodes] = useState<string[]>([]);
  const [verifyCode, setVerifyCode] = useState("");

  useEffect(() => {
    loadProfile();
  }, []);

  const loadProfile = async () => {
    try {
      const res = await api.get("/auth/me");
      setProfile(res.data);
      setEmpresa(res.data.empresa || "");
      setNome(res.data.nome || "");
      setTelefone(res.data.telefone || "");
    } catch (err) {
      showToast("Erro ao carregar perfil", "error");
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      await api.put("/auth/me", { empresa, nome, telefone });
      showToast("Perfil atualizado com sucesso!", "success");
      loadProfile();
    } catch (err: any) {
      showToast(err.response?.data?.detail || "Erro ao atualizar perfil", "error");
    } finally {
      setSaving(false);
    }
  };

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (newPassword !== confirmNewPassword) {
      showToast("As senhas não coincidem", "error");
      return;
    }
    setSaving(true);
    try {
      await api.put("/auth/me/password", {
        current_password: currentPassword,
        new_password: newPassword,
      });
      showToast("Senha alterada com sucesso!", "success");
      setCurrentPassword("");
      setNewPassword("");
      setConfirmNewPassword("");
    } catch (err: any) {
      showToast(err.response?.data?.detail || "Erro ao alterar senha", "error");
    } finally {
      setSaving(false);
    }
  };

  const handleEnable2FA = async () => {
    try {
      const res = await api.post("/auth/enable-2fa");
      setQrCodeUrl(res.data.qr_code_url);
      setSecret(res.data.secret);
      setBackupCodes(res.data.backup_codes);
      setShow2FASetup(true);
    } catch (err: any) {
      showToast(err.response?.data?.detail || "Erro ao ativar 2FA", "error");
    }
  };

  const handleConfirm2FA = async () => {
    if (verifyCode.length !== 6) {
      showToast("Digite o código de 6 dígitos", "error");
      return;
    }
    try {
      await api.post("/auth/confirm-2fa", { code: verifyCode });
      showToast("2FA ativado com sucesso!", "success");
      setShow2FASetup(false);
      loadProfile();
    } catch (err: any) {
      showToast(err.response?.data?.detail || "Código inválido", "error");
    }
  };

  const handleDisable2FA = async () => {
    const code = prompt("Digite o código do seu autenticador para desativar 2FA:");
    if (!code) return;
    try {
      await api.delete("/auth/disable-2fa", { data: { code } });
      showToast("2FA desativado", "success");
      loadProfile();
    } catch (err: any) {
      showToast(err.response?.data?.detail || "Código inválido", "error");
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    showToast("Copiado!", "success");
  };

  if (loading) {
    return (
      <SidebarLayout>
        <div style={{ display: "flex", justifyContent: "center", alignItems: "center", height: "60vh" }}>
          <div className="animate-spin" style={{ width: "40px", height: "40px", border: "3px solid #1e3a5f", borderTopColor: "#00A1FF", borderRadius: "50%" }} />
        </div>
      </SidebarLayout>
    );
  }

  return (
    <SidebarLayout>
      <div style={{ maxWidth: "900px", margin: "0 auto", padding: "24px" }}>
        {/* Header */}
        <div style={{ marginBottom: "32px" }}>
          <h1 style={{ color: "#fff", fontSize: "28px", fontWeight: 700, margin: 0 }}>
            Minha Conta
          </h1>
          <p style={{ color: "#64748b", marginTop: "8px" }}>
            Gerencie suas informações e configurações de segurança
          </p>
        </div>

        {/* Tabs */}
        <div
          style={{
            display: "flex",
            gap: "4px",
            marginBottom: "24px",
            background: "rgba(15, 23, 42, 0.6)",
            padding: "4px",
            borderRadius: "12px",
            width: "fit-content",
          }}
        >
          {[
            { id: "profile", label: "Perfil", icon: <FaUser /> },
            { id: "security", label: "Segurança", icon: <FaShieldAlt /> },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "8px",
                padding: "12px 24px",
                background: activeTab === tab.id ? "rgba(0, 161, 255, 0.15)" : "transparent",
                border: "none",
                borderRadius: "8px",
                color: activeTab === tab.id ? "#00A1FF" : "#64748b",
                fontSize: "14px",
                fontWeight: 600,
                cursor: "pointer",
                transition: "all 0.2s",
              }}
            >
              {tab.icon} {tab.label}
            </button>
          ))}
        </div>

        {/* Profile Tab */}
        {activeTab === "profile" && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            style={{
              background: "rgba(15, 23, 42, 0.8)",
              border: "1px solid rgba(0, 161, 255, 0.1)",
              borderRadius: "16px",
              padding: "32px",
            }}
          >
            {/* Account Info */}
            <div style={{ marginBottom: "32px", paddingBottom: "24px", borderBottom: "1px solid rgba(100, 116, 139, 0.2)" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
                <div
                  style={{
                    width: "72px",
                    height: "72px",
                    borderRadius: "50%",
                    background: "linear-gradient(135deg, #00A1FF 0%, #0066CC 100%)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    fontSize: "28px",
                    color: "#fff",
                    fontWeight: 700,
                  }}
                >
                  {(profile?.nome || profile?.email || "U").charAt(0).toUpperCase()}
                </div>
                <div>
                  <h3 style={{ color: "#fff", fontSize: "18px", fontWeight: 600, margin: 0 }}>
                    {profile?.nome || profile?.email?.split("@")[0]}
                  </h3>
                  <p style={{ color: "#64748b", fontSize: "14px", margin: "4px 0 0" }}>
                    {profile?.email}
                  </p>
                  <div style={{ display: "flex", gap: "8px", marginTop: "8px" }}>
                    <span
                      style={{
                        padding: "4px 10px",
                        background: "rgba(0, 161, 255, 0.15)",
                        borderRadius: "20px",
                        color: "#00A1FF",
                        fontSize: "12px",
                        fontWeight: 600,
                        textTransform: "uppercase",
                      }}
                    >
                      {profile?.tier}
                    </span>
                    {profile?.email_verified ? (
                      <span style={{ padding: "4px 10px", background: "rgba(16, 185, 129, 0.15)", borderRadius: "20px", color: "#10B981", fontSize: "12px", fontWeight: 600 }}>
                        <FaCheckCircle style={{ marginRight: "4px" }} /> Email verificado
                      </span>
                    ) : (
                      <span style={{ padding: "4px 10px", background: "rgba(245, 158, 11, 0.15)", borderRadius: "20px", color: "#f59e0b", fontSize: "12px", fontWeight: 600 }}>
                        <FaExclamationTriangle style={{ marginRight: "4px" }} /> Email não verificado
                      </span>
                    )}
                  </div>
                </div>
              </div>
            </div>

            {/* Profile Form */}
            <form onSubmit={handleUpdateProfile}>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "20px" }}>
                <div>
                  <label style={{ display: "flex", alignItems: "center", gap: "8px", color: "#94a3b8", fontSize: "14px", marginBottom: "8px" }}>
                    <FaUser /> Nome
                  </label>
                  <input
                    type="text"
                    value={nome}
                    onChange={(e) => setNome(e.target.value)}
                    placeholder="Seu nome completo"
                    style={{
                      width: "100%",
                      padding: "12px 16px",
                      background: "rgba(30, 41, 59, 0.8)",
                      border: "1px solid rgba(100, 116, 139, 0.3)",
                      borderRadius: "10px",
                      color: "#fff",
                      fontSize: "14px",
                      outline: "none",
                    }}
                  />
                </div>

                <div>
                  <label style={{ display: "flex", alignItems: "center", gap: "8px", color: "#94a3b8", fontSize: "14px", marginBottom: "8px" }}>
                    <FaBuilding /> Empresa
                  </label>
                  <input
                    type="text"
                    value={empresa}
                    onChange={(e) => setEmpresa(e.target.value)}
                    placeholder="Nome da empresa"
                    style={{
                      width: "100%",
                      padding: "12px 16px",
                      background: "rgba(30, 41, 59, 0.8)",
                      border: "1px solid rgba(100, 116, 139, 0.3)",
                      borderRadius: "10px",
                      color: "#fff",
                      fontSize: "14px",
                      outline: "none",
                    }}
                  />
                </div>

                <div>
                  <label style={{ display: "flex", alignItems: "center", gap: "8px", color: "#94a3b8", fontSize: "14px", marginBottom: "8px" }}>
                    <FaEnvelope /> Email
                  </label>
                  <input
                    type="email"
                    value={profile?.email || ""}
                    disabled
                    style={{
                      width: "100%",
                      padding: "12px 16px",
                      background: "rgba(30, 41, 59, 0.4)",
                      border: "1px solid rgba(100, 116, 139, 0.2)",
                      borderRadius: "10px",
                      color: "#64748b",
                      fontSize: "14px",
                      cursor: "not-allowed",
                    }}
                  />
                </div>

                <div>
                  <label style={{ display: "flex", alignItems: "center", gap: "8px", color: "#94a3b8", fontSize: "14px", marginBottom: "8px" }}>
                    <FaPhone /> Telefone
                  </label>
                  <input
                    type="tel"
                    value={telefone}
                    onChange={(e) => setTelefone(e.target.value)}
                    placeholder="+55 (11) 99999-9999"
                    style={{
                      width: "100%",
                      padding: "12px 16px",
                      background: "rgba(30, 41, 59, 0.8)",
                      border: "1px solid rgba(100, 116, 139, 0.3)",
                      borderRadius: "10px",
                      color: "#fff",
                      fontSize: "14px",
                      outline: "none",
                    }}
                  />
                </div>
              </div>

              <motion.button
                type="submit"
                disabled={saving}
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                style={{
                  marginTop: "24px",
                  padding: "12px 24px",
                  background: saving ? "rgba(0, 161, 255, 0.3)" : "linear-gradient(135deg, #00A1FF 0%, #0066CC 100%)",
                  border: "none",
                  borderRadius: "10px",
                  color: "#fff",
                  fontSize: "14px",
                  fontWeight: 600,
                  cursor: saving ? "not-allowed" : "pointer",
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                }}
              >
                <FaCheck /> {saving ? "Salvando..." : "Salvar Alterações"}
              </motion.button>
            </form>
          </motion.div>
        )}

        {/* Security Tab */}
        {activeTab === "security" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
            {/* Change Password */}
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              style={{
                background: "rgba(15, 23, 42, 0.8)",
                border: "1px solid rgba(0, 161, 255, 0.1)",
                borderRadius: "16px",
                padding: "24px",
              }}
            >
              <h3 style={{ color: "#fff", fontSize: "18px", fontWeight: 600, margin: "0 0 20px", display: "flex", alignItems: "center", gap: "10px" }}>
                <FaLock /> Alterar Senha
              </h3>
              <form onSubmit={handleChangePassword}>
                <div style={{ display: "flex", flexDirection: "column", gap: "16px", maxWidth: "400px" }}>
                  <input
                    type="password"
                    value={currentPassword}
                    onChange={(e) => setCurrentPassword(e.target.value)}
                    placeholder="Senha atual"
                    required
                    style={{
                      padding: "12px 16px",
                      background: "rgba(30, 41, 59, 0.8)",
                      border: "1px solid rgba(100, 116, 139, 0.3)",
                      borderRadius: "10px",
                      color: "#fff",
                      fontSize: "14px",
                      outline: "none",
                    }}
                  />
                  <input
                    type="password"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    placeholder="Nova senha (mínimo 8 caracteres)"
                    required
                    minLength={8}
                    style={{
                      padding: "12px 16px",
                      background: "rgba(30, 41, 59, 0.8)",
                      border: "1px solid rgba(100, 116, 139, 0.3)",
                      borderRadius: "10px",
                      color: "#fff",
                      fontSize: "14px",
                      outline: "none",
                    }}
                  />
                  <input
                    type="password"
                    value={confirmNewPassword}
                    onChange={(e) => setConfirmNewPassword(e.target.value)}
                    placeholder="Confirmar nova senha"
                    required
                    style={{
                      padding: "12px 16px",
                      background: "rgba(30, 41, 59, 0.8)",
                      border: `1px solid ${confirmNewPassword && confirmNewPassword !== newPassword ? "rgba(239, 68, 68, 0.5)" : "rgba(100, 116, 139, 0.3)"}`,
                      borderRadius: "10px",
                      color: "#fff",
                      fontSize: "14px",
                      outline: "none",
                    }}
                  />
                  <motion.button
                    type="submit"
                    disabled={saving}
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    style={{
                      padding: "12px 24px",
                      background: "linear-gradient(135deg, #00A1FF 0%, #0066CC 100%)",
                      border: "none",
                      borderRadius: "10px",
                      color: "#fff",
                      fontSize: "14px",
                      fontWeight: 600,
                      cursor: "pointer",
                      width: "fit-content",
                    }}
                  >
                    Alterar Senha
                  </motion.button>
                </div>
              </form>
            </motion.div>

            {/* 2FA */}
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
              style={{
                background: "rgba(15, 23, 42, 0.8)",
                border: "1px solid rgba(0, 161, 255, 0.1)",
                borderRadius: "16px",
                padding: "24px",
              }}
            >
              <h3 style={{ color: "#fff", fontSize: "18px", fontWeight: 600, margin: "0 0 16px", display: "flex", alignItems: "center", gap: "10px" }}>
                <FaKey /> Autenticação em Duas Etapas (2FA)
              </h3>
              <p style={{ color: "#64748b", fontSize: "14px", marginBottom: "20px" }}>
                Adicione uma camada extra de segurança à sua conta usando um aplicativo autenticador como Google Authenticator ou Authy.
              </p>

              {!show2FASetup ? (
                profile?.two_factor_enabled ? (
                  <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
                    <span style={{ color: "#10B981", display: "flex", alignItems: "center", gap: "8px" }}>
                      <FaCheckCircle /> 2FA está ativado
                    </span>
                    <button
                      onClick={handleDisable2FA}
                      style={{
                        padding: "8px 16px",
                        background: "rgba(239, 68, 68, 0.1)",
                        border: "1px solid rgba(239, 68, 68, 0.3)",
                        borderRadius: "8px",
                        color: "#ef4444",
                        fontSize: "13px",
                        cursor: "pointer",
                      }}
                    >
                      Desativar 2FA
                    </button>
                  </div>
                ) : (
                  <motion.button
                    onClick={handleEnable2FA}
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    style={{
                      padding: "12px 24px",
                      background: "linear-gradient(135deg, #10B981 0%, #059669 100%)",
                      border: "none",
                      borderRadius: "10px",
                      color: "#fff",
                      fontSize: "14px",
                      fontWeight: 600,
                      cursor: "pointer",
                      display: "flex",
                      alignItems: "center",
                      gap: "8px",
                    }}
                  >
                    <FaShieldAlt /> Ativar 2FA
                  </motion.button>
                )
              ) : (
                /* 2FA Setup Flow */
                <div style={{ maxWidth: "500px" }}>
                  <div style={{ marginBottom: "24px" }}>
                    <p style={{ color: "#94a3b8", fontSize: "14px", marginBottom: "16px" }}>
                      1. Escaneie o QR code abaixo com seu aplicativo autenticador:
                    </p>
                    <div
                      style={{
                        background: "#fff",
                        padding: "16px",
                        borderRadius: "12px",
                        width: "fit-content",
                        marginBottom: "16px",
                      }}
                    >
                      <img
                        src={`https://api.qrserver.com/v1/create-qr-code/?size=180x180&data=${encodeURIComponent(qrCodeUrl)}`}
                        alt="QR Code"
                        style={{ display: "block" }}
                      />
                    </div>
                    <p style={{ color: "#64748b", fontSize: "13px" }}>
                      Ou digite manualmente o código:
                    </p>
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "8px",
                        background: "rgba(30, 41, 59, 0.8)",
                        padding: "12px",
                        borderRadius: "8px",
                        marginTop: "8px",
                      }}
                    >
                      <code style={{ color: "#00A1FF", fontSize: "14px", letterSpacing: "2px" }}>
                        {secret}
                      </code>
                      <button
                        onClick={() => copyToClipboard(secret)}
                        style={{
                          background: "none",
                          border: "none",
                          color: "#64748b",
                          cursor: "pointer",
                          padding: "4px",
                        }}
                      >
                        <FaCopy />
                      </button>
                    </div>
                  </div>

                  <div style={{ marginBottom: "24px" }}>
                    <p style={{ color: "#94a3b8", fontSize: "14px", marginBottom: "12px" }}>
                      2. Guarde estes códigos de backup em um local seguro:
                    </p>
                    <div
                      style={{
                        display: "grid",
                        gridTemplateColumns: "repeat(4, 1fr)",
                        gap: "8px",
                        background: "rgba(30, 41, 59, 0.8)",
                        padding: "16px",
                        borderRadius: "8px",
                      }}
                    >
                      {backupCodes.map((code, i) => (
                        <code key={i} style={{ color: "#f59e0b", fontSize: "13px", fontFamily: "monospace" }}>
                          {code}
                        </code>
                      ))}
                    </div>
                  </div>

                  <div>
                    <p style={{ color: "#94a3b8", fontSize: "14px", marginBottom: "12px" }}>
                      3. Digite o código de 6 dígitos do seu autenticador para confirmar:
                    </p>
                    <div style={{ display: "flex", gap: "12px" }}>
                      <input
                        type="text"
                        value={verifyCode}
                        onChange={(e) => setVerifyCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
                        placeholder="000000"
                        maxLength={6}
                        style={{
                          width: "160px",
                          padding: "12px 16px",
                          background: "rgba(30, 41, 59, 0.8)",
                          border: "1px solid rgba(100, 116, 139, 0.3)",
                          borderRadius: "10px",
                          color: "#fff",
                          fontSize: "18px",
                          textAlign: "center",
                          letterSpacing: "8px",
                          outline: "none",
                        }}
                      />
                      <motion.button
                        onClick={handleConfirm2FA}
                        disabled={verifyCode.length !== 6}
                        whileHover={{ scale: 1.02 }}
                        whileTap={{ scale: 0.98 }}
                        style={{
                          padding: "12px 24px",
                          background: verifyCode.length === 6 ? "linear-gradient(135deg, #10B981 0%, #059669 100%)" : "rgba(100, 116, 139, 0.3)",
                          border: "none",
                          borderRadius: "10px",
                          color: "#fff",
                          fontSize: "14px",
                          fontWeight: 600,
                          cursor: verifyCode.length === 6 ? "pointer" : "not-allowed",
                        }}
                      >
                        Confirmar
                      </motion.button>
                      <button
                        onClick={() => setShow2FASetup(false)}
                        style={{
                          padding: "12px 24px",
                          background: "transparent",
                          border: "1px solid rgba(100, 116, 139, 0.3)",
                          borderRadius: "10px",
                          color: "#64748b",
                          fontSize: "14px",
                          cursor: "pointer",
                        }}
                      >
                        Cancelar
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </motion.div>

            {/* Danger Zone */}
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
              style={{
                background: "rgba(239, 68, 68, 0.05)",
                border: "1px solid rgba(239, 68, 68, 0.2)",
                borderRadius: "16px",
                padding: "24px",
              }}
            >
              <h3 style={{ color: "#ef4444", fontSize: "18px", fontWeight: 600, margin: "0 0 16px", display: "flex", alignItems: "center", gap: "10px" }}>
                <FaTrash /> Zona de Perigo
              </h3>
              <p style={{ color: "#64748b", fontSize: "14px", marginBottom: "20px" }}>
                A exclusão da conta é permanente e irreversível. Todos os seus dados serão removidos.
              </p>
              <button
                onClick={() => {
                  if (window.confirm("Tem certeza que deseja excluir sua conta? Esta ação é IRREVERSÍVEL.")) {
                    // TODO: Implement account deletion
                    showToast("Função de exclusão será implementada em breve", "info");
                  }
                }}
                style={{
                  padding: "12px 24px",
                  background: "transparent",
                  border: "1px solid rgba(239, 68, 68, 0.5)",
                  borderRadius: "10px",
                  color: "#ef4444",
                  fontSize: "14px",
                  fontWeight: 600,
                  cursor: "pointer",
                }}
              >
                Excluir Minha Conta
              </button>
            </motion.div>
          </div>
        )}
      </div>
    </SidebarLayout>
  );
};

export default Profile;
