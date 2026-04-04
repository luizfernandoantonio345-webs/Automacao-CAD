/**
 * ═══════════════════════════════════════════════════════════════════════════════
 * CncMaterialLibrary - Banco de Materiais Personalizável
 * ═══════════════════════════════════════════════════════════════════════════════
 *
 * Melhoria #3: CRUD completo para materiais customizados
 * - Cadastro de novos materiais
 * - Parâmetros de corte por espessura
 * - Importação/Exportação JSON
 * - Materiais favoritos
 */

import React, { useState, useEffect, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Database,
  Plus,
  Edit3,
  Trash2,
  Star,
  StarOff,
  Search,
  Download,
  Upload,
  Copy,
  Save,
  X,
  Layers,
  Flame,
  Wind,
  Droplet,
  Settings,
  AlertTriangle,
  Check,
  ChevronDown,
  ChevronRight,
  FileJson,
} from "lucide-react";

interface CutParameter {
  thickness: number; // mm
  feedRate: number; // mm/min
  pierceTime: number; // seconds
  cutHeight: number; // mm
  pierceHeight: number; // mm
  amperage: number; // A
  kerf: number; // mm
  gasFlow?: number; // L/min
  secondaryGas?: string;
}

interface Material {
  id: string;
  name: string;
  type: "ferrous" | "non-ferrous" | "exotic";
  density: number; // kg/m³
  thermalConductivity: number; // W/(m·K)
  meltingPoint: number; // °C
  color: string;
  favorite: boolean;
  parameters: CutParameter[];
  notes?: string;
  createdAt: string;
  updatedAt: string;
}

interface CncMaterialLibraryProps {
  theme: {
    surface: string;
    surfaceAlt: string;
    border: string;
    accentPrimary: string;
    success: string;
    warning: string;
    danger: string;
    textPrimary: string;
    textSecondary: string;
  };
  onSelectMaterial?: (material: Material) => void;
}

// Default materials
const defaultMaterials: Material[] = [
  {
    id: "mat-001",
    name: "Aço Carbono",
    type: "ferrous",
    density: 7850,
    thermalConductivity: 50,
    meltingPoint: 1500,
    color: "#4A4A4A",
    favorite: true,
    parameters: [
      {
        thickness: 3,
        feedRate: 4500,
        pierceTime: 0.3,
        cutHeight: 1.5,
        pierceHeight: 3,
        amperage: 45,
        kerf: 1.2,
      },
      {
        thickness: 6,
        feedRate: 2800,
        pierceTime: 0.5,
        cutHeight: 1.8,
        pierceHeight: 4,
        amperage: 65,
        kerf: 1.5,
      },
      {
        thickness: 10,
        feedRate: 1800,
        pierceTime: 0.8,
        cutHeight: 2.0,
        pierceHeight: 5,
        amperage: 85,
        kerf: 1.8,
      },
      {
        thickness: 12,
        feedRate: 1400,
        pierceTime: 1.0,
        cutHeight: 2.2,
        pierceHeight: 6,
        amperage: 105,
        kerf: 2.0,
      },
      {
        thickness: 20,
        feedRate: 800,
        pierceTime: 1.5,
        cutHeight: 2.5,
        pierceHeight: 8,
        amperage: 130,
        kerf: 2.5,
      },
    ],
    createdAt: "2024-01-01",
    updatedAt: "2024-01-01",
  },
  {
    id: "mat-002",
    name: "Aço Inox 304",
    type: "ferrous",
    density: 8000,
    thermalConductivity: 16,
    meltingPoint: 1450,
    color: "#C0C0C0",
    favorite: true,
    parameters: [
      {
        thickness: 3,
        feedRate: 3800,
        pierceTime: 0.4,
        cutHeight: 1.5,
        pierceHeight: 3.5,
        amperage: 55,
        kerf: 1.3,
        gasFlow: 20,
        secondaryGas: "N2",
      },
      {
        thickness: 6,
        feedRate: 2200,
        pierceTime: 0.6,
        cutHeight: 1.8,
        pierceHeight: 4.5,
        amperage: 80,
        kerf: 1.6,
        gasFlow: 25,
        secondaryGas: "N2",
      },
      {
        thickness: 10,
        feedRate: 1400,
        pierceTime: 1.0,
        cutHeight: 2.0,
        pierceHeight: 5.5,
        amperage: 100,
        kerf: 2.0,
        gasFlow: 30,
        secondaryGas: "N2",
      },
    ],
    createdAt: "2024-01-01",
    updatedAt: "2024-01-01",
  },
  {
    id: "mat-003",
    name: "Alumínio",
    type: "non-ferrous",
    density: 2700,
    thermalConductivity: 237,
    meltingPoint: 660,
    color: "#E8E8E8",
    favorite: false,
    parameters: [
      {
        thickness: 3,
        feedRate: 5000,
        pierceTime: 0.2,
        cutHeight: 1.2,
        pierceHeight: 2.5,
        amperage: 60,
        kerf: 1.4,
        gasFlow: 40,
        secondaryGas: "N2",
      },
      {
        thickness: 6,
        feedRate: 3500,
        pierceTime: 0.4,
        cutHeight: 1.5,
        pierceHeight: 3.5,
        amperage: 90,
        kerf: 1.8,
        gasFlow: 50,
        secondaryGas: "N2",
      },
    ],
    createdAt: "2024-01-01",
    updatedAt: "2024-01-01",
  },
];

const CncMaterialLibrary: React.FC<CncMaterialLibraryProps> = ({
  theme,
  onSelectMaterial,
}) => {
  const [materials, setMaterials] = useState<Material[]>(defaultMaterials);
  const [searchTerm, setSearchTerm] = useState("");
  const [typeFilter, setTypeFilter] = useState<string>("all");
  const [showFavoritesOnly, setShowFavoritesOnly] = useState(false);
  const [expandedMaterial, setExpandedMaterial] = useState<string | null>(null);
  const [editingMaterial, setEditingMaterial] = useState<Material | null>(null);
  const [showNewModal, setShowNewModal] = useState(false);
  const [notification, setNotification] = useState<{
    type: "success" | "error";
    message: string;
  } | null>(null);

  // Filtered materials
  const filteredMaterials = useMemo(() => {
    let result = [...materials];

    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      result = result.filter((m) => m.name.toLowerCase().includes(term));
    }

    if (typeFilter !== "all") {
      result = result.filter((m) => m.type === typeFilter);
    }

    if (showFavoritesOnly) {
      result = result.filter((m) => m.favorite);
    }

    // Sort: favorites first, then alphabetically
    result.sort((a, b) => {
      if (a.favorite && !b.favorite) return -1;
      if (!a.favorite && b.favorite) return 1;
      return a.name.localeCompare(b.name);
    });

    return result;
  }, [materials, searchTerm, typeFilter, showFavoritesOnly]);

  const showNotification = (type: "success" | "error", message: string) => {
    setNotification({ type, message });
    setTimeout(() => setNotification(null), 3000);
  };

  const toggleFavorite = (id: string) => {
    setMaterials((prev) =>
      prev.map((m) => (m.id === id ? { ...m, favorite: !m.favorite } : m)),
    );
  };

  const deleteMaterial = (id: string) => {
    if (confirm("Tem certeza que deseja excluir este material?")) {
      setMaterials((prev) => prev.filter((m) => m.id !== id));
      showNotification("success", "Material excluído com sucesso");
    }
  };

  const duplicateMaterial = (material: Material) => {
    const newMaterial: Material = {
      ...material,
      id: `mat-${Date.now()}`,
      name: `${material.name} (Cópia)`,
      favorite: false,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };
    setMaterials((prev) => [...prev, newMaterial]);
    showNotification("success", "Material duplicado com sucesso");
  };

  const exportMaterials = () => {
    const data = JSON.stringify(materials, null, 2);
    const blob = new Blob([data], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "materiais_plasma.json";
    a.click();
    URL.revokeObjectURL(url);
    showNotification("success", "Materiais exportados com sucesso");
  };

  const importMaterials = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const imported = JSON.parse(e.target?.result as string) as Material[];
        setMaterials((prev) => [
          ...prev,
          ...imported.map((m) => ({
            ...m,
            id: `mat-${Date.now()}-${Math.random()}`,
          })),
        ]);
        showNotification("success", `${imported.length} materiais importados`);
      } catch {
        showNotification("error", "Erro ao importar arquivo JSON");
      }
    };
    reader.readAsText(file);
    event.target.value = "";
  };

  const getTypeLabel = (type: Material["type"]) => {
    switch (type) {
      case "ferrous":
        return "Ferroso";
      case "non-ferrous":
        return "Não-Ferroso";
      case "exotic":
        return "Exótico";
      default:
        return type;
    }
  };

  const getTypeColor = (type: Material["type"]) => {
    switch (type) {
      case "ferrous":
        return theme.accentPrimary;
      case "non-ferrous":
        return theme.success;
      case "exotic":
        return theme.warning;
      default:
        return theme.textSecondary;
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      style={{ display: "flex", flexDirection: "column", gap: 20 }}
    >
      {/* Notification */}
      <AnimatePresence>
        {notification && (
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            style={{
              position: "fixed",
              top: 20,
              right: 20,
              padding: "12px 20px",
              borderRadius: 8,
              background:
                notification.type === "success" ? theme.success : theme.danger,
              color: "#FFF",
              display: "flex",
              alignItems: "center",
              gap: 8,
              zIndex: 1000,
              boxShadow: "0 4px 12px rgba(0,0,0,0.3)",
            }}
          >
            {notification.type === "success" ? (
              <Check size={18} />
            ) : (
              <AlertTriangle size={18} />
            )}
            {notification.message}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Header */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <Database size={24} color={theme.accentPrimary} />
          <h2 style={{ margin: 0, color: theme.textPrimary, fontSize: 20 }}>
            Biblioteca de Materiais
          </h2>
          <span
            style={{
              padding: "4px 8px",
              borderRadius: 4,
              background: `${theme.accentPrimary}20`,
              color: theme.accentPrimary,
              fontSize: 12,
              fontWeight: 500,
            }}
          >
            {materials.length} materiais
          </span>
        </div>

        <div style={{ display: "flex", gap: 8 }}>
          <label
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              padding: "8px 16px",
              borderRadius: 6,
              border: `1px solid ${theme.border}`,
              background: "transparent",
              color: theme.textSecondary,
              cursor: "pointer",
              fontSize: 13,
            }}
          >
            <Upload size={16} />
            Importar
            <input
              type="file"
              accept=".json"
              onChange={importMaterials}
              style={{ display: "none" }}
            />
          </label>

          <button
            onClick={exportMaterials}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              padding: "8px 16px",
              borderRadius: 6,
              border: `1px solid ${theme.border}`,
              background: "transparent",
              color: theme.textSecondary,
              cursor: "pointer",
              fontSize: 13,
            }}
          >
            <Download size={16} />
            Exportar
          </button>

          <button
            onClick={() => setShowNewModal(true)}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              padding: "8px 16px",
              borderRadius: 6,
              border: "none",
              background: theme.accentPrimary,
              color: "#FFF",
              cursor: "pointer",
              fontSize: 13,
              fontWeight: 500,
            }}
          >
            <Plus size={16} />
            Novo Material
          </button>
        </div>
      </div>

      {/* Filters */}
      <div
        style={{
          display: "flex",
          gap: 12,
          padding: 16,
          background: theme.surface,
          border: `1px solid ${theme.border}`,
          borderRadius: 8,
        }}
      >
        {/* Search */}
        <div style={{ flex: 1, position: "relative" }}>
          <Search
            size={16}
            style={{
              position: "absolute",
              left: 12,
              top: "50%",
              transform: "translateY(-50%)",
              color: theme.textSecondary,
            }}
          />
          <input
            type="text"
            placeholder="Buscar material..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            style={{
              width: "100%",
              padding: "8px 12px 8px 36px",
              borderRadius: 6,
              border: `1px solid ${theme.border}`,
              background: theme.surfaceAlt,
              color: theme.textPrimary,
              fontSize: 14,
            }}
          />
        </div>

        {/* Type filter */}
        <select
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
          style={{
            padding: "8px 12px",
            borderRadius: 6,
            border: `1px solid ${theme.border}`,
            background: theme.surfaceAlt,
            color: theme.textPrimary,
            fontSize: 14,
          }}
        >
          <option value="all">Todos os Tipos</option>
          <option value="ferrous">Ferrosos</option>
          <option value="non-ferrous">Não-Ferrosos</option>
          <option value="exotic">Exóticos</option>
        </select>

        {/* Favorites toggle */}
        <button
          onClick={() => setShowFavoritesOnly(!showFavoritesOnly)}
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            padding: "8px 16px",
            borderRadius: 6,
            border: `1px solid ${showFavoritesOnly ? theme.warning : theme.border}`,
            background: showFavoritesOnly
              ? `${theme.warning}20`
              : "transparent",
            color: showFavoritesOnly ? theme.warning : theme.textSecondary,
            cursor: "pointer",
            fontSize: 13,
          }}
        >
          <Star size={16} fill={showFavoritesOnly ? theme.warning : "none"} />
          Favoritos
        </button>
      </div>

      {/* Material List */}
      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        <AnimatePresence>
          {filteredMaterials.map((material) => (
            <motion.div
              key={material.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              style={{
                background: theme.surface,
                border: `1px solid ${theme.border}`,
                borderRadius: 8,
                overflow: "hidden",
              }}
            >
              {/* Material Header */}
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  padding: 16,
                  cursor: "pointer",
                }}
                onClick={() =>
                  setExpandedMaterial(
                    expandedMaterial === material.id ? null : material.id,
                  )
                }
              >
                <div
                  style={{
                    width: 8,
                    height: 40,
                    borderRadius: 4,
                    background: material.color,
                    marginRight: 16,
                  }}
                />

                <div style={{ flex: 1 }}>
                  <div
                    style={{ display: "flex", alignItems: "center", gap: 8 }}
                  >
                    <span
                      style={{
                        color: theme.textPrimary,
                        fontWeight: 600,
                        fontSize: 15,
                      }}
                    >
                      {material.name}
                    </span>
                    <span
                      style={{
                        padding: "2px 6px",
                        borderRadius: 4,
                        background: `${getTypeColor(material.type)}20`,
                        color: getTypeColor(material.type),
                        fontSize: 11,
                        fontWeight: 500,
                      }}
                    >
                      {getTypeLabel(material.type)}
                    </span>
                  </div>
                  <div
                    style={{
                      color: theme.textSecondary,
                      fontSize: 12,
                      marginTop: 4,
                      display: "flex",
                      gap: 16,
                    }}
                  >
                    <span>Densidade: {material.density} kg/m³</span>
                    <span>Fusão: {material.meltingPoint}°C</span>
                    <span>
                      {material.parameters.length} espessuras configuradas
                    </span>
                  </div>
                </div>

                {/* Actions */}
                <div
                  style={{ display: "flex", gap: 8 }}
                  onClick={(e) => e.stopPropagation()}
                >
                  <button
                    onClick={() => toggleFavorite(material.id)}
                    style={{
                      width: 32,
                      height: 32,
                      borderRadius: 6,
                      border: "none",
                      background: "transparent",
                      color: material.favorite
                        ? theme.warning
                        : theme.textSecondary,
                      cursor: "pointer",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                    }}
                  >
                    <Star
                      size={18}
                      fill={material.favorite ? theme.warning : "none"}
                    />
                  </button>

                  <button
                    onClick={() => onSelectMaterial?.(material)}
                    style={{
                      padding: "6px 12px",
                      borderRadius: 6,
                      border: `1px solid ${theme.accentPrimary}`,
                      background: "transparent",
                      color: theme.accentPrimary,
                      cursor: "pointer",
                      fontSize: 12,
                      fontWeight: 500,
                    }}
                  >
                    Selecionar
                  </button>

                  <button
                    onClick={() => duplicateMaterial(material)}
                    style={{
                      width: 32,
                      height: 32,
                      borderRadius: 6,
                      border: `1px solid ${theme.border}`,
                      background: "transparent",
                      color: theme.textSecondary,
                      cursor: "pointer",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                    }}
                    title="Duplicar"
                  >
                    <Copy size={14} />
                  </button>

                  <button
                    onClick={() => setEditingMaterial(material)}
                    style={{
                      width: 32,
                      height: 32,
                      borderRadius: 6,
                      border: `1px solid ${theme.border}`,
                      background: "transparent",
                      color: theme.textSecondary,
                      cursor: "pointer",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                    }}
                    title="Editar"
                  >
                    <Edit3 size={14} />
                  </button>

                  <button
                    onClick={() => deleteMaterial(material.id)}
                    style={{
                      width: 32,
                      height: 32,
                      borderRadius: 6,
                      border: `1px solid ${theme.danger}`,
                      background: "transparent",
                      color: theme.danger,
                      cursor: "pointer",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                    }}
                    title="Excluir"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>

                <div style={{ marginLeft: 16, color: theme.textSecondary }}>
                  {expandedMaterial === material.id ? (
                    <ChevronDown size={20} />
                  ) : (
                    <ChevronRight size={20} />
                  )}
                </div>
              </div>

              {/* Expanded Parameters */}
              <AnimatePresence>
                {expandedMaterial === material.id && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: "auto", opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    style={{ overflow: "hidden" }}
                  >
                    <div
                      style={{
                        padding: 16,
                        paddingTop: 0,
                        borderTop: `1px solid ${theme.border}`,
                      }}
                    >
                      <h4
                        style={{
                          margin: "16px 0 12px",
                          color: theme.textPrimary,
                          fontSize: 14,
                          display: "flex",
                          alignItems: "center",
                          gap: 8,
                        }}
                      >
                        <Settings size={16} />
                        Parâmetros de Corte por Espessura
                      </h4>

                      <div style={{ overflowX: "auto" }}>
                        <table
                          style={{
                            width: "100%",
                            borderCollapse: "collapse",
                            fontSize: 13,
                          }}
                        >
                          <thead>
                            <tr style={{ background: theme.surfaceAlt }}>
                              <th
                                style={{
                                  padding: 10,
                                  textAlign: "left",
                                  color: theme.textSecondary,
                                  fontWeight: 500,
                                }}
                              >
                                Espessura
                              </th>
                              <th
                                style={{
                                  padding: 10,
                                  textAlign: "left",
                                  color: theme.textSecondary,
                                  fontWeight: 500,
                                }}
                              >
                                Velocidade
                              </th>
                              <th
                                style={{
                                  padding: 10,
                                  textAlign: "left",
                                  color: theme.textSecondary,
                                  fontWeight: 500,
                                }}
                              >
                                Pierce Time
                              </th>
                              <th
                                style={{
                                  padding: 10,
                                  textAlign: "left",
                                  color: theme.textSecondary,
                                  fontWeight: 500,
                                }}
                              >
                                Altura Corte
                              </th>
                              <th
                                style={{
                                  padding: 10,
                                  textAlign: "left",
                                  color: theme.textSecondary,
                                  fontWeight: 500,
                                }}
                              >
                                Amperagem
                              </th>
                              <th
                                style={{
                                  padding: 10,
                                  textAlign: "left",
                                  color: theme.textSecondary,
                                  fontWeight: 500,
                                }}
                              >
                                Kerf
                              </th>
                              {material.parameters.some((p) => p.gasFlow) && (
                                <th
                                  style={{
                                    padding: 10,
                                    textAlign: "left",
                                    color: theme.textSecondary,
                                    fontWeight: 500,
                                  }}
                                >
                                  Gás
                                </th>
                              )}
                            </tr>
                          </thead>
                          <tbody>
                            {material.parameters.map((param, idx) => (
                              <tr
                                key={idx}
                                style={{
                                  borderTop: `1px solid ${theme.border}`,
                                }}
                              >
                                <td
                                  style={{
                                    padding: 10,
                                    color: theme.textPrimary,
                                    fontWeight: 500,
                                  }}
                                >
                                  {param.thickness} mm
                                </td>
                                <td
                                  style={{
                                    padding: 10,
                                    color: theme.textSecondary,
                                  }}
                                >
                                  {param.feedRate} mm/min
                                </td>
                                <td
                                  style={{
                                    padding: 10,
                                    color: theme.textSecondary,
                                  }}
                                >
                                  {param.pierceTime}s
                                </td>
                                <td
                                  style={{
                                    padding: 10,
                                    color: theme.textSecondary,
                                  }}
                                >
                                  {param.cutHeight} mm
                                </td>
                                <td
                                  style={{
                                    padding: 10,
                                    color: theme.textSecondary,
                                  }}
                                >
                                  {param.amperage} A
                                </td>
                                <td
                                  style={{
                                    padding: 10,
                                    color: theme.textSecondary,
                                  }}
                                >
                                  {param.kerf} mm
                                </td>
                                {material.parameters.some((p) => p.gasFlow) && (
                                  <td
                                    style={{
                                      padding: 10,
                                      color: theme.textSecondary,
                                    }}
                                  >
                                    {param.gasFlow
                                      ? `${param.secondaryGas} ${param.gasFlow} L/min`
                                      : "-"}
                                  </td>
                                )}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>

                      {material.notes && (
                        <div
                          style={{
                            marginTop: 12,
                            padding: 12,
                            background: theme.surfaceAlt,
                            borderRadius: 6,
                            color: theme.textSecondary,
                            fontSize: 12,
                          }}
                        >
                          <strong>Notas:</strong> {material.notes}
                        </div>
                      )}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.div>
          ))}
        </AnimatePresence>

        {filteredMaterials.length === 0 && (
          <div
            style={{
              padding: 40,
              textAlign: "center",
              color: theme.textSecondary,
            }}
          >
            <Database size={40} style={{ opacity: 0.5, marginBottom: 12 }} />
            <div>Nenhum material encontrado</div>
          </div>
        )}
      </div>

      {/* New/Edit Material Modal */}
      <AnimatePresence>
        {(showNewModal || editingMaterial) && (
          <MaterialModal
            material={editingMaterial}
            theme={theme}
            onSave={(material) => {
              if (editingMaterial) {
                setMaterials((prev) =>
                  prev.map((m) => (m.id === material.id ? material : m)),
                );
                showNotification("success", "Material atualizado com sucesso");
              } else {
                setMaterials((prev) => [
                  ...prev,
                  { ...material, id: `mat-${Date.now()}` },
                ]);
                showNotification("success", "Material criado com sucesso");
              }
              setShowNewModal(false);
              setEditingMaterial(null);
            }}
            onClose={() => {
              setShowNewModal(false);
              setEditingMaterial(null);
            }}
          />
        )}
      </AnimatePresence>
    </motion.div>
  );
};

// Modal for creating/editing materials
const MaterialModal: React.FC<{
  material: Material | null;
  theme: CncMaterialLibraryProps["theme"];
  onSave: (material: Material) => void;
  onClose: () => void;
}> = ({ material, theme, onSave, onClose }) => {
  const [formData, setFormData] = useState<Partial<Material>>(
    material || {
      name: "",
      type: "ferrous",
      density: 7850,
      thermalConductivity: 50,
      meltingPoint: 1500,
      color: "#4A4A4A",
      favorite: false,
      parameters: [
        {
          thickness: 3,
          feedRate: 3000,
          pierceTime: 0.5,
          cutHeight: 1.5,
          pierceHeight: 3,
          amperage: 50,
          kerf: 1.5,
        },
      ],
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    },
  );

  const addParameter = () => {
    setFormData((prev) => ({
      ...prev,
      parameters: [
        ...(prev.parameters || []),
        {
          thickness: 6,
          feedRate: 2000,
          pierceTime: 0.8,
          cutHeight: 1.8,
          pierceHeight: 4,
          amperage: 70,
          kerf: 1.8,
        },
      ],
    }));
  };

  const removeParameter = (index: number) => {
    setFormData((prev) => ({
      ...prev,
      parameters: prev.parameters?.filter((_, i) => i !== index),
    }));
  };

  const updateParameter = (
    index: number,
    field: keyof CutParameter,
    value: number,
  ) => {
    setFormData((prev) => ({
      ...prev,
      parameters: prev.parameters?.map((p, i) =>
        i === index ? { ...p, [field]: value } : p,
      ),
    }));
  };

  const handleSave = () => {
    if (!formData.name) {
      alert("Nome é obrigatório");
      return;
    }
    onSave({
      ...formData,
      id: material?.id || "",
      updatedAt: new Date().toISOString(),
    } as Material);
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.7)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 1000,
      }}
      onClick={onClose}
    >
      <motion.div
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0.9, opacity: 0 }}
        style={{
          background: theme.surface,
          borderRadius: 12,
          width: "90%",
          maxWidth: 800,
          maxHeight: "90vh",
          overflow: "auto",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            padding: 20,
            borderBottom: `1px solid ${theme.border}`,
          }}
        >
          <h3 style={{ margin: 0, color: theme.textPrimary }}>
            {material ? "Editar Material" : "Novo Material"}
          </h3>
          <button
            onClick={onClose}
            style={{
              width: 32,
              height: 32,
              borderRadius: 6,
              border: "none",
              background: "transparent",
              color: theme.textSecondary,
              cursor: "pointer",
            }}
          >
            <X size={20} />
          </button>
        </div>

        {/* Form */}
        <div style={{ padding: 20 }}>
          {/* Basic info */}
          <div
            style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}
          >
            <div>
              <label style={{ color: theme.textSecondary, fontSize: 12 }}>
                Nome
              </label>
              <input
                type="text"
                value={formData.name || ""}
                onChange={(e) =>
                  setFormData({ ...formData, name: e.target.value })
                }
                style={{
                  width: "100%",
                  padding: 10,
                  borderRadius: 6,
                  border: `1px solid ${theme.border}`,
                  background: theme.surfaceAlt,
                  color: theme.textPrimary,
                  marginTop: 4,
                }}
              />
            </div>
            <div>
              <label style={{ color: theme.textSecondary, fontSize: 12 }}>
                Tipo
              </label>
              <select
                value={formData.type}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    type: e.target.value as Material["type"],
                  })
                }
                style={{
                  width: "100%",
                  padding: 10,
                  borderRadius: 6,
                  border: `1px solid ${theme.border}`,
                  background: theme.surfaceAlt,
                  color: theme.textPrimary,
                  marginTop: 4,
                }}
              >
                <option value="ferrous">Ferroso</option>
                <option value="non-ferrous">Não-Ferroso</option>
                <option value="exotic">Exótico</option>
              </select>
            </div>
            <div>
              <label style={{ color: theme.textSecondary, fontSize: 12 }}>
                Densidade (kg/m³)
              </label>
              <input
                type="number"
                value={formData.density}
                onChange={(e) =>
                  setFormData({ ...formData, density: Number(e.target.value) })
                }
                style={{
                  width: "100%",
                  padding: 10,
                  borderRadius: 6,
                  border: `1px solid ${theme.border}`,
                  background: theme.surfaceAlt,
                  color: theme.textPrimary,
                  marginTop: 4,
                }}
              />
            </div>
            <div>
              <label style={{ color: theme.textSecondary, fontSize: 12 }}>
                Ponto de Fusão (°C)
              </label>
              <input
                type="number"
                value={formData.meltingPoint}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    meltingPoint: Number(e.target.value),
                  })
                }
                style={{
                  width: "100%",
                  padding: 10,
                  borderRadius: 6,
                  border: `1px solid ${theme.border}`,
                  background: theme.surfaceAlt,
                  color: theme.textPrimary,
                  marginTop: 4,
                }}
              />
            </div>
            <div>
              <label style={{ color: theme.textSecondary, fontSize: 12 }}>
                Cor
              </label>
              <input
                type="color"
                value={formData.color}
                onChange={(e) =>
                  setFormData({ ...formData, color: e.target.value })
                }
                style={{
                  width: "100%",
                  height: 42,
                  borderRadius: 6,
                  border: `1px solid ${theme.border}`,
                  cursor: "pointer",
                  marginTop: 4,
                }}
              />
            </div>
          </div>

          {/* Parameters */}
          <div style={{ marginTop: 24 }}>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                marginBottom: 12,
              }}
            >
              <h4 style={{ margin: 0, color: theme.textPrimary, fontSize: 14 }}>
                Parâmetros de Corte
              </h4>
              <button
                onClick={addParameter}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 6,
                  padding: "6px 12px",
                  borderRadius: 6,
                  border: `1px solid ${theme.accentPrimary}`,
                  background: "transparent",
                  color: theme.accentPrimary,
                  cursor: "pointer",
                  fontSize: 12,
                }}
              >
                <Plus size={14} />
                Adicionar Espessura
              </button>
            </div>

            {formData.parameters?.map((param, idx) => (
              <div
                key={idx}
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(7, 1fr) auto",
                  gap: 8,
                  marginBottom: 8,
                  alignItems: "end",
                }}
              >
                <div>
                  <label style={{ color: theme.textSecondary, fontSize: 10 }}>
                    Esp. (mm)
                  </label>
                  <input
                    type="number"
                    value={param.thickness}
                    onChange={(e) =>
                      updateParameter(idx, "thickness", Number(e.target.value))
                    }
                    style={{
                      width: "100%",
                      padding: 8,
                      borderRadius: 4,
                      border: `1px solid ${theme.border}`,
                      background: theme.surfaceAlt,
                      color: theme.textPrimary,
                      fontSize: 12,
                    }}
                  />
                </div>
                <div>
                  <label style={{ color: theme.textSecondary, fontSize: 10 }}>
                    Vel. (mm/min)
                  </label>
                  <input
                    type="number"
                    value={param.feedRate}
                    onChange={(e) =>
                      updateParameter(idx, "feedRate", Number(e.target.value))
                    }
                    style={{
                      width: "100%",
                      padding: 8,
                      borderRadius: 4,
                      border: `1px solid ${theme.border}`,
                      background: theme.surfaceAlt,
                      color: theme.textPrimary,
                      fontSize: 12,
                    }}
                  />
                </div>
                <div>
                  <label style={{ color: theme.textSecondary, fontSize: 10 }}>
                    Pierce (s)
                  </label>
                  <input
                    type="number"
                    step="0.1"
                    value={param.pierceTime}
                    onChange={(e) =>
                      updateParameter(idx, "pierceTime", Number(e.target.value))
                    }
                    style={{
                      width: "100%",
                      padding: 8,
                      borderRadius: 4,
                      border: `1px solid ${theme.border}`,
                      background: theme.surfaceAlt,
                      color: theme.textPrimary,
                      fontSize: 12,
                    }}
                  />
                </div>
                <div>
                  <label style={{ color: theme.textSecondary, fontSize: 10 }}>
                    Altura (mm)
                  </label>
                  <input
                    type="number"
                    step="0.1"
                    value={param.cutHeight}
                    onChange={(e) =>
                      updateParameter(idx, "cutHeight", Number(e.target.value))
                    }
                    style={{
                      width: "100%",
                      padding: 8,
                      borderRadius: 4,
                      border: `1px solid ${theme.border}`,
                      background: theme.surfaceAlt,
                      color: theme.textPrimary,
                      fontSize: 12,
                    }}
                  />
                </div>
                <div>
                  <label style={{ color: theme.textSecondary, fontSize: 10 }}>
                    Amp. (A)
                  </label>
                  <input
                    type="number"
                    value={param.amperage}
                    onChange={(e) =>
                      updateParameter(idx, "amperage", Number(e.target.value))
                    }
                    style={{
                      width: "100%",
                      padding: 8,
                      borderRadius: 4,
                      border: `1px solid ${theme.border}`,
                      background: theme.surfaceAlt,
                      color: theme.textPrimary,
                      fontSize: 12,
                    }}
                  />
                </div>
                <div>
                  <label style={{ color: theme.textSecondary, fontSize: 10 }}>
                    Kerf (mm)
                  </label>
                  <input
                    type="number"
                    step="0.1"
                    value={param.kerf}
                    onChange={(e) =>
                      updateParameter(idx, "kerf", Number(e.target.value))
                    }
                    style={{
                      width: "100%",
                      padding: 8,
                      borderRadius: 4,
                      border: `1px solid ${theme.border}`,
                      background: theme.surfaceAlt,
                      color: theme.textPrimary,
                      fontSize: 12,
                    }}
                  />
                </div>
                <div>
                  <label style={{ color: theme.textSecondary, fontSize: 10 }}>
                    Gás (L/min)
                  </label>
                  <input
                    type="number"
                    value={param.gasFlow || ""}
                    onChange={(e) =>
                      updateParameter(
                        idx,
                        "gasFlow",
                        Number(e.target.value) || 0,
                      )
                    }
                    style={{
                      width: "100%",
                      padding: 8,
                      borderRadius: 4,
                      border: `1px solid ${theme.border}`,
                      background: theme.surfaceAlt,
                      color: theme.textPrimary,
                      fontSize: 12,
                    }}
                  />
                </div>
                <button
                  onClick={() => removeParameter(idx)}
                  style={{
                    width: 32,
                    height: 32,
                    borderRadius: 4,
                    border: "none",
                    background: `${theme.danger}20`,
                    color: theme.danger,
                    cursor: "pointer",
                  }}
                >
                  <Trash2 size={14} />
                </button>
              </div>
            ))}
          </div>
        </div>

        {/* Footer */}
        <div
          style={{
            display: "flex",
            justifyContent: "flex-end",
            gap: 12,
            padding: 20,
            borderTop: `1px solid ${theme.border}`,
          }}
        >
          <button
            onClick={onClose}
            style={{
              padding: "10px 20px",
              borderRadius: 6,
              border: `1px solid ${theme.border}`,
              background: "transparent",
              color: theme.textSecondary,
              cursor: "pointer",
            }}
          >
            Cancelar
          </button>
          <button
            onClick={handleSave}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              padding: "10px 20px",
              borderRadius: 6,
              border: "none",
              background: theme.accentPrimary,
              color: "#FFF",
              cursor: "pointer",
              fontWeight: 500,
            }}
          >
            <Save size={16} />
            Salvar Material
          </button>
        </div>
      </motion.div>
    </motion.div>
  );
};

export default CncMaterialLibrary;
