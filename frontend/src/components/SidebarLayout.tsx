import React, { useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import {
  FaChartLine,
  FaBox,
  FaDraftingCompass,
  FaShieldAlt,
  FaCogs,
  FaFileAlt,
  FaDesktop,
  FaTerminal,
  FaSignOutAlt,
  FaBrain,
  FaTachometerAlt,
  FaFire,
  FaRobot,
  FaCrown,
  FaBars,
  FaTimes,
  FaPlug,
} from "react-icons/fa";
import { ApiService } from "../services/api";
import { useTheme } from "../context/ThemeContext";

interface NavEntry {
  path: string;
  label: string;
  icon: React.ReactNode;
}

const NAV_ITEMS: NavEntry[] = [
  { path: "/dashboard", label: "Dashboard", icon: <FaChartLine /> },
  { path: "/global-setup", label: "Configuração Global", icon: <FaCogs /> },
  { path: "/ingestion", label: "Ingestão de Dados", icon: <FaBox /> },
  {
    path: "/autopilot",
    label: "Piping & Autopilot",
    icon: <FaDraftingCompass />,
  },
  { path: "/auto-connect", label: "AutoConnect CAD", icon: <FaPlug /> },
  { path: "/quality", label: "Quality Gate", icon: <FaShieldAlt /> },
  { path: "/final-report", label: "Relatório Final", icon: <FaFileAlt /> },
  { path: "/cad-dashboard", label: "Painel CAD", icon: <FaDesktop /> },
  { path: "/cnc-control", label: "Controle CNC Plasma", icon: <FaFire /> },
  { path: "/chatcad", label: "ChatCAD (IA)", icon: <FaRobot /> },
  { path: "/ai-dashboard", label: "Central de IAs", icon: <FaBrain /> },
  { path: "/analytics", label: "Analytics", icon: <FaTachometerAlt /> },
  { path: "/cad-console", label: "Console CAD", icon: <FaTerminal /> },
  { path: "/pricing", label: "Planos & Preços", icon: <FaCrown /> },
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
  const demo = isDemoMode();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const closeSidebar = () => setSidebarOpen(false);

  // Estilos dinâmicos baseados no tema
  const sidebarStyles: Record<string, React.CSSProperties> = {
    container: {
      display: "flex",
      height: "100vh",
      backgroundColor: theme.background,
      color: theme.textPrimary,
    },
    sidebar: {
      width: "260px",
      background: theme.surface,
      borderRight: `1px solid ${theme.border}`,
      boxShadow: "4px 0 20px rgba(0,0,0,0.2)",
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
      backgroundColor: `${theme.accentPrimary}15`,
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
      backgroundColor: theme.background,
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

      {/* Hamburger button (mobile only) */}
      <button
        className="sl-hamburger"
        style={sidebarStyles.hamburger}
        onClick={() => setSidebarOpen((o) => !o)}
        aria-label="Abrir menu"
      >
        {sidebarOpen ? <FaTimes /> : <FaBars />}
      </button>

      {/* Overlay (mobile only, when sidebar open) */}
      {sidebarOpen && (
        <div
          className="sl-overlay"
          style={sidebarStyles.overlay}
          onClick={closeSidebar}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`sl-sidebar${sidebarOpen ? " open" : ""}`}
        style={sidebarStyles.sidebar as React.CSSProperties}
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
                background: "linear-gradient(135deg, #00A1FF, #7C3AED)",
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

        <nav style={sidebarStyles.nav as React.CSSProperties}>
          {NAV_ITEMS.map((item) => (
            <div
              key={item.path}
              style={getNavStyle(item.path)}
              onClick={() => {
                navigate(item.path);
                closeSidebar();
              }}
              onMouseEnter={(e) => {
                if (location.pathname !== item.path) {
                  e.currentTarget.style.backgroundColor = `${theme.accentPrimary}08`;
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
              {item.icon} {item.label}
            </div>
          ))}
        </nav>

        <div style={sidebarStyles.sidebarFooter}>
          <div
            style={sidebarStyles.logoutBtn}
            onClick={handleLogout}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = `${theme.danger}15`;
              e.currentTarget.style.color = theme.danger;
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = "transparent";
              e.currentTarget.style.color = theme.textTertiary;
            }}
          >
            <FaSignOutAlt /> Sair
          </div>
        </div>
      </aside>

      {/* Área de Trabalho */}
      <main className="sl-main" style={sidebarStyles.main}>
        {children}
      </main>
    </div>
  );
};
