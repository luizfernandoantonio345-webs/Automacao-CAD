import React from "react";
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
} from "react-icons/fa";
import { ApiService } from "../services/api";

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
  { path: "/quality", label: "Quality Gate", icon: <FaShieldAlt /> },
  { path: "/final-report", label: "Relatório Final", icon: <FaFileAlt /> },
  { path: "/cad-dashboard", label: "Painel CAD", icon: <FaDesktop /> },
  { path: "/cad-console", label: "Console CAD", icon: <FaTerminal /> },
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
  const demo = isDemoMode();

  const getNavStyle = (path: string) => {
    return location.pathname === path ? db.navActive : db.navItem;
  };

  const handleLogout = () => {
    ApiService.logout();
    navigate("/");
  };

  return (
    <div style={db.container}>
      {/* Sidebar */}
      <aside style={db.sidebar}>
        <div style={db.brand}>
          ENGENHARIA <span style={{ color: "#00A1FF" }}>CAD</span>
          <span style={db.versionTag}>v1.0</span>
        </div>

        {demo && (
          <div style={db.demoBanner}>
            <span style={db.demoDot} />
            MODO DEMONSTRAÇÃO
          </div>
        )}

        <nav style={db.nav}>
          {NAV_ITEMS.map((item) => (
            <div
              key={item.path}
              style={getNavStyle(item.path)}
              onClick={() => navigate(item.path)}
            >
              {item.icon} {item.label}
            </div>
          ))}
        </nav>

        <div style={db.sidebarFooter}>
          <div style={db.logoutBtn} onClick={handleLogout}>
            <FaSignOutAlt /> Sair
          </div>
        </div>
      </aside>

      {/* Área de Trabalho */}
      <main style={db.main}>{children}</main>
    </div>
  );
};

const db: { [key: string]: React.CSSProperties } = {
  container: {
    display: "flex",
    height: "100vh",
    backgroundColor: "#0A0A0B",
    color: "#FFF",
  },
  sidebar: {
    width: "280px",
    background: "#0D0D0F",
    borderRight: "1px solid #1a1c22",
    boxShadow: "10px 0 30px rgba(0,0,0,0.5)",
    padding: "40px 20px 20px",
    flexShrink: 0,
    display: "flex",
    flexDirection: "column" as const,
  },
  brand: {
    fontSize: "22px",
    fontWeight: "bold",
    letterSpacing: "4px",
    marginBottom: "16px",
    display: "flex",
    alignItems: "baseline",
    gap: "8px",
  },
  versionTag: {
    fontSize: "10px",
    color: "#556",
    letterSpacing: "1px",
    fontWeight: 400,
  },
  demoBanner: {
    display: "flex",
    alignItems: "center",
    gap: "8px",
    padding: "8px 12px",
    marginBottom: "20px",
    backgroundColor: "rgba(255, 215, 0, 0.08)",
    border: "1px solid rgba(255, 215, 0, 0.25)",
    borderRadius: "4px",
    color: "#FFD700",
    fontSize: "10px",
    letterSpacing: "1.5px",
    fontWeight: 700,
  },
  demoDot: {
    width: "6px",
    height: "6px",
    backgroundColor: "#FFD700",
    borderRadius: "50%",
    boxShadow: "0 0 6px #FFD700",
    flexShrink: 0,
  },
  nav: {
    display: "flex",
    flexDirection: "column" as const,
    gap: "8px",
    flex: 1,
  },
  navItem: {
    padding: "12px 15px",
    color: "#555",
    cursor: "pointer",
    display: "flex",
    alignItems: "center",
    gap: "12px",
    borderRadius: "4px",
    fontSize: "14px",
    transition: "color 0.15s",
  },
  navActive: {
    padding: "12px 15px",
    backgroundColor: "rgba(0,161,255,0.1)",
    color: "#00A1FF",
    borderRadius: "4px",
    borderLeft: "4px solid #00A1FF",
    display: "flex",
    alignItems: "center",
    gap: "12px",
    fontSize: "14px",
  },
  sidebarFooter: {
    borderTop: "1px solid #1a1c22",
    paddingTop: "16px",
  },
  logoutBtn: {
    padding: "12px 15px",
    color: "#666",
    cursor: "pointer",
    display: "flex",
    alignItems: "center",
    gap: "10px",
    fontSize: "13px",
    borderRadius: "4px",
    transition: "color 0.15s",
  },
  main: { flex: 1, overflowY: "auto" as const },
};
