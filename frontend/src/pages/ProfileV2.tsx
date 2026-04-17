/**
 * ProfileV2 Page — AutomAção CAD Enterprise v2.0
 *
 * Luxurious profile settings page with tabbed navigation.
 * Includes account settings, security (2FA), notifications, and plan info.
 */

import React, { useState, useEffect } from "react";
import { motion } from "framer-motion";
import {
  User,
  Mail,
  Building2,
  Phone,
  Shield,
  Lock,
  Key,
  Trash2,
  Check,
  QrCode,
  Copy,
  AlertTriangle,
  Bell,
  CreditCard,
  LogOut,
  Camera,
  Save,
  Eye,
  EyeOff,
  Smartphone,
  Globe,
  Moon,
  Sun,
} from "lucide-react";
import { colors, radius, shadows, spacing, blur } from "../design/tokens";
import {
  fontFamily,
  fontSize,
  fontWeight,
  textStyles,
} from "../design/typography";
import {
  Button,
  Card,
  CardHeader,
  CardBody,
  Input,
  Badge,
  Tabs,
  TabsList,
  TabsTrigger,
  TabsContent,
  Avatar,
  Select,
  BottomTabBar,
} from "../components/ui";
import { api } from "../services/api";

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// TYPES
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

interface UserProfile {
  email: string;
  empresa?: string;
  nome?: string;
  telefone?: string;
  tier: string;
  email_verified?: boolean;
  two_factor_enabled?: boolean;
  avatar_url?: string;
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// ANIMATIONS
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

const fadeIn = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { duration: 0.3 } },
};

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// SECTION COMPONENTS
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

interface SectionProps {
  title: string;
  description?: string;
  children: React.ReactNode;
}

const Section: React.FC<SectionProps> = ({ title, description, children }) => {
  const styles = {
    section: {
      marginBottom: spacing[8],
    },
    header: {
      marginBottom: spacing[4],
    },
    title: {
      fontFamily: fontFamily.display,
      fontSize: fontSize.lg,
      fontWeight: fontWeight.semibold,
      color: colors.text.primary,
      marginBottom: spacing[1],
    },
    description: {
      fontFamily: fontFamily.sans,
      fontSize: fontSize.sm,
      color: colors.text.secondary,
    },
  };

  return (
    <div style={styles.section}>
      <div style={styles.header}>
        <h3 style={styles.title}>{title}</h3>
        {description && <p style={styles.description}>{description}</p>}
      </div>
      {children}
    </div>
  );
};

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// FORM ROW
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

interface FormRowProps {
  children: React.ReactNode;
  columns?: number;
}

const FormRow: React.FC<FormRowProps> = ({ children, columns = 2 }) => (
  <div
    style={{
      display: "grid",
      gridTemplateColumns: `repeat(${columns}, 1fr)`,
      gap: spacing[4],
      marginBottom: spacing[4],
    }}
  >
    {children}
  </div>
);

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// ACCOUNT TAB
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

interface AccountTabProps {
  profile: UserProfile | null;
  onSave: (data: Partial<UserProfile>) => Promise<void>;
  saving: boolean;
}

const AccountTab: React.FC<AccountTabProps> = ({ profile, onSave, saving }) => {
  const [nome, setNome] = useState(profile?.nome || "");
  const [empresa, setEmpresa] = useState(profile?.empresa || "");
  const [telefone, setTelefone] = useState(profile?.telefone || "");

  useEffect(() => {
    if (profile) {
      setNome(profile.nome || "");
      setEmpresa(profile.empresa || "");
      setTelefone(profile.telefone || "");
    }
  }, [profile]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSave({ nome, empresa, telefone });
  };

  const styles = {
    avatarSection: {
      display: "flex",
      alignItems: "center",
      gap: spacing[5],
      marginBottom: spacing[8],
      padding: spacing[5],
      backgroundColor: colors.dark.surface,
      borderRadius: radius.xl,
      border: `1px solid ${colors.border.subtle}`,
    },
    avatarInfo: {
      flex: 1,
    },
    avatarName: {
      fontFamily: fontFamily.display,
      fontSize: fontSize.xl,
      fontWeight: fontWeight.semibold,
      color: colors.text.primary,
      marginBottom: spacing[1],
    },
    avatarEmail: {
      fontFamily: fontFamily.sans,
      fontSize: fontSize.sm,
      color: colors.text.secondary,
      display: "flex",
      alignItems: "center",
      gap: spacing[2],
    },
    form: {
      backgroundColor: colors.dark.surface,
      borderRadius: radius.xl,
      border: `1px solid ${colors.border.subtle}`,
      padding: spacing[6],
    },
  };

  return (
    <motion.div initial="hidden" animate="visible" variants={fadeIn}>
      {/* Avatar Section */}
      <div style={styles.avatarSection}>
        <Avatar
          name={nome || profile?.email || "User"}
          size="2xl"
          status="online"
        />
        <div style={styles.avatarInfo}>
          <h3 style={styles.avatarName}>{nome || "Seu Nome"}</h3>
          <p style={styles.avatarEmail}>
            <Mail size={14} />
            {profile?.email}
            {profile?.email_verified && (
              <Badge variant="success" size="sm">
                Verificado
              </Badge>
            )}
          </p>
        </div>
        <Button variant="outline" size="sm" leftIcon={<Camera size={16} />}>
          Alterar Foto
        </Button>
      </div>

      {/* Profile Form */}
      <form onSubmit={handleSubmit} style={styles.form}>
        <Section
          title="Informações Pessoais"
          description="Atualize seus dados de perfil"
        >
          <FormRow>
            <Input
              label="Nome Completo"
              placeholder="Seu nome"
              value={nome}
              onChange={(e) => setNome(e.target.value)}
              leftIcon={<User size={18} />}
            />
            <Input
              label="Email"
              type="email"
              value={profile?.email || ""}
              disabled
              leftIcon={<Mail size={18} />}
            />
          </FormRow>
          <FormRow>
            <Input
              label="Empresa"
              placeholder="Nome da empresa"
              value={empresa}
              onChange={(e) => setEmpresa(e.target.value)}
              leftIcon={<Building2 size={18} />}
            />
            <Input
              label="Telefone"
              placeholder="(11) 99999-9999"
              value={telefone}
              onChange={(e) => setTelefone(e.target.value)}
              leftIcon={<Phone size={18} />}
            />
          </FormRow>
        </Section>

        <div
          style={{
            display: "flex",
            justifyContent: "flex-end",
            gap: spacing[3],
          }}
        >
          <Button type="button" variant="ghost">
            Cancelar
          </Button>
          <Button
            type="submit"
            variant="primary"
            loading={saving}
            leftIcon={<Save size={18} />}
          >
            Salvar Alterações
          </Button>
        </div>
      </form>
    </motion.div>
  );
};

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// SECURITY TAB
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

interface SecurityTabProps {
  profile: UserProfile | null;
  onChangePassword: (current: string, newPass: string) => Promise<void>;
  saving: boolean;
}

const SecurityTab: React.FC<SecurityTabProps> = ({
  profile,
  onChangePassword,
  saving,
}) => {
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showCurrentPassword, setShowCurrentPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (newPassword === confirmPassword) {
      onChangePassword(currentPassword, newPassword);
    }
  };

  const styles = {
    card: {
      backgroundColor: colors.dark.surface,
      borderRadius: radius.xl,
      border: `1px solid ${colors.border.subtle}`,
      padding: spacing[6],
      marginBottom: spacing[6],
    },
    twoFactorCard: {
      backgroundColor: colors.dark.surface,
      borderRadius: radius.xl,
      border: `1px solid ${profile?.two_factor_enabled ? colors.success.DEFAULT : colors.border.subtle}`,
      padding: spacing[6],
      display: "flex",
      alignItems: "center",
      justifyContent: "space-between",
      gap: spacing[4],
    },
    twoFactorInfo: {
      display: "flex",
      alignItems: "center",
      gap: spacing[4],
    },
    twoFactorIcon: {
      width: "48px",
      height: "48px",
      borderRadius: radius.lg,
      backgroundColor: profile?.two_factor_enabled
        ? colors.success.soft
        : colors.dark.elevated,
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      color: profile?.two_factor_enabled
        ? colors.success.DEFAULT
        : colors.text.tertiary,
    },
    twoFactorText: {
      flex: 1,
    },
    twoFactorTitle: {
      fontFamily: fontFamily.sans,
      fontSize: fontSize.base,
      fontWeight: fontWeight.medium,
      color: colors.text.primary,
      marginBottom: spacing[1],
    },
    twoFactorDesc: {
      fontFamily: fontFamily.sans,
      fontSize: fontSize.sm,
      color: colors.text.secondary,
    },
    dangerZone: {
      backgroundColor: "rgba(239, 68, 68, 0.05)",
      borderRadius: radius.xl,
      border: `1px solid ${colors.danger.DEFAULT}20`,
      padding: spacing[6],
    },
    dangerHeader: {
      display: "flex",
      alignItems: "center",
      gap: spacing[3],
      marginBottom: spacing[4],
    },
    dangerTitle: {
      fontFamily: fontFamily.display,
      fontSize: fontSize.lg,
      fontWeight: fontWeight.semibold,
      color: colors.danger.DEFAULT,
    },
    dangerText: {
      fontFamily: fontFamily.sans,
      fontSize: fontSize.sm,
      color: colors.text.secondary,
      marginBottom: spacing[4],
    },
  };

  return (
    <motion.div initial="hidden" animate="visible" variants={fadeIn}>
      {/* Change Password */}
      <form onSubmit={handleSubmit} style={styles.card}>
        <Section
          title="Alterar Senha"
          description="Recomendamos uma senha forte com pelo menos 12 caracteres"
        >
          <FormRow columns={1}>
            <Input
              label="Senha Atual"
              type={showCurrentPassword ? "text" : "password"}
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              leftIcon={<Lock size={18} />}
              rightIcon={
                <button
                  type="button"
                  onClick={() => setShowCurrentPassword(!showCurrentPassword)}
                  style={{
                    background: "none",
                    border: "none",
                    cursor: "pointer",
                    color: colors.text.tertiary,
                  }}
                >
                  {showCurrentPassword ? (
                    <EyeOff size={18} />
                  ) : (
                    <Eye size={18} />
                  )}
                </button>
              }
            />
          </FormRow>
          <FormRow>
            <Input
              label="Nova Senha"
              type={showNewPassword ? "text" : "password"}
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              leftIcon={<Key size={18} />}
            />
            <Input
              label="Confirmar Nova Senha"
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              leftIcon={<Key size={18} />}
              error={
                confirmPassword && newPassword !== confirmPassword
                  ? "As senhas não coincidem"
                  : undefined
              }
            />
          </FormRow>
          <div style={{ display: "flex", justifyContent: "flex-end" }}>
            <Button
              type="submit"
              variant="primary"
              loading={saving}
              disabled={
                !currentPassword ||
                !newPassword ||
                newPassword !== confirmPassword
              }
            >
              Atualizar Senha
            </Button>
          </div>
        </Section>
      </form>

      {/* Two-Factor Authentication */}
      <div style={styles.twoFactorCard}>
        <div style={styles.twoFactorInfo}>
          <div style={styles.twoFactorIcon}>
            <Smartphone size={24} />
          </div>
          <div style={styles.twoFactorText}>
            <h4 style={styles.twoFactorTitle}>
              Autenticação de Dois Fatores (2FA)
              {profile?.two_factor_enabled && (
                <Badge
                  variant="success"
                  size="sm"
                  style={{ marginLeft: spacing[2] }}
                >
                  Ativo
                </Badge>
              )}
            </h4>
            <p style={styles.twoFactorDesc}>
              {profile?.two_factor_enabled
                ? "Sua conta está protegida com autenticação de dois fatores."
                : "Adicione uma camada extra de segurança à sua conta."}
            </p>
          </div>
        </div>
        <Button
          variant={profile?.two_factor_enabled ? "outline" : "primary"}
          leftIcon={
            profile?.two_factor_enabled ? (
              <Shield size={18} />
            ) : (
              <QrCode size={18} />
            )
          }
        >
          {profile?.two_factor_enabled ? "Gerenciar 2FA" : "Configurar 2FA"}
        </Button>
      </div>

      {/* Sessions */}
      <div style={{ ...styles.card, marginTop: spacing[6] }}>
        <Section
          title="Sessões Ativas"
          description="Gerencie os dispositivos conectados à sua conta"
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              padding: spacing[4],
              backgroundColor: colors.dark.elevated,
              borderRadius: radius.lg,
            }}
          >
            <div
              style={{ display: "flex", alignItems: "center", gap: spacing[3] }}
            >
              <Globe size={20} style={{ color: colors.primary.DEFAULT }} />
              <div>
                <p
                  style={{
                    fontFamily: fontFamily.sans,
                    fontSize: fontSize.sm,
                    fontWeight: fontWeight.medium,
                    color: colors.text.primary,
                  }}
                >
                  Sessão Atual • Windows
                </p>
                <p
                  style={{
                    fontFamily: fontFamily.sans,
                    fontSize: fontSize.xs,
                    color: colors.text.tertiary,
                  }}
                >
                  Último acesso: Agora
                </p>
              </div>
            </div>
            <Badge variant="success" size="sm">
              Ativa
            </Badge>
          </div>
        </Section>
      </div>

      {/* Danger Zone */}
      <div style={styles.dangerZone}>
        <div style={styles.dangerHeader}>
          <AlertTriangle size={24} style={{ color: colors.danger.DEFAULT }} />
          <h3 style={styles.dangerTitle}>Zona de Perigo</h3>
        </div>
        <p style={styles.dangerText}>
          Ações irreversíveis que afetam permanentemente sua conta. Tenha
          certeza antes de prosseguir.
        </p>
        <div style={{ display: "flex", gap: spacing[3] }}>
          <Button variant="outline" size="sm" leftIcon={<LogOut size={16} />}>
            Sair de Todos os Dispositivos
          </Button>
          <Button variant="danger" size="sm" leftIcon={<Trash2 size={16} />}>
            Excluir Conta
          </Button>
        </div>
      </div>
    </motion.div>
  );
};

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// PLAN TAB
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

interface PlanTabProps {
  profile: UserProfile | null;
}

const PlanTab: React.FC<PlanTabProps> = ({ profile }) => {
  const tierConfig: Record<
    string,
    { name: string; color: string; badge: string }
  > = {
    starter: { name: "Starter", color: colors.success.DEFAULT, badge: "Basic" },
    professional: {
      name: "Professional",
      color: colors.primary.DEFAULT,
      badge: "Pro",
    },
    enterprise: {
      name: "Enterprise",
      color: colors.gold.DEFAULT,
      badge: "Premium",
    },
  };

  const currentTier =
    tierConfig[profile?.tier || "starter"] || tierConfig.starter;

  const styles = {
    planCard: {
      backgroundColor: colors.dark.surface,
      borderRadius: radius.xl,
      border: `1px solid ${currentTier.color}`,
      padding: spacing[6],
      marginBottom: spacing[6],
      position: "relative" as const,
      overflow: "hidden",
    },
    planGlow: {
      position: "absolute" as const,
      top: 0,
      left: 0,
      right: 0,
      height: "3px",
      background: `linear-gradient(90deg, transparent, ${currentTier.color}, transparent)`,
    },
    planHeader: {
      display: "flex",
      alignItems: "center",
      justifyContent: "space-between",
      marginBottom: spacing[4],
    },
    planInfo: {
      display: "flex",
      alignItems: "center",
      gap: spacing[3],
    },
    planIcon: {
      width: "48px",
      height: "48px",
      borderRadius: radius.lg,
      backgroundColor: `${currentTier.color}15`,
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      color: currentTier.color,
    },
    planName: {
      fontFamily: fontFamily.display,
      fontSize: fontSize.xl,
      fontWeight: fontWeight.bold,
      color: colors.text.primary,
    },
    planBadge: {
      fontFamily: fontFamily.sans,
      fontSize: fontSize.xs,
      color: colors.text.secondary,
    },
    usageSection: {
      display: "grid",
      gridTemplateColumns: "repeat(3, 1fr)",
      gap: spacing[4],
      marginTop: spacing[6],
    },
    usageCard: {
      padding: spacing[4],
      backgroundColor: colors.dark.elevated,
      borderRadius: radius.lg,
      textAlign: "center" as const,
    },
    usageValue: {
      fontFamily: fontFamily.display,
      fontSize: fontSize["2xl"],
      fontWeight: fontWeight.bold,
      color: colors.text.primary,
    },
    usageLabel: {
      fontFamily: fontFamily.sans,
      fontSize: fontSize.xs,
      color: colors.text.secondary,
      marginTop: spacing[1],
    },
  };

  return (
    <motion.div initial="hidden" animate="visible" variants={fadeIn}>
      {/* Current Plan */}
      <div style={styles.planCard}>
        <div style={styles.planGlow} />
        <div style={styles.planHeader}>
          <div style={styles.planInfo}>
            <div style={styles.planIcon}>
              <CreditCard size={24} />
            </div>
            <div>
              <h3 style={styles.planName}>{currentTier.name}</h3>
              <p style={styles.planBadge}>Plano atual</p>
            </div>
          </div>
          <Badge
            variant={profile?.tier === "enterprise" ? "gold" : "primary"}
            size="md"
          >
            {currentTier.badge}
          </Badge>
        </div>

        <div style={styles.usageSection}>
          <div style={styles.usageCard}>
            <p style={styles.usageValue}>5/50</p>
            <p style={styles.usageLabel}>Projetos</p>
          </div>
          <div style={styles.usageCard}>
            <p style={styles.usageValue}>87</p>
            <p style={styles.usageLabel}>Consultas IA</p>
          </div>
          <div style={styles.usageCard}>
            <p style={styles.usageValue}>3</p>
            <p style={styles.usageLabel}>Licenças</p>
          </div>
        </div>

        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginTop: spacing[6],
            paddingTop: spacing[4],
            borderTop: `1px solid ${colors.border.subtle}`,
          }}
        >
          <div>
            <p
              style={{
                fontFamily: fontFamily.sans,
                fontSize: fontSize.sm,
                color: colors.text.secondary,
              }}
            >
              Próxima cobrança:{" "}
              <strong style={{ color: colors.text.primary }}>
                15 de Janeiro, 2025
              </strong>
            </p>
          </div>
          <div style={{ display: "flex", gap: spacing[3] }}>
            <Button variant="outline" size="sm">
              Ver Faturas
            </Button>
            <Button variant="primary" size="sm">
              Fazer Upgrade
            </Button>
          </div>
        </div>
      </div>

      {/* Payment Method */}
      <Section
        title="Método de Pagamento"
        description="Gerencie suas formas de pagamento"
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            padding: spacing[4],
            backgroundColor: colors.dark.surface,
            borderRadius: radius.lg,
            border: `1px solid ${colors.border.subtle}`,
          }}
        >
          <div
            style={{ display: "flex", alignItems: "center", gap: spacing[3] }}
          >
            <div
              style={{
                width: "48px",
                height: "32px",
                backgroundColor: "#1A1F2E",
                borderRadius: radius.md,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <CreditCard size={20} style={{ color: colors.primary.DEFAULT }} />
            </div>
            <div>
              <p
                style={{
                  fontFamily: fontFamily.sans,
                  fontSize: fontSize.sm,
                  fontWeight: fontWeight.medium,
                  color: colors.text.primary,
                }}
              >
                •••• •••• •••• 4242
              </p>
              <p
                style={{
                  fontFamily: fontFamily.sans,
                  fontSize: fontSize.xs,
                  color: colors.text.tertiary,
                }}
              >
                Expira 12/26
              </p>
            </div>
          </div>
          <Button variant="ghost" size="sm">
            Alterar
          </Button>
        </div>
      </Section>
    </motion.div>
  );
};

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// MAIN PAGE COMPONENT
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

const ProfileV2: React.FC = () => {
  const [activeTab, setActiveTab] = useState("account");
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    loadProfile();
  }, []);

  const loadProfile = async () => {
    try {
      const res = await api.get("/auth/me");
      setProfile(res.data);
    } catch (err) {
      console.error("Error loading profile:", err);
      // For demo, set mock data
      setProfile({
        email: "usuario@empresa.com.br",
        nome: "João Silva",
        empresa: "Engenharia CAD Ltda",
        telefone: "(11) 99999-9999",
        tier: "professional",
        email_verified: true,
        two_factor_enabled: false,
      });
    } finally {
      setLoading(false);
    }
  };

  const handleSaveProfile = async (data: Partial<UserProfile>) => {
    setSaving(true);
    try {
      await api.put("/auth/me", data);
      setProfile((prev) => (prev ? { ...prev, ...data } : prev));
    } catch (err) {
      console.error("Error saving profile:", err);
    } finally {
      setSaving(false);
    }
  };

  const handleChangePassword = async (current: string, newPass: string) => {
    setSaving(true);
    try {
      await api.put("/auth/me/password", {
        current_password: current,
        new_password: newPass,
      });
    } catch (err) {
      console.error("Error changing password:", err);
    } finally {
      setSaving(false);
    }
  };

  const styles = {
    page: {
      minHeight: "100vh",
      backgroundColor: colors.dark.base,
      paddingBottom: "100px",
    },

    container: {
      maxWidth: "900px",
      margin: "0 auto",
      padding: `${spacing[8]} ${spacing[4]}`,
    },

    header: {
      marginBottom: spacing[8],
    },

    title: {
      ...textStyles.heading.h2,
      color: colors.text.primary,
      marginBottom: spacing[2],
    },

    subtitle: {
      fontFamily: fontFamily.sans,
      fontSize: fontSize.base,
      color: colors.text.secondary,
    },

    tabsContainer: {
      marginBottom: spacing[6],
    },
  };

  return (
    <div style={styles.page}>
      <div style={styles.container}>
        {/* Header */}
        <header style={styles.header}>
          <h1 style={styles.title}>Configurações</h1>
          <p style={styles.subtitle}>
            Gerencie sua conta, segurança e preferências
          </p>
        </header>

        {/* Tabs */}
        <Tabs value={activeTab} onChange={setActiveTab} variant="pills">
          <div style={styles.tabsContainer}>
            <TabsList>
              <TabsTrigger value="account" icon={<User size={16} />}>
                Conta
              </TabsTrigger>
              <TabsTrigger value="security" icon={<Shield size={16} />}>
                Segurança
              </TabsTrigger>
              <TabsTrigger value="plan" icon={<CreditCard size={16} />}>
                Plano
              </TabsTrigger>
            </TabsList>
          </div>

          <TabsContent value="account">
            <AccountTab
              profile={profile}
              onSave={handleSaveProfile}
              saving={saving}
            />
          </TabsContent>

          <TabsContent value="security">
            <SecurityTab
              profile={profile}
              onChangePassword={handleChangePassword}
              saving={saving}
            />
          </TabsContent>

          <TabsContent value="plan">
            <PlanTab profile={profile} />
          </TabsContent>
        </Tabs>
      </div>

      {/* Bottom Tab Bar */}
      <BottomTabBar />
    </div>
  );
};

export default ProfileV2;
