import React, { useState, useRef, useEffect, useCallback } from "react";
import {
  FaPaperPlane,
  FaRobot,
  FaUser,
  FaPlay,
  FaLightbulb,
  FaCheckCircle,
  FaTimesCircle,
  FaSpinner,
  FaCog,
  FaChevronDown,
  FaTrash,
} from "react-icons/fa";
import { api as apiClient } from "../services/api";
import { useTheme } from "../context/ThemeContext";
import { useToast } from "../context/ToastContext";

// ═══════════════════════════════════════════════════════════════
// ChatCAD — Interface de Linguagem Natural para o AutoCAD
// Interpreta comandos em português → Planeja → Executa
// ═══════════════════════════════════════════════════════════════

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
}

interface Example {
  comando: string;
  descricao: string;
}

const ChatCAD: React.FC = () => {
  const { theme } = useTheme();
  const { addToast, handleApiError } = useToast();
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 0,
      role: "system",
      content: "Bem-vindo ao ChatCAD! Descreva o que deseja criar no AutoCAD usando linguagem natural. Eu interpreto, planejo e executo para você.",
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [examples, setExamples] = useState<Record<string, Example[]>>({});
  const [showExamples, setShowExamples] = useState(false);
  const [autoExecute, setAutoExecute] = useState(true);
  const chatEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const nextId = useRef(1);

  // Auto-scroll
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Load examples
  useEffect(() => {
    apiClient
      .get(`/api/chatcad/examples`)
      .then((r) => setExamples(r.data))
      .catch(() => {});
  }, []);

  const addMsg = useCallback(
    (role: ChatMessage["role"], content: string, extra?: Partial<ChatMessage>) => {
      const msg: ChatMessage = {
        id: nextId.current++,
        role,
        content,
        timestamp: new Date(),
        ...extra,
      };
      setMessages((prev) => [...prev, msg]);
      return msg.id;
    },
    []
  );

  const updateMsg = useCallback((id: number, updates: Partial<ChatMessage>) => {
    setMessages((prev) =>
      prev.map((m) => (m.id === id ? { ...m, ...updates } : m))
    );
  }, []);

  // ── Send message ──
  const handleSend = async () => {
    const texto = input.trim();
    if (!texto || loading) return;

    setInput("");
    addMsg("user", texto);
    setLoading(true);

    const assistantId = addMsg("assistant", "", { loading: true });

    try {
      const endpoint = autoExecute ? "/api/chatcad/chat" : "/api/chatcad/interpret";
      const res = await apiClient.post(endpoint, { texto });
      const data = res.data;

      let content = "";
      let plano: any[] | undefined;
      let execucao: any | undefined;
      let sugestoes: string[] | undefined;

      if (data.resposta?.response) {
        content = data.resposta.response;
      } else if (data.tipo === "desconhecido") {
        content = "Não entendi esse comando. Veja as sugestões abaixo.";
        sugestoes = data.interpretacao?.sugestoes;
      }

      // Correction notice
      if (data.interpretacao?.correcao) {
        content = `📝 *Correção:* "${data.interpretacao.correcao}"\n\n${content}`;
      }

      if (!autoExecute && data.tipo !== "pergunta" && data.tipo !== "desconhecido") {
        content = `📋 **Plano interpretado** (${data.tipo})\n\n`;
        plano = data.dados?.plano || data.plano;
        if (plano) {
          plano.forEach((a: any, i: number) => {
            content += `${i + 1}. ${a.descricao || a.acao}\n`;
          });
          content += "\nClique ▶ Executar para rodar no AutoCAD.";
        }
      }

      if (data.execucao) {
        execucao = data.execucao;
        plano = data.interpretacao?.dados?.plano;
      }

      sugestoes = sugestoes || data.interpretacao?.sugestoes;

      updateMsg(assistantId, {
        content: content || "Comando processado.",
        loading: false,
        tipo: data.tipo,
        plano,
        execucao,
        sugestoes,
      });

      if (data.executado) {
        addToast(
          data.execucao?.falhas === 0 ? "success" : "warning",
          "ChatCAD",
          data.resposta?.response || "Comando executado"
        );
      }
    } catch (err: any) {
      handleApiError(err);
      updateMsg(assistantId, {
        content: "❌ Erro ao processar comando. Verifique se o servidor está rodando.",
        loading: false,
      });
    } finally {
      setLoading(false);
    }
  };

  // ── Execute pending plan ──
  const handleExecutePlan = async (plano: any[]) => {
    setLoading(true);
    const execId = addMsg("assistant", "", { loading: true });

    try {
      const res = await apiClient.post(`/api/chatcad/execute`, { plano });
      const data = res.data;
      const ok = data.executadas || 0;
      const total = data.total || 0;
      const falhas = data.falhas || 0;

      let content = falhas === 0
        ? `✅ Executado com sucesso! ${ok}/${total} operações concluídas.`
        : `⚠️ ${ok}/${total} OK, ${falhas} falhas.`;

      if (data.resultados) {
        content += "\n\n";
        data.resultados.forEach((r: any) => {
          content += `${r.success ? "✅" : "❌"} ${r.descricao || r.acao}: ${r.message}\n`;
        });
      }

      updateMsg(execId, { content, loading: false, execucao: data });
      addToast(
        falhas === 0 ? "success" : "warning",
        "Execução",
        `${ok}/${total} operações concluídas`
      );
    } catch (err: any) {
      handleApiError(err);
      updateMsg(execId, {
        content: "❌ Erro ao executar plano.",
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

  const handleExampleClick = (cmd: string) => {
    setInput(cmd);
    setShowExamples(false);
    inputRef.current?.focus();
  };

  const handleClearChat = () => {
    setMessages([
      {
        id: 0,
        role: "system",
        content: "Chat limpo. Descreva o que deseja criar no AutoCAD.",
        timestamp: new Date(),
      },
    ]);
    nextId.current = 1;
  };

  // ── Styles ──
  const s = buildStyles(theme);

  return (
    <div style={s.container}>
      <div style={s.wrapper}>
        {/* Header */}
        <div style={s.header}>
          <div style={s.headerLeft}>
            <span style={{ color: theme.accentPrimary, fontSize: "1.5rem", display: "flex" }}><FaRobot /></span>
            <div>
              <h1 style={s.title}>
                Chat<span style={{ color: theme.accentPrimary }}>CAD</span>
              </h1>
              <p style={s.subtitle}>Linguagem natural → AutoCAD</p>
            </div>
          </div>
          <div style={s.headerActions}>
            <label style={s.toggleLabel}>
              <input
                type="checkbox"
                checked={autoExecute}
                onChange={(e) => setAutoExecute(e.target.checked)}
                style={s.checkbox}
              />
              <span style={{ fontWeight: 500 }}>Auto-executar</span>
            </label>
            <button onClick={() => setShowExamples(!showExamples)} style={s.iconBtn} title="Exemplos">
              <FaLightbulb />
            </button>
            <button onClick={handleClearChat} style={s.iconBtn} title="Limpar chat">
              <FaTrash />
            </button>
          </div>
        </div>

        {/* Examples panel */}
        {showExamples && (
          <div style={s.examplesPanel}>
            {Object.entries(examples).map(([category, items]) => (
              <div key={category} style={{ marginBottom: "12px" }}>
                <div style={s.exampleCategory}>{category}</div>
                <div style={s.exampleGrid}>
                  {(items as Example[]).map((ex, i) => (
                    <button
                      key={i}
                      onClick={() => handleExampleClick(ex.comando)}
                      style={s.exampleChip}
                    >
                      <span style={s.exampleCmd}>{ex.comando}</span>
                      <span style={s.exampleDesc}>{ex.descricao}</span>
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Messages */}
        <div style={s.messagesContainer}>
          {messages.map((msg) => (
            <div key={msg.id} style={s.messageRow(msg.role)}>
              <div style={s.avatar(msg.role)}>
                {msg.role === "user" ? <FaUser /> : msg.role === "system" ? <FaCog /> : <FaRobot />}
              </div>
              <div style={s.messageBubble(msg.role)}>
                {msg.loading ? (
                  <div style={s.loadingDots}>
                    <span style={{ animation: "spin 1s linear infinite", display: "inline-flex" }}><FaSpinner /></span>
                    <span style={{ marginLeft: 8, color: theme.textTertiary }}>Processando...</span>
                  </div>
                ) : (
                  <>
                    <div style={s.messageContent}>{msg.content}</div>

                    {/* Execution results */}
                    {msg.execucao && (
                      <div style={s.execResult(msg.execucao.falhas === 0)}>
                        <div style={s.execHeader}>
                          {msg.execucao.falhas === 0 ? (
                            <span style={{ color: theme.accentSecondary }}><FaCheckCircle /></span>
                          ) : (
                            <span style={{ color: theme.accentDanger }}><FaTimesCircle /></span>
                          )}
                          <span>
                            {msg.execucao.executadas}/{msg.execucao.total} operações
                          </span>
                        </div>
                        {msg.execucao.resultados?.map((r: any, i: number) => (
                          <div key={i} style={s.execLine(r.success)}>
                            <span>{r.success ? "✓" : "✗"}</span>
                            <span>{r.descricao || r.acao}</span>
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Plan preview (when not auto-executing) */}
                    {msg.plano && !msg.execucao && (
                      <div style={{ marginTop: 12 }}>
                        <button onClick={() => handleExecutePlan(msg.plano!)} style={s.execBtn} disabled={loading}>
                          <FaPlay /> Executar Plano
                        </button>
                      </div>
                    )}

                    {/* Suggestions */}
                    {msg.sugestoes && msg.sugestoes.length > 0 && (
                      <div style={s.suggestions}>
                        {msg.sugestoes.map((sug, i) => (
                          <button key={i} onClick={() => handleExampleClick(sug)} style={s.suggestionChip}>
                            {sug}
                          </button>
                        ))}
                      </div>
                    )}
                  </>
                )}
                <div style={s.timestamp}>
                  {msg.timestamp.toLocaleTimeString("pt-BR", { hour12: false })}
                </div>
              </div>
            </div>
          ))}
          <div ref={chatEndRef} />
        </div>

        {/* Input */}
        <div style={s.inputArea}>
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder='Descreva o que quer criar... Ex: "tubo 6 polegadas 1000mm eixo x"'
            style={s.textarea}
            rows={1}
            disabled={loading}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || loading}
            style={{
              ...s.sendBtn,
              opacity: !input.trim() || loading ? 0.4 : 1,
            }}
          >
            <FaPaperPlane />
          </button>
        </div>
      </div>

      {/* Spinner keyframes */}
      <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
    </div>
  );
};

// ── Styles factory ──
function buildStyles(theme: any) {
  const isDark = theme.background === "#121212" || theme.bg === "#121212";

  return {
    container: {
      minHeight: "100vh",
      backgroundColor: theme.background,
      color: theme.textPrimary,
      fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
      display: "flex",
      flexDirection: "column" as const,
    },
    wrapper: {
      maxWidth: 900,
      width: "100%",
      margin: "0 auto",
      display: "flex",
      flexDirection: "column" as const,
      height: "100vh",
      padding: "0 16px",
    },

    // Header
    header: {
      display: "flex",
      alignItems: "center",
      justifyContent: "space-between",
      padding: "20px 0 16px",
      borderBottom: `1px solid ${theme.border}`,
      flexShrink: 0,
    },
    headerLeft: {
      display: "flex",
      alignItems: "center",
      gap: 12,
    },
    title: {
      margin: 0,
      fontSize: "1.35rem",
      fontWeight: 700,
      letterSpacing: "0.02em",
      color: theme.textPrimary,
    },
    subtitle: {
      margin: 0,
      fontSize: "0.75rem",
      color: theme.textTertiary,
      letterSpacing: "0.04em",
    },
    headerActions: {
      display: "flex",
      alignItems: "center",
      gap: 8,
    },
    toggleLabel: {
      display: "flex",
      alignItems: "center",
      gap: 6,
      fontSize: "0.8rem",
      color: theme.textSecondary,
      cursor: "pointer",
    },
    checkbox: {
      accentColor: theme.accentPrimary,
    },
    iconBtn: {
      background: "none",
      border: `1px solid ${theme.border}`,
      borderRadius: 8,
      padding: "8px 10px",
      color: theme.textSecondary,
      cursor: "pointer",
      fontSize: "0.85rem",
      transition: "all 0.15s",
    } as React.CSSProperties,

    // Examples
    examplesPanel: {
      padding: "16px 0",
      borderBottom: `1px solid ${theme.border}`,
      maxHeight: 300,
      overflowY: "auto" as const,
      flexShrink: 0,
    },
    exampleCategory: {
      fontSize: "0.7rem",
      fontWeight: 600,
      textTransform: "uppercase" as const,
      letterSpacing: "0.08em",
      color: theme.textTertiary,
      marginBottom: 8,
    },
    exampleGrid: {
      display: "flex",
      flexWrap: "wrap" as const,
      gap: 8,
    },
    exampleChip: {
      background: isDark ? "rgba(255,255,255,0.04)" : "rgba(0,0,0,0.03)",
      border: `1px solid ${theme.border}`,
      borderRadius: 8,
      padding: "8px 14px",
      cursor: "pointer",
      textAlign: "left" as const,
      transition: "all 0.15s",
      maxWidth: 400,
    } as React.CSSProperties,
    exampleCmd: {
      display: "block",
      fontSize: "0.82rem",
      fontWeight: 500,
      color: theme.accentPrimary,
    },
    exampleDesc: {
      display: "block",
      fontSize: "0.7rem",
      color: theme.textTertiary,
      marginTop: 2,
    },

    // Messages
    messagesContainer: {
      flex: 1,
      overflowY: "auto" as const,
      padding: "20px 0",
      display: "flex",
      flexDirection: "column" as const,
      gap: 16,
    },
    messageRow: (role: string) =>
      ({
        display: "flex",
        gap: 12,
        alignItems: "flex-start",
        flexDirection: role === "user" ? "row-reverse" : "row",
      } as React.CSSProperties),
    avatar: (role: string) =>
      ({
        width: 34,
        height: 34,
        borderRadius: "50%",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontSize: "0.8rem",
        flexShrink: 0,
        backgroundColor:
          role === "user"
            ? theme.accentPrimary + "20"
            : role === "system"
            ? theme.accentWarning + "20"
            : isDark
            ? "rgba(255,255,255,0.06)"
            : "rgba(0,0,0,0.04)",
        color:
          role === "user"
            ? theme.accentPrimary
            : role === "system"
            ? theme.accentWarning
            : theme.textSecondary,
      } as React.CSSProperties),
    messageBubble: (role: string) =>
      ({
        maxWidth: "75%",
        padding: "12px 16px",
        borderRadius: 12,
        backgroundColor:
          role === "user"
            ? theme.accentPrimary + (isDark ? "18" : "10")
            : role === "system"
            ? theme.accentWarning + "08"
            : isDark
            ? "rgba(255,255,255,0.04)"
            : "rgba(0,0,0,0.02)",
        border: `1px solid ${
          role === "user"
            ? theme.accentPrimary + "30"
            : role === "system"
            ? theme.accentWarning + "20"
            : theme.border
        }`,
      } as React.CSSProperties),
    messageContent: {
      fontSize: "0.88rem",
      lineHeight: 1.6,
      whiteSpace: "pre-wrap" as const,
      wordBreak: "break-word" as const,
      color: theme.textPrimary,
    },
    timestamp: {
      fontSize: "0.65rem",
      color: theme.textTertiary,
      marginTop: 6,
      textAlign: "right" as const,
    },
    loadingDots: {
      display: "flex",
      alignItems: "center",
      padding: "4px 0",
    },

    // Execution results
    execResult: (success: boolean) =>
      ({
        marginTop: 10,
        padding: "10px 14px",
        borderRadius: 8,
        backgroundColor: success
          ? (theme.accentSecondary || "#32CD32") + "10"
          : theme.accentDanger + "10",
        border: `1px solid ${
          success ? (theme.accentSecondary || "#32CD32") + "30" : theme.accentDanger + "30"
        }`,
        fontSize: "0.8rem",
      } as React.CSSProperties),
    execHeader: {
      display: "flex",
      alignItems: "center",
      gap: 8,
      fontWeight: 600,
      marginBottom: 6,
      fontSize: "0.82rem",
    },
    execLine: (success: boolean) =>
      ({
        padding: "3px 0",
        color: success ? theme.textSecondary : theme.accentDanger,
        display: "flex",
        gap: 8,
        fontSize: "0.78rem",
      } as React.CSSProperties),
    execBtn: {
      display: "inline-flex",
      alignItems: "center",
      gap: 8,
      padding: "8px 20px",
      backgroundColor: theme.accentPrimary,
      color: "#fff",
      border: "none",
      borderRadius: 8,
      fontSize: "0.85rem",
      fontWeight: 600,
      cursor: "pointer",
      transition: "opacity 0.15s",
    } as React.CSSProperties,

    // Suggestions
    suggestions: {
      marginTop: 10,
      display: "flex",
      flexWrap: "wrap" as const,
      gap: 6,
    },
    suggestionChip: {
      background: isDark ? "rgba(255,255,255,0.06)" : "rgba(0,0,0,0.04)",
      border: `1px solid ${theme.border}`,
      borderRadius: 6,
      padding: "4px 12px",
      fontSize: "0.75rem",
      color: theme.accentPrimary,
      cursor: "pointer",
      transition: "all 0.15s",
    } as React.CSSProperties,

    // Input area
    inputArea: {
      display: "flex",
      gap: 10,
      padding: "16px 0 20px",
      borderTop: `1px solid ${theme.border}`,
      alignItems: "flex-end",
      flexShrink: 0,
    },
    textarea: {
      flex: 1,
      padding: "12px 16px",
      backgroundColor: theme.inputBackground || theme.surface,
      border: `1px solid ${theme.inputBorder || theme.border}`,
      borderRadius: 12,
      color: theme.textPrimary,
      fontSize: "0.9rem",
      fontFamily: "'Inter', sans-serif",
      resize: "none" as const,
      outline: "none",
      minHeight: 44,
      maxHeight: 120,
      lineHeight: 1.5,
    } as React.CSSProperties,
    sendBtn: {
      padding: "12px 16px",
      backgroundColor: theme.accentPrimary,
      color: "#fff",
      border: "none",
      borderRadius: 12,
      cursor: "pointer",
      fontSize: "1rem",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      transition: "opacity 0.15s",
      flexShrink: 0,
    } as React.CSSProperties,
  };
}

export default ChatCAD;
