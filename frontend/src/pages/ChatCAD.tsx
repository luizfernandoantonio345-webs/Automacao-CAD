/**
 * ENGENHARIA CAD – ChatCAD v2.0
 * Interface de IA estilo ChatGPT com:
 * - Markdown rendering nativo
 * - Efeito de digitação (streaming)
 * - Demo com limite de consultas
 * - Sugestões inteligentes
 * - Design moderno imersivo
 */
import React, { useState, useRef, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import {
  FaPaperPlane,
  FaRobot,
  FaUser,
  FaPlay,
  FaCheckCircle,
  FaTimesCircle,
  FaCog,
  FaTrash,
  FaCrown,
  FaCopy,
  FaCheck,
  FaBolt,
} from "react-icons/fa";
import { api as apiClient } from "../services/api";
import { useTheme } from "../context/ThemeContext";
import { useToast } from "../context/ToastContext";
import { useLicense } from "../context/LicenseContext";

// ─────────────────── Types ───────────────────
interface ChatMessage {
  id: number;
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: Date;
  tipo?: string;
  plano?: any[];
  execucao?: any;
  sugestoes?: string[];
  loading?: boolean;
  streaming?: boolean;
  copiedId?: boolean;
}

// ─────────────────── Markdown renderer ───────────────────
function renderMarkdown(text: string): React.ReactNode[] {
  const lines = text.split("\n");
  const result: React.ReactNode[] = [];
  let listBuffer: string[] = [];
  let codeBuffer: string[] = [];
  let inCode = false;
  let inCodeLang = "";

  const flushList = (key: string) => {
    if (listBuffer.length > 0) {
      result.push(
        <ul key={`ul-${key}`} style={{ margin: "8px 0", paddingLeft: "20px" }}>
          {listBuffer.map((li, i) => (
            <li key={i} style={{ marginBottom: "4px", lineHeight: 1.6 }}>
              {parseLine(li)}
            </li>
          ))}
        </ul>,
      );
      listBuffer = [];
    }
  };

  const flushCode = (key: string) => {
    if (codeBuffer.length > 0) {
      result.push(
        <div
          key={`code-${key}`}
          style={{ position: "relative", margin: "12px 0" }}
        >
          {inCodeLang && (
            <div
              style={{
                background: "#1e293b",
                borderRadius: "8px 8px 0 0",
                padding: "4px 12px",
                fontSize: "11px",
                color: "#8899aa",
                borderBottom: "1px solid #334155",
              }}
            >
              {inCodeLang}
            </div>
          )}
          <pre
            style={{
              background: "#0d1117",
              border: "1px solid #1e293b",
              borderRadius: inCodeLang ? "0 0 8px 8px" : "8px",
              padding: "14px",
              margin: 0,
              overflowX: "auto",
              fontSize: "13px",
              lineHeight: 1.6,
              color: "#e2e8f0",
            }}
          >
            <code>{codeBuffer.join("\n")}</code>
          </pre>
        </div>,
      );
      codeBuffer = [];
      inCode = false;
      inCodeLang = "";
    }
  };

  const parseLine = (line: string): React.ReactNode => {
    const parts = line.split(/(\*\*[^*]+\*\*|`[^`]+`|\*[^*]+\*)/g);
    return (
      <>
        {parts.map((part, i) => {
          if (part.startsWith("**") && part.endsWith("**"))
            return <strong key={i}>{part.slice(2, -2)}</strong>;
          if (part.startsWith("`") && part.endsWith("`"))
            return (
              <code
                key={i}
                style={{
                  background: "rgba(255,255,255,0.08)",
                  borderRadius: "4px",
                  padding: "1px 6px",
                  fontSize: "13px",
                  fontFamily: "monospace",
                }}
              >
                {part.slice(1, -1)}
              </code>
            );
          if (part.startsWith("*") && part.endsWith("*"))
            return <em key={i}>{part.slice(1, -1)}</em>;
          return <React.Fragment key={i}>{part}</React.Fragment>;
        })}
      </>
    );
  };

  lines.forEach((line, idx) => {
    const key = String(idx);
    if (line.startsWith("```")) {
      if (inCode) {
        flushCode(key);
      } else {
        flushList(key);
        inCode = true;
        inCodeLang = line.slice(3).trim();
      }
      return;
    }
    if (inCode) {
      codeBuffer.push(line);
      return;
    }
    if (line.startsWith("### ")) {
      flushList(key);
      result.push(
        <h3
          key={key}
          style={{
            color: "#00A1FF",
            fontSize: "15px",
            fontWeight: 700,
            margin: "16px 0 6px",
          }}
        >
          {parseLine(line.slice(4))}
        </h3>,
      );
      return;
    }
    if (line.startsWith("## ")) {
      flushList(key);
      result.push(
        <h2
          key={key}
          style={{
            color: "#e2e8f0",
            fontSize: "17px",
            fontWeight: 700,
            margin: "18px 0 8px",
          }}
        >
          {parseLine(line.slice(3))}
        </h2>,
      );
      return;
    }
    if (line.startsWith("# ")) {
      flushList(key);
      result.push(
        <h1
          key={key}
          style={{
            color: "#fff",
            fontSize: "19px",
            fontWeight: 800,
            margin: "20px 0 10px",
          }}
        >
          {parseLine(line.slice(2))}
        </h1>,
      );
      return;
    }
    if (line === "---") {
      flushList(key);
      result.push(
        <hr
          key={key}
          style={{
            border: "none",
            borderTop: "1px solid #1e293b",
            margin: "14px 0",
          }}
        />,
      );
      return;
    }
    if (line.startsWith("> ")) {
      flushList(key);
      result.push(
        <blockquote
          key={key}
          style={{
            borderLeft: "3px solid #00A1FF",
            paddingLeft: "12px",
            margin: "8px 0",
            color: "#8899aa",
            fontStyle: "italic",
          }}
        >
          {parseLine(line.slice(2))}
        </blockquote>,
      );
      return;
    }
    if (line.match(/^[-*•]\s/)) {
      listBuffer.push(line.replace(/^[-*•]\s/, ""));
      return;
    }
    if (line.match(/^\d+\.\s/)) {
      flushList(key);
      result.push(
        <div
          key={key}
          style={{ display: "flex", gap: "8px", marginBottom: "4px" }}
        >
          <span
            style={{
              color: "#00A1FF",
              fontWeight: 700,
              minWidth: "20px",
              flexShrink: 0,
            }}
          >
            {line.match(/^(\d+)\./)?.[1]}.
          </span>
          <span>{parseLine(line.replace(/^\d+\.\s/, ""))}</span>
        </div>,
      );
      return;
    }
    if (line.trim() === "") {
      flushList(key);
      result.push(<div key={key} style={{ height: "8px" }} />);
      return;
    }
    flushList(key);
    result.push(
      <p key={key} style={{ margin: "4px 0", lineHeight: 1.7 }}>
        {parseLine(line)}
      </p>,
    );
  });
  flushList("end");
  flushCode("end");
  return result;
}

// ─────────────────── Typing effect ───────────────────
function TypingContent({ text, active }: { text: string; active: boolean }) {
  const [displayed, setDisplayed] = useState(active ? "" : text);
  const indexRef = useRef(active ? 0 : text.length);

  useEffect(() => {
    if (!active) {
      setDisplayed(text);
      return;
    }
    setDisplayed("");
    indexRef.current = 0;
    const iv = setInterval(() => {
      if (indexRef.current >= text.length) {
        clearInterval(iv);
        return;
      }
      const chunk = text.slice(indexRef.current, indexRef.current + 10);
      setDisplayed((p) => p + chunk);
      indexRef.current += chunk.length;
    }, 16);
    return () => clearInterval(iv);
  }, [text, active]);

  return <>{renderMarkdown(displayed)}</>;
}

// ─────────────────── Starter prompts ───────────────────
const STARTER_PROMPTS = [
  {
    icon: "🔧",
    text: "Criar flange DN150 #150 com furações padrão ASME B16.5",
    cat: "Piping",
  },
  {
    icon: "📐",
    text: "Gerar isométrico de linha de vapor 6' pressão 150 PSI",
    cat: "Isométrico",
  },
  {
    icon: "⚙️",
    text: "Simular corte plasma chapa 12mm aço carbono nesting automático",
    cat: "CNC/Plasma",
  },
  {
    icon: "🏭",
    text: "Validar P&ID da linha 100-HN-0042 norma Petrobras N-133",
    cat: "Validação",
  },
  {
    icon: "💰",
    text: "Estimar custo fabricação tanque vertical 5000L AISI 316L",
    cat: "Estimativa",
  },
  {
    icon: "🔍",
    text: "Listar componentes faltantes nos isométricos ISO-001 a ISO-012",
    cat: "Análise",
  },
];

// ─────────────────── Main Component ───────────────────
const STORAGE_KEY = "chatcad_history";

const ChatCAD: React.FC = () => {
  const { addToast, handleApiError } = useToast();
  const { license, consumeAiQuery, triggerUpgrade } = useLicense();
  const navigate = useNavigate();

  // Load messages from localStorage on mount
  const [messages, setMessages] = useState<ChatMessage[]>(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) {
        const parsed = JSON.parse(saved);
        return parsed.map((m: any) => ({
          ...m,
          timestamp: new Date(m.timestamp),
        }));
      }
    } catch (e) {
      console.warn("Failed to load chat history:", e);
    }
    return [];
  });
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [autoExecute, setAutoExecute] = useState(true);
  const chatEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const nextId = useRef(1);

  // Save messages to localStorage whenever they change
  useEffect(() => {
    if (messages.length > 0) {
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(messages.slice(-50))); // Keep last 50
      } catch (e) {
        console.warn("Failed to save chat history:", e);
      }
    }
  }, [messages]);

  // Initialize nextId from loaded messages
  useEffect(() => {
    if (messages.length > 0) {
      const maxId = Math.max(...messages.map((m) => m.id));
      nextId.current = maxId + 1;
    }
  }, []);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const addMsg = useCallback(
    (
      role: ChatMessage["role"],
      content: string,
      extra?: Partial<ChatMessage>,
    ): number => {
      const id = nextId.current++;
      setMessages((prev) => [
        ...prev,
        { id, role, content, timestamp: new Date(), ...extra },
      ]);
      return id;
    },
    [],
  );

  const updateMsg = useCallback((id: number, updates: Partial<ChatMessage>) => {
    setMessages((prev) =>
      prev.map((m) => (m.id === id ? { ...m, ...updates } : m)),
    );
  }, []);

  const handleSend = async () => {
    const texto = input.trim();
    if (!texto || loading) return;
    if (!consumeAiQuery()) return;

    setInput("");
    // Reset textarea height
    if (inputRef.current) {
      inputRef.current.style.height = "auto";
    }
    addMsg("user", texto);
    setLoading(true);
    const assistantId = addMsg("assistant", "", { loading: true });

    try {
      const endpoint = autoExecute
        ? "/api/chatcad/chat"
        : "/api/chatcad/interpret";
      const res = await apiClient.post(endpoint, { texto });
      const data = res.data;

      let content = "";
      let plano: any[] | undefined;
      let execucao: any | undefined;
      let sugestoes: string[] | undefined;

      if (data.resposta?.response) content = data.resposta.response;
      else if (data.tipo === "desconhecido") {
        content =
          "Não entendi esse comando. Reformule ou use uma das sugestões abaixo.";
        sugestoes = data.interpretacao?.sugestoes;
      } else if (data.resposta) {
        content =
          typeof data.resposta === "string"
            ? data.resposta
            : JSON.stringify(data.resposta, null, 2);
      }

      if (data.interpretacao?.correcao) {
        content = `> 📝 *Correção:* "${data.interpretacao.correcao}"\n\n${content}`;
      }

      if (
        !autoExecute &&
        data.tipo !== "pergunta" &&
        data.tipo !== "desconhecido"
      ) {
        plano = data.dados?.plano || data.plano;
        if (plano?.length) {
          content = `**Plano de execução** (${plano.length} etapas):\n\n`;
          plano.forEach((a: any, i: number) => {
            content += `${i + 1}. ${a.descricao || a.acao}\n`;
          });
          content += `\n*Clique em **Executar** para rodar no AutoCAD.*`;
        }
      }

      if (data.execucao) {
        execucao = data.execucao;
        plano = data.interpretacao?.dados?.plano;
      }
      sugestoes = sugestoes || data.interpretacao?.sugestoes;

      updateMsg(assistantId, {
        content: content || "Comando processado com sucesso.",
        loading: false,
        streaming: true,
        tipo: data.tipo,
        plano,
        execucao,
        sugestoes,
      });

      if (data.executado)
        addToast(
          data.execucao?.falhas === 0 ? "success" : "warning",
          "ChatCAD",
          data.resposta?.response || "Executado",
        );
    } catch (err: any) {
      updateMsg(assistantId, {
        content: !err?.response
          ? "❌ Servidor indisponível. Verifique sua conexão e tente novamente."
          : `❌ Erro ao processar (${err?.response?.status}). Tente novamente.`,
        loading: false,
      });
      if (err?.response) handleApiError(err);
    } finally {
      setLoading(false);
    }
  };

  const handleExecutePlan = async (plano: any[]) => {
    if (!consumeAiQuery()) return;
    setLoading(true);
    const execId = addMsg("assistant", "", { loading: true });

    try {
      const res = await apiClient.post("/api/chatcad/execute", { plano });
      const data = res.data;
      const ok = data.executadas || 0,
        total = data.total || 0,
        falhas = data.falhas || 0;
      updateMsg(execId, {
        content:
          falhas === 0
            ? `✅ Plano executado! **${ok}/${total}** operações concluídas.`
            : `⚠️ Execução parcial: **${ok}/${total}** OK, **${falhas}** falhas.`,
        loading: false,
        streaming: true,
        execucao: data,
      });
      addToast(
        falhas === 0 ? "success" : "warning",
        "Execução",
        `${ok}/${total} concluídas`,
      );
    } catch {
      updateMsg(execId, {
        content: "❌ Erro ao executar plano no AutoCAD.",
        loading: false,
      });
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleCopy = (id: number, text: string) => {
    navigator.clipboard.writeText(text).then(() => {
      updateMsg(id, { copiedId: true });
      setTimeout(() => updateMsg(id, { copiedId: false }), 2500);
    });
  };

  const remaining = license.aiQueriesLimit - license.aiQueriesUsed;
  const isLow = license.isDemo && remaining / license.aiQueriesLimit <= 0.3;

  return (
    <div
      style={{
        height: "100vh",
        display: "flex",
        flexDirection: "column",
        background: "#0d1117",
        color: "#e2e8f0",
        fontFamily: "'Inter','Segoe UI',Roboto,sans-serif",
      }}
    >
      {/* Header */}
      <div
        style={{
          padding: "14px 24px",
          borderBottom: "1px solid #1e293b",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          flexShrink: 0,
          background: "rgba(13,17,23,0.97)",
          backdropFilter: "blur(12px)",
          position: "sticky",
          top: 0,
          zIndex: 50,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <div
            style={{
              width: "36px",
              height: "36px",
              borderRadius: "10px",
              background: "linear-gradient(135deg, #00A1FF, #0077CC)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "#FFF",
              fontSize: "16px",
              boxShadow: "0 4px 16px rgba(0,161,255,0.3)",
            }}
          >
            <FaRobot />
          </div>
          <div>
            <h1 style={{ margin: 0, fontSize: "17px", fontWeight: 800 }}>
              Chat<span style={{ color: "#00A1FF" }}>CAD</span>
            </h1>
            <p style={{ margin: 0, fontSize: "11px", color: "#556677" }}>
              IA para AutoCAD • Linguagem Natural
            </p>
          </div>
        </div>

        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "10px",
            flexWrap: "wrap" as const,
          }}
        >
          {license.isDemo && (
            <button
              onClick={() =>
                triggerUpgrade("Faça upgrade para consultas de IA ilimitadas!")
              }
              style={{
                display: "flex",
                alignItems: "center",
                gap: "6px",
                padding: "6px 12px",
                background: isLow
                  ? "rgba(245,158,11,0.15)"
                  : "rgba(0,161,255,0.08)",
                border: `1px solid ${isLow ? "rgba(245,158,11,0.4)" : "rgba(0,161,255,0.2)"}`,
                borderRadius: "20px",
                color: isLow ? "#F59E0B" : "#8899aa",
                fontSize: "12px",
                cursor: "pointer",
                fontWeight: 600,
              }}
            >
              <FaBolt size={11} />
              {remaining}/{license.aiQueriesLimit} consultas
            </button>
          )}

          {!license.isPaid && (
            <motion.button
              whileHover={{ boxShadow: "0 4px 20px rgba(0,161,255,0.3)" }}
              onClick={() => navigate("/pricing")}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "6px",
                padding: "7px 14px",
                background: "linear-gradient(135deg, #00A1FF, #0077CC)",
                border: "none",
                borderRadius: "8px",
                color: "#FFF",
                fontSize: "12px",
                fontWeight: 700,
                cursor: "pointer",
              }}
            >
              <FaCrown size={11} /> Upgrade
            </motion.button>
          )}

          {/* Auto-execute toggle */}
          <label
            style={{
              display: "flex",
              alignItems: "center",
              gap: "6px",
              cursor: "pointer",
              color: "#8899aa",
              fontSize: "12px",
            }}
          >
            <div
              onClick={() => setAutoExecute(!autoExecute)}
              style={{
                width: "36px",
                height: "20px",
                borderRadius: "10px",
                background: autoExecute ? "#00A1FF" : "#1e293b",
                position: "relative" as const,
                cursor: "pointer",
                border: "1px solid #334155",
                transition: "background 0.2s",
              }}
            >
              <div
                style={{
                  position: "absolute" as const,
                  top: "2px",
                  left: autoExecute ? "18px" : "2px",
                  width: "14px",
                  height: "14px",
                  borderRadius: "50%",
                  background: "#FFF",
                  transition: "left 0.2s",
                }}
              />
            </div>
            Auto-executar
          </label>

          <button
            onClick={() => {
              setMessages([]);
              localStorage.removeItem(STORAGE_KEY);
              addToast("info", "ChatCAD", "Nova conversa iniciada");
            }}
            style={{
              background:
                "linear-gradient(135deg, rgba(0,161,255,0.1), rgba(139,92,246,0.1))",
              border: "1px solid rgba(0,161,255,0.3)",
              borderRadius: "8px",
              padding: "7px 12px",
              color: "#00A1FF",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: "6px",
              fontSize: "12px",
              fontWeight: 600,
              transition: "all 0.2s",
            }}
          >
            <FaTrash size={11} /> Nova conversa
          </button>
        </div>
      </div>

      {/* Messages */}
      <div style={{ flex: 1, overflowY: "auto" }}>
        {/* Empty state */}
        {messages.length === 0 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            style={{
              maxWidth: "700px",
              margin: "0 auto",
              padding: "60px 24px 20px",
            }}
          >
            <div style={{ textAlign: "center", marginBottom: "48px" }}>
              <motion.div
                animate={{ rotate: [0, 360] }}
                transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
                style={{
                  width: "64px",
                  height: "64px",
                  borderRadius: "18px",
                  background: "linear-gradient(135deg, #00A1FF, #0077CC)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  color: "#FFF",
                  fontSize: "28px",
                  margin: "0 auto 20px",
                  boxShadow: "0 8px 32px rgba(0,161,255,0.4)",
                }}
              >
                <FaRobot />
              </motion.div>
              <h2
                style={{
                  color: "#FFF",
                  fontSize: "26px",
                  fontWeight: 800,
                  margin: "0 0 10px",
                }}
              >
                Como posso ajudar?
              </h2>
              <p
                style={{
                  color: "#8899aa",
                  fontSize: "15px",
                  lineHeight: 1.6,
                  margin: 0,
                }}
              >
                Descreva o que quer criar no AutoCAD em linguagem natural.
                <br />
                Interpreto, planejo e executo para você.
              </p>
            </div>

            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))",
                gap: "12px",
              }}
            >
              {STARTER_PROMPTS.map((p, i) => (
                <motion.button
                  key={i}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.07 }}
                  whileHover={{ scale: 1.02 }}
                  onClick={() => {
                    setInput(p.text);
                    inputRef.current?.focus();
                  }}
                  style={{
                    padding: "16px",
                    background: "rgba(255,255,255,0.02)",
                    border: "1px solid #1e293b",
                    borderRadius: "12px",
                    cursor: "pointer",
                    textAlign: "left" as const,
                    transition: "all 0.15s",
                  }}
                >
                  <div style={{ fontSize: "22px", marginBottom: "8px" }}>
                    {p.icon}
                  </div>
                  <div
                    style={{
                      fontSize: "13px",
                      color: "#d4dde8",
                      lineHeight: 1.5,
                    }}
                  >
                    {p.text}
                  </div>
                  <div
                    style={{
                      marginTop: "8px",
                      fontSize: "10px",
                      color: "#00A1FF",
                      fontWeight: 600,
                      letterSpacing: "0.05em",
                    }}
                  >
                    {p.cat}
                  </div>
                </motion.button>
              ))}
            </div>
          </motion.div>
        )}

        {/* Chat messages */}
        {messages.length > 0 && (
          <div
            style={{
              maxWidth: "780px",
              margin: "0 auto",
              padding: "20px 24px",
            }}
          >
            {messages.map((msg, idx) => {
              if (msg.role === "user") {
                return (
                  <motion.div
                    key={msg.id}
                    initial={{ opacity: 0, x: 20 }}
                    animate={{ opacity: 1, x: 0 }}
                    style={{
                      display: "flex",
                      gap: "12px",
                      flexDirection: "row-reverse" as const,
                      marginBottom: "24px",
                    }}
                  >
                    <div
                      style={{
                        width: "34px",
                        height: "34px",
                        borderRadius: "10px",
                        flexShrink: 0,
                        background: "rgba(0,161,255,0.15)",
                        border: "1px solid rgba(0,161,255,0.3)",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        color: "#00A1FF",
                      }}
                    >
                      <FaUser size={14} />
                    </div>
                    <div
                      style={{
                        maxWidth: "70%",
                        padding: "12px 16px",
                        background: "rgba(0,161,255,0.1)",
                        border: "1px solid rgba(0,161,255,0.2)",
                        borderRadius: "12px 2px 12px 12px",
                      }}
                    >
                      <div
                        style={{
                          fontSize: "14px",
                          lineHeight: 1.7,
                          color: "#e2e8f0",
                          whiteSpace: "pre-wrap",
                          wordBreak: "break-word",
                        }}
                      >
                        {msg.content}
                      </div>
                      <div
                        style={{
                          fontSize: "10px",
                          color: "#556677",
                          marginTop: "6px",
                          textAlign: "right" as const,
                        }}
                      >
                        {msg.timestamp.toLocaleTimeString("pt-BR", {
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </div>
                    </div>
                  </motion.div>
                );
              }

              const isLatest = idx === messages.length - 1;
              return (
                <motion.div
                  key={msg.id}
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  style={{
                    display: "flex",
                    gap: "14px",
                    alignItems: "flex-start",
                    marginBottom: "24px",
                  }}
                >
                  <div
                    style={{
                      width: "34px",
                      height: "34px",
                      borderRadius: "10px",
                      flexShrink: 0,
                      background: "rgba(0,161,255,0.1)",
                      border: "1px solid rgba(0,161,255,0.2)",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      color: "#00A1FF",
                    }}
                  >
                    <FaRobot size={15} />
                  </div>

                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "8px",
                        marginBottom: "6px",
                      }}
                    >
                      <span
                        style={{
                          fontSize: "12px",
                          fontWeight: 700,
                          color: "#00A1FF",
                        }}
                      >
                        ChatCAD
                      </span>
                      <span style={{ fontSize: "10px", color: "#556677" }}>
                        {msg.timestamp.toLocaleTimeString("pt-BR", {
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </span>
                    </div>

                    <div
                      style={{
                        fontSize: "14px",
                        lineHeight: 1.7,
                        color: "#d4dde8",
                        wordBreak: "break-word",
                      }}
                    >
                      {msg.loading ? (
                        <div
                          style={{
                            display: "flex",
                            gap: "4px",
                            padding: "6px 0",
                          }}
                        >
                          {[0, 1, 2].map((i) => (
                            <motion.div
                              key={i}
                              animate={{
                                opacity: [0.3, 1, 0.3],
                                y: [0, -4, 0],
                              }}
                              transition={{
                                duration: 0.8,
                                repeat: Infinity,
                                delay: i * 0.15,
                              }}
                              style={{
                                width: "7px",
                                height: "7px",
                                borderRadius: "50%",
                                background: "#00A1FF",
                              }}
                            />
                          ))}
                        </div>
                      ) : (
                        <TypingContent
                          text={msg.content}
                          active={isLatest && !!msg.streaming && !loading}
                        />
                      )}
                    </div>

                    {/* Execution result */}
                    {msg.execucao && !msg.loading && (
                      <div
                        style={{
                          marginTop: "12px",
                          padding: "12px",
                          borderRadius: "10px",
                          background:
                            msg.execucao.falhas === 0
                              ? "rgba(16,185,129,0.08)"
                              : "rgba(239,68,68,0.08)",
                          border: `1px solid ${msg.execucao.falhas === 0 ? "rgba(16,185,129,0.3)" : "rgba(239,68,68,0.3)"}`,
                        }}
                      >
                        <div
                          style={{
                            display: "flex",
                            alignItems: "center",
                            gap: "8px",
                            marginBottom: "8px",
                          }}
                        >
                          {msg.execucao.falhas === 0 ? (
                            <FaCheckCircle color="#10B981" />
                          ) : (
                            <FaTimesCircle color="#EF4444" />
                          )}
                          <span
                            style={{
                              fontSize: "13px",
                              fontWeight: 600,
                              color:
                                msg.execucao.falhas === 0
                                  ? "#10B981"
                                  : "#EF4444",
                            }}
                          >
                            {msg.execucao.executadas}/{msg.execucao.total}{" "}
                            operações
                          </span>
                        </div>
                        {msg.execucao.resultados?.map((r: any, i: number) => (
                          <div
                            key={i}
                            style={{
                              fontSize: "12px",
                              color: r.success ? "#8899aa" : "#ef9999",
                              marginBottom: "4px",
                              display: "flex",
                              gap: "6px",
                            }}
                          >
                            <span>{r.success ? "✓" : "✗"}</span>
                            <span>{r.descricao || r.acao}</span>
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Pending plan */}
                    {msg.plano && !msg.execucao && !msg.loading && (
                      <button
                        onClick={() => handleExecutePlan(msg.plano!)}
                        style={{
                          marginTop: "10px",
                          padding: "8px 14px",
                          background: "rgba(0,161,255,0.15)",
                          border: "1px solid rgba(0,161,255,0.4)",
                          borderRadius: "8px",
                          color: "#00A1FF",
                          cursor: "pointer",
                          fontSize: "13px",
                          fontWeight: 600,
                          display: "flex",
                          alignItems: "center",
                          gap: "6px",
                        }}
                      >
                        <FaPlay size={11} /> Executar no AutoCAD
                      </button>
                    )}

                    {/* Suggestions */}
                    {msg.sugestoes &&
                      msg.sugestoes.length > 0 &&
                      !msg.loading && (
                        <div
                          style={{
                            display: "flex",
                            flexWrap: "wrap" as const,
                            gap: "6px",
                            marginTop: "10px",
                          }}
                        >
                          {msg.sugestoes.slice(0, 4).map((s, i) => (
                            <button
                              key={i}
                              onClick={() => {
                                setInput(s);
                                inputRef.current?.focus();
                              }}
                              style={{
                                padding: "6px 12px",
                                background: "rgba(255,255,255,0.04)",
                                border: "1px solid #1e293b",
                                borderRadius: "20px",
                                color: "#8899aa",
                                cursor: "pointer",
                                fontSize: "12px",
                              }}
                            >
                              {s}
                            </button>
                          ))}
                        </div>
                      )}

                    {/* Copy */}
                    {!msg.loading && msg.content && (
                      <button
                        onClick={() => handleCopy(msg.id, msg.content)}
                        style={{
                          marginTop: "8px",
                          padding: "4px 8px",
                          background: "transparent",
                          border: "1px solid #1e293b",
                          borderRadius: "6px",
                          color: msg.copiedId ? "#10B981" : "#556677",
                          cursor: "pointer",
                          fontSize: "11px",
                          display: "flex",
                          alignItems: "center",
                          gap: "4px",
                        }}
                      >
                        {msg.copiedId ? (
                          <FaCheck size={10} />
                        ) : (
                          <FaCopy size={10} />
                        )}
                        {msg.copiedId ? "Copiado!" : "Copiar"}
                      </button>
                    )}

                    {/* Quick actions for assistant messages */}
                    {!msg.loading && msg.role === "assistant" && msg.content && (
                      <div style={{ display: "flex", flexWrap: "wrap" as const, gap: "6px", marginTop: "10px" }}>
                        {/* Gerar novamente */}
                        {idx > 0 && messages[idx - 1]?.role === "user" && (
                          <button
                            onClick={async () => {
                              const prev = messages[idx - 1];
                              if (!prev || loading) return;
                              if (!consumeAiQuery()) return;
                              setLoading(true);
                              const assistantId = addMsg("assistant", "", { loading: true });
                              try {
                                const res = await apiClient.post("/api/chatcad/chat", { texto: prev.content });
                                const data = res.data;
                                const content = data.resposta?.response || (typeof data.resposta === "string" ? data.resposta : "Comando processado.");
                                updateMsg(assistantId, { content, loading: false, streaming: true, tipo: data.tipo });
                              } catch {
                                updateMsg(assistantId, { content: "❌ Erro ao regenerar resposta.", loading: false });
                              } finally {
                                setLoading(false);
                              }
                            }}
                            title="Gerar novamente"
                            style={{
                              padding: "5px 10px",
                              background: "rgba(99,102,241,0.12)",
                              border: "1px solid rgba(99,102,241,0.3)",
                              borderRadius: "6px",
                              color: "#818cf8",
                              cursor: "pointer",
                              fontSize: "11px",
                              fontWeight: 600,
                              display: "flex",
                              alignItems: "center",
                              gap: "5px",
                            }}
                          >
                            🔄 Gerar novamente
                          </button>
                        )}
                        {/* Melhorar desenho */}
                        <button
                          onClick={() => {
                            if (loading) return;
                            setInput("Melhore e otimize o desenho anterior com mais detalhes técnicos");
                            inputRef.current?.focus();
                          }}
                          title="Melhorar desenho"
                          style={{
                            padding: "5px 10px",
                            background: "rgba(16,185,129,0.1)",
                            border: "1px solid rgba(16,185,129,0.3)",
                            borderRadius: "6px",
                            color: "#10B981",
                            cursor: "pointer",
                            fontSize: "11px",
                            fontWeight: 600,
                            display: "flex",
                            alignItems: "center",
                            gap: "5px",
                          }}
                        >
                          ✨ Melhorar desenho
                        </button>
                        {/* Explicar código */}
                        {msg.content.includes("(") && msg.content.includes(")") && (
                          <button
                            onClick={() => {
                              if (loading) return;
                              setInput("Explique o código LISP gerado na resposta anterior, passo a passo");
                              inputRef.current?.focus();
                            }}
                            title="Explicar código"
                            style={{
                              padding: "5px 10px",
                              background: "rgba(245,158,11,0.1)",
                              border: "1px solid rgba(245,158,11,0.3)",
                              borderRadius: "6px",
                              color: "#F59E0B",
                              cursor: "pointer",
                              fontSize: "11px",
                              fontWeight: 600,
                              display: "flex",
                              alignItems: "center",
                              gap: "5px",
                            }}
                          >
                            📖 Explicar código
                          </button>
                        )}
                        {/* Executar no AutoCAD — sempre visível para qualquer assistente */}
                        {!msg.plano && (
                          <button
                            onClick={() => {
                              if (loading) return;
                              setInput(`Execute no AutoCAD: ${msg.content.slice(0, 120)}`);
                              inputRef.current?.focus();
                            }}
                            title="Executar no AutoCAD"
                            style={{
                              padding: "5px 10px",
                              background: "rgba(0,161,255,0.1)",
                              border: "1px solid rgba(0,161,255,0.3)",
                              borderRadius: "6px",
                              color: "#00A1FF",
                              cursor: "pointer",
                              fontSize: "11px",
                              fontWeight: 600,
                              display: "flex",
                              alignItems: "center",
                              gap: "5px",
                            }}
                          >
                            <FaPlay size={9} /> Executar no AutoCAD
                          </button>
                        )}
                      </div>
                    )}
                  </div>
                </motion.div>
              );
            })}
            <div ref={chatEndRef} />
          </div>
        )}
      </div>

      {/* Input */}
      <div
        style={{
          padding: "16px 24px 24px",
          background: "rgba(13,17,23,0.97)",
          borderTop: "1px solid #1e293b",
          flexShrink: 0,
        }}
      >
        {/* Low usage warning */}
        <AnimatePresence>
          {license.isDemo && isLow && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                padding: "10px 14px",
                marginBottom: "12px",
                background: "rgba(245,158,11,0.1)",
                border: "1px solid rgba(245,158,11,0.3)",
                borderRadius: "10px",
                gap: "12px",
                maxWidth: "780px",
                margin: "0 auto 12px",
              }}
            >
              <span style={{ fontSize: "13px", color: "#F59E0B" }}>
                ⚠️ Apenas <strong>{remaining}</strong> consulta
                {remaining !== 1 ? "s" : ""} restante
                {remaining !== 1 ? "s" : ""} no demo
              </span>
              <button
                onClick={() => navigate("/pricing")}
                style={{
                  padding: "6px 14px",
                  background: "#F59E0B",
                  border: "none",
                  borderRadius: "6px",
                  color: "#000",
                  fontSize: "12px",
                  fontWeight: 700,
                  cursor: "pointer",
                  flexShrink: 0,
                }}
              >
                Upgrade
              </button>
            </motion.div>
          )}
        </AnimatePresence>

        <div
          style={{
            maxWidth: "780px",
            margin: "0 auto",
            display: "flex",
            gap: "12px",
            alignItems: "flex-end",
            background: "#161d28",
            border: "1px solid #1e293b",
            borderRadius: "14px",
            padding: "12px",
            boxShadow: "0 4px 24px rgba(0,0,0,0.3)",
          }}
        >
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => {
              setInput(e.target.value);
              e.target.style.height = "auto";
              e.target.style.height =
                Math.min(e.target.scrollHeight, 200) + "px";
            }}
            onKeyDown={handleKeyDown}
            placeholder="Descreva o que quer criar no AutoCAD... ou clique em uma sugestão acima"
            disabled={loading}
            style={{
              flex: 1,
              background: "transparent",
              border: "none",
              outline: "none",
              resize: "none",
              color: "#e2e8f0",
              fontSize: "14px",
              lineHeight: 1.6,
              fontFamily: "inherit",
              minHeight: "24px",
              maxHeight: "200px",
              overflowY: "auto",
            }}
            rows={1}
          />
          <motion.button
            whileHover={{ scale: input.trim() && !loading ? 1.05 : 1 }}
            whileTap={{ scale: input.trim() && !loading ? 0.95 : 1 }}
            onClick={handleSend}
            disabled={!input.trim() || loading}
            style={{
              width: "38px",
              height: "38px",
              borderRadius: "10px",
              flexShrink: 0,
              background:
                input.trim() && !loading
                  ? "linear-gradient(135deg, #00A1FF, #0077CC)"
                  : "#1e293b",
              border: "none",
              cursor: input.trim() && !loading ? "pointer" : "not-allowed",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: input.trim() && !loading ? "#FFF" : "#334155",
              transition: "all 0.2s",
            }}
          >
            {loading ? (
              <motion.div
                animate={{ rotate: 360 }}
                transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
              >
                <FaCog size={16} />
              </motion.div>
            ) : (
              <FaPaperPlane size={14} />
            )}
          </motion.button>
        </div>

        <p
          style={{
            textAlign: "center",
            color: "#334455",
            fontSize: "11px",
            margin: "8px 0 0",
            maxWidth: "780px",
            marginLeft: "auto",
            marginRight: "auto",
          }}
        >
          Enter para enviar • Shift+Enter para nova linha • ChatCAD executa
          comandos no AutoCAD automaticamente
        </p>
      </div>
    </div>
  );
};

export default ChatCAD;
