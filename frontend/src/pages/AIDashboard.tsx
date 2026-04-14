import React, { useEffect, useState, useCallback } from "react";
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
  FaDownload,
  FaPlay,
  FaWrench,
  FaCalendarCheck,
  FaClipboardList,
} from "react-icons/fa";
import { useTheme } from "../context/ThemeContext";
import { API_BASE_URL } from "../services/api";
import createStyles, { spacing, radius } from "../styles/shared";
import QuotaCard from "../components/QuotaCard";

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

// ── Configuração das IAs (Nomes em Português) ──
const AI_ENGINES_CONFIG: Record<
  string,
  {
    icon: React.ReactNode;
    color: string;
    description: string;
    displayName: string;
  }
> = {
  DrawingAnalyzerAI: {
    icon: <FaRoute />,
    color: "#00D4FF",
    displayName: "Analisador de Desenhos",
    description:
      "Analisa desenhos CAD, extrai componentes, valida normas técnicas",
  },
  PipeOptimizerAI: {
    icon: <FaRoute />,
    color: "#00FF94",
    displayName: "Otimizador de Rotas",
    description: "Otimiza rotas de tubulação, calcula materiais e custos",
  },
  ConflictDetectorAI: {
    icon: <FaExclamationTriangle />,
    color: "#FF6B6B",
    displayName: "Detector de Conflitos",
    description: "Detecta colisões e interferências entre componentes",
  },
  CostEstimatorAI: {
    icon: <FaDollarSign />,
    color: "#FFD93D",
    displayName: "Estimador de Custos",
    description: "Estima custos, gera MTO e relatórios financeiros",
  },
  QualityInspectorAI: {
    icon: <FaCheckCircle />,
    color: "#6BCB77",
    displayName: "Inspetor de Qualidade",
    description: "Inspeção automática de qualidade e conformidade",
  },
  DocumentGeneratorAI: {
    icon: <FaFileAlt />,
    color: "#9B59B6",
    displayName: "Gerador de Documentos",
    description: "Gera documentação técnica automaticamente",
  },
  MaintenancePredictorAI: {
    icon: <FaTools />,
    color: "#FF8C00",
    displayName: "Preditor de Manutenção",
    description: "Predição de manutenção baseada em padrões",
  },
  AssistantChatbotAI: {
    icon: <FaComments />,
    color: "#00B4D8",
    displayName: "Assistente Técnico",
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
    displayName: engine.name.replace("AI", ""),
  };

  return (
    <div
      onClick={onSelect}
      style={{
        background: isSelected
          ? `linear-gradient(135deg, ${config.color}20 0%, ${theme.bgSecondary} 100%)`
          : theme.bgSecondary,
        border: `2px solid ${isSelected ? config.color : theme.border}`,
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
            {config.displayName}
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
        border: `1px solid ${theme.border}`,
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
            border: `1px solid ${theme.border}`,
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
          border: `1px solid ${theme.border}`,
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
        border: `1px solid ${theme.border}`,
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
          {config?.displayName || selectedEngine.name.replace("AI", "")}
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
                border: `1px solid ${theme.border}`,
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

// ── Panel de Estimativa de Custos ──
const CostEstimatorPanel: React.FC<{
  theme: ReturnType<typeof useTheme>["theme"];
  onSubmit: (data: any) => Promise<any>;
}> = ({ theme, onSubmit }) => {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [formData, setFormData] = useState({
    project_name: "",
    materials: "Aço Carbono ASTM A106",
    labor_hours: 100,
    complexity: "medium",
  });

  const handleSubmit = async () => {
    setLoading(true);
    try {
      const res = await onSubmit(formData);
      setResult(res);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        background: theme.bgSecondary,
        borderRadius: radius.lg,
        border: `1px solid ${theme.border}`,
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
            width: 36,
            height: 36,
            borderRadius: radius.md,
            background: "#FFD93D20",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: "#FFD93D",
          }}
        >
          <FaDollarSign />
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
            Estimativa de Custos
          </h3>
          <span style={{ color: theme.textSecondary, fontSize: 11 }}>
            CostEstimator AI
          </span>
        </div>
      </div>

      <div
        style={{ display: "flex", flexDirection: "column", gap: spacing.sm }}
      >
        <input
          placeholder="Nome do Projeto"
          value={formData.project_name}
          onChange={(e) =>
            setFormData({ ...formData, project_name: e.target.value })
          }
          style={{
            padding: spacing.sm,
            borderRadius: radius.md,
            border: `1px solid ${theme.border}`,
            background: theme.bgPrimary,
            color: theme.textPrimary,
            outline: "none",
          }}
        />
        <select
          value={formData.materials}
          onChange={(e) =>
            setFormData({ ...formData, materials: e.target.value })
          }
          style={{
            padding: spacing.sm,
            borderRadius: radius.md,
            border: `1px solid ${theme.border}`,
            background: theme.bgPrimary,
            color: theme.textPrimary,
            outline: "none",
          }}
        >
          <option value="Aço Carbono ASTM A106">Aço Carbono ASTM A106</option>
          <option value="Aço Inox 316L">Aço Inox 316L</option>
          <option value="Inconel 625">Inconel 625</option>
          <option value="Hastelloy C-276">Hastelloy C-276</option>
        </select>
        <div style={{ display: "flex", gap: spacing.sm }}>
          <input
            type="number"
            placeholder="Horas de trabalho"
            value={formData.labor_hours}
            onChange={(e) =>
              setFormData({ ...formData, labor_hours: Number(e.target.value) })
            }
            style={{
              flex: 1,
              padding: spacing.sm,
              borderRadius: radius.md,
              border: `1px solid ${theme.border}`,
              background: theme.bgPrimary,
              color: theme.textPrimary,
              outline: "none",
            }}
          />
          <select
            value={formData.complexity}
            onChange={(e) =>
              setFormData({ ...formData, complexity: e.target.value })
            }
            style={{
              flex: 1,
              padding: spacing.sm,
              borderRadius: radius.md,
              border: `1px solid ${theme.border}`,
              background: theme.bgPrimary,
              color: theme.textPrimary,
              outline: "none",
            }}
          >
            <option value="low">Baixa complexidade</option>
            <option value="medium">Média complexidade</option>
            <option value="high">Alta complexidade</option>
          </select>
        </div>
        <button
          onClick={handleSubmit}
          disabled={loading || !formData.project_name}
          style={{
            padding: spacing.sm,
            borderRadius: radius.md,
            border: "none",
            background: loading ? theme.textSecondary : "#FFD93D",
            color: "#000",
            cursor: loading ? "not-allowed" : "pointer",
            fontWeight: 600,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: spacing.xs,
          }}
        >
          {loading ? (
            <span style={{ animation: "spin 1s linear infinite" }}>
              <FaSync />
            </span>
          ) : (
            <FaPlay />
          )}{" "}
          {loading ? "Calculando..." : "Estimar Custo"}
        </button>
      </div>

      {result && (
        <div
          style={{
            marginTop: spacing.md,
            padding: spacing.sm,
            borderRadius: radius.md,
            background: theme.bgPrimary,
          }}
        >
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              marginBottom: spacing.xs,
            }}
          >
            <span style={{ color: theme.textSecondary, fontSize: 11 }}>
              RESULTADO
            </span>
            <span style={{ color: "#00FF94", fontSize: 11 }}>✓ Estimado</span>
          </div>
          <div
            style={{ color: theme.textPrimary, fontSize: 20, fontWeight: 700 }}
          >
            R${" "}
            {result?.data?.total_cost?.toLocaleString("pt-BR") ||
              result?.total_cost?.toLocaleString("pt-BR") ||
              "---"}
          </div>
          <div
            style={{
              color: theme.textSecondary,
              fontSize: 11,
              marginTop: spacing.xs,
            }}
          >
            Materiais: R${" "}
            {result?.data?.material_cost?.toLocaleString("pt-BR") || "---"} |
            Mão de obra: R${" "}
            {result?.data?.labor_cost?.toLocaleString("pt-BR") || "---"}
          </div>
        </div>
      )}
    </div>
  );
};

// ── Panel de Predição de Manutenção ──
const MaintenancePredictorPanel: React.FC<{
  theme: ReturnType<typeof useTheme>["theme"];
  onSubmit: (data: any) => Promise<any>;
}> = ({ theme, onSubmit }) => {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [formData, setFormData] = useState({
    equipment_type: "pipe_segment",
    operating_hours: 8760,
    last_maintenance: "2024-01-15",
    pressure_bar: 10,
    temperature_c: 150,
  });

  const handleSubmit = async () => {
    setLoading(true);
    try {
      const res = await onSubmit(formData);
      setResult(res);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        background: theme.bgSecondary,
        borderRadius: radius.lg,
        border: `1px solid ${theme.border}`,
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
            width: 36,
            height: 36,
            borderRadius: radius.md,
            background: "#FF8C0020",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: "#FF8C00",
          }}
        >
          <FaWrench />
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
            Predição de Manutenção
          </h3>
          <span style={{ color: theme.textSecondary, fontSize: 11 }}>
            MaintenancePredictor AI
          </span>
        </div>
      </div>

      <div
        style={{ display: "flex", flexDirection: "column", gap: spacing.sm }}
      >
        <select
          value={formData.equipment_type}
          onChange={(e) =>
            setFormData({ ...formData, equipment_type: e.target.value })
          }
          style={{
            padding: spacing.sm,
            borderRadius: radius.md,
            border: `1px solid ${theme.border}`,
            background: theme.bgPrimary,
            color: theme.textPrimary,
            outline: "none",
          }}
        >
          <option value="pipe_segment">Segmento de Tubulação</option>
          <option value="valve">Válvula</option>
          <option value="pump">Bomba</option>
          <option value="heat_exchanger">Trocador de Calor</option>
          <option value="vessel">Vaso de Pressão</option>
        </select>
        <div style={{ display: "flex", gap: spacing.sm }}>
          <input
            type="number"
            placeholder="Horas de operação"
            value={formData.operating_hours}
            onChange={(e) =>
              setFormData({
                ...formData,
                operating_hours: Number(e.target.value),
              })
            }
            style={{
              flex: 1,
              padding: spacing.sm,
              borderRadius: radius.md,
              border: `1px solid ${theme.border}`,
              background: theme.bgPrimary,
              color: theme.textPrimary,
              outline: "none",
            }}
          />
          <input
            type="date"
            value={formData.last_maintenance}
            onChange={(e) =>
              setFormData({ ...formData, last_maintenance: e.target.value })
            }
            style={{
              flex: 1,
              padding: spacing.sm,
              borderRadius: radius.md,
              border: `1px solid ${theme.border}`,
              background: theme.bgPrimary,
              color: theme.textPrimary,
              outline: "none",
            }}
          />
        </div>
        <div style={{ display: "flex", gap: spacing.sm }}>
          <input
            type="number"
            placeholder="Pressão (bar)"
            value={formData.pressure_bar}
            onChange={(e) =>
              setFormData({ ...formData, pressure_bar: Number(e.target.value) })
            }
            style={{
              flex: 1,
              padding: spacing.sm,
              borderRadius: radius.md,
              border: `1px solid ${theme.border}`,
              background: theme.bgPrimary,
              color: theme.textPrimary,
              outline: "none",
            }}
          />
          <input
            type="number"
            placeholder="Temperatura (°C)"
            value={formData.temperature_c}
            onChange={(e) =>
              setFormData({
                ...formData,
                temperature_c: Number(e.target.value),
              })
            }
            style={{
              flex: 1,
              padding: spacing.sm,
              borderRadius: radius.md,
              border: `1px solid ${theme.border}`,
              background: theme.bgPrimary,
              color: theme.textPrimary,
              outline: "none",
            }}
          />
        </div>
        <button
          onClick={handleSubmit}
          disabled={loading}
          style={{
            padding: spacing.sm,
            borderRadius: radius.md,
            border: "none",
            background: loading ? theme.textSecondary : "#FF8C00",
            color: "#fff",
            cursor: loading ? "not-allowed" : "pointer",
            fontWeight: 600,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: spacing.xs,
          }}
        >
          {loading ? (
            <span style={{ animation: "spin 1s linear infinite" }}>
              <FaSync />
            </span>
          ) : (
            <FaCalendarCheck />
          )}{" "}
          {loading ? "Analisando..." : "Prever Manutenção"}
        </button>
      </div>

      {result && (
        <div
          style={{
            marginTop: spacing.md,
            padding: spacing.sm,
            borderRadius: radius.md,
            background: theme.bgPrimary,
          }}
        >
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              marginBottom: spacing.xs,
            }}
          >
            <span style={{ color: theme.textSecondary, fontSize: 11 }}>
              PREDIÇÃO
            </span>
            <span
              style={{
                color:
                  (result?.data?.risk_level || result?.risk_level) === "high"
                    ? "#FF6B6B"
                    : (result?.data?.risk_level || result?.risk_level) ===
                        "medium"
                      ? "#FFD93D"
                      : "#00FF94",
                fontSize: 11,
              }}
            >
              Risco:{" "}
              {(
                result?.data?.risk_level ||
                result?.risk_level ||
                "baixo"
              ).toUpperCase()}
            </span>
          </div>
          <div
            style={{ color: theme.textPrimary, fontSize: 14, fontWeight: 600 }}
          >
            Próxima manutenção:{" "}
            {result?.data?.next_maintenance ||
              result?.next_maintenance ||
              "---"}
          </div>
          <div
            style={{
              color: theme.textSecondary,
              fontSize: 11,
              marginTop: spacing.xs,
            }}
          >
            Vida útil restante:{" "}
            {result?.data?.remaining_life_percent ||
              result?.remaining_life_percent ||
              "---"}
            % | Confiança:{" "}
            {result?.data?.confidence || result?.confidence || "---"}%
          </div>
        </div>
      )}
    </div>
  );
};

// ── Panel de Geração de Documentos ──
const DocumentGeneratorPanel: React.FC<{
  theme: ReturnType<typeof useTheme>["theme"];
  onSubmit: (data: any) => Promise<any>;
}> = ({ theme, onSubmit }) => {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [formData, setFormData] = useState({
    document_type: "technical_report",
    project_name: "",
    include_sections: ["summary", "specifications", "materials", "costs"],
    language: "pt-BR",
  });

  const handleSubmit = async () => {
    setLoading(true);
    try {
      const res = await onSubmit(formData);
      setResult(res);
    } finally {
      setLoading(false);
    }
  };

  const downloadDocument = () => {
    const content =
      result?.data?.content || result?.content || "Documento gerado";
    const blob = new Blob([content], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${formData.project_name || "documento"}_${formData.document_type}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div
      style={{
        background: theme.bgSecondary,
        borderRadius: radius.lg,
        border: `1px solid ${theme.border}`,
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
            width: 36,
            height: 36,
            borderRadius: radius.md,
            background: "#9B59B620",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: "#9B59B6",
          }}
        >
          <FaFileAlt />
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
            Geração de Documentos
          </h3>
          <span style={{ color: theme.textSecondary, fontSize: 11 }}>
            DocumentGenerator AI
          </span>
        </div>
      </div>

      <div
        style={{ display: "flex", flexDirection: "column", gap: spacing.sm }}
      >
        <input
          placeholder="Nome do Projeto"
          value={formData.project_name}
          onChange={(e) =>
            setFormData({ ...formData, project_name: e.target.value })
          }
          style={{
            padding: spacing.sm,
            borderRadius: radius.md,
            border: `1px solid ${theme.border}`,
            background: theme.bgPrimary,
            color: theme.textPrimary,
            outline: "none",
          }}
        />
        <select
          value={formData.document_type}
          onChange={(e) =>
            setFormData({ ...formData, document_type: e.target.value })
          }
          style={{
            padding: spacing.sm,
            borderRadius: radius.md,
            border: `1px solid ${theme.border}`,
            background: theme.bgPrimary,
            color: theme.textPrimary,
            outline: "none",
          }}
        >
          <option value="technical_report">Relatório Técnico</option>
          <option value="material_list">Lista de Materiais (BOM)</option>
          <option value="specification">Especificação Técnica</option>
          <option value="maintenance_manual">Manual de Manutenção</option>
          <option value="quality_report">Relatório de Qualidade</option>
        </select>
        <div style={{ display: "flex", flexWrap: "wrap", gap: spacing.xs }}>
          {[
            "summary",
            "specifications",
            "materials",
            "costs",
            "drawings",
            "appendix",
          ].map((section) => (
            <label
              key={section}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 4,
                padding: "4px 8px",
                borderRadius: radius.sm,
                background: theme.bgPrimary,
                cursor: "pointer",
                fontSize: 11,
                color: theme.textSecondary,
                border: formData.include_sections.includes(section)
                  ? `1px solid #9B59B6`
                  : `1px solid ${theme.border}`,
              }}
            >
              <input
                type="checkbox"
                checked={formData.include_sections.includes(section)}
                onChange={(e) => {
                  if (e.target.checked) {
                    setFormData({
                      ...formData,
                      include_sections: [...formData.include_sections, section],
                    });
                  } else {
                    setFormData({
                      ...formData,
                      include_sections: formData.include_sections.filter(
                        (s) => s !== section,
                      ),
                    });
                  }
                }}
                style={{ display: "none" }}
              />
              <span
                style={{
                  color: formData.include_sections.includes(section)
                    ? "#9B59B6"
                    : theme.textSecondary,
                }}
              >
                {section === "summary"
                  ? "Resumo"
                  : section === "specifications"
                    ? "Especificações"
                    : section === "materials"
                      ? "Materiais"
                      : section === "costs"
                        ? "Custos"
                        : section === "drawings"
                          ? "Desenhos"
                          : "Anexos"}
              </span>
            </label>
          ))}
        </div>
        <button
          onClick={handleSubmit}
          disabled={loading || !formData.project_name}
          style={{
            padding: spacing.sm,
            borderRadius: radius.md,
            border: "none",
            background: loading ? theme.textSecondary : "#9B59B6",
            color: "#fff",
            cursor: loading ? "not-allowed" : "pointer",
            fontWeight: 600,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: spacing.xs,
          }}
        >
          {loading ? (
            <span style={{ animation: "spin 1s linear infinite" }}>
              <FaSync />
            </span>
          ) : (
            <FaClipboardList />
          )}{" "}
          {loading ? "Gerando..." : "Gerar Documento"}
        </button>
      </div>

      {result && (
        <div
          style={{
            marginTop: spacing.md,
            padding: spacing.sm,
            borderRadius: radius.md,
            background: theme.bgPrimary,
          }}
        >
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              marginBottom: spacing.xs,
            }}
          >
            <span style={{ color: theme.textSecondary, fontSize: 11 }}>
              DOCUMENTO GERADO
            </span>
            <button
              onClick={downloadDocument}
              style={{
                background: "transparent",
                border: "none",
                color: "#00D4FF",
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                gap: 4,
                fontSize: 11,
              }}
            >
              <FaDownload size={10} /> Baixar
            </button>
          </div>
          <div
            style={{
              color: theme.textPrimary,
              fontSize: 12,
              maxHeight: 100,
              overflow: "auto",
            }}
          >
            {(
              result?.data?.content ||
              result?.content ||
              "Documento processado com sucesso"
            ).slice(0, 300)}
            ...
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
  const [activeTab, setActiveTab] = useState<"engines" | "tools">("tools");
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

  // Handler para estimativa de custos
  const handleCostEstimate = useCallback(async (data: any) => {
    const token = localStorage.getItem("token");
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };
    if (token) headers["Authorization"] = `Bearer ${token}`;
    const res = await fetch(`${API_BASE_URL}/api/ai/estimate/costs`, {
      method: "POST",
      headers,
      body: JSON.stringify({ data, options: {} }),
    });
    return res.json();
  }, []);

  // Handler para predição de manutenção
  const handleMaintenancePredict = useCallback(async (data: any) => {
    const token = localStorage.getItem("token");
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };
    if (token) headers["Authorization"] = `Bearer ${token}`;
    const res = await fetch(`${API_BASE_URL}/api/ai/estimate/maintenance`, {
      method: "POST",
      headers,
      body: JSON.stringify({ data, options: {} }),
    });
    return res.json();
  }, []);

  // Handler para geração de documentos
  const handleDocumentGenerate = useCallback(async (data: any) => {
    const token = localStorage.getItem("token");
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };
    if (token) headers["Authorization"] = `Bearer ${token}`;
    const res = await fetch(`${API_BASE_URL}/api/ai/generate/document`, {
      method: "POST",
      headers,
      body: JSON.stringify({ data, options: {} }),
    });
    return res.json();
  }, []);

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

        {/* Quota Usage Card */}
        <div style={{ marginBottom: spacing.lg }}>
          <QuotaCard />
        </div>

        {/* Tabs de navegação */}
        <div
          style={{
            display: "flex",
            gap: spacing.sm,
            marginBottom: spacing.lg,
            borderBottom: `1px solid ${theme.border}`,
            paddingBottom: spacing.sm,
          }}
        >
          <button
            onClick={() => setActiveTab("tools")}
            style={{
              padding: `${spacing.sm} ${spacing.md}`,
              borderRadius: `${radius.md} ${radius.md} 0 0`,
              border: "none",
              background: activeTab === "tools" ? "#00D4FF20" : "transparent",
              color: activeTab === "tools" ? "#00D4FF" : theme.textSecondary,
              cursor: "pointer",
              fontWeight: 600,
              display: "flex",
              alignItems: "center",
              gap: spacing.xs,
              borderBottom:
                activeTab === "tools"
                  ? "2px solid #00D4FF"
                  : "2px solid transparent",
            }}
          >
            <FaTools /> Ferramentas IA
          </button>
          <button
            onClick={() => setActiveTab("engines")}
            style={{
              padding: `${spacing.sm} ${spacing.md}`,
              borderRadius: `${radius.md} ${radius.md} 0 0`,
              border: "none",
              background: activeTab === "engines" ? "#00D4FF20" : "transparent",
              color: activeTab === "engines" ? "#00D4FF" : theme.textSecondary,
              cursor: "pointer",
              fontWeight: 600,
              display: "flex",
              alignItems: "center",
              gap: spacing.xs,
              borderBottom:
                activeTab === "engines"
                  ? "2px solid #00D4FF"
                  : "2px solid transparent",
            }}
          >
            <FaRobot /> Engines ({engines.length})
          </button>
        </div>

        {/* Tab: Ferramentas IA (Painéis diretos) */}
        {activeTab === "tools" && (
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: spacing.lg,
            }}
          >
            <div
              style={{
                display: "flex",
                flexDirection: "column",
                gap: spacing.lg,
              }}
            >
              <CostEstimatorPanel theme={theme} onSubmit={handleCostEstimate} />
              <MaintenancePredictorPanel
                theme={theme}
                onSubmit={handleMaintenancePredict}
              />
            </div>
            <div
              style={{
                display: "flex",
                flexDirection: "column",
                gap: spacing.lg,
              }}
            >
              <DocumentGeneratorPanel
                theme={theme}
                onSubmit={handleDocumentGenerate}
              />
              <ChatInterface
                messages={chatMessages}
                onSend={handleSendChat}
                loading={loading}
                theme={theme}
              />
            </div>
          </div>
        )}

        {/* Tab: Engines Grid */}
        {activeTab === "engines" && (
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
        )}
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
      border: `1px solid ${theme.border}`,
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
