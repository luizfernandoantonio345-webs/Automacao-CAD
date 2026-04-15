import React, { useState } from "react";
import {
  Box,
  Button,
  Typography,
  Chip,
  Paper,
  CircularProgress,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  IconButton,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  alpha,
} from "@mui/material";
import { useTheme } from "@mui/material/styles";
import { useAutoCADConnection } from "../hooks/useAutoCADConnection";
import {
  Wifi,
  WifiOff,
  Download,
  Monitor,
  X,
  Terminal,
  Copy,
  CheckCheck,
  ChevronDown,
  FolderOpen,
  MousePointerClick,
} from "lucide-react";

const STATUS_CONFIG = {
  disconnected: { chipLabel: "Desconectado", chipColor: "error" as const },
  connecting:   { chipLabel: "Conectando",   chipColor: "warning" as const },
  connected:    { chipLabel: "Conectado",    chipColor: "success" as const },
  error:        { chipLabel: "Erro",         chipColor: "error" as const },
} as const;

// URL do instalador .bat no repositório (único arquivo de instalação)
const INSTALLER_BAT_URL =
  "https://raw.githubusercontent.com/luizfernandoantonio345-webs/Automacao-CAD/main/AutoCAD_Cliente/install-agent.bat";

// Comandos avançados (modo PowerShell) — para usuários técnicos
const PS_SCRIPT_URL =
  "https://raw.githubusercontent.com/luizfernandoantonio345-webs/Automacao-CAD/main/AutoCAD_Cliente/SINCRONIZADOR.ps1";
const PS_ADVANCED =
  `powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "(New-Object System.Net.WebClient).DownloadFile('${PS_SCRIPT_URL}','%TEMP%\\sincronizador.ps1')"; powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%TEMP%\\sincronizador.ps1"`;

interface AutoCADConnectButtonProps {}

// Passo visual numerado
const Step: React.FC<{
  n: number;
  icon: React.ReactNode;
  label: string;
  sub?: string;
  action?: React.ReactNode;
}> = ({ n, icon, label, sub, action }) => (
  <Box sx={{ display: "flex", gap: 1.5, alignItems: "flex-start", mb: 2 }}>
    <Box
      sx={{
        width: 28,
        height: 28,
        borderRadius: "50%",
        bgcolor: "primary.main",
        color: "#fff",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontWeight: 700,
        fontSize: "0.8rem",
        flexShrink: 0,
        mt: 0.2,
      }}
    >
      {n}
    </Box>
    <Box sx={{ flex: 1 }}>
      <Box sx={{ display: "flex", alignItems: "center", gap: 0.8, mb: 0.4 }}>
        {icon}
        <Typography variant="body2" sx={{ fontWeight: 600 }}>{label}</Typography>
      </Box>
      {sub && (
        <Typography variant="caption" color="text.secondary" sx={{ display: "block", mb: action ? 1 : 0 }}>
          {sub}
        </Typography>
      )}
      {action}
    </Box>
  </Box>
);

export const AutoCADConnectButton: React.FC<AutoCADConnectButtonProps> = () => {
  const theme = useTheme();
  const { status, cadStatus, error, connect, disconnect, isLoading } =
    useAutoCADConnection();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [copied, setCopied] = useState(false);

  const config = STATUS_CONFIG[status];
  const isConnected = status === "connected";
  const isError = status === "error" || status === "disconnected";

  const accentColor = isConnected
    ? theme.palette.success.main
    : isError
      ? theme.palette.error.main
      : theme.palette.warning.main;

  const handleConnect = () => { isConnected ? disconnect() : connect(); };

  const handleDownloadInstaller = () => {
    // Força download direto do .bat — funciona em qualquer Windows com duplo clique
    const a = document.createElement("a");
    a.href = INSTALLER_BAT_URL;
    a.download = "install-agent-autocad.bat";
    a.click();
  };

  const handleCopyAdvanced = () => {
    navigator.clipboard.writeText(PS_ADVANCED).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  return (
    <Paper
      elevation={0}
      sx={{
        maxWidth: 360,
        borderRadius: 3,
        border: `1px solid ${alpha(accentColor, 0.3)}`,
        background: alpha(accentColor, 0.04),
        overflow: "hidden",
      }}
    >
      {/* Header */}
      <Box sx={{ display: "flex", alignItems: "center", gap: 1.5, px: 2, py: 1.5 }}>
        <Box
          sx={{
            width: 36, height: 36, borderRadius: 2,
            display: "flex", alignItems: "center", justifyContent: "center",
            background: alpha(accentColor, 0.12), color: accentColor, flexShrink: 0,
          }}
        >
          <Monitor size={20} />
        </Box>
        <Box sx={{ flex: 1 }}>
          <Typography variant="subtitle2" sx={{ fontWeight: 600, lineHeight: 1.3 }}>AutoCAD</Typography>
          <Chip label={config.chipLabel} color={config.chipColor} size="small" variant="filled"
            sx={{ height: 20, fontSize: "0.7rem", fontWeight: 600, mt: 0.3 }} />
        </Box>
      </Box>

      {/* Info quando conectado */}
      {isConnected && cadStatus && (
        <Box sx={{ px: 2, pb: 1, fontSize: "0.75rem", color: "text.secondary", display: "flex", gap: 2 }}>
          <span>CAD: <b>{cadStatus.cad_running ? "Aberto" : "Fechado"}</b></span>
          <span>Driver: <b>{cadStatus.driver_status}</b></span>
        </Box>
      )}

      {/* Botão principal */}
      <Box sx={{ px: 2, pb: isError ? 1 : 2, pt: 0.5 }}>
        <Button
          onClick={handleConnect}
          disabled={isLoading}
          variant={isConnected ? "outlined" : "contained"}
          size="small"
          fullWidth
          startIcon={isLoading
            ? <CircularProgress size={16} color="inherit" />
            : isConnected ? <Wifi size={16} /> : <WifiOff size={16} />}
          sx={{
            borderRadius: 2, textTransform: "none", fontWeight: 600, fontSize: "0.8rem", py: 0.8,
            ...(isConnected
              ? { borderColor: theme.palette.success.main, color: theme.palette.success.main,
                  "&:hover": { borderColor: theme.palette.error.main, color: theme.palette.error.main, background: alpha(theme.palette.error.main, 0.06) } }
              : { background: `linear-gradient(135deg, ${theme.palette.primary.main}, ${theme.palette.primary.dark})`,
                  boxShadow: `0 2px 8px ${alpha(theme.palette.primary.main, 0.3)}`,
                  "&:hover": { boxShadow: `0 4px 12px ${alpha(theme.palette.primary.main, 0.45)}` } }),
          }}
        >
          {isConnected ? "Desconectar" : "Conectar ao AutoCAD"}
        </Button>
      </Box>

      {/* Seção agente */}
      {isError && (
        <Box sx={{ px: 2, pb: 2, pt: 0.5, borderTop: `1px dashed ${alpha(theme.palette.divider, 0.5)}` }}>
          <Typography variant="caption" sx={{ display: "block", color: "text.secondary", mb: 1, lineHeight: 1.4 }}>
            {error || "Agente local não detectado."}
          </Typography>
          <Button
            onClick={() => setDialogOpen(true)}
            variant="outlined" size="small" fullWidth
            startIcon={<Download size={14} />}
            sx={{
              borderRadius: 2, textTransform: "none", fontWeight: 600, fontSize: "0.75rem", py: 0.6,
              borderColor: alpha(theme.palette.info.main, 0.4), color: theme.palette.info.main,
              "&:hover": { borderColor: theme.palette.info.main, background: alpha(theme.palette.info.main, 0.06) },
            }}
          >
            Instalar / Executar Agente
          </Button>
        </Box>
      )}

      {/* Dialog — 3 passos simples */}
      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="sm" fullWidth
        PaperProps={{ sx: { borderRadius: 3, overflow: "hidden" } }}>
        <DialogTitle sx={{
          display: "flex", alignItems: "center", justifyContent: "space-between",
          background: `linear-gradient(135deg, ${theme.palette.primary.main}, ${theme.palette.primary.dark})`,
          color: "#fff", py: 2,
        }}>
          <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
            <Download size={20} />
            <span>Instalar Agente AutoCAD</span>
          </Box>
          <IconButton onClick={() => setDialogOpen(false)} size="small"
            sx={{ color: "rgba(255,255,255,0.7)", "&:hover": { color: "#fff" } }}>
            <X size={18} />
          </IconButton>
        </DialogTitle>

        <DialogContent sx={{ pt: 3, pb: 1 }}>

          {/* ── PASSOS PRINCIPAIS ── */}
          <Step
            n={1}
            icon={<Download size={16} color={theme.palette.primary.main} />}
            label="Baixe o instalador"
            sub='Clique no botão abaixo para baixar o arquivo "install-agent-autocad.bat"'
            action={
              <Button
                onClick={handleDownloadInstaller}
                variant="contained" size="medium" fullWidth
                startIcon={<Download size={16} />}
                sx={{
                  borderRadius: 2, textTransform: "none", fontWeight: 700,
                  background: `linear-gradient(135deg, ${theme.palette.primary.main}, ${theme.palette.primary.dark})`,
                  boxShadow: `0 3px 10px ${alpha(theme.palette.primary.main, 0.35)}`,
                  "&:hover": { boxShadow: `0 5px 15px ${alpha(theme.palette.primary.main, 0.5)}` },
                }}
              >
                Baixar install-agent-autocad.bat
              </Button>
            }
          />

          <Step
            n={2}
            icon={<FolderOpen size={16} color={theme.palette.warning.main} />}
            label="Localize o arquivo baixado"
            sub='Abra a pasta de Downloads e encontre o arquivo "install-agent-autocad.bat"'
          />

          <Step
            n={3}
            icon={<MousePointerClick size={16} color={theme.palette.success.main} />}
            label="Dê duplo clique para executar"
            sub="Uma janela preta abrirá, baixará os arquivos e iniciará o agente automaticamente. Aguarde até ver ✅ CONECTADO."
          />

          {/* ── MODO AVANÇADO ── */}
          <Accordion
            expanded={advancedOpen}
            onChange={() => setAdvancedOpen((v) => !v)}
            elevation={0}
            sx={{ mt: 1, border: `1px solid ${theme.palette.divider}`, borderRadius: "8px !important",
              "&:before": { display: "none" }, bgcolor: alpha(theme.palette.common.black, 0.02) }}
          >
            <AccordionSummary expandIcon={<ChevronDown size={16} />}>
              <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                <Terminal size={15} color={theme.palette.text.secondary} />
                <Typography variant="caption" sx={{ fontWeight: 600, color: "text.secondary" }}>
                  Modo avançado — usar linha de comando (CMD / PowerShell)
                </Typography>
              </Box>
            </AccordionSummary>
            <AccordionDetails sx={{ pt: 0 }}>
              <Typography variant="caption" color="text.secondary" sx={{ display: "block", mb: 1.5 }}>
                Abra o <b>Prompt de Comando (CMD)</b> como Administrador e cole o comando abaixo.
                Ele baixa e executa o agente sem precisar do arquivo .bat.
              </Typography>
              <Box sx={{
                display: "flex", alignItems: "flex-start", gap: 1, p: 1.5, borderRadius: 2,
                background: alpha(theme.palette.common.black, 0.06), border: `1px solid ${theme.palette.divider}`,
              }}>
                <Box component="code" sx={{
                  flex: 1, fontSize: "0.68rem", fontFamily: "monospace",
                  wordBreak: "break-all", color: "text.primary", lineHeight: 1.6,
                }}>
                  {PS_ADVANCED}
                </Box>
                <IconButton onClick={handleCopyAdvanced} size="small" sx={{ flexShrink: 0, mt: 0.2 }}>
                  {copied
                    ? <CheckCheck size={16} color={theme.palette.success.main} />
                    : <Copy size={16} />}
                </IconButton>
              </Box>
              <Typography variant="caption" sx={{ display: "block", mt: 1, color: theme.palette.warning.main, fontWeight: 600 }}>
                ⚠ Este comando só funciona no CMD (Prompt de Comando), não no PowerShell diretamente.
              </Typography>
            </AccordionDetails>
          </Accordion>

        </DialogContent>

        <DialogActions sx={{ px: 3, pb: 2, pt: 1 }}>
          <Button onClick={() => setDialogOpen(false)} sx={{ textTransform: "none", fontWeight: 600 }}>
            Fechar
          </Button>
        </DialogActions>
      </Dialog>
    </Paper>
  );
};
    <Paper
      elevation={0}
      sx={{
        maxWidth: 360,
        borderRadius: 3,
        border: `1px solid ${alpha(accentColor, 0.3)}`,
        background: alpha(accentColor, 0.04),
        overflow: "hidden",
      }}
    >
      {/* Header com status */}
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          gap: 1.5,
          px: 2,
          py: 1.5,
        }}
      >
        <Box
          sx={{
            width: 36,
            height: 36,
            borderRadius: 2,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            background: alpha(accentColor, 0.12),
            color: accentColor,
            flexShrink: 0,
          }}
        >
          <Monitor size={20} />
        </Box>
        <Box sx={{ flex: 1, minWidth: 0 }}>
          <Typography
            variant="subtitle2"
            sx={{ fontWeight: 600, lineHeight: 1.3 }}
          >
            AutoCAD
          </Typography>
          <Chip
            label={config.chipLabel}
            color={config.chipColor}
            size="small"
            variant="filled"
            sx={{
              height: 20,
              fontSize: "0.7rem",
              fontWeight: 600,
              mt: 0.3,
            }}
          />
        </Box>
      </Box>

      {/* Info conectado */}
      {isConnected && cadStatus && (
        <Box sx={{ px: 2, pb: 1 }}>
          <Box
            sx={{
              display: "flex",
              gap: 2,
              fontSize: "0.75rem",
              color: "text.secondary",
            }}
          >
            <span>
              CAD: <b>{cadStatus.cad_running ? "Aberto" : "Fechado"}</b>
            </span>
            <span>
              Driver: <b>{cadStatus.driver_status}</b>
            </span>
          </Box>
        </Box>
      )}

      {/* Botão principal */}
      <Box sx={{ px: 2, pb: isError ? 1 : 2, pt: 0.5 }}>
        <Button
          onClick={handleClick}
          disabled={isLoading}
          variant={isConnected ? "outlined" : "contained"}
          size="small"
          fullWidth
          startIcon={
            isLoading ? (
              <CircularProgress size={16} color="inherit" />
            ) : isConnected ? (
              <Wifi size={16} />
            ) : (
              <WifiOff size={16} />
            )
          }
          sx={{
            borderRadius: 2,
            textTransform: "none",
            fontWeight: 600,
            fontSize: "0.8rem",
            py: 0.8,
            ...(isConnected
              ? {
                  borderColor: theme.palette.success.main,
                  color: theme.palette.success.main,
                  "&:hover": {
                    borderColor: theme.palette.error.main,
                    color: theme.palette.error.main,
                    background: alpha(theme.palette.error.main, 0.06),
                  },
                }
              : {
                  background: `linear-gradient(135deg, ${theme.palette.primary.main}, ${theme.palette.primary.dark})`,
                  boxShadow: `0 2px 8px ${alpha(theme.palette.primary.main, 0.3)}`,
                  "&:hover": {
                    boxShadow: `0 4px 12px ${alpha(theme.palette.primary.main, 0.45)}`,
                  },
                }),
          }}
        >
          {isConnected ? "Desconectar" : config.text}
        </Button>
      </Box>

      {/* Seção agente — só quando desconectado / erro */}
      {isError && (
        <Box
          sx={{
            px: 2,
            pb: 2,
            pt: 0.5,
            borderTop: `1px dashed ${alpha(theme.palette.divider, 0.5)}`,
          }}
        >
          <Typography
            variant="caption"
            sx={{
              display: "block",
              color: "text.secondary",
              mb: 1,
              lineHeight: 1.4,
            }}
          >
            {error || "Agente local não detectado."}
          </Typography>
          <Button
            onClick={() => setDialogOpen(true)}
            variant="outlined"
            size="small"
            fullWidth
            startIcon={<Download size={14} />}
            sx={{
              borderRadius: 2,
              textTransform: "none",
              fontWeight: 600,
              fontSize: "0.75rem",
              py: 0.6,
              borderColor: alpha(theme.palette.info.main, 0.4),
              color: theme.palette.info.main,
              "&:hover": {
                borderColor: theme.palette.info.main,
                background: alpha(theme.palette.info.main, 0.06),
              },
            }}
          >
            Instalar / Executar Agente
          </Button>
          <Typography
            variant="caption"
            sx={{
              display: "block",
              mt: 1,
              fontSize: "0.65rem",
              color: "text.disabled",
              lineHeight: 1.4,
            }}
          >
            Execute{" "}
            <Box component="span" sx={{ fontWeight: 700 }}>
              SINCRONIZADOR_INTELIGENTE.ps1
            </Box>{" "}
            ou{" "}
            <Box component="span" sx={{ fontWeight: 700 }}>
              AutoSetup_License_Connect.bat
            </Box>{" "}
            na pasta AutoCAD_Cliente.
          </Typography>
        </Box>
      )}

      {/* Dialog de instalação do agente */}
      <Dialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        maxWidth="sm"
        fullWidth
        PaperProps={{
          sx: { borderRadius: 3, overflow: "hidden" },
        }}
      >
        <DialogTitle
          sx={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            background: `linear-gradient(135deg, ${theme.palette.primary.main}, ${theme.palette.primary.dark})`,
            color: "#fff",
            py: 2,
          }}
        >
          <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
            <Download size={22} />
            <span>Instalar Agente AutoCAD</span>
          </Box>
          <IconButton
            onClick={() => setDialogOpen(false)}
            size="small"
            sx={{
              color: "rgba(255,255,255,0.7)",
              "&:hover": { color: "#fff" },
            }}
          >
            <X size={18} />
          </IconButton>
        </DialogTitle>

        <DialogContent sx={{ pt: 3, pb: 1 }}>
          {/* Opção 1a — PowerShell */}
          <Typography
            variant="subtitle2"
            sx={{
              fontWeight: 700,
              mb: 1,
              display: "flex",
              alignItems: "center",
              gap: 1,
            }}
          >
            <Terminal size={16} /> Opção 1 — Comando rápido
          </Typography>

          {/* PowerShell */}
          <Paper
            variant="outlined"
            sx={{
              p: 1.5,
              borderRadius: 2,
              mb: 1.5,
              background: alpha("#012456", 0.05),
              borderColor: alpha("#012456", 0.2),
            }}
          >
            <Typography
              variant="caption"
              sx={{
                fontWeight: 700,
                color: "#012456",
                display: "flex",
                alignItems: "center",
                gap: 0.5,
                mb: 0.8,
              }}
            >
              ⚡ Windows PowerShell
              <Chip label="Recomendado" size="small" color="primary" sx={{ height: 18, fontSize: "0.6rem", ml: 0.5 }} />
            </Typography>
            <Typography variant="caption" color="text.secondary" sx={{ display: "block", mb: 1 }}>
              Clique com botão direito no menu Iniciar → <b>Windows PowerShell (Admin)</b>
            </Typography>
            <Typography
              variant="caption"
              sx={{
                display: "block",
                mb: 1,
                color: theme.palette.warning.main,
                fontWeight: 600,
              }}
            >
              Se aparecer "IRM não reconhecido", você está no terminal errado. Use este comando sem alterar.
            </Typography>
            <Box
              sx={{
                display: "flex",
                alignItems: "center",
                gap: 1,
                p: 1,
                borderRadius: 1.5,
                background: alpha(theme.palette.common.black, 0.06),
              }}
            >
              <Box
                component="code"
                sx={{
                  flex: 1,
                  fontSize: "0.7rem",
                  fontFamily: "monospace",
                  wordBreak: "break-all",
                  color: "text.primary",
                }}
              >
                {psCommand}
              </Box>
              <IconButton
                onClick={() => handleCopy(psCommand, "ps")}
                size="small"
                sx={{ flexShrink: 0 }}
              >
                {copiedCmd === "ps" ? (
                  <CheckCheck size={16} color={theme.palette.success.main} />
                ) : (
                  <Copy size={16} />
                )}
              </IconButton>
            </Box>
          </Paper>

          {/* CMD */}
          <Paper
            variant="outlined"
            sx={{
              p: 1.5,
              borderRadius: 2,
              mb: 2.5,
              background: alpha("#000", 0.03),
              borderColor: alpha("#000", 0.12),
            }}
          >
            <Typography
              variant="caption"
              sx={{
                fontWeight: 700,
                color: "text.primary",
                display: "flex",
                alignItems: "center",
                gap: 0.5,
                mb: 0.8,
              }}
            >
              ▪ Prompt de Comando (CMD)
            </Typography>
            <Typography variant="caption" color="text.secondary" sx={{ display: "block", mb: 1 }}>
              Tecle <b>Win + R</b> → digite <b>cmd</b> → Enter
            </Typography>
            <Box
              sx={{
                display: "flex",
                alignItems: "center",
                gap: 1,
                p: 1,
                borderRadius: 1.5,
                background: alpha(theme.palette.common.black, 0.06),
              }}
            >
              <Box
                component="code"
                sx={{
                  flex: 1,
                  fontSize: "0.7rem",
                  fontFamily: "monospace",
                  wordBreak: "break-all",
                  color: "text.primary",
                }}
              >
                {cmdCommand}
              </Box>
              <IconButton
                onClick={() => handleCopy(cmdCommand, "cmd")}
                size="small"
                sx={{ flexShrink: 0 }}
              >
                {copiedCmd === "cmd" ? (
                  <CheckCheck size={16} color={theme.palette.success.main} />
                ) : (
                  <Copy size={16} />
                )}
              </IconButton>
            </Box>
          </Paper>

          {/* Opção 2 — Download manual */}
          <Typography
            variant="subtitle2"
            sx={{
              fontWeight: 700,
              mb: 1,
              display: "flex",
              alignItems: "center",
              gap: 1,
            }}
          >
            <FileCode size={16} /> Opção 2 — Download manual
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
            Baixe o script, salve na sua máquina e execute:
          </Typography>
          <Box sx={{ display: "flex", gap: 1, mb: 2 }}>
            <Button
              onClick={handleDownloadPS1}
              variant="contained"
              size="small"
              startIcon={<Download size={14} />}
              sx={{
                borderRadius: 2,
                textTransform: "none",
                fontWeight: 600,
                fontSize: "0.78rem",
              }}
            >
              SINCRONIZADOR.ps1
            </Button>
            <Button
              onClick={handleDownloadBAT}
              variant="outlined"
              size="small"
              startIcon={<Download size={14} />}
              sx={{
                borderRadius: 2,
                textTransform: "none",
                fontWeight: 600,
                fontSize: "0.78rem",
              }}
            >
              AutoSetup.bat
            </Button>
          </Box>

          {/* Passos */}
          <Paper
            variant="outlined"
            sx={{
              p: 2,
              borderRadius: 2,
              background: alpha(theme.palette.info.main, 0.04),
              borderColor: alpha(theme.palette.info.main, 0.2),
            }}
          >
            <Typography
              variant="caption"
              sx={{
                fontWeight: 700,
                display: "block",
                mb: 1,
                color: theme.palette.info.main,
              }}
            >
              Após instalar:
            </Typography>
            <Box
              component="ol"
              sx={{
                m: 0,
                pl: 2.5,
                "& li": {
                  fontSize: "0.78rem",
                  color: "text.secondary",
                  mb: 0.5,
                },
              }}
            >
              <li>O agente detecta o AutoCAD automaticamente</li>
              <li>
                O ícone acima mudará para{" "}
                <b style={{ color: theme.palette.success.main }}>Conectado</b>
              </li>
              <li>Você poderá enviar comandos diretamente pelo app</li>
            </Box>
          </Paper>
        </DialogContent>

        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button
            onClick={() => setDialogOpen(false)}
            sx={{ textTransform: "none", fontWeight: 600 }}
          >
            Fechar
          </Button>
        </DialogActions>
      </Dialog>
    </Paper>
  );
};
