import React, { useState, useEffect, lazy, Suspense } from "react";
import {
  BrowserRouter as Router,
  Routes,
  Route,
  Navigate,
  useLocation,
} from "react-router-dom";
import axios from "axios";
import Login from "./pages/Login";
import { SidebarLayout } from "./components/SidebarLayout";
import License from "./components/License";
import { ApiService } from "./services/api";
import { LICENSING_BASE_URL } from "./services/endpoints";
import { ThemeProvider } from "./context/ThemeContext";
import { GlobalProvider } from "./context/GlobalContext";
import { ToastProvider } from "./context/ToastContext";
import { LicenseProvider } from "./context/LicenseContext";
import DemoUpgradeModal from "./components/DemoUpgradeModal";
import { UIGuard } from "./middleware/UIGuard";
import { ErrorBoundary } from "./components/ErrorBoundary";
import {
  orchestrator,
  startHeartbeat,
  stopHeartbeat,
} from "./middleware/AIOrchestrator";

// Lazy-loaded pages for code splitting
const Dashboard = lazy(() => import("./pages/Dashboard"));
const DataIngestion = lazy(() => import("./pages/DataIngestion"));
const QualityGate = lazy(() => import("./pages/QualityGate"));
const FinalReport = lazy(() => import("./pages/FinalReport"));
const GlobalSetup = lazy(() => import("./pages/GlobalSetup"));
const CadConsole = lazy(() => import("./pages/CadConsole"));
const CadDashboard = lazy(() => import("./pages/CadDashboard"));
const AutoCADControl = lazy(() => import("./pages/AutoCADControl"));
const AIDashboard = lazy(() => import("./pages/AIDashboard"));
const AnalyticsDashboard = lazy(() => import("./pages/AnalyticsDashboard"));
const CncControl = lazy(() => import("./pages/CncControl"));
const ChatCAD = lazy(() => import("./pages/ChatCAD"));
const Pricing = lazy(() => import("./pages/Pricing"));
const Checkout = lazy(() => import("./pages/Checkout"));
type User = { email: string; empresa: string; limite: number; usado: number };
type LicenseCache = { licenseKey: string; machineId: string };

const licensingApi = axios.create({
  baseURL: LICENSING_BASE_URL,
  timeout: 8000,
});

// Wrapper para aplicar temas e contextos globais
const AppLayout: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <ThemeProvider>
    <GlobalProvider>
      <LicenseProvider>
        <ToastProvider>
          {children}
          <DemoUpgradeModal />
        </ToastProvider>
      </LicenseProvider>
    </GlobalProvider>
  </ThemeProvider>
);

/** Tela de carregamento com branding Engenharia CAD */
const LoadingScreen: React.FC<{ message: string }> = ({ message }) => (
  <div
    style={{
      minHeight: "100vh",
      backgroundColor: "#050507",
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      justifyContent: "center",
      fontFamily: "'Segoe UI', Roboto, sans-serif",
    }}
  >
    <div
      style={{
        fontSize: "28px",
        fontWeight: 900,
        letterSpacing: "8px",
        color: "#FFF",
        marginBottom: "20px",
      }}
    >
      ENGENHARIA <span style={{ color: "#00A1FF" }}>CAD</span>
    </div>
    <div
      style={{
        width: "180px",
        height: "3px",
        backgroundColor: "#111827",
        borderRadius: "2px",
        overflow: "hidden",
        marginBottom: "16px",
      }}
    >
      <div
        style={{
          width: "40%",
          height: "100%",
          backgroundColor: "#00A1FF",
          borderRadius: "2px",
          animation: "loadSlide 1.2s ease-in-out infinite alternate",
        }}
      />
    </div>
    <div style={{ color: "#556677", fontSize: "13px", letterSpacing: "1px" }}>
      {message}
    </div>
    <style>{`@keyframes loadSlide { from { margin-left: 0 } to { margin-left: 60% } }`}</style>
  </div>
);

function AppContent() {
  const [user, setUser] = useState<User | null>(null);
  const [licensed, setLicensed] = useState(false);
  const [demoMode, setDemoMode] = useState(false);
  const [checkingLicense, setCheckingLicense] = useState(true);
  const [restoringSession, setRestoringSession] = useState(true);

  useEffect(() => {
    let mounted = true;

    const bootstrapLicense = async () => {
      try {
        const raw = window.localStorage.getItem("license");
        if (!raw) {
          // Sem licença armazenada — continuar em modo demo
          if (mounted) {
            setLicensed(true);
            setDemoMode(true);
          }
          return;
        }
        const parsed = JSON.parse(raw) as Partial<LicenseCache>;
        const licenseKey = String(parsed.licenseKey || "").trim();
        const machineId = String(parsed.machineId || "").trim();
        if (!licenseKey || !machineId) {
          window.localStorage.removeItem("license");
          if (mounted) {
            setLicensed(true);
            setDemoMode(true);
          }
          return;
        }
        try {
          await licensingApi.post("/validate", {
            license_key: licenseKey,
            machine_id: machineId,
          });
          if (mounted) {
            setLicensed(true);
            setDemoMode(false);
          }
        } catch {
          // Servidor de licenças offline — continuar em modo demo
          if (mounted) {
            setLicensed(true);
            setDemoMode(true);
          }
        }
      } catch {
        if (mounted) {
          setLicensed(true);
          setDemoMode(true);
        }
      } finally {
        if (mounted) setCheckingLicense(false);
      }
    };

    bootstrapLicense();
    return () => {
      mounted = false;
    };
  }, []);

  useEffect(() => {
    let mounted = true;

    const restoreSession = async () => {
      try {
        const currentUser = await ApiService.getCurrentUser();
        if (mounted) {
          setUser(currentUser);
        }
      } catch {
        // Sessão expirada ou inexistente — manter não-autenticado
        if (mounted) {
          setUser(null);
        }
      } finally {
        if (mounted) {
          setRestoringSession(false);
        }
      }
    };

    restoreSession();
    return () => {
      mounted = false;
    };
  }, []);

  const handleLogout = () => {
    ApiService.logout();
    setUser(null);
  };

  if (checkingLicense) return <LoadingScreen message="Validando licença..." />;
  if (restoringSession)
    return <LoadingScreen message="Restaurando sessão..." />;

  // Usuário autenticado - exibir aplicação com rotas
  const fallback = <LoadingScreen message="Carregando módulo..." />;

  return (
    <>
      {demoMode && (
        <div style={{
          background: 'linear-gradient(90deg, #f59e0b, #d97706)',
          color: '#fff',
          textAlign: 'center',
          padding: '8px 16px',
          fontSize: '14px',
          fontWeight: 500,
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          zIndex: 9999,
        }}>
          ⚠️ Modo Demonstração — Licença não validada. Algumas funcionalidades podem estar limitadas.
        </div>
      )}
      <div style={demoMode ? { marginTop: '40px' } : undefined}>
        <Router>
          <RouteAnticipator />
          <BackendHeartbeat />
      <Suspense fallback={fallback}>
        <Routes>
          <Route path="/" element={<Login />} />
          <Route path="/pricing" element={<Pricing />} />
          <Route path="/planos" element={<Pricing />} />
          <Route path="/checkout" element={<Checkout />} />
          <Route
            path="/dashboard"
            element={
              <SidebarLayout>
                <Dashboard />
              </SidebarLayout>
            }
          />
          <Route
            path="/ingestion"
            element={
              <SidebarLayout>
                <DataIngestion />
              </SidebarLayout>
            }
          />
          <Route
            path="/autopilot"
            element={
              <SidebarLayout>
                <AutoCADControl />
              </SidebarLayout>
            }
          />
          <Route
            path="/quality"
            element={
              <SidebarLayout>
                <QualityGate />
              </SidebarLayout>
            }
          />
          <Route
            path="/final-report"
            element={
              <SidebarLayout>
                <FinalReport />
              </SidebarLayout>
            }
          />
          <Route
            path="/global-setup"
            element={
              <SidebarLayout>
                <GlobalSetup />
              </SidebarLayout>
            }
          />
          <Route
            path="/cad-console"
            element={
              <SidebarLayout>
                <CadConsole />
              </SidebarLayout>
            }
          />
          <Route
            path="/cad-dashboard"
            element={
              <SidebarLayout>
                <CadDashboard />
              </SidebarLayout>
            }
          />
          <Route
            path="/cnc-control"
            element={
              <SidebarLayout>
                <CncControl />
              </SidebarLayout>
            }
          />
          <Route
            path="/ai-dashboard"
            element={
              <SidebarLayout>
                <AIDashboard />
              </SidebarLayout>
            }
          />
          <Route
            path="/analytics"
            element={
              <SidebarLayout>
                <AnalyticsDashboard />
              </SidebarLayout>
            }
          />
          <Route
            path="/chatcad"
            element={
              <SidebarLayout>
                <ChatCAD />
              </SidebarLayout>
            }
          />
          {/* Redirects para rotas legadas */}
          <Route
            path="/autocad-control"
            element={<Navigate to="/autopilot" replace />}
          />
          <Route
            path="/setup"
            element={<Navigate to="/global-setup" replace />}
          />
        </Routes>
      </Suspense>
    </Router>
      </div>
    </>
  );
}

/** Componente invisível que pré-aquece dados ao detectar navegação */
function RouteAnticipator() {
  const location = useLocation();
  useEffect(() => {
    orchestrator.anticipate(location.pathname);
  }, [location.pathname]);
  return null;
}

/** Componente invisível que mantém heartbeat silencioso com o backend */
function BackendHeartbeat() {
  useEffect(() => {
    // Inicia ping silencioso a cada 30s — monitora saúde do backend
    const api = (window as any).__ENGCAD_AXIOS__;
    if (api) startHeartbeat(api);
    return () => stopHeartbeat();
  }, []);
  return null;
}

function App() {
  return (
    <ErrorBoundary>
      <AppLayout>
        <UIGuard>
          <AppContent />
        </UIGuard>
      </AppLayout>
    </ErrorBoundary>
  );
}

export default App;
