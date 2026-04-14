import React from "react";
import {
  Box,
  Button,
  Typography,
  Chip,
  Paper,
  CircularProgress,
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

  const handleInstallAgent = () => {
    window.open("/AutoCAD_Cliente/SINCRONIZADOR_INTELIGENTE.ps1", "_blank");
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
            onClick={handleInstallAgent}
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
    </Paper>
  );
};
