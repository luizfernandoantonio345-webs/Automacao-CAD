import React, { useState, useEffect, useRef, useCallback } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import {
  FaChartLine,
  FaBox,
  FaDraftingCompass,
  FaShieldAlt,
  FaCogs,
  FaFileAlt,
  FaSignOutAlt,
  FaBrain,
  FaFire,
  FaRobot,
  FaCrown,
  FaBars,
  FaTimes,
  FaUserTie,
  FaClipboardList,
  FaCreditCard,
} from "react-icons/fa";
import { ApiService } from "../services/api";
import { useTheme } from "../context/ThemeContext";
import { useLicense } from "../context/LicenseContext";

interface NavEntry {
  path: string;
  label: string;
  icon: React.ReactNode;
}

const NAV_ITEMS: NavEntry[] = [
  { path: "/dashboard", label: "Dashboard", icon: <FaChartLine /> },
  { path: "/pricing", label: "Planos & Preços", icon: <FaCrown /> },
  { path: "/global-setup", label: "Configuração Global", icon: <FaCogs /> },
  { path: "/ingestion", label: "Ingestão de Dados", icon: <FaBox /> },
  { path: "/autopilot", label: "Controle CAD", icon: <FaDraftingCompass /> },
  { path: "/quality", label: "Quality Gate", icon: <FaShieldAlt /> },
  { path: "/final-report", label: "Relatório Final", icon: <FaFileAlt /> },
  { path: "/cnc-control", label: "Controle CNC/Plasma", icon: <FaFire /> },
  { path: "/chatcad", label: "ChatCAD (IA)", icon: <FaRobot /> },
  { path: "/ai-dashboard", label: "Central de IAs", icon: <FaBrain /> },
  { path: "/admin-panel", label: "Auditoria", icon: <FaClipboardList /> },
  { path: "/billing", label: "Faturamento", icon: <FaCreditCard /> },
  { path: "/roles-manager", label: "Gerenciar Funções", icon: <FaUserTie /> },
  {
    path: "/system-monitor",
    label: "Monitor do Sistema",
    icon: <FaChartLine />,
  },
];

/** Detecta modo demo via token JWT (email demo@engenharia-cad.com) */
function isDemoMode(): boolean {
  try {
    const token = window.localStorage.getItem("token");
    if (!token) return false;
    const payload = JSON.parse(atob(token.split(".")[1]));
    return payload?.sub === "demo@engenharia-cad.com";
  } catch {
    return false;
  }
}

export const SidebarLayout: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const navigate = useNavigate();
  const location = useLocation();
  const { theme } = useTheme();
  const { license } = useLicense();
  const demo = isDemoMode();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const sidebarRef = useRef<HTMLElement>(null);
  const hamburgerRef = useRef<HTMLButtonElement>(null);

  // Keyboard navigation: Escape closes sidebar
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && sidebarOpen) {
        setSidebarOpen(false);
        hamburgerRef.current?.focus();
      }
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [sidebarOpen]);

  // Focus trap when sidebar is open on mobile
  useEffect(() => {
    if (sidebarOpen && sidebarRef.current) {
      const focusableElements =
        sidebarRef.current.querySelectorAll<HTMLElement>(
          'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])',
        );
      const firstElement = focusableElements[0];
      const lastElement = focusableElements[focusableElements.length - 1];

      const handleTabKey = (e: KeyboardEvent) => {
        if (e.key !== "Tab") return;
        if (e.shiftKey) {
          if (document.activeElement === firstElement) {
            e.preventDefault();
            lastElement?.focus();
          }
        } else {
          if (document.activeElement === lastElement) {
            e.preventDefault();
            firstElement?.focus();
          }
        }
      };

      document.addEventListener("keydown", handleTabKey);
      firstElement?.focus();
      return () => document.removeEventListener("keydown", handleTabKey);
    }
  }, [sidebarOpen]);

  // Handle nav item keyboard activation
  const handleNavKeyDown = useCallback(
    (e: React.KeyboardEvent, path: string) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        navigate(path);
        setSidebarOpen(false);
      }
    },
    [navigate],
  );

  const tierLabel = demo
    ? "Demo"
    : (license.tier ?? "demo").charAt(0).toUpperCase() +
      (license.tier ?? "demo").slice(1);
  const tierColor = demo
    ? theme.warning
    : license.tier === "enterprise"
      ? "#10B981"
      : license.tier === "professional"
        ? "#8B5CF6"
        : theme.accentPrimary;

  const closeSidebar = () => setSidebarOpen(false);

  // Estilos dinâmicos baseados no tema
  const sidebarStyles: Record<string, React.CSSProperties> = {
    container: {
      display: "flex",
      height: "100vh",
      background: theme.gradientPage || theme.background,
      color: theme.textPrimary,
    },
    sidebar: {
      width: "260px",
      background: theme.gradientPanel || theme.surface,
      borderRight: `1px solid ${theme.borderStrong || theme.border}`,
      boxShadow: `4px 0 24px ${theme.shadowMedium}`,
      padding: "32px 16px 16px",
      flexShrink: 0,
      display: "flex",
      flexDirection: "column",
    },
    brand: {
      fontSize: "18px",
      fontWeight: 700,
      letterSpacing: "0.15em",
      marginBottom: "12px",
      display: "flex",
      alignItems: "baseline",
      gap: "6px",
      paddingLeft: "12px",
      color: theme.textPrimary,
    },
    versionTag: {
      fontSize: "9px",
      color: theme.textTertiary,
      letterSpacing: "0.05em",
      fontWeight: 400,
    },
    demoBanner: {
      display: "flex",
      alignItems: "center",
      gap: "8px",
      padding: "8px 12px",
      marginBottom: "16px",
      backgroundColor: `${theme.warning}15`,
      border: `1px solid ${theme.warning}40`,
      borderRadius: "6px",
      color: theme.warning,
      fontSize: "9px",
      letterSpacing: "0.1em",
      fontWeight: 600,
    },
    demoDot: {
      width: "6px",
      height: "6px",
      backgroundColor: theme.warning,
      borderRadius: "50%",
      boxShadow: `0 0 6px ${theme.warning}`,
    },
    nav: {
      display: "flex",
      flexDirection: "column",
      gap: "4px",
      flex: 1,
      marginTop: "8px",
    },
    navItem: {
      padding: "12px 14px",
      color: theme.textSecondary,
      cursor: "pointer",
      display: "flex",
      alignItems: "center",
      gap: "12px",
      borderRadius: "8px",
      fontSize: "13px",
      fontWeight: 500,
      transition: "all 0.15s ease",
    },
    navActive: {
      padding: "12px 14px",
      backgroundColor: theme.accentSoft || `${theme.accentPrimary}15`,
      color: theme.accentPrimary,
      borderRadius: "8px",
      borderLeft: `3px solid ${theme.accentPrimary}`,
      display: "flex",
      alignItems: "center",
      gap: "12px",
      fontSize: "13px",
      fontWeight: 600,
      marginLeft: "-3px",
    },
    sidebarFooter: {
      borderTop: `1px solid ${theme.border}`,
      paddingTop: "12px",
      marginTop: "auto",
    },
    logoutBtn: {
      padding: "12px 14px",
      color: theme.textTertiary,
      cursor: "pointer",
      display: "flex",
      alignItems: "center",
      gap: "10px",
      fontSize: "13px",
      borderRadius: "8px",
      transition: "color 0.15s, background-color 0.15s",
    },
    main: {
      flex: 1,
      overflowY: "auto",
      background: theme.gradientPage || theme.background,
    },
    hamburger: {
      display: "none",
    },
    overlay: {
      display: "none",
    },
  };

  const getNavStyle = (path: string): React.CSSProperties => {
    return location.pathname === path
      ? sidebarStyles.navActive
      : sidebarStyles.navItem;
  };

  const handleLogout = () => {
    ApiService.logout();
    navigate("/");
  };

  return (
    <div style={sidebarStyles.container}>
      <style>{`
        /* Focus indicators for accessibility */
        .sl-sidebar [role="menuitem"]:focus,
        .sl-sidebar [role="button"]:focus {
          outline: 2px solid ${theme.accentPrimary};
          outline-offset: 2px;
        }
        .sl-hamburger:focus {
          outline: 2px solid ${theme.accentPrimary};
          outline-offset: 2px;
        }
        /* Skip to content link for screen readers */
        .skip-link {
          position: absolute;
          top: -40px;
          left: 0;
          background: ${theme.accentPrimary};
          color: white;
          padding: 8px 16px;
          z-index: 9999;
          font-weight: 600;
          border-radius: 0 0 8px 0;
          text-decoration: none;
        }
        .skip-link:focus {
          top: 0;
        }
        @media (max-width: 900px) {
          .sl-hamburger {
            display: flex !important;
            position: fixed;
            top: 14px;
            left: 14px;
            z-index: 1100;
            background: ${theme.surface};
            border: 1px solid ${theme.border};
            color: ${theme.textPrimary};
            border-radius: 8px;
            width: 40px;
            height: 40px;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            font-size: 18px;
            box-shadow: 0 2px 12px rgba(0,0,0,0.3);
          }
          .sl-sidebar {
            position: fixed !important;
            top: 0;
            left: 0;
            height: 100vh !important;
            z-index: 1050;
            transform: translateX(-100%);
            transition: transform 0.28s cubic-bezier(0.4,0,0.2,1);
          }
          .sl-sidebar.open {
            transform: translateX(0);
          }
          .sl-overlay {
            display: block !important;
            position: fixed;
            inset: 0;
            background: rgba(0,0,0,0.55);
            z-index: 1040;
          }
          .sl-main {
            padding-top: 60px;
          }
        }
      `}</style>

      {/* Skip to main content link for screen readers */}
      <a href="#main-content" className="skip-link">
        Pular para conteúdo principal
      </a>

      {/* Hamburger button (mobile only) */}
      <button
        ref={hamburgerRef}
        className="sl-hamburger"
        style={sidebarStyles.hamburger}
        onClick={() => setSidebarOpen((o) => !o)}
        aria-label={
          sidebarOpen ? "Fechar menu de navegação" : "Abrir menu de navegação"
        }
        aria-expanded={sidebarOpen}
        aria-controls="main-sidebar"
      >
        {sidebarOpen ? (
          <FaTimes aria-hidden="true" />
        ) : (
          <FaBars aria-hidden="true" />
        )}
      </button>

      {/* Overlay (mobile only, when sidebar open) */}
      {sidebarOpen && (
        <div
          className="sl-overlay"
          style={sidebarStyles.overlay}
          onClick={closeSidebar}
          aria-hidden="true"
        />
      )}

      {/* Sidebar */}
      <aside
        ref={sidebarRef}
        id="main-sidebar"
        className={`sl-sidebar${sidebarOpen ? " open" : ""}`}
        style={sidebarStyles.sidebar as React.CSSProperties}
        role="navigation"
        aria-label="Menu principal"
      >
        <div style={sidebarStyles.brand}>
          ENGENHARIA <span style={{ color: theme.accentPrimary }}>CAD</span>
          <span style={sidebarStyles.versionTag}>v1.0</span>
        </div>

        {demo && (
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              gap: "8px",
              margin: "8px 12px",
            }}
          >
            <div style={sidebarStyles.demoBanner as React.CSSProperties}>
              <span style={sidebarStyles.demoDot as React.CSSProperties} />
              MODO DEMONSTRAÇÃO
            </div>
            <button
              onClick={() => navigate("/pricing")}
              style={{
                width: "100%",
                padding: "10px 0",
                background: theme.gradientAccent || theme.accentPrimary,
                border: "none",
                borderRadius: "8px",
                color: "#fff",
                fontSize: "12px",
                fontWeight: 700,
                cursor: "pointer",
                letterSpacing: "0.5px",
              }}
            >
              🚀 Fazer Upgrade
            </button>
          </div>
        )}

        <nav
          style={sidebarStyles.nav as React.CSSProperties}
          role="menubar"
          aria-label="Navegação principal"
        >
          {NAV_ITEMS.map((item) => (
            <div
              key={item.path}
              role="menuitem"
              tabIndex={0}
              aria-current={
                location.pathname === item.path ? "page" : undefined
              }
              style={getNavStyle(item.path)}
              onClick={() => {
                navigate(item.path);
                closeSidebar();
              }}
              onKeyDown={(e) => handleNavKeyDown(e, item.path)}
              onMouseEnter={(e) => {
                if (location.pathname !== item.path) {
                  e.currentTarget.style.backgroundColor =
                    theme.accentSoft || `${theme.accentPrimary}08`;
                  e.currentTarget.style.color = theme.textPrimary;
                }
              }}
              onMouseLeave={(e) => {
                if (location.pathname !== item.path) {
                  e.currentTarget.style.backgroundColor = "transparent";
                  e.currentTarget.style.color = theme.textSecondary;
                }
              }}
            >
              <span aria-hidden="true">{item.icon}</span> {item.label}
            </div>
          ))}
        </nav>

        <div style={sidebarStyles.sidebarFooter}>
          {/* Tier badge */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              padding: "10px 14px",
              marginBottom: 8,
              borderRadius: 8,
              background: `${tierColor}10`,
              border: `1px solid ${tierColor}25`,
            }}
          >
            <FaCrown size={12} color={tierColor} />
            <span
              style={{
                fontSize: 11,
                fontWeight: 700,
                color: tierColor,
                letterSpacing: "0.5px",
              }}
            >
              Plano {tierLabel}
            </span>
            {!demo && license.tier !== "enterprise" && (
              <span
                onClick={() => navigate("/pricing")}
                style={{
                  marginLeft: "auto",
                  fontSize: 10,
                  color: theme.accentPrimary,
                  cursor: "pointer",
                  fontWeight: 600,
                }}
              >
                Upgrade
              </span>
            )}
          </div>
          <div
            role="button"
            tabIndex={0}
            style={sidebarStyles.logoutBtn}
            onClick={handleLogout}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                handleLogout();
              }
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = `${theme.danger}15`;
              e.currentTarget.style.color = theme.danger;
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = "transparent";
              e.currentTarget.style.color = theme.textTertiary;
            }}
            aria-label="Sair da conta"
          >
            <FaSignOutAlt aria-hidden="true" /> Sair
          </div>
        </div>
      </aside>

      {/* Área de Trabalho */}
      <main
        id="main-content"
        className="sl-main"
        style={sidebarStyles.main}
        role="main"
        aria-label="Conteúdo principal"
      >
        {children}
      </main>
    </div>
  );
};
