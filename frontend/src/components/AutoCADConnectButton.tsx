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
  alpha,
} from "@mui/material";
import { useTheme } from "@mui/material/styles";
import { useAutoCADConnection } from "../hooks/useAutoCADConnection";
import {
  Loader2,
  AlertCircle,
  CheckCircle2,
  Wifi,
  WifiOff,
  Download,
  Monitor,
  X,
  Terminal,
  FileCode,
  Copy,
  CheckCheck,
} from "lucide-react";

const STATUS_CONFIG = {
  disconnected: {
    text: "Conectar ao AutoCAD",
    chipLabel: "Desconectado",
    chipColor: "error" as const,
  },
  connecting: {
    text: "Conectando...",
    chipLabel: "Conectando",
    chipColor: "warning" as const,
  },
  connected: {
    text: "AutoCAD Conectado",
    chipLabel: "Conectado",
    chipColor: "success" as const,
  },
  error: {
    text: "Erro de Conexão",
    chipLabel: "Erro",
    chipColor: "error" as const,
  },
} as const;

interface AutoCADConnectButtonProps {}

export const AutoCADConnectButton: React.FC<AutoCADConnectButtonProps> = () => {
  const theme = useTheme();
  const { status, cadStatus, error, connect, disconnect, isLoading } =
    useAutoCADConnection();
  const [dialogOpen, setDialogOpen] = useState(false);

  const config = STATUS_CONFIG[status];
  const isConnected = status === "connected";
  const isError = status === "error" || status === "disconnected";

  const handleClick = () => {
    if (isConnected) {
      disconnect();
    } else {
      connect();
    }
  };

  const REPO_BASE =
    "https://raw.githubusercontent.com/luizfernandoantonio345-webs/Automacao-CAD/main/AutoCAD_Cliente";

  const handleDownloadPS1 = () => {
    window.open(`${REPO_BASE}/SINCRONIZADOR_INTELIGENTE.ps1`, "_blank");
  };

  const handleDownloadBAT = () => {
    window.open(`${REPO_BASE}/../AutoSetup_License_Connect.bat`, "_blank");
  };

  const psCommand =
    '[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-Command -ScriptBlock ([ScriptBlock]::Create((Invoke-WebRequest -UseBasicParsing -Uri "https://raw.githubusercontent.com/luizfernandoantonio345-webs/Automacao-CAD/main/AutoCAD_Cliente/SINCRONIZADOR_INTELIGENTE.ps1").Content))';

  const cmdCommand =
    'powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; Invoke-Command -ScriptBlock ([ScriptBlock]::Create((Invoke-WebRequest -UseBasicParsing -Uri ''https://raw.githubusercontent.com/luizfernandoantonio345-webs/Automacao-CAD/main/AutoCAD_Cliente/SINCRONIZADOR_INTELIGENTE.ps1'').Content))"';

  const [copiedCmd, setCopiedCmd] = useState<"ps" | "cmd" | null>(null);

  const handleCopy = (text: string, type: "ps" | "cmd") => {
    navigator.clipboard.writeText(text).then(() => {
      setCopiedCmd(type);
      setTimeout(() => setCopiedCmd(null), 2000);
    });
  };

  const accentColor = isConnected
    ? theme.palette.success.main
    : isError
      ? theme.palette.error.main
      : theme.palette.warning.main;

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
