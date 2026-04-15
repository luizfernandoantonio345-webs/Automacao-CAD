import React, { useState, useEffect } from "react";
import {
  Box,
  Container,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Button,
  TextField,
  MenuItem,
  CircularProgress,
  Alert,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Typography,
  Chip,
  Stack,
} from "@mui/material";
import { useTheme } from "@mui/material/styles";
import axios from "axios";
import { FiDownload, FiFilter, FiX } from "react-icons/fi";

interface AuditEvent {
  id: string;
  timestamp: string;
  user_id: string;
  user_email: string;
  action: string;
  resource_type: string;
  resource_id: string;
  status: "success" | "failure";
  ip_address: string;
  user_agent: string;
  details: Record<string, any>;
}

interface FilterOptions {
  user_email: string;
  action: string;
  status: string;
  date_from: string;
  date_to: string;
}

const AdminPanel: React.FC = () => {
  const theme = useTheme();
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedEvent, setSelectedEvent] = useState<AuditEvent | null>(null);
  const [detailsOpen, setDetailsOpen] = useState(false);
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(20);
  const [total, setTotal] = useState(0);

  // Filter state
  const [filters, setFilters] = useState<FilterOptions>({
    user_email: "",
    action: "",
    status: "",
    date_from: "",
    date_to: "",
  });

  // Unique values for dropdowns
  const [actions, setActions] = useState<string[]>([]);

  // Fetch audit events
  const fetchEvents = async (pageNum: number = 0) => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      params.append("skip", (pageNum * rowsPerPage).toString());
      params.append("limit", rowsPerPage.toString());

      if (filters.user_email) params.append("user_email", filters.user_email);
      if (filters.action) params.append("action", filters.action);
      if (filters.status) params.append("status", filters.status);
      if (filters.date_from) params.append("date_from", filters.date_from);
      if (filters.date_to) params.append("date_to", filters.date_to);

      const response = await axios.get(
        `/api/enterprise/audit/events?${params}`,
        {
          headers: {
            Authorization: `Bearer ${localStorage.getItem("access_token") || ""}`,
          },
        },
      );

      setEvents(response.data.events || []);
      setTotal(response.data.total || 0);
      setPage(pageNum);
    } catch (err: any) {
      setError(
        err.response?.data?.message || "Falha ao carregar eventos de auditoria",
      );
      console.error("Erro ao buscar eventos:", err);
    } finally {
      setLoading(false);
    }
  };

  // Fetch available actions for filter
  const fetchAvailableActions = async () => {
    try {
      const response = await axios.get("/api/enterprise/audit/actions", {
        headers: {
          Authorization: `Bearer ${localStorage.getItem("access_token") || ""}`,
        },
      });
      setActions(response.data.actions || []);
    } catch (err) {
      console.error("Erro ao buscar ações disponíveis:", err);
    }
  };

  useEffect(() => {
    fetchEvents();
    fetchAvailableActions();
  }, []);

  // Aplicar filtros
  const handleApplyFilters = () => {
    setPage(0);
    fetchEvents(0);
  };

  // Limpar filtros
  const handleClearFilters = () => {
    setFilters({
      user_email: "",
      action: "",
      status: "",
      date_from: "",
      date_to: "",
    });
    setPage(0);
    fetchEvents(0);
  };

  // Exportar para CSV
  const handleExportCSV = async () => {
    try {
      const params = new URLSearchParams();
      if (filters.user_email) params.append("user_email", filters.user_email);
      if (filters.action) params.append("action", filters.action);
      if (filters.status) params.append("status", filters.status);
      if (filters.date_from) params.append("date_from", filters.date_from);
      if (filters.date_to) params.append("date_to", filters.date_to);

      const response = await axios.get(
        `/api/enterprise/audit/export?${params}&format=csv`,
        {
          headers: {
            Authorization: `Bearer ${localStorage.getItem("access_token") || ""}`,
          },
          responseType: "blob",
        },
      );

      // Criar link para download
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute(
        "download",
        `audit_trail_${new Date().toISOString().split("T")[0]}.csv`,
      );
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setError("Falha ao exportar dados");
      console.error("Erro ao exportar:", err);
    }
  };

  // Mostrar detalhes do evento
  const handleShowDetails = (event: AuditEvent) => {
    setSelectedEvent(event);
    setDetailsOpen(true);
  };

  const getStatusColor = (status: string) => {
    return status === "success" ? "success" : "error";
  };

  const getActionColor = (action: string): any => {
    const colorMap: Record<string, any> = {
      CREATE: "success",
      UPDATE: "info",
      DELETE: "error",
      READ: "default",
      LOGIN: "success",
      LOGOUT: "default",
      EXPORT: "info",
    };
    return colorMap[action] || "default";
  };

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Box sx={{ mb: 4 }}>
        <Typography
          variant="h4"
          sx={{ mb: 2, fontWeight: 600, color: theme.palette.primary.main }}
        >
          Auditoria do Sistema
        </Typography>
        <Typography variant="body2" color="textSecondary">
          Registros de todas as ações e operações do sistema
        </Typography>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      {/* Filtros */}
      <Paper
        sx={{ p: 3, mb: 3, backgroundColor: theme.palette.background.paper }}
      >
        <Typography
          variant="h6"
          sx={{ mb: 2, display: "flex", alignItems: "center", gap: 1 }}
        >
          <FiFilter size={18} /> Filtros
        </Typography>

        <Stack spacing={2} sx={{ mb: 3 }}>
          <Stack direction={{ xs: "column", sm: "row" }} spacing={2}>
            <TextField
              label="Email do Usuário"
              size="small"
              value={filters.user_email}
              onChange={(e) =>
                setFilters({ ...filters, user_email: e.target.value })
              }
              placeholder="ex: user@example.com"
              sx={{ flex: 1 }}
            />

            <TextField
              select
              label="Ação"
              size="small"
              value={filters.action}
              onChange={(e) =>
                setFilters({ ...filters, action: e.target.value })
              }
              sx={{ flex: 1, minWidth: 200 }}
            >
              <MenuItem value="">Todas</MenuItem>
              {actions.map((action) => (
                <MenuItem key={action} value={action}>
                  {action}
                </MenuItem>
              ))}
            </TextField>

            <TextField
              select
              label="Status"
              size="small"
              value={filters.status}
              onChange={(e) =>
                setFilters({ ...filters, status: e.target.value })
              }
              sx={{ flex: 1, minWidth: 150 }}
            >
              <MenuItem value="">Todos</MenuItem>
              <MenuItem value="success">Sucesso</MenuItem>
              <MenuItem value="failure">Falha</MenuItem>
            </TextField>
          </Stack>

          <Stack direction={{ xs: "column", sm: "row" }} spacing={2}>
            <TextField
              type="date"
              label="Data Inicial"
              InputLabelProps={{ shrink: true }}
              size="small"
              value={filters.date_from}
              onChange={(e) =>
                setFilters({ ...filters, date_from: e.target.value })
              }
              sx={{ flex: 1 }}
            />

            <TextField
              type="date"
              label="Data Final"
              InputLabelProps={{ shrink: true }}
              size="small"
              value={filters.date_to}
              onChange={(e) =>
                setFilters({ ...filters, date_to: e.target.value })
              }
              sx={{ flex: 1 }}
            />
          </Stack>

          <Stack direction="row" spacing={2}>
            <Button
              variant="contained"
              color="primary"
              onClick={handleApplyFilters}
              sx={{ flexGrow: 1 }}
            >
              Aplicar Filtros
            </Button>
            <Button
              variant="outlined"
              onClick={handleClearFilters}
              startIcon={<FiX size={16} />}
            >
              Limpar
            </Button>
            <Button
              variant="outlined"
              onClick={handleExportCSV}
              startIcon={<FiDownload size={16} />}
            >
              Exportar CSV
            </Button>
          </Stack>
        </Stack>
      </Paper>

      {/* Tabela */}
      <TableContainer component={Paper}>
        {loading ? (
          <Box sx={{ display: "flex", justifyContent: "center", py: 4 }}>
            <CircularProgress />
          </Box>
        ) : (
          <>
            <Table>
              <TableHead sx={{ backgroundColor: theme.palette.action.hover }}>
                <TableRow>
                  <TableCell sx={{ fontWeight: 600 }}>Data/Hora</TableCell>
                  <TableCell sx={{ fontWeight: 600 }}>Usuário</TableCell>
                  <TableCell sx={{ fontWeight: 600 }}>Ação</TableCell>
                  <TableCell sx={{ fontWeight: 600 }}>Recurso</TableCell>
                  <TableCell sx={{ fontWeight: 600 }}>Status</TableCell>
                  <TableCell sx={{ fontWeight: 600 }}>
                    IP / User Agent
                  </TableCell>
                  <TableCell sx={{ fontWeight: 600, textAlign: "center" }}>
                    Ações
                  </TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {events.map((event) => (
                  <TableRow
                    key={event.id}
                    hover
                    sx={{
                      backgroundColor:
                        event.status === "failure"
                          ? "rgba(211, 47, 47, 0.05)"
                          : "inherit",
                    }}
                  >
                    <TableCell>
                      {new Date(event.timestamp).toLocaleString("pt-BR")}
                    </TableCell>
                    <TableCell>{event.user_email}</TableCell>
                    <TableCell>
                      <Chip
                        label={event.action}
                        size="small"
                        color={getActionColor(event.action)}
                        variant="outlined"
                      />
                    </TableCell>
                    <TableCell>
                      {event.resource_type} / {event.resource_id}
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={event.status === "success" ? "Sucesso" : "Falha"}
                        size="small"
                        color={getStatusColor(event.status)}
                        variant="outlined"
                      />
                    </TableCell>
                    <TableCell
                      sx={{ fontSize: "0.85rem", color: "text.secondary" }}
                    >
                      <div>{event.ip_address}</div>
                      <div>{event.user_agent?.substring(0, 30)}...</div>
                    </TableCell>
                    <TableCell sx={{ textAlign: "center" }}>
                      <Button
                        size="small"
                        onClick={() => handleShowDetails(event)}
                      >
                        Detalhes
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>

            {events.length === 0 && !loading && (
              <Box sx={{ textAlign: "center", py: 4, color: "text.secondary" }}>
                <Typography>Nenhum evento encontrado</Typography>
              </Box>
            )}
          </>
        )}
      </TableContainer>

      {/* Paginação */}
      {events.length > 0 && (
        <Box
          sx={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            mt: 3,
          }}
        >
          <Typography variant="body2" color="textSecondary">
            Mostrando {page * rowsPerPage + 1} a{" "}
            {Math.min((page + 1) * rowsPerPage, total)} de {total} eventos
          </Typography>
          <Stack direction="row" spacing={1}>
            <Button disabled={page === 0} onClick={() => fetchEvents(page - 1)}>
              Anterior
            </Button>
            <Button variant="outlined">Página {page + 1}</Button>
            <Button
              disabled={(page + 1) * rowsPerPage >= total}
              onClick={() => fetchEvents(page + 1)}
            >
              Próxima
            </Button>
          </Stack>
        </Box>
      )}

      {/* Dialog de detalhes */}
      <Dialog
        open={detailsOpen}
        onClose={() => setDetailsOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Detalhes do Evento</DialogTitle>
        <DialogContent sx={{ py: 3 }}>
          {selectedEvent && (
            <Stack spacing={2}>
              <Box>
                <Typography variant="caption" color="textSecondary">
                  ID do Evento
                </Typography>
                <Typography variant="body2" sx={{ fontFamily: "monospace" }}>
                  {selectedEvent.id}
                </Typography>
              </Box>
              <Box>
                <Typography variant="caption" color="textSecondary">
                  Data/Hora
                </Typography>
                <Typography variant="body2">
                  {new Date(selectedEvent.timestamp).toLocaleString("pt-BR")}
                </Typography>
              </Box>
              <Box>
                <Typography variant="caption" color="textSecondary">
                  Usuário
                </Typography>
                <Typography variant="body2">
                  {selectedEvent.user_email}
                </Typography>
              </Box>
              <Box>
                <Typography variant="caption" color="textSecondary">
                  Ação
                </Typography>
                <Typography variant="body2">{selectedEvent.action}</Typography>
              </Box>
              <Box>
                <Typography variant="caption" color="textSecondary">
                  Recurso
                </Typography>
                <Typography variant="body2">
                  {selectedEvent.resource_type} / {selectedEvent.resource_id}
                </Typography>
              </Box>
              <Box>
                <Typography variant="caption" color="textSecondary">
                  IP Address
                </Typography>
                <Typography variant="body2" sx={{ fontFamily: "monospace" }}>
                  {selectedEvent.ip_address}
                </Typography>
              </Box>
              <Box>
                <Typography variant="caption" color="textSecondary">
                  Detalhes Técnicos
                </Typography>
                <Typography
                  variant="body2"
                  sx={{
                    fontFamily: "monospace",
                    fontSize: "0.75rem",
                    backgroundColor: theme.palette.action.hover,
                    p: 1,
                    borderRadius: 1,
                    overflow: "auto",
                    maxHeight: 200,
                  }}
                >
                  {JSON.stringify(selectedEvent.details, null, 2)}
                </Typography>
              </Box>
            </Stack>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDetailsOpen(false)}>Fechar</Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
};

export default AdminPanel;
