import React, { useState, useEffect } from "react";
import {
  Card,
  CardHeader,
  CardContent,
  Box,
  LinearProgress,
  Typography,
  Grid,
  Stack,
  Button,
  Alert,
  CircularProgress,
} from "@mui/material";
import { useTheme } from "@mui/material/styles";
import { FiBarChart2, FiAlertCircle, FiUpgrade } from "react-icons/fi";
import axios from "axios";

interface QuotaData {
  tier: string;
  api_calls: { used: number; limit: number };
  cam_jobs: { used: number; limit: number };
  ai_queries: { used: number; limit: number };
  storage_gb: { used: number; limit: number };
  reset_date?: string;
}

const QuotaCard: React.FC = () => {
  const theme = useTheme();
  const [quotas, setQuotas] = useState<QuotaData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchQuotas();
  }, []);

  const fetchQuotas = async () => {
    try {
      setLoading(true);
      const response = await axios.get("/api/billing/quotas", {
        headers: {
          Authorization: `Bearer ${localStorage.getItem("access_token") || ""}`,
        },
      });
      setQuotas(response.data);
      setError(null);
    } catch (err: any) {
      setError(err.response?.data?.message || "Falha ao carregar quotas");
      console.error("Erro ao buscar quotas:", err);
    } finally {
      setLoading(false);
    }
  };

  const getProgressColor = (
    used: number,
    limit: number,
  ): "success" | "warning" | "error" => {
    const percentage = (used / limit) * 100;
    if (percentage >= 90) return "error";
    if (percentage >= 70) return "warning";
    return "success";
  };

  const QuotaItem: React.FC<{
    label: string;
    used: number;
    limit: number;
    unit: string;
  }> = ({ label, used, limit, unit }) => {
    const color = getProgressColor(used, limit);
    const percentage = (used / limit) * 100;
    const isUnlimited = limit === -1;

    return (
      <Box sx={{ mb: 2 }}>
        <Stack direction="row" justifyContent="space-between" sx={{ mb: 1 }}>
          <Typography variant="body2" sx={{ fontWeight: 500 }}>
            {label}
          </Typography>
          <Typography variant="body2" color="textSecondary">
            {isUnlimited ? (
              <span
                style={{ color: theme.palette.success.main, fontWeight: 600 }}
              >
                Ilimitado
              </span>
            ) : (
              `${used.toLocaleString()} / ${limit.toLocaleString()} ${unit}`
            )}
          </Typography>
        </Stack>
        {!isUnlimited && (
          <>
            <LinearProgress
              variant="determinate"
              value={percentage}
              color={color}
              sx={{ height: 8, borderRadius: 4 }}
            />
            <Typography
              variant="caption"
              color="textSecondary"
              sx={{ mt: 0.5 }}
            >
              {percentage.toFixed(1)}% utilizado
            </Typography>
          </>
        )}
      </Box>
    );
  };

  if (loading) {
    return (
      <Card>
        <CardHeader title="Uso de Quotas" />
        <CardContent sx={{ display: "flex", justifyContent: "center", py: 4 }}>
          <CircularProgress />
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardHeader title="Uso de Quotas" />
        <CardContent>
          <Alert severity="error">{error}</Alert>
        </CardContent>
      </Card>
    );
  }

  if (!quotas) {
    return null;
  }

  const shouldShowUpgradePrompt =
    (quotas.api_calls.used / quotas.api_calls.limit) * 100 >= 80 ||
    (quotas.cam_jobs.used / quotas.cam_jobs.limit) * 100 >= 80 ||
    (quotas.ai_queries.used / quotas.ai_queries.limit) * 100 >= 80;

  return (
    <Card
      sx={{
        background: `linear-gradient(135deg, ${theme.palette.background.paper} 0%, ${theme.palette.mode === "dark" ? "#1a2332" : "#f5f7fa"} 100%)`,
      }}
    >
      <CardHeader
        title="Uso de Quotas"
        subheader={`Plano: ${quotas.tier} ${quotas.reset_date ? `- Reset em ${new Date(quotas.reset_date).toLocaleDateString("pt-BR")}` : ""}`}
        avatar={<FiBarChart2 size={20} />}
      />
      <CardContent>
        {shouldShowUpgradePrompt && (
          <Alert
            severity="warning"
            sx={{ mb: 3, display: "flex", alignItems: "center", gap: 1 }}
          >
            <FiAlertCircle size={18} />
            <Box>
              <Typography variant="body2" sx={{ fontWeight: 600 }}>
                Você está usando mais de 80% de suas quotas
              </Typography>
              <Typography variant="caption">
                Considere atualizar seu plano para continuar sem interrupções
              </Typography>
            </Box>
          </Alert>
        )}

        <Grid container spacing={3}>
          {/* API Calls */}
          <Grid item xs={12} sm={6}>
            <Box
              sx={{
                p: 2,
                backgroundColor: theme.palette.action.hover,
                borderRadius: 1,
              }}
            >
              <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>
                Chamadas de API
              </Typography>
              <QuotaItem
                label="Requisições"
                used={quotas.api_calls.used}
                limit={quotas.api_calls.limit}
                unit="chamadas"
              />
            </Box>
          </Grid>

          {/* CAM Jobs */}
          <Grid item xs={12} sm={6}>
            <Box
              sx={{
                p: 2,
                backgroundColor: theme.palette.action.hover,
                borderRadius: 1,
              }}
            >
              <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>
                Jobs CAM
              </Typography>
              <QuotaItem
                label="Processamento CNC"
                used={quotas.cam_jobs.used}
                limit={quotas.cam_jobs.limit}
                unit="jobs"
              />
            </Box>
          </Grid>

          {/* AI Queries */}
          <Grid item xs={12} sm={6}>
            <Box
              sx={{
                p: 2,
                backgroundColor: theme.palette.action.hover,
                borderRadius: 1,
              }}
            >
              <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>
                Consultas IA
              </Typography>
              <QuotaItem
                label="Análises"
                used={quotas.ai_queries.used}
                limit={quotas.ai_queries.limit}
                unit="consultas"
              />
            </Box>
          </Grid>

          {/* Storage */}
          <Grid item xs={12} sm={6}>
            <Box
              sx={{
                p: 2,
                backgroundColor: theme.palette.action.hover,
                borderRadius: 1,
              }}
            >
              <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>
                Armazenamento
              </Typography>
              <QuotaItem
                label="Espaço em Disco"
                used={quotas.storage_gb.used}
                limit={quotas.storage_gb.limit}
                unit="GB"
              />
            </Box>
          </Grid>
        </Grid>

        {shouldShowUpgradePrompt && (
          <Box
            sx={{
              mt: 3,
              pt: 3,
              borderTop: `1px solid ${theme.palette.divider}`,
            }}
          >
            <Button
              variant="contained"
              color="primary"
              fullWidth
              startIcon={<FiUpgrade size={16} />}
              href="/pricing"
            >
              Atualizar Plano
            </Button>
          </Box>
        )}
      </CardContent>
    </Card>
  );
};

export default QuotaCard;
