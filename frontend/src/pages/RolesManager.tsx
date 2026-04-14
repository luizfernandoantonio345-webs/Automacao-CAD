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
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  FormControl,
  FormControlLabel,
  Checkbox,
  Typography,
  Alert,
  CircularProgress,
  Stack,
  Card,
  CardHeader,
  CardContent,
  Divider,
} from "@mui/material";
import { useTheme } from "@mui/material/styles";
import axios from "axios";
import { FiPlus, FiEdit2, FiTrash2, FiSave } from "react-icons/fi";

interface Role {
  id: string;
  name: string;
  description: string;
  permissions: string[];
  users_count: number;
  created_at: string;
}

interface Permission {
  id: string;
  name: string;
  description: string;
  category: string;
}

const RolesManager: React.FC = () => {
  const theme = useTheme();
  const [roles, setRoles] = useState<Role[]>([]);
  const [permissions, setPermissions] = useState<Permission[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Dialog states
  const [createOpen, setCreateOpen] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [selectedRole, setSelectedRole] = useState<Role | null>(null);

  // Form state
  const [formData, setFormData] = useState({
    name: "",
    description: "",
    permissions: [] as string[],
  });

  // Fetch roles
  const fetchRoles = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await axios.get("/api/enterprise/roles", {
        headers: {
          Authorization: `Bearer ${localStorage.getItem("access_token") || ""}`,
        },
      });
      setRoles(response.data.roles || []);
    } catch (err: any) {
      setError(err.response?.data?.message || "Falha ao carregar funções");
    } finally {
      setLoading(false);
    }
  };

  // Fetch permissions
  const fetchPermissions = async () => {
    try {
      const response = await axios.get("/api/enterprise/permissions", {
        headers: {
          Authorization: `Bearer ${localStorage.getItem("access_token") || ""}`,
        },
      });
      setPermissions(response.data.permissions || []);
    } catch (err) {
      console.error("Erro ao buscar permissões:", err);
    }
  };

  useEffect(() => {
    fetchRoles();
    fetchPermissions();
  }, []);

  const handleCreateRole = async () => {
    if (!formData.name.trim()) {
      setError("Nome da função é obrigatório");
      return;
    }
    if (formData.permissions.length === 0) {
      setError("Selecione pelo menos uma permissão");
      return;
    }

    try {
      await axios.post(
        "/api/enterprise/roles",
        {
          name: formData.name,
          description: formData.description,
          permissions: formData.permissions,
        },
        {
          headers: {
            Authorization: `Bearer ${localStorage.getItem("access_token") || ""}`,
          },
        },
      );
      setCreateOpen(false);
      setFormData({ name: "", description: "", permissions: [] });
      fetchRoles();
    } catch (err: any) {
      setError(err.response?.data?.message || "Erro ao criar função");
    }
  };

  const handleUpdateRole = async () => {
    if (!selectedRole) return;
    if (!formData.name.trim()) {
      setError("Nome da função é obrigatório");
      return;
    }

    try {
      await axios.patch(
        `/api/enterprise/roles/${selectedRole.id}`,
        {
          name: formData.name,
          description: formData.description,
          permissions: formData.permissions,
        },
        {
          headers: {
            Authorization: `Bearer ${localStorage.getItem("access_token") || ""}`,
          },
        },
      );
      setEditOpen(false);
      setSelectedRole(null);
      setFormData({ name: "", description: "", permissions: [] });
      fetchRoles();
    } catch (err: any) {
      setError(err.response?.data?.message || "Erro ao atualizar função");
    }
  };

  const handleDeleteRole = async (roleId: string) => {
    if (
      window.confirm(
        "Confirmado que deseja remover esta função? Usuários com esta função não perderão acesso.",
      )
    ) {
      try {
        await axios.delete(`/api/enterprise/roles/${roleId}`, {
          headers: {
            Authorization: `Bearer ${localStorage.getItem("access_token") || ""}`,
          },
        });
        fetchRoles();
      } catch (err: any) {
        setError(err.response?.data?.message || "Erro ao deletar função");
      }
    }
  };

  const handleEditClick = (role: Role) => {
    setSelectedRole(role);
    setFormData({
      name: role.name,
      description: role.description,
      permissions: role.permissions,
    });
    setEditOpen(true);
  };

  const handleCreateClick = () => {
    setSelectedRole(null);
    setFormData({ name: "", description: "", permissions: [] });
    setCreateOpen(true);
  };

  const togglePermission = (permissionId: string) => {
    setFormData((prev) => ({
      ...prev,
      permissions: prev.permissions.includes(permissionId)
        ? prev.permissions.filter((p) => p !== permissionId)
        : [...prev.permissions, permissionId],
    }));
  };

  const groupedPermissions = permissions.reduce(
    (acc, perm) => {
      if (!acc[perm.category]) {
        acc[perm.category] = [];
      }
      acc[perm.category].push(perm);
      return acc;
    },
    {} as Record<string, Permission[]>,
  );

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Box sx={{ mb: 4 }}>
        <Typography
          variant="h4"
          sx={{ mb: 2, fontWeight: 600, color: theme.palette.primary.main }}
        >
          Gerenciador de Funções
        </Typography>
        <Typography variant="body2" color="textSecondary">
          Criar e gerenciar funções de usuário com permissões específicas
        </Typography>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      <Button
        variant="contained"
        color="primary"
        startIcon={<FiPlus size={16} />}
        onClick={handleCreateClick}
        sx={{ mb: 3 }}
      >
        Nova Função
      </Button>

      {loading ? (
        <Box sx={{ display: "flex", justifyContent: "center", py: 4 }}>
          <CircularProgress />
        </Box>
      ) : (
        <TableContainer component={Paper}>
          <Table>
            <TableHead sx={{ backgroundColor: theme.palette.action.hover }}>
              <TableRow>
                <TableCell sx={{ fontWeight: 600 }}>Nome</TableCell>
                <TableCell sx={{ fontWeight: 600 }}>Descrição</TableCell>
                <TableCell sx={{ fontWeight: 600 }}>Permissões</TableCell>
                <TableCell sx={{ fontWeight: 600 }}>Usuários</TableCell>
                <TableCell sx={{ fontWeight: 600, textAlign: "center" }}>
                  Ações
                </TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {roles.map((role) => (
                <TableRow key={role.id} hover>
                  <TableCell sx={{ fontWeight: 500 }}>{role.name}</TableCell>
                  <TableCell sx={{ color: "text.secondary" }}>
                    {role.description}
                  </TableCell>
                  <TableCell>{role.permissions.length} permissões</TableCell>
                  <TableCell>{role.users_count}</TableCell>
                  <TableCell sx={{ textAlign: "center" }}>
                    <Button
                      size="small"
                      startIcon={<FiEdit2 size={14} />}
                      onClick={() => handleEditClick(role)}
                    >
                      Editar
                    </Button>
                    <Button
                      size="small"
                      color="error"
                      startIcon={<FiTrash2 size={14} />}
                      onClick={() => handleDeleteRole(role.id)}
                    >
                      Deletar
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          {roles.length === 0 && (
            <Box sx={{ textAlign: "center", py: 4, color: "text.secondary" }}>
              <Typography>Nenhuma função criada ainda</Typography>
            </Box>
          )}
        </TableContainer>
      )}

      {/* Create/Edit Dialog */}
      <Dialog
        open={createOpen || editOpen}
        onClose={() => {
          setCreateOpen(false);
          setEditOpen(false);
        }}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>
          {selectedRole ? "Editar Função" : "Nova Função"}
        </DialogTitle>
        <DialogContent sx={{ py: 3 }}>
          <Stack spacing={3}>
            <TextField
              fullWidth
              label="Nome da Função"
              value={formData.name}
              onChange={(e) =>
                setFormData({ ...formData, name: e.target.value })
              }
              placeholder="ex: Gerenciador"
            />
            <TextField
              fullWidth
              multiline
              rows={3}
              label="Descrição"
              value={formData.description}
              onChange={(e) =>
                setFormData({ ...formData, description: e.target.value })
              }
              placeholder="Descreva esta função"
            />

            <Card>
              <CardHeader title="Permissões" />
              <CardContent>
                <Stack spacing={2}>
                  {Object.entries(groupedPermissions).map(
                    ([category, perms]) => (
                      <Box key={category}>
                        <Typography
                          variant="subtitle2"
                          sx={{
                            mb: 1,
                            fontWeight: 600,
                            color: theme.palette.primary.main,
                          }}
                        >
                          {category}
                        </Typography>
                        <Stack sx={{ pl: 2 }}>
                          {perms.map((perm) => (
                            <FormControlLabel
                              key={perm.id}
                              control={
                                <Checkbox
                                  checked={formData.permissions.includes(
                                    perm.id,
                                  )}
                                  onChange={() => togglePermission(perm.id)}
                                />
                              }
                              label={
                                <Box>
                                  <Typography variant="body2">
                                    {perm.name}
                                  </Typography>
                                  <Typography
                                    variant="caption"
                                    color="textSecondary"
                                  >
                                    {perm.description}
                                  </Typography>
                                </Box>
                              }
                            />
                          ))}
                        </Stack>
                      </Box>
                    ),
                  )}
                </Stack>
              </CardContent>
            </Card>
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button
            onClick={() => {
              setCreateOpen(false);
              setEditOpen(false);
            }}
          >
            Cancelar
          </Button>
          <Button
            variant="contained"
            startIcon={<FiSave size={16} />}
            onClick={selectedRole ? handleUpdateRole : handleCreateRole}
          >
            {selectedRole ? "Atualizar" : "Criar"}
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
};

export default RolesManager;
