import React, { useEffect, useState } from "react";
import {
  FaBrain,
  FaRobot,
  FaRoute,
  FaExclamationTriangle,
  FaDollarSign,
  FaCheckCircle,
  FaFileAlt,
  FaTools,
  FaComments,
  FaChartLine,
  FaSync,
  FaCog,
  FaPaperPlane,
} from "react-icons/fa";
import { useTheme } from "../context/ThemeContext";
import { API_BASE_URL } from "../services/api";
import createStyles, { spacing, radius } from "../styles/shared";

// ── Tipos ──
interface AIEngine {
  name: string;
  status: "online" | "offline" | "loading";
  metrics: {
    calls: number;
    successRate: number;
    avgResponseTime: number;
  };
  capabilities: string[];
  description: string;
}

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
}

interface AnalysisResult {
  type: string;
  success: boolean;
  data: Record<string, unknown>;
  timestamp: Date;
}

// ── Configuração das IAs ──
const AI_ENGINES_CONFIG: Record<
  string,
  { icon: React.ReactNode; color: string; description: string }
> = {
  DrawingAnalyzerAI: {
    icon: <FaRoute />,
    color: "#00D4FF",
    description:
      "Analisa desenhos CAD, extrai componentes, valida normas técnicas",
  },
  PipeOptimizerAI: {
    icon: <FaRoute />,
    color: "#00FF94",
    description: "Otimiza rotas de tubulação, calcula materiais e custos",
  },
  ConflictDetectorAI: {
    icon: <FaExclamationTriangle />,
    color: "#FF6B6B",
    description: "Detecta colisões e interferências entre componentes",
  },
  CostEstimatorAI: {
    icon: <FaDollarSign />,
    color: "#FFD93D",
    description: "Estima custos, gera MTO e relatórios financeiros",
  },
  QualityInspectorAI: {
    icon: <FaCheckCircle />,
    color: "#6BCB77",
    description: "Inspeção automática de qualidade e conformidade",
  },
  DocumentGeneratorAI: {
    icon: <FaFileAlt />,
    color: "#9B59B6",
    description: "Gera documentação técnica automaticamente",
  },
  MaintenancePredictorAI: {
    icon: <FaTools />,
    color: "#FF8C00",
    description: "Predição de manutenção baseada em padrões",
  },
  AssistantChatbotAI: {
    icon: <FaComments />,
    color: "#00B4D8",
    description: "Assistente técnico com conhecimento CAD/Industrial",
  },
};

// ── Componentes ──
const AICard: React.FC<{
  engine: AIEngine;
  theme: ReturnType<typeof useTheme>["theme"];
  onSelect: () => void;
  isSelected: boolean;
}> = ({ engine, theme, onSelect, isSelected }) => {
  const config = AI_ENGINES_CONFIG[engine.name] || {
    icon: <FaBrain />,
    color: theme.accentPrimary,
    description: engine.description,
  };

  return (
    <div
      onClick={onSelect}
      style={{
        background: isSelected
          ? `linear-gradient(135deg, ${config.color}20 0%, ${theme.bgSecondary} 100%)`
          : theme.bgSecondary,
        border: `2px solid ${isSelected ? config.color : theme.borderColor}`,
        borderRadius: radius.lg,
        padding: spacing.md,
        cursor: "pointer",
        transition: "all 0.3s ease",
        boxShadow: isSelected ? `0 4px 20px ${config.color}30` : "none",
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: spacing.sm,
          marginBottom: spacing.sm,
        }}
      >
        <div
          style={{
            width: 40,
            height: 40,
            borderRadius: radius.md,
            background: `${config.color}20`,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: config.color,
            fontSize: 20,
          }}
        >
          {config.icon}
        </div>
        <div>
          <h3
            style={{
              color: theme.textPrimary,
              fontWeight: 600,
              fontSize: 14,
              margin: 0,
            }}
          >
            {engine.name.replace("AI", "")}
          </h3>
          <span
            style={{
              fontSize: 10,
              padding: "2px 8px",
              borderRadius: radius.sm,
              background:
                engine.status === "online" ? "#00FF9420" : "#FF6B6B20",
              color: engine.status === "online" ? "#00FF94" : "#FF6B6B",
            }}
          >
            {engine.status.toUpperCase()}
          </span>
        </div>
      </div>
      <p
        style={{
          color: theme.textSecondary,
          fontSize: 12,
          margin: 0,
          lineHeight: 1.4,
        }}
      >
        {config.description}
      </p>
      <div
        style={{
          marginTop: spacing.sm,
          display: "flex",
          gap: spacing.xs,
          flexWrap: "wrap",
        }}
      >
        {engine.metrics && (
          <>
            <span
              style={{
                fontSize: 10,
                padding: "2px 6px",
                borderRadius: radius.sm,
                background: theme.bgPrimary,
                color: theme.textSecondary,
              }}
            >
              {engine.metrics.calls} chamadas
            </span>
            <span
              style={{
                fontSize: 10,
                padding: "2px 6px",
                borderRadius: radius.sm,
                background: theme.bgPrimary,
                color: engine.metrics.successRate > 90 ? "#00FF94" : "#FFD93D",
              }}
            >
              {engine.metrics.successRate}% sucesso
            </span>
          </>
        )}
      </div>
    </div>
  );
};

const ChatInterface: React.FC<{
  messages: ChatMessage[];
  onSend: (msg: string) => void;
  loading: boolean;
  theme: ReturnType<typeof useTheme>["theme"];
}> = ({ messages, onSend, loading, theme }) => {
  const [input, setInput] = useState("");

  const handleSend = () => {
    if (input.trim() && !loading) {
      onSend(input.trim());
      setInput("");
    }
  };

  return (
    <div
      style={{
        background: theme.bgSecondary,
        borderRadius: radius.lg,
        border: `1px solid ${theme.borderColor}`,
        display: "flex",
        flexDirection: "column",
        height: 400,
      }}
    >
      <div
        style={{
          padding: spacing.md,
          borderBottom: `1px solid ${theme.border}`,
          display: "flex",
          alignItems: "center",
          gap: spacing.sm,
        }}
      >
        <span style={{ color: "#00B4D8" }}>
          <FaComments />
        </span>
        <span style={{ color: theme.textPrimary, fontWeight: 600 }}>
          Assistente IA
        </span>
      </div>

      <div
        style={{
          flex: 1,
          overflowY: "auto",
          padding: spacing.md,
          display: "flex",
          flexDirection: "column",
          gap: spacing.sm,
        }}
      >
        {messages.length === 0 && (
          <div
            style={{
              textAlign: "center",
              color: theme.textSecondary,
              marginTop: spacing.xl,
            }}
          >
            <span
              style={{
                marginBottom: spacing.sm,
                opacity: 0.5,
                display: "inline-block",
              }}
            >
              <FaRobot size={40} />
            </span>
            <p>Olá! Como posso ajudar com seu projeto CAD?</p>
            <p style={{ fontSize: 12 }}>
              Pergunte sobre normas, materiais, comandos AutoCAD, cálculos...
            </p>
          </div>
        )}
        {messages.map((msg, idx) => (
          <div
            key={idx}
            style={{
              alignSelf: msg.role === "user" ? "flex-end" : "flex-start",
              maxWidth: "80%",
              padding: spacing.sm,
              borderRadius: radius.md,
              background:
                msg.role === "user" ? theme.accentPrimary : theme.bgPrimary,
              color: msg.role === "user" ? "#fff" : theme.textPrimary,
            }}
          >
            {msg.content}
          </div>
        ))}
        {loading && (
          <div
            style={{
              alignSelf: "flex-start",
              padding: spacing.sm,
              borderRadius: radius.md,
              background: theme.bgPrimary,
              color: theme.textSecondary,
            }}
          >
            <FaSync /> Processando...
          </div>
        )}
      </div>

      <div
        style={{
          padding: spacing.md,
          borderTop: `1px solid ${theme.border}`,
          display: "flex",
          gap: spacing.sm,
        }}
      >
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={(e) => e.key === "Enter" && handleSend()}
          placeholder="Digite sua pergunta..."
          style={{
            flex: 1,
            padding: spacing.sm,
            borderRadius: radius.md,
            border: `1px solid ${theme.borderColor}`,
            background: theme.bgPrimary,
            color: theme.textPrimary,
            outline: "none",
          }}
        />
        <button
          onClick={handleSend}
          disabled={loading || !input.trim()}
          style={{
            padding: spacing.sm,
            borderRadius: radius.md,
            border: "none",
            background: theme.accentPrimary,
            color: "#fff",
            cursor: loading ? "not-allowed" : "pointer",
            opacity: loading || !input.trim() ? 0.5 : 1,
          }}
        >
          <FaPaperPlane />
        </button>
      </div>
    </div>
  );
};

const AnalysisPanel: React.FC<{
  selectedEngine: AIEngine | null;
  onAnalyze: (type: string, data: Record<string, unknown>) => void;
  results: AnalysisResult[];
  loading: boolean;
  theme: ReturnType<typeof useTheme>["theme"];
}> = ({ selectedEngine, onAnalyze, results, loading, theme }) => {
  if (!selectedEngine) {
    return (
      <div
        style={{
          background: theme.bgSecondary,
          borderRadius: radius.lg,
          border: `1px solid ${theme.borderColor}`,
          padding: spacing.xl,
          textAlign: "center",
          color: theme.textSecondary,
        }}
      >
        <span
          style={{
            marginBottom: spacing.sm,
            opacity: 0.5,
            display: "inline-block",
          }}
        >
          <FaCog size={40} />
        </span>
        <p>Selecione uma IA para ver opções de análise</p>
      </div>
    );
  }

  const config = AI_ENGINES_CONFIG[selectedEngine.name];

  return (
    <div
      style={{
        background: theme.bgSecondary,
        borderRadius: radius.lg,
        border: `1px solid ${theme.borderColor}`,
        padding: spacing.md,
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: spacing.sm,
          marginBottom: spacing.md,
        }}
      >
        <div
          style={{
            width: 32,
            height: 32,
            borderRadius: radius.md,
            background: `${config?.color}20`,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: config?.color,
          }}
        >
          {config?.icon}
        </div>
        <span style={{ color: theme.textPrimary, fontWeight: 600 }}>
          {selectedEngine.name.replace("AI", "")}
        </span>
      </div>

      <div style={{ marginBottom: spacing.md }}>
        <h4
          style={{
            color: theme.textSecondary,
            fontSize: 12,
            marginBottom: spacing.sm,
          }}
        >
          CAPACIDADES
        </h4>
        <div style={{ display: "flex", flexWrap: "wrap", gap: spacing.xs }}>
          {selectedEngine.capabilities.map((cap, idx) => (
            <button
              key={idx}
              onClick={() => onAnalyze(cap, {})}
              disabled={loading}
              style={{
                padding: `${spacing.xs} ${spacing.sm}`,
                borderRadius: radius.md,
                border: `1px solid ${theme.borderColor}`,
                background: theme.bgPrimary,
                color: theme.textPrimary,
                cursor: loading ? "not-allowed" : "pointer",
                fontSize: 11,
                opacity: loading ? 0.5 : 1,
              }}
            >
              {cap.replace(/_/g, " ")}
            </button>
          ))}
        </div>
      </div>

      {results.length > 0 && (
        <div>
          <h4
            style={{
              color: theme.textSecondary,
              fontSize: 12,
              marginBottom: spacing.sm,
            }}
          >
            RESULTADOS RECENTES
          </h4>
          <div style={{ maxHeight: 200, overflowY: "auto" }}>
            {results.slice(-3).map((result, idx) => (
              <div
                key={idx}
                style={{
                  padding: spacing.sm,
                  borderRadius: radius.md,
                  background: theme.bgPrimary,
                  marginBottom: spacing.xs,
                }}
              >
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    marginBottom: 4,
                  }}
                >
                  <span style={{ color: theme.textPrimary, fontSize: 12 }}>
                    {result.type}
                  </span>
                  <span
                    style={{
                      fontSize: 10,
                      color: result.success ? "#00FF94" : "#FF6B6B",
                    }}
                  >
                    {result.success ? "✓ Sucesso" : "✗ Erro"}
                  </span>
                </div>
                <pre
                  style={{
                    fontSize: 10,
                    color: theme.textSecondary,
                    margin: 0,
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                  }}
                >
                  {JSON.stringify(result.data).slice(0, 100)}...
                </pre>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

// ── Página Principal ──
const AIDashboard: React.FC = () => {
  const { theme } = useTheme();
  const styles = createStyles(theme);

  const [engines, setEngines] = useState<AIEngine[]>([]);
  const [selectedEngine, setSelectedEngine] = useState<AIEngine | null>(null);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [analysisResults, setAnalysisResults] = useState<AnalysisResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [systemStatus, setSystemStatus] = useState<
    "online" | "offline" | "loading"
  >("loading");

  // Carregar status das IAs
  useEffect(() => {
    let cancelled = false;
    const loadEngines = async () => {
      try {
        const res = await fetch(`${API_BASE_URL}/api/ai/engines`);
        if (res.ok) {
          const data = await res.json();
          if (!cancelled) {
            setEngines(data.engines || []);
            setSystemStatus("online");
          }
        } else {
          throw new Error("API offline");
        }
      } catch {
        if (!cancelled) {
          // Fallback: engines padrão offline
          setEngines(
            Object.keys(AI_ENGINES_CONFIG).map((name) => ({
              name,
              status: "offline" as const,
              metrics: { calls: 0, successRate: 0, avgResponseTime: 0 },
              capabilities: [],
              description: AI_ENGINES_CONFIG[name].description,
            })),
          );
          setSystemStatus("offline");
        }
      }
    };
    loadEngines();
    return () => {
      cancelled = true;
    };
  }, []);

  // Enviar mensagem ao chat
  const handleSendChat = async (message: string) => {
    setChatMessages((prev) => [
      ...prev,
      { role: "user", content: message, timestamp: new Date() },
    ]);
    setLoading(true);

    try {
      const token = localStorage.getItem("token");
      const headers: Record<string, string> = {
        "Content-Type": "application/json",
      };
      if (token) headers["Authorization"] = `Bearer ${token}`;
      const res = await fetch(`${API_BASE_URL}/api/ai/chat`, {
        method: "POST",
        headers,
        body: JSON.stringify({ message, context: {} }),
      });
      const data = await res.json();

      // Extrair resposta do formato agregado do router de IAs
      const chatResponse =
        data.data?.AssistantChatbot?.response ||
        data.response ||
        data.message ||
        (data.success === false ? data.error : null) ||
        "Desculpe, não consegui processar.";

      setChatMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: chatResponse,
          timestamp: new Date(),
        },
      ]);
    } catch {
      setChatMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "Erro ao conectar com o servidor de IA.",
          timestamp: new Date(),
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  // Executar análise
  const handleAnalyze = async (
    type: string,
    inputData: Record<string, unknown>,
  ) => {
    if (!selectedEngine) return;
    setLoading(true);

    try {
      const token = localStorage.getItem("token");
      const headers: Record<string, string> = {
        "Content-Type": "application/json",
      };
      if (token) headers["Authorization"] = `Bearer ${token}`;
      const res = await fetch(
        `${API_BASE_URL}/api/ai/engine/${selectedEngine.name}/execute`,
        {
          method: "POST",
          headers,
          body: JSON.stringify({ capability: type, input: inputData }),
        },
      );
      const data = await res.json();
      setAnalysisResults((prev) => [
        ...prev,
        { type, success: data.success !== false, data, timestamp: new Date() },
      ]);
    } catch {
      setAnalysisResults((prev) => [
        ...prev,
        {
          type,
          success: false,
          data: { error: "Erro de conexão" },
          timestamp: new Date(),
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  // Engines with status "idle", "processing", or "completed" are considered online/available
  const onlineCount = engines.filter((e) =>
    ["idle", "processing", "completed", "online"].includes(
      e.status?.toLowerCase() || "",
    ),
  ).length;

  return (
    <div style={{ ...styles.pageContainer, padding: 0 }}>
      <main style={{ flex: 1, padding: spacing.lg, overflowY: "auto" }}>
        {/* Header */}
        <header style={styles.pageHeader}>
          <div>
            <h1 style={styles.pageTitle}>
              <span style={{ color: "#00D4FF", display: "flex" }}>
                <FaBrain />
              </span>
              Central de IAs
            </h1>
            <p style={styles.pageSubtitle}>
              {onlineCount}/{engines.length} IAs ativas | Sistema{" "}
              <span
                style={{
                  color:
                    systemStatus === "online"
                      ? "#00FF94"
                      : systemStatus === "loading"
                        ? "#FFD93D"
                        : "#FF6B6B",
                }}
              >
                {systemStatus.toUpperCase()}
              </span>
            </p>
          </div>
          <button
            onClick={() => window.location.reload()}
            style={{
              ...styles.buttonPrimary,
              background: `linear-gradient(135deg, #00D4FF 0%, #00D4FFCC 100%)`,
              boxShadow: `0 4px 15px #00D4FF40`,
            }}
          >
            <FaSync size={12} /> ATUALIZAR STATUS
          </button>
        </header>

        {/* Métricas Globais */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
            gap: spacing.md,
            marginBottom: spacing.lg,
          }}
        >
          <MetricCard
            icon={<FaBrain />}
            label="IAs Ativas"
            value={onlineCount}
            total={engines.length}
            color="#00D4FF"
            theme={theme}
          />
          <MetricCard
            icon={<FaChartLine />}
            label="Chamadas Hoje"
            value={engines.reduce((sum, e) => sum + (e.metrics?.calls || 0), 0)}
            color="#00FF94"
            theme={theme}
          />
          <MetricCard
            icon={<FaCheckCircle />}
            label="Taxa de Sucesso"
            value={
              engines.length > 0
                ? Math.round(
                    engines.reduce(
                      (sum, e) => sum + (e.metrics?.successRate || 0),
                      0,
                    ) / engines.length,
                  )
                : 0
            }
            suffix="%"
            color="#6BCB77"
            theme={theme}
          />
          <MetricCard
            icon={<FaCog />}
            label="Tempo Médio"
            value={
              engines.length > 0
                ? Math.round(
                    engines.reduce(
                      (sum, e) => sum + (e.metrics?.avgResponseTime || 0),
                      0,
                    ) / engines.length,
                  )
                : 0
            }
            suffix="ms"
            color="#FFD93D"
            theme={theme}
          />
        </div>

        {/* Grid Principal */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: spacing.lg,
          }}
        >
          {/* Coluna Esquerda: IAs + Análise */}
          <div>
            <h2
              style={{
                color: theme.textPrimary,
                fontSize: 16,
                fontWeight: 600,
                marginBottom: spacing.md,
                display: "flex",
                alignItems: "center",
                gap: spacing.sm,
              }}
            >
              <span style={{ color: "#00D4FF" }}>
                <FaRobot />
              </span>
              Engines de IA
            </h2>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(2, 1fr)",
                gap: spacing.sm,
                marginBottom: spacing.lg,
              }}
            >
              {engines.map((engine) => (
                <AICard
                  key={engine.name}
                  engine={engine}
                  theme={theme}
                  onSelect={() => setSelectedEngine(engine)}
                  isSelected={selectedEngine?.name === engine.name}
                />
              ))}
            </div>

            <AnalysisPanel
              selectedEngine={selectedEngine}
              onAnalyze={handleAnalyze}
              results={analysisResults}
              loading={loading}
              theme={theme}
            />
          </div>

          {/* Coluna Direita: Chat */}
          <div>
            <h2
              style={{
                color: theme.textPrimary,
                fontSize: 16,
                fontWeight: 600,
                marginBottom: spacing.md,
                display: "flex",
                alignItems: "center",
                gap: spacing.sm,
              }}
            >
              <span style={{ color: "#00B4D8" }}>
                <FaComments />
              </span>
              Assistente Técnico
            </h2>
            <ChatInterface
              messages={chatMessages}
              onSend={handleSendChat}
              loading={loading}
              theme={theme}
            />

            {/* Quick Actions */}
            <div style={{ marginTop: spacing.lg }}>
              <h3
                style={{
                  color: theme.textSecondary,
                  fontSize: 12,
                  marginBottom: spacing.sm,
                }}
              >
                AÇÕES RÁPIDAS
              </h3>
              <div
                style={{ display: "flex", flexWrap: "wrap", gap: spacing.xs }}
              >
                {[
                  "Calcular perda de carga",
                  "Norma ASME B31.3",
                  "Materiais para vapor",
                  "Comandos AutoCAD",
                ].map((action, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleSendChat(action)}
                    style={{
                      padding: `${spacing.xs} ${spacing.sm}`,
                      borderRadius: radius.md,
                      border: `1px solid ${theme.border}`,
                      background: theme.panel,
                      color: theme.textPrimary,
                      cursor: "pointer",
                      fontSize: 11,
                    }}
                  >
                    {action}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
};

// ── Componente Auxiliar: Metric Card ──
const MetricCard: React.FC<{
  icon: React.ReactElement;
  label: string;
  value: number;
  total?: number;
  suffix?: string;
  color: string;
  theme: ReturnType<typeof useTheme>["theme"];
}> = ({ icon, label, value, total, suffix, color, theme }) => (
  <div
    style={{
      background: theme.bgSecondary,
      borderRadius: radius.lg,
      border: `1px solid ${theme.borderColor}`,
      padding: spacing.md,
      display: "flex",
      alignItems: "center",
      gap: spacing.md,
    }}
  >
    <div
      style={{
        width: 48,
        height: 48,
        borderRadius: radius.md,
        background: `${color}15`,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        color,
        fontSize: 20,
      }}
    >
      {icon}
    </div>
    <div>
      <div style={{ color: theme.textPrimary, fontSize: 24, fontWeight: 700 }}>
        {value}
        {total !== undefined && (
          <span style={{ color: theme.textSecondary, fontSize: 14 }}>
            /{total}
          </span>
        )}
        {suffix && <span style={{ fontSize: 14 }}>{suffix}</span>}
      </div>
      <div style={{ color: theme.textSecondary, fontSize: 12 }}>{label}</div>
    </div>
  </div>
);

export default AIDashboard;
