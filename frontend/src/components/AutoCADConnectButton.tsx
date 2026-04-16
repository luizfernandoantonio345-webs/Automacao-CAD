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
  Collapse,
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
  connecting: { chipLabel: "Conectando", chipColor: "warning" as const },
  connected: { chipLabel: "Conectado", chipColor: "success" as const },
  error: { chipLabel: "Erro", chipColor: "error" as const },
} as const;

const INSTALLER_BAT_URL =
  "https://raw.githubusercontent.com/luizfernandoantonio345-webs/Automacao-CAD/main/AutoCAD_Cliente/install-agent.bat";

const PS_SCRIPT_URL =
  "https://raw.githubusercontent.com/luizfernandoantonio345-webs/Automacao-CAD/main/AutoCAD_Cliente/SINCRONIZADOR.ps1";

const PS_ADVANCED = `powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "(New-Object System.Net.WebClient).DownloadFile('${PS_SCRIPT_URL}','%TEMP%\\sincronizador.ps1')"; powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%TEMP%\\sincronizador.ps1"`;

interface AutoCADConnectButtonProps {}

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
        <Typography variant="body2" sx={{ fontWeight: 600 }}>
          {label}
        </Typography>
      </Box>
      {sub && (
        <Typography
          variant="caption"
          color="text.secondary"
          sx={{ display: "block", mb: action ? 1 : 0 }}
        >
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

  const handleConnect = () => {
    isConnected ? disconnect() : connect();
  };

  const handleDownloadInstaller = async () => {
    try {
      // Fetch o conteúdo e criar blob local para forçar download (cross-origin não permite download direto)
      const response = await fetch(INSTALLER_BAT_URL);
      const text = await response.text();
      const blob = new Blob([text], { type: "application/octet-stream" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "install-agent-autocad.bat";
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (error) {
      // Fallback: abre em nova aba se fetch falhar
      window.open(INSTALLER_BAT_URL, "_blank");
    }
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
      <Box
        sx={{ display: "flex", alignItems: "center", gap: 1.5, px: 2, py: 1.5 }}
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
        <Box sx={{ flex: 1 }}>
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
            sx={{ height: 20, fontSize: "0.7rem", fontWeight: 600, mt: 0.3 }}
          />
        </Box>
      </Box>

      {isConnected && cadStatus && (
        <Box
          sx={{
            px: 2,
            pb: 1,
            fontSize: "0.75rem",
            color: "text.secondary",
            display: "flex",
            gap: 2,
          }}
        >
          <span>
            CAD: <b>{cadStatus.cad_running ? "Aberto" : "Fechado"}</b>
          </span>
          <span>
            Driver: <b>{cadStatus.driver_status}</b>
          </span>
        </Box>
      )}

      <Box sx={{ px: 2, pb: isError ? 1 : 2, pt: 0.5 }}>
        <Button
          onClick={handleConnect}
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
          {isConnected ? "Desconectar" : "Conectar ao AutoCAD"}
        </Button>
      </Box>

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
            {error || "Agente local nao detectado."}
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
        </Box>
      )}

      <Dialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        maxWidth="sm"
        fullWidth
        PaperProps={{ sx: { borderRadius: 3, overflow: "hidden" } }}
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
            <Download size={20} />
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
          <Step
            n={1}
            icon={<Download size={16} color={theme.palette.primary.main} />}
            label="Baixe o instalador"
            sub='Clique no botao abaixo para baixar o arquivo "install-agent-autocad.bat"'
            action={
              <Button
                onClick={handleDownloadInstaller}
                variant="contained"
                size="medium"
                fullWidth
                startIcon={<Download size={16} />}
                sx={{
                  borderRadius: 2,
                  textTransform: "none",
                  fontWeight: 700,
                  background: `linear-gradient(135deg, ${theme.palette.primary.main}, ${theme.palette.primary.dark})`,
                  boxShadow: `0 3px 10px ${alpha(theme.palette.primary.main, 0.35)}`,
                  "&:hover": {
                    boxShadow: `0 5px 15px ${alpha(theme.palette.primary.main, 0.5)}`,
                  },
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
            icon={
              <MousePointerClick size={16} color={theme.palette.success.main} />
            }
            label="De duplo clique para executar"
            sub="Uma janela preta abrira, baixara os arquivos e iniciara o agente automaticamente."
          />

          {/* Aviso sobre SmartScreen / Antivírus */}
          <Box
            sx={{
              mt: 1,
              mb: 2,
              p: 1.5,
              borderRadius: 2,
              bgcolor: alpha(theme.palette.warning.main, 0.08),
              border: `1px solid ${alpha(theme.palette.warning.main, 0.3)}`,
            }}
          >
            <Typography
              variant="caption"
              sx={{
                fontWeight: 700,
                color: theme.palette.warning.dark,
                display: "block",
                mb: 0.5,
              }}
            >
              Windows SmartScreen ou Antivirus bloqueou?
            </Typography>
            <Typography
              variant="caption"
              color="text.secondary"
              sx={{ display: "block", lineHeight: 1.5 }}
            >
              Se aparecer "Windows protegeu seu PC": clique em{" "}
              <b>"Mais informacoes"</b> e depois em{" "}
              <b>"Executar assim mesmo"</b>. O arquivo e seguro e o codigo e
              aberto no GitHub.
            </Typography>
          </Box>

          {/* Modo avançado - expansível */}
          <Box
            onClick={() => setAdvancedOpen((v) => !v)}
            sx={{
              mt: 1,
              p: 1.5,
              border: `1px solid ${theme.palette.divider}`,
              borderRadius: 2,
              bgcolor: alpha(theme.palette.common.black, 0.02),
              cursor: "pointer",
              "&:hover": { bgcolor: alpha(theme.palette.common.black, 0.04) },
            }}
          >
            <Box
              sx={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
              }}
            >
              <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                <Terminal size={15} color={theme.palette.text.secondary} />
                <Typography
                  variant="caption"
                  sx={{ fontWeight: 600, color: "text.secondary" }}
                >
                  Modo avançado - usar linha de comando (CMD)
                </Typography>
              </Box>
              <ChevronDown
                size={16}
                style={{
                  transform: advancedOpen ? "rotate(180deg)" : "rotate(0deg)",
                  transition: "transform 0.2s",
                }}
              />
            </Box>
          </Box>

          <Collapse in={advancedOpen}>
            <Box sx={{ p: 1.5, pt: 1 }}>
              <Typography
                variant="caption"
                color="text.secondary"
                sx={{ display: "block", mb: 1.5 }}
              >
                Abra o <b>Prompt de Comando (CMD)</b> como Administrador e cole
                o comando abaixo.
              </Typography>
              <Box
                sx={{
                  display: "flex",
                  alignItems: "flex-start",
                  gap: 1,
                  p: 1.5,
                  borderRadius: 2,
                  background: alpha(theme.palette.common.black, 0.06),
                  border: `1px solid ${theme.palette.divider}`,
                }}
              >
                <Box
                  component="code"
                  sx={{
                    flex: 1,
                    fontSize: "0.68rem",
                    fontFamily: "monospace",
                    wordBreak: "break-all",
                    color: "text.primary",
                    lineHeight: 1.6,
                  }}
                >
                  {PS_ADVANCED}
                </Box>
                <IconButton
                  onClick={handleCopyAdvanced}
                  size="small"
                  sx={{ flexShrink: 0, mt: 0.2 }}
                >
                  {copied ? (
                    <CheckCheck size={16} color={theme.palette.success.main} />
                  ) : (
                    <Copy size={16} />
                  )}
                </IconButton>
              </Box>
              <Typography
                variant="caption"
                sx={{
                  display: "block",
                  mt: 1,
                  color: theme.palette.warning.main,
                  fontWeight: 600,
                }}
              >
                Use apenas se o botão de download não funcionar.
              </Typography>
            </Box>
          </Collapse>
        </DialogContent>

        <DialogActions sx={{ px: 3, pb: 2, pt: 1 }}>
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
