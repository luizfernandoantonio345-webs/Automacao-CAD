/**
 * ═══════════════════════════════════════════════════════════════════════════════
 * CncTemplateLibrary - Biblioteca Visual de Templates de Peças
 * ═══════════════════════════════════════════════════════════════════════════════
 *
 * Melhoria #7: Galeria visual de peças salvas/templates
 * - Grid visual com preview SVG
 * - Categorização e tags
 * - Import/Export DXF
 * - Busca e filtros
 */

import React, { useState, useMemo, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Grid,
  List,
  Search,
  Filter,
  Plus,
  Edit3,
  Trash2,
  Download,
  Upload,
  Copy,
  Star,
  Tag,
  Folder,
  FolderOpen,
  Image,
  FileText,
  Layers,
  Box,
  Circle,
  Square,
  Triangle,
  Hexagon,
  Heart,
  X,
  Check,
  ChevronRight,
  MoreVertical,
  Eye,
} from "lucide-react";

interface PieceTemplate {
  id: string;
  name: string;
  category: string;
  tags: string[];
  width: number;
  height: number;
  area: number;
  perimeter: number;
  svgPath: string;
  svgViewBox: string;
  holes?: number;
  lastUsed?: string;
  useCount: number;
  favorite: boolean;
  createdAt: string;
  dxfFile?: string;
}

interface Category {
  id: string;
  name: string;
  icon: React.ReactNode;
  pieceCount: number;
}

interface CncTemplateLibraryProps {
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
  onSelectTemplate?: (template: PieceTemplate) => void;
  onDeleteTemplate?: (template: PieceTemplate) => void;
}

// Mock data with SVG paths
const mockTemplates: PieceTemplate[] = [
  {
    id: "tpl-001",
    name: "Flange Circular Ø150",
    category: "Flanges",
    tags: ["circular", "padrão", "conexão"],
    width: 150,
    height: 150,
    area: 15394,
    perimeter: 471,
    svgPath: "M75,10 A65,65 0 1,1 74.9,10 Z M75,30 A45,45 0 1,0 75.1,30 Z",
    svgViewBox: "0 0 150 150",
    holes: 4,
    useCount: 45,
    favorite: true,
    createdAt: "2024-12-01",
    lastUsed: "2025-01-15",
  },
  {
    id: "tpl-002",
    name: "Suporte L 100x80",
    category: "Suportes",
    tags: ["angular", "estrutural"],
    width: 100,
    height: 80,
    area: 4800,
    perimeter: 360,
    svgPath: "M10,10 L90,10 L90,40 L40,40 L40,70 L10,70 Z",
    svgViewBox: "0 0 100 80",
    holes: 2,
    useCount: 32,
    favorite: false,
    createdAt: "2024-11-15",
    lastUsed: "2025-01-14",
  },
  {
    id: "tpl-003",
    name: "Chapa Perfurada Grid",
    category: "Chapas",
    tags: ["perfurado", "ventilação"],
    width: 200,
    height: 200,
    area: 32000,
    perimeter: 800,
    svgPath:
      "M10,10 L190,10 L190,190 L10,190 Z M30,30 A10,10 0 1,1 30.1,30 M70,30 A10,10 0 1,1 70.1,30 M110,30 A10,10 0 1,1 110.1,30 M150,30 A10,10 0 1,1 150.1,30",
    svgViewBox: "0 0 200 200",
    holes: 16,
    useCount: 18,
    favorite: true,
    createdAt: "2024-10-20",
    lastUsed: "2025-01-10",
  },
  {
    id: "tpl-004",
    name: "Bracket Triangular",
    category: "Suportes",
    tags: ["triangular", "reforço"],
    width: 80,
    height: 80,
    area: 2720,
    perimeter: 232,
    svgPath: "M10,70 L70,70 L70,10 Z",
    svgViewBox: "0 0 80 80",
    holes: 1,
    useCount: 56,
    favorite: false,
    createdAt: "2024-09-05",
  },
  {
    id: "tpl-005",
    name: "Tampa Hexagonal",
    category: "Tampas",
    tags: ["hexagonal", "cobertura"],
    width: 120,
    height: 104,
    area: 10392,
    perimeter: 360,
    svgPath: "M60,5 L110,30 L110,74 L60,99 L10,74 L10,30 Z",
    svgViewBox: "0 0 120 104",
    useCount: 12,
    favorite: false,
    createdAt: "2024-08-12",
  },
  {
    id: "tpl-006",
    name: "Anel de Vedação",
    category: "Vedação",
    tags: ["anel", "circular"],
    width: 100,
    height: 100,
    area: 5890,
    perimeter: 377,
    svgPath: "M50,5 A45,45 0 1,1 49.9,5 Z M50,20 A30,30 0 1,0 50.1,20 Z",
    svgViewBox: "0 0 100 100",
    useCount: 89,
    favorite: true,
    createdAt: "2024-07-01",
    lastUsed: "2025-01-15",
  },
];

const mockCategories: Category[] = [
  { id: "all", name: "Todos", icon: <Layers size={16} />, pieceCount: 6 },
  { id: "Flanges", name: "Flanges", icon: <Circle size={16} />, pieceCount: 1 },
  {
    id: "Suportes",
    name: "Suportes",
    icon: <Triangle size={16} />,
    pieceCount: 2,
  },
  { id: "Chapas", name: "Chapas", icon: <Square size={16} />, pieceCount: 1 },
  { id: "Tampas", name: "Tampas", icon: <Hexagon size={16} />, pieceCount: 1 },
  { id: "Vedação", name: "Vedação", icon: <Circle size={16} />, pieceCount: 1 },
];

const CncTemplateLibrary: React.FC<CncTemplateLibraryProps> = ({
  theme,
  onSelectTemplate,
  onDeleteTemplate,
}) => {
  const [templates, setTemplates] = useState<PieceTemplate[]>(mockTemplates);
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("all");
  const [showFavoritesOnly, setShowFavoritesOnly] = useState(false);
  const [viewMode, setViewMode] = useState<"grid" | "list">("grid");
  const [sortBy, setSortBy] = useState<"name" | "useCount" | "createdAt">(
    "useCount",
  );
  const [selectedTemplate, setSelectedTemplate] =
    useState<PieceTemplate | null>(null);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Filtered and sorted templates
  const filteredTemplates = useMemo(() => {
    let result = [...templates];

    // Search
    if (searchTerm) {
      const term = searchTerm.toLowerCase();
      result = result.filter(
        (t) =>
          t.name.toLowerCase().includes(term) ||
          t.tags.some((tag) => tag.toLowerCase().includes(term)),
      );
    }

    // Category
    if (selectedCategory !== "all") {
      result = result.filter((t) => t.category === selectedCategory);
    }

    // Favorites
    if (showFavoritesOnly) {
      result = result.filter((t) => t.favorite);
    }

    // Sort
    result.sort((a, b) => {
      switch (sortBy) {
        case "name":
          return a.name.localeCompare(b.name);
        case "useCount":
          return b.useCount - a.useCount;
        case "createdAt":
          return (
            new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()
          );
        default:
          return 0;
      }
    });

    return result;
  }, [templates, searchTerm, selectedCategory, showFavoritesOnly, sortBy]);

  const toggleFavorite = (id: string) => {
    setTemplates((prev) =>
      prev.map((t) => (t.id === id ? { ...t, favorite: !t.favorite } : t)),
    );
  };

  const duplicateTemplate = (template: PieceTemplate) => {
    const newTemplate: PieceTemplate = {
      ...template,
      id: `tpl-${Date.now()}`,
      name: `${template.name} (Cópia)`,
      favorite: false,
      useCount: 0,
      createdAt: new Date().toISOString(),
    };
    setTemplates((prev) => [...prev, newTemplate]);
  };

  const deleteTemplate = (template: PieceTemplate) => {
    if (confirm(`Excluir template "${template.name}"?`)) {
      setTemplates((prev) => prev.filter((t) => t.id !== template.id));
      onDeleteTemplate?.(template);
    }
  };

  const exportTemplate = (template: PieceTemplate) => {
    const data = JSON.stringify(template, null, 2);
    const blob = new Blob([data], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${template.name.replace(/\s+/g, "_")}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const data = JSON.parse(e.target?.result as string);
        if (data.svgPath && data.name) {
          setTemplates((prev) => [
            ...prev,
            {
              ...data,
              id: `tpl-${Date.now()}`,
              useCount: 0,
              createdAt: new Date().toISOString(),
            },
          ]);
        }
      } catch {
        alert("Arquivo inválido");
      }
    };
    reader.readAsText(file);
    event.target.value = "";
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      style={{ display: "flex", gap: 20 }}
    >
      {/* Sidebar - Categories */}
      <div
        style={{
          width: 200,
          background: theme.surface,
          border: `1px solid ${theme.border}`,
          borderRadius: 8,
          padding: 16,
          height: "fit-content",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            marginBottom: 16,
          }}
        >
          <FolderOpen size={18} color={theme.accentPrimary} />
          <span style={{ color: theme.textPrimary, fontWeight: 600 }}>
            Categorias
          </span>
        </div>

        {mockCategories.map((cat) => (
          <button
            key={cat.id}
            onClick={() => setSelectedCategory(cat.id)}
            style={{
              width: "100%",
              display: "flex",
              alignItems: "center",
              gap: 10,
              padding: "10px 12px",
              borderRadius: 6,
              border: "none",
              background:
                selectedCategory === cat.id
                  ? `${theme.accentPrimary}20`
                  : "transparent",
              color:
                selectedCategory === cat.id
                  ? theme.accentPrimary
                  : theme.textSecondary,
              cursor: "pointer",
              marginBottom: 4,
              textAlign: "left",
            }}
          >
            {cat.icon}
            <span style={{ flex: 1, fontSize: 13 }}>{cat.name}</span>
            <span
              style={{
                padding: "2px 6px",
                borderRadius: 10,
                background: theme.surfaceAlt,
                fontSize: 11,
              }}
            >
              {cat.pieceCount}
            </span>
          </button>
        ))}

        {/* Tags Section */}
        <div style={{ marginTop: 24 }}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              marginBottom: 12,
            }}
          >
            <Tag size={16} color={theme.textSecondary} />
            <span style={{ color: theme.textSecondary, fontSize: 12 }}>
              Tags populares
            </span>
          </div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
            {["circular", "estrutural", "padrão", "perfurado"].map((tag) => (
              <button
                key={tag}
                onClick={() => setSearchTerm(tag)}
                style={{
                  padding: "4px 8px",
                  borderRadius: 4,
                  border: `1px solid ${theme.border}`,
                  background: "transparent",
                  color: theme.textSecondary,
                  fontSize: 11,
                  cursor: "pointer",
                }}
              >
                #{tag}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div style={{ flex: 1 }}>
        {/* Header */}
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: 20,
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <Grid size={24} color={theme.accentPrimary} />
            <h2 style={{ margin: 0, color: theme.textPrimary, fontSize: 20 }}>
              Biblioteca de Templates
            </h2>
            <span
              style={{
                padding: "4px 8px",
                borderRadius: 4,
                background: `${theme.accentPrimary}20`,
                color: theme.accentPrimary,
                fontSize: 12,
              }}
            >
              {filteredTemplates.length} templates
            </span>
          </div>

          <div style={{ display: "flex", gap: 8 }}>
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileUpload}
              accept=".json,.dxf"
              style={{ display: "none" }}
            />
            <button
              onClick={() => fileInputRef.current?.click()}
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
            </button>
            <button
              onClick={() => setShowUploadModal(true)}
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
              Novo Template
            </button>
          </div>
        </div>

        {/* Filters & Controls */}
        <div
          style={{
            display: "flex",
            gap: 12,
            marginBottom: 20,
            flexWrap: "wrap",
            alignItems: "center",
          }}
        >
          {/* Search */}
          <div style={{ flex: 1, minWidth: 200, position: "relative" }}>
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
              placeholder="Buscar por nome ou tag..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              style={{
                width: "100%",
                padding: "8px 12px 8px 36px",
                borderRadius: 6,
                border: `1px solid ${theme.border}`,
                background: theme.surface,
                color: theme.textPrimary,
                fontSize: 14,
              }}
            />
          </div>

          {/* Sort */}
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as typeof sortBy)}
            style={{
              padding: "8px 12px",
              borderRadius: 6,
              border: `1px solid ${theme.border}`,
              background: theme.surface,
              color: theme.textPrimary,
              fontSize: 13,
            }}
          >
            <option value="useCount">Mais usados</option>
            <option value="name">Nome A-Z</option>
            <option value="createdAt">Mais recentes</option>
          </select>

          {/* Favorites toggle */}
          <button
            onClick={() => setShowFavoritesOnly(!showFavoritesOnly)}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 6,
              padding: "8px 12px",
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
            <Star size={14} fill={showFavoritesOnly ? theme.warning : "none"} />
            Favoritos
          </button>

          {/* View mode */}
          <div
            style={{
              display: "flex",
              border: `1px solid ${theme.border}`,
              borderRadius: 6,
              overflow: "hidden",
            }}
          >
            <button
              onClick={() => setViewMode("grid")}
              style={{
                padding: 8,
                border: "none",
                background:
                  viewMode === "grid" ? theme.accentPrimary : "transparent",
                color: viewMode === "grid" ? "#FFF" : theme.textSecondary,
                cursor: "pointer",
              }}
            >
              <Grid size={16} />
            </button>
            <button
              onClick={() => setViewMode("list")}
              style={{
                padding: 8,
                border: "none",
                background:
                  viewMode === "list" ? theme.accentPrimary : "transparent",
                color: viewMode === "list" ? "#FFF" : theme.textSecondary,
                cursor: "pointer",
              }}
            >
              <List size={16} />
            </button>
          </div>
        </div>

        {/* Templates Grid/List */}
        {viewMode === "grid" ? (
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))",
              gap: 16,
            }}
          >
            <AnimatePresence>
              {filteredTemplates.map((template) => (
                <motion.div
                  key={template.id}
                  layout
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.9 }}
                  whileHover={{ y: -4 }}
                  style={{
                    background: theme.surface,
                    border: `1px solid ${theme.border}`,
                    borderRadius: 8,
                    overflow: "hidden",
                    cursor: "pointer",
                  }}
                  onClick={() => setSelectedTemplate(template)}
                >
                  {/* SVG Preview */}
                  <div
                    style={{
                      height: 140,
                      background: "#0a0a1a",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      position: "relative",
                    }}
                  >
                    <svg
                      viewBox={template.svgViewBox}
                      width="80%"
                      height="80%"
                      style={{ maxWidth: 120, maxHeight: 100 }}
                    >
                      <path
                        d={template.svgPath}
                        fill="none"
                        stroke={theme.accentPrimary}
                        strokeWidth={2}
                      />
                    </svg>

                    {/* Favorite button */}
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        toggleFavorite(template.id);
                      }}
                      style={{
                        position: "absolute",
                        top: 8,
                        right: 8,
                        width: 28,
                        height: 28,
                        borderRadius: "50%",
                        border: "none",
                        background: "rgba(0,0,0,0.5)",
                        color: template.favorite ? theme.warning : "#FFF",
                        cursor: "pointer",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                      }}
                    >
                      <Star
                        size={14}
                        fill={template.favorite ? theme.warning : "none"}
                      />
                    </button>
                  </div>

                  {/* Info */}
                  <div style={{ padding: 12 }}>
                    <div
                      style={{
                        color: theme.textPrimary,
                        fontWeight: 600,
                        fontSize: 13,
                        marginBottom: 4,
                        whiteSpace: "nowrap",
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                      }}
                    >
                      {template.name}
                    </div>
                    <div
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        color: theme.textSecondary,
                        fontSize: 11,
                      }}
                    >
                      <span>
                        {template.width}×{template.height} mm
                      </span>
                      <span>{template.useCount} usos</span>
                    </div>

                    {/* Tags */}
                    <div
                      style={{
                        display: "flex",
                        gap: 4,
                        marginTop: 8,
                        flexWrap: "wrap",
                      }}
                    >
                      {template.tags.slice(0, 2).map((tag) => (
                        <span
                          key={tag}
                          style={{
                            padding: "2px 6px",
                            borderRadius: 4,
                            background: theme.surfaceAlt,
                            color: theme.textSecondary,
                            fontSize: 10,
                          }}
                        >
                          {tag}
                        </span>
                      ))}
                    </div>
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
        ) : (
          /* List View */
          <div
            style={{
              background: theme.surface,
              border: `1px solid ${theme.border}`,
              borderRadius: 8,
              overflow: "hidden",
            }}
          >
            {filteredTemplates.map((template, idx) => (
              <div
                key={template.id}
                onClick={() => setSelectedTemplate(template)}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 16,
                  padding: 12,
                  borderTop: idx > 0 ? `1px solid ${theme.border}` : "none",
                  cursor: "pointer",
                }}
              >
                {/* Mini preview */}
                <div
                  style={{
                    width: 50,
                    height: 50,
                    background: "#0a0a1a",
                    borderRadius: 4,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                  }}
                >
                  <svg viewBox={template.svgViewBox} width="40" height="40">
                    <path
                      d={template.svgPath}
                      fill="none"
                      stroke={theme.accentPrimary}
                      strokeWidth={2}
                    />
                  </svg>
                </div>

                {/* Info */}
                <div style={{ flex: 1 }}>
                  <div
                    style={{ display: "flex", alignItems: "center", gap: 8 }}
                  >
                    <span style={{ color: theme.textPrimary, fontWeight: 500 }}>
                      {template.name}
                    </span>
                    {template.favorite && (
                      <Star
                        size={12}
                        color={theme.warning}
                        fill={theme.warning}
                      />
                    )}
                  </div>
                  <div style={{ color: theme.textSecondary, fontSize: 12 }}>
                    {template.width}×{template.height} mm | {template.category}
                  </div>
                </div>

                <div style={{ color: theme.textSecondary, fontSize: 12 }}>
                  {template.useCount} usos
                </div>

                {/* Actions */}
                <div
                  style={{ display: "flex", gap: 4 }}
                  onClick={(e) => e.stopPropagation()}
                >
                  <button
                    onClick={() => onSelectTemplate?.(template)}
                    style={{
                      padding: "6px 12px",
                      borderRadius: 4,
                      border: "none",
                      background: theme.accentPrimary,
                      color: "#FFF",
                      cursor: "pointer",
                      fontSize: 11,
                    }}
                  >
                    Usar
                  </button>
                  <button
                    onClick={() => duplicateTemplate(template)}
                    style={{
                      padding: 6,
                      borderRadius: 4,
                      border: `1px solid ${theme.border}`,
                      background: "transparent",
                      color: theme.textSecondary,
                      cursor: "pointer",
                    }}
                  >
                    <Copy size={14} />
                  </button>
                  <button
                    onClick={() => deleteTemplate(template)}
                    style={{
                      padding: 6,
                      borderRadius: 4,
                      border: `1px solid ${theme.danger}`,
                      background: "transparent",
                      color: theme.danger,
                      cursor: "pointer",
                    }}
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Empty state */}
        {filteredTemplates.length === 0 && (
          <div
            style={{
              padding: 60,
              textAlign: "center",
              color: theme.textSecondary,
            }}
          >
            <Image size={48} style={{ opacity: 0.3, marginBottom: 16 }} />
            <div style={{ fontSize: 16, marginBottom: 8 }}>
              Nenhum template encontrado
            </div>
            <div style={{ fontSize: 13 }}>
              Tente ajustar os filtros ou importe um novo template
            </div>
          </div>
        )}
      </div>

      {/* Template Detail Modal */}
      <AnimatePresence>
        {selectedTemplate && (
          <TemplateDetailModal
            template={selectedTemplate}
            theme={theme}
            onClose={() => setSelectedTemplate(null)}
            onUse={() => {
              onSelectTemplate?.(selectedTemplate);
              setSelectedTemplate(null);
            }}
            onExport={() => exportTemplate(selectedTemplate)}
            onDuplicate={() => {
              duplicateTemplate(selectedTemplate);
              setSelectedTemplate(null);
            }}
          />
        )}
      </AnimatePresence>
    </motion.div>
  );
};

// Detail Modal Component
const TemplateDetailModal: React.FC<{
  template: PieceTemplate;
  theme: CncTemplateLibraryProps["theme"];
  onClose: () => void;
  onUse: () => void;
  onExport: () => void;
  onDuplicate: () => void;
}> = ({ template, theme, onClose, onUse, onExport, onDuplicate }) => (
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
        maxWidth: 600,
        overflow: "hidden",
      }}
      onClick={(e) => e.stopPropagation()}
    >
      {/* Preview */}
      <div
        style={{
          height: 200,
          background: "#0a0a1a",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <svg viewBox={template.svgViewBox} width="60%" height="80%">
          <path
            d={template.svgPath}
            fill="none"
            stroke={theme.accentPrimary}
            strokeWidth={2}
          />
        </svg>
      </div>

      {/* Info */}
      <div style={{ padding: 24 }}>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 12,
            marginBottom: 16,
          }}
        >
          <h3 style={{ margin: 0, color: theme.textPrimary, flex: 1 }}>
            {template.name}
          </h3>
          {template.favorite && (
            <Star size={20} color={theme.warning} fill={theme.warning} />
          )}
        </div>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(3, 1fr)",
            gap: 16,
            marginBottom: 20,
          }}
        >
          <div>
            <div style={{ color: theme.textSecondary, fontSize: 12 }}>
              Dimensões
            </div>
            <div style={{ color: theme.textPrimary, fontWeight: 500 }}>
              {template.width} × {template.height} mm
            </div>
          </div>
          <div>
            <div style={{ color: theme.textSecondary, fontSize: 12 }}>Área</div>
            <div style={{ color: theme.textPrimary, fontWeight: 500 }}>
              {(template.area / 100).toFixed(1)} cm²
            </div>
          </div>
          <div>
            <div style={{ color: theme.textSecondary, fontSize: 12 }}>
              Perímetro
            </div>
            <div style={{ color: theme.textPrimary, fontWeight: 500 }}>
              {template.perimeter} mm
            </div>
          </div>
          <div>
            <div style={{ color: theme.textSecondary, fontSize: 12 }}>
              Furos
            </div>
            <div style={{ color: theme.textPrimary, fontWeight: 500 }}>
              {template.holes || 0}
            </div>
          </div>
          <div>
            <div style={{ color: theme.textSecondary, fontSize: 12 }}>
              Vezes usado
            </div>
            <div style={{ color: theme.textPrimary, fontWeight: 500 }}>
              {template.useCount}
            </div>
          </div>
          <div>
            <div style={{ color: theme.textSecondary, fontSize: 12 }}>
              Categoria
            </div>
            <div style={{ color: theme.textPrimary, fontWeight: 500 }}>
              {template.category}
            </div>
          </div>
        </div>

        {/* Tags */}
        <div
          style={{
            display: "flex",
            gap: 8,
            marginBottom: 20,
            flexWrap: "wrap",
          }}
        >
          {template.tags.map((tag) => (
            <span
              key={tag}
              style={{
                padding: "4px 10px",
                borderRadius: 4,
                background: theme.surfaceAlt,
                color: theme.textSecondary,
                fontSize: 12,
              }}
            >
              #{tag}
            </span>
          ))}
        </div>

        {/* Actions */}
        <div style={{ display: "flex", gap: 12 }}>
          <button
            onClick={onClose}
            style={{
              flex: 1,
              padding: 12,
              borderRadius: 6,
              border: `1px solid ${theme.border}`,
              background: "transparent",
              color: theme.textSecondary,
              cursor: "pointer",
            }}
          >
            Fechar
          </button>
          <button
            onClick={onDuplicate}
            style={{
              padding: "12px 16px",
              borderRadius: 6,
              border: `1px solid ${theme.border}`,
              background: "transparent",
              color: theme.textSecondary,
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: 6,
            }}
          >
            <Copy size={16} />
            Duplicar
          </button>
          <button
            onClick={onExport}
            style={{
              padding: "12px 16px",
              borderRadius: 6,
              border: `1px solid ${theme.border}`,
              background: "transparent",
              color: theme.textSecondary,
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: 6,
            }}
          >
            <Download size={16} />
            Exportar
          </button>
          <button
            onClick={onUse}
            style={{
              flex: 1,
              padding: 12,
              borderRadius: 6,
              border: "none",
              background: theme.accentPrimary,
              color: "#FFF",
              cursor: "pointer",
              fontWeight: 500,
            }}
          >
            Usar Template
          </button>
        </div>
      </div>
    </motion.div>
  </motion.div>
);

export default CncTemplateLibrary;
