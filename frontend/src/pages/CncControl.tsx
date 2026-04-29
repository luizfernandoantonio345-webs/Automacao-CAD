/**
 * ═══════════════════════════════════════════════════════════════════════════════
 * Engenharia CAD - Tela de Controle CNC / Geração de Corte Plasma
 * ═══════════════════════════════════════════════════════════════════════════════
 *
 * Esta tela permite:
 * - Importar geometria do CAD interno ou arquivos DXF/SVG
 * - Configurar parâmetros de corte plasma
 * - Visualizar preview do toolpath
 * - Gerar e baixar G-code otimizado
 */

import React, {
  useState,
  useCallback,
  useRef,
  useEffect,
  useMemo,
} from "react";
import { useTheme } from "../context/ThemeContext";
import { API_BASE_URL } from "../services/api";
import { useLicense } from "../context/LicenseContext";
import { motion, AnimatePresence } from "framer-motion";

// Componentes visuais avançados
import CncCanvas from "../components/CncCanvas";
import CncStatisticsPanel from "../components/CncStatisticsPanel";
import CncValidationPanel from "../components/CncValidationPanel";
import {
  Flame,
  Upload,
  Settings2,
  Play,
  Download,
  Eye,
  FileCode,
  Layers,
  Target,
  Zap,
  Ruler,
  Thermometer,
  RotateCcw,
  CheckCircle2,
  AlertTriangle,
  Info,
  ChevronRight,
  Box,
  Circle,
  Square,
  Minus,
  ArrowRight,
  Clock,
  FileText,
  Copy,
  DollarSign,
  Percent,
  Maximize2,
  HelpCircle,
  BookOpen,
  Sparkles,
  Monitor,
  ArrowDown,
  X,
  FileUp,
  Cog,
  Send,
  Check,
  Plus,
  Trash2,
  Grid,
  Layout,
  Move,
  LayoutGrid,
  Scissors,
  Bot,
  Brain,
  MessageSquare,
  Lightbulb,
  TrendingUp,
  Package,
  PenTool,
  CircleDot,
  RectangleHorizontal,
  CornerDownRight,
  Save,
  RefreshCw,
  Maximize,
  ZoomIn,
  ZoomOut,
  RotateCw,
  Crosshair,
} from "lucide-react";

// ═══════════════════════════════════════════════════════════════════════════════
// Types
// ═══════════════════════════════════════════════════════════════════════════════

interface Point {
  x: number;
  y: number;
}

interface GeometryEntity {
  type: "line" | "arc" | "circle" | "polyline";
  points?: Point[];
  center?: Point;
  radius?: number;
  startAngle?: number;
  endAngle?: number;
  closed?: boolean;
}

interface Geometry {
  entities: GeometryEntity[];
  boundingBox: { min: Point; max: Point };
  stats: {
    lines: number;
    arcs: number;
    circles: number;
    polylines: number;
    totalLength: number;
  };
}

interface CuttingConfig {
  material: "mild_steel" | "stainless" | "aluminum" | "copper";
  thickness: number;
  amperage: number;
  cuttingSpeed: number;
  pierceDelay: number;
  pierceHeight: number;
  cutHeight: number;
  safeHeight: number;
  kerfWidth: number;
  leadInLength: number;
  leadOutLength: number;
  leadType: "arc" | "line";
  thcEnabled: boolean;
  arcVoltage: number;
}

interface ToolpathStats {
  totalCuts: number;
  cuttingLength: number;
  rapidLength: number;
  estimatedTime: number;
  internalContours: number;
  externalContours: number;
}

interface CostEstimate {
  materialCost: number;
  cuttingTimeCost: number;
  totalCost: number;
  scrapPercentage: number;
}

interface GCodeResult {
  code: string;
  stats: ToolpathStats;
  warnings: Array<{ level: string; message: string; suggestion?: string }>;
  costEstimate?: CostEstimate;
}

type ProcessingStep =
  | "idle"
  | "uploading"
  | "parsing"
  | "generating"
  | "complete"
  | "error";

// ═══════════════════════════════════════════════════════════════════════════════
// Sistema de Criação de Peças
// ═══════════════════════════════════════════════════════════════════════════════

type PieceType = "rectangle" | "circle" | "L_shape" | "U_shape" | "custom";

interface HoleDefinition {
  id: string;
  x: number;
  y: number;
  diameter: number;
}

interface CutoutDefinition {
  id: string;
  type: "rectangle" | "circle" | "slot";
  x: number;
  y: number;
  width?: number;
  height?: number;
  diameter?: number;
  length?: number;
}

interface PieceDefinition {
  id: string;
  type: PieceType;
  name: string;
  width: number;
  height: number;
  radius?: number; // Para círculos
  legWidth?: number; // Para L e U
  legHeight?: number;
  holes: HoleDefinition[];
  cutouts: CutoutDefinition[];
  quantity: number;
  rotation: number; // 0, 90, 180, 270
}

interface SheetConfig {
  width: number;
  height: number;
  margin: number;
  spacing: number;
}

interface NestingResult {
  placements: Array<{
    pieceId: string;
    x: number;
    y: number;
    rotation: number;
  }>;
  efficiency: number;
  wasteArea: number;
  usedArea: number;
  totalPieces: number;
  unplacedPieces: number;
}

interface AISuggestion {
  id: string;
  type: "warning" | "optimization" | "info" | "error";
  title: string;
  message: string;
  action?: string;
  priority: number;
}

// ═══════════════════════════════════════════════════════════════════════════════
// Material presets
// ═══════════════════════════════════════════════════════════════════════════════

const MATERIAL_PRESETS: Record<
  string,
  { name: string; color: string; thicknessRange: [number, number] }
> = {
  mild_steel: {
    name: "Aço Carbono",
    color: "#6B7280",
    thicknessRange: [1, 50],
  },
  stainless: { name: "Aço Inox", color: "#9CA3AF", thicknessRange: [1, 25] },
  aluminum: { name: "Alumínio", color: "#D1D5DB", thicknessRange: [1, 20] },
  copper: { name: "Cobre", color: "#F59E0B", thicknessRange: [1, 12] },
  brass: { name: "Latão", color: "#EAB308", thicknessRange: [1, 10] },
  galvanized: { name: "Galvanizado", color: "#71717A", thicknessRange: [1, 6] },
};

const CUTTING_TABLES: Record<
  string,
  Record<number, { amperage: number; speed: number; kerf: number }>
> = {
  mild_steel: {
    3: { amperage: 30, speed: 3500, kerf: 1.0 },
    6: { amperage: 45, speed: 2000, kerf: 1.5 },
    10: { amperage: 65, speed: 1200, kerf: 1.8 },
    12: { amperage: 80, speed: 900, kerf: 2.0 },
    16: { amperage: 100, speed: 600, kerf: 2.2 },
    20: { amperage: 130, speed: 450, kerf: 2.5 },
    25: { amperage: 200, speed: 350, kerf: 3.0 },
  },
  stainless: {
    3: { amperage: 40, speed: 2800, kerf: 1.2 },
    6: { amperage: 60, speed: 1600, kerf: 1.8 },
    10: { amperage: 80, speed: 900, kerf: 2.2 },
    12: { amperage: 100, speed: 700, kerf: 2.5 },
  },
  aluminum: {
    3: { amperage: 40, speed: 4000, kerf: 1.5 },
    6: { amperage: 65, speed: 2500, kerf: 2.0 },
    10: { amperage: 100, speed: 1500, kerf: 2.5 },
  },
  copper: {
    3: { amperage: 50, speed: 2500, kerf: 1.8 },
    6: { amperage: 80, speed: 1500, kerf: 2.2 },
  },
  brass: {
    3: { amperage: 45, speed: 2800, kerf: 1.6 },
    6: { amperage: 70, speed: 1800, kerf: 2.0 },
  },
  galvanized: {
    1.5: { amperage: 25, speed: 4500, kerf: 0.8 },
    3: { amperage: 35, speed: 3200, kerf: 1.2 },
    6: { amperage: 50, speed: 1800, kerf: 1.6 },
  },
};

// ═══════════════════════════════════════════════════════════════════════════════
// CncControl Component
// ═══════════════════════════════════════════════════════════════════════════════

const CncControl: React.FC = () => {
  const { theme } = useTheme();
  const { canUse, triggerUpgrade } = useLicense();

  // ── State ──
  const [step, setStep] = useState<ProcessingStep>("idle");
  const [geometry, setGeometry] = useState<Geometry | null>(null);
  const [fileName, setFileName] = useState<string>("");
  const [gcode, setGcode] = useState<GCodeResult | null>(null);
  const [activeTab, setActiveTab] = useState<"config" | "preview" | "gcode">(
    "config",
  );
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showTutorial, setShowTutorial] = useState(false);
  const [showAutoCADGuide, setShowAutoCADGuide] = useState(false);
  const [tutorialStep, setTutorialStep] = useState(0);

  // ── Simulação CNC ──
  const [simPlaying, setSimPlaying] = useState(false);
  const [simProgress, setSimProgress] = useState(0); // 0–100
  const [simSpeed, setSimSpeed] = useState(1); // 0.5x | 1x | 2x | 4x
  const simIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const simulationMilestones = useMemo(
    () => [
      { id: "prep", label: "Preparação", threshold: 0 },
      { id: "pierce", label: "Piercing", threshold: 18 },
      { id: "cutting", label: "Corte", threshold: 52 },
      { id: "finishing", label: "Finalização", threshold: 84 },
    ],
    [],
  );
  const currentSimulationStage = useMemo(
    () =>
      [...simulationMilestones]
        .reverse()
        .find((milestone) => simProgress >= milestone.threshold)?.label ||
      simulationMilestones[0].label,
    [simProgress, simulationMilestones],
  );

  useEffect(() => {
    if (simPlaying) {
      simIntervalRef.current = setInterval(() => {
        setSimProgress((p) => {
          if (p >= 100) {
            setSimPlaying(false);
            return 100;
          }
          return Math.min(100, p + 0.5 * simSpeed);
        });
      }, 50);
    } else {
      if (simIntervalRef.current) clearInterval(simIntervalRef.current);
    }
    return () => {
      if (simIntervalRef.current) clearInterval(simIntervalRef.current);
    };
  }, [simPlaying, simSpeed]);

  // ── Modo de operação ──
  type OperationMode = "import" | "create" | "nesting";
  const [operationMode, setOperationMode] = useState<OperationMode>("import");

  // ── Sistema de Criação de Peças ──
  const [pieces, setPieces] = useState<PieceDefinition[]>([]);
  const [editingPiece, setEditingPiece] = useState<PieceDefinition | null>(
    null,
  );
  const [showPieceEditor, setShowPieceEditor] = useState(false);

  // ── Sistema de Nesting ──
  const [sheetConfig, setSheetConfig] = useState<SheetConfig>({
    width: 3000,
    height: 1500,
    margin: 10,
    spacing: 5,
  });
  const [nestingResult, setNestingResult] = useState<NestingResult | null>(
    null,
  );
  const [isNesting, setIsNesting] = useState(false);

  // ── IA Assistente ──
  const [showAIAssistant, setShowAIAssistant] = useState(true);
  const [aiSuggestions, setAiSuggestions] = useState<AISuggestion[]>([]);
  const [aiChatMessages, setAiChatMessages] = useState<
    Array<{ role: "user" | "ai"; content: string }>
  >([
    {
      role: "ai",
      content:
        "Olá! Sou seu assistente de corte plasma. Posso ajudar você a criar peças, otimizar o uso da chapa e evitar erros. O que você precisa?",
    },
  ]);
  const [aiInput, setAiInput] = useState("");
  const [isAiThinking, setIsAiThinking] = useState(false);

  // ── Algoritmo de Nesting ──
  type NestingAlgorithmType = "blf" | "nfp" | "genetic" | "sa" | "guillotine";
  const [nestingAlgorithm, setNestingAlgorithm] =
    useState<NestingAlgorithmType>("blf");
  const [nestingPriority, setNestingPriority] = useState<
    "speed" | "efficiency" | "balanced"
  >("balanced");

  const NESTING_ALGORITHMS = {
    blf: {
      name: "Bottom-Left Fill",
      description: "Rápido, ideal para retângulos",
      icon: "📦",
    },
    nfp: {
      name: "No-Fit Polygon",
      description: "Preciso para formas complexas",
      icon: "🔷",
    },
    genetic: {
      name: "Algoritmo Genético",
      description: "Otimização global (mais lento)",
      icon: "🧬",
    },
    sa: {
      name: "Simulated Annealing",
      description: "Refinamento iterativo",
      icon: "🔥",
    },
    guillotine: {
      name: "Guilhotina",
      description: "Melhor para cortes lineares",
      icon: "✂️",
    },
  };

  // ── Painel de Estatísticas e Validações ──
  const [showStatisticsPanel, setShowStatisticsPanel] = useState(true);
  const [validationIssues, setValidationIssues] = useState<
    Array<{
      id: string;
      severity: "error" | "warning" | "info" | "success";
      category: "geometry" | "nesting" | "toolpath" | "material" | "machine";
      code: string;
      message: string;
      description?: string;
      pieceId?: string;
      pieceName?: string;
      location?: { x: number; y: number };
      autoFixAvailable?: boolean;
    }>
  >([]);
  const [isValidating, setIsValidating] = useState(false);

  // Configuração de corte
  const [config, setConfig] = useState<CuttingConfig>({
    material: "mild_steel",
    thickness: 6,
    amperage: 45,
    cuttingSpeed: 2000,
    pierceDelay: 0.5,
    pierceHeight: 3.0,
    cutHeight: 1.5,
    safeHeight: 10.0,
    kerfWidth: 1.5,
    leadInLength: 3.0,
    leadOutLength: 2.0,
    leadType: "arc",
    thcEnabled: true,
    arcVoltage: 120,
  });

  const fileInputRef = useRef<HTMLInputElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  // ── Helpers ──
  const updateConfig = useCallback((updates: Partial<CuttingConfig>) => {
    setConfig((prev) => ({ ...prev, ...updates }));
  }, []);

  const getRecommendedParams = useCallback(
    (material: string, thickness: number) => {
      const table = CUTTING_TABLES[material] || CUTTING_TABLES.mild_steel;
      const thicknesses = Object.keys(table)
        .map(Number)
        .sort((a, b) => a - b);

      // Encontrar espessura mais próxima
      let closest = thicknesses[0];
      for (const t of thicknesses) {
        if (Math.abs(t - thickness) < Math.abs(closest - thickness)) {
          closest = t;
        }
      }

      const params = table[closest];

      // Ajustar velocidade proporcionalmente
      const ratio = closest / thickness;
      const adjustedSpeed = Math.round(params.speed * Math.sqrt(ratio));

      return {
        amperage: params.amperage,
        cuttingSpeed: adjustedSpeed,
        kerfWidth: params.kerf,
        pierceDelay: 0.3 + thickness * 0.05,
        cutHeight: 1.0 + thickness * 0.05,
        pierceHeight: 2.0 + thickness * 0.1,
      };
    },
    [],
  );

  // ── Atualizar parâmetros quando material/espessura mudam ──
  useEffect(() => {
    const recommended = getRecommendedParams(config.material, config.thickness);
    updateConfig(recommended);
  }, [config.material, config.thickness]);

  // ── Validar geometria automaticamente ──
  const runValidation = useCallback(() => {
    if (!geometry) {
      setValidationIssues([]);
      return;
    }

    setIsValidating(true);

    // Simular validação (em produção, chamar API backend)
    const issues: typeof validationIssues = [];

    // Verificar se há geometria fechada
    if (geometry.stats.circles < 1 && geometry.stats.polylines < 1) {
      issues.push({
        id: "val_1",
        severity: "warning",
        category: "geometry",
        code: "GEO-001",
        message: "Poucas geometrias fechadas detectadas",
        description:
          "Certifique-se de que todos os contornos estão fechados para corte correto.",
        autoFixAvailable: false,
      });
    }

    // Verificar espessura vs amperagem
    if (config.thickness > 12 && config.amperage < 80) {
      issues.push({
        id: "val_2",
        severity: "error",
        category: "material",
        code: "MAT-001",
        message: "Amperagem insuficiente para espessura",
        description: `Para ${config.thickness}mm, recomenda-se pelo menos 80A. Atual: ${config.amperage}A`,
        autoFixAvailable: true,
      });
    }

    // Verificar velocidade de corte
    if (config.cuttingSpeed > 5000) {
      issues.push({
        id: "val_3",
        severity: "warning",
        category: "machine",
        code: "MAC-001",
        message: "Velocidade de corte muito alta",
        description:
          "Velocidades acima de 5000 mm/min podem comprometer a qualidade do corte.",
        autoFixAvailable: true,
      });
    }

    // Verificar dimensões pequenas
    const minDim = Math.min(
      geometry.boundingBox.max.x - geometry.boundingBox.min.x,
      geometry.boundingBox.max.y - geometry.boundingBox.min.y,
    );
    if (minDim < 10) {
      issues.push({
        id: "val_4",
        severity: "warning",
        category: "geometry",
        code: "GEO-002",
        message: "Geometria muito pequena",
        description:
          "Peças menores que 10mm podem ter qualidade de corte inferior.",
        location: {
          x: geometry.boundingBox.min.x,
          y: geometry.boundingBox.min.y,
        },
      });
    }

    setValidationIssues(issues);
    setIsValidating(false);
  }, [geometry, config.thickness, config.amperage, config.cuttingSpeed]);

  // Executar validação quando geometria ou config mudam
  useEffect(() => {
    runValidation();
  }, [geometry, config.thickness, config.amperage, config.cuttingSpeed]);

  // ── Memoized theme for panels ──
  const panelTheme = useMemo(
    () => ({
      surface: theme.surface || theme.panel,
      border: theme.border,
      accentPrimary: theme.accentPrimary,
      success: theme.success,
      warning: theme.warning,
      danger: theme.danger,
      textPrimary: theme.textPrimary,
      textSecondary: theme.textSecondary,
      inputBackground: theme.inputBackground,
    }),
    [theme],
  );

  // ── File handling ──
  const handleFileSelect = useCallback(
    async (event: React.ChangeEvent<HTMLInputElement>) => {
      const file = event.target.files?.[0];
      if (!file) return;

      setFileName(file.name);
      setStep("uploading");
      setGcode(null);

      try {
        const formData = new FormData();
        formData.append("file", file);

        setStep("parsing");

        // Chamar API para parse do arquivo
        const response = await fetch(`${API_BASE_URL}/api/cam/parse`, {
          method: "POST",
          body: formData,
        });

        if (!response.ok) {
          throw new Error("Erro ao processar arquivo");
        }

        const result = await response.json();
        setGeometry(result.geometry);
        setStep("idle");
        setActiveTab("config");
      } catch (error) {
        console.error("Erro ao carregar arquivo:", error);
        // Simular geometria para demonstração
        simulateGeometry();
      }
    },
    [],
  );

  const simulateGeometry = () => {
    // Simular geometria para demo
    const demoGeometry: Geometry = {
      entities: [
        { type: "circle", center: { x: 100, y: 100 }, radius: 50 },
        { type: "circle", center: { x: 100, y: 100 }, radius: 20 },
        {
          type: "polyline",
          points: [
            { x: 200, y: 50 },
            { x: 300, y: 50 },
            { x: 300, y: 150 },
            { x: 200, y: 150 },
            { x: 200, y: 50 },
          ],
          closed: true,
        },
        { type: "circle", center: { x: 250, y: 100 }, radius: 15 },
      ],
      boundingBox: { min: { x: 50, y: 50 }, max: { x: 300, y: 150 } },
      stats: {
        lines: 4,
        arcs: 0,
        circles: 3,
        polylines: 1,
        totalLength: 628.32,
      },
    };

    setGeometry(demoGeometry);
    setStep("idle");
  };

  // ── Generate G-code ──
  const handleGenerate = useCallback(async () => {
    if (!geometry) return;

    setStep("generating");

    try {
      const response = await fetch(`${API_BASE_URL}/api/cam/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ geometry, config }),
      });

      if (!response.ok) {
        throw new Error("Erro ao gerar G-code");
      }

      const result = await response.json();
      setGcode(result);
      setStep("complete");
      setActiveTab("gcode");
    } catch (error) {
      console.error("Erro ao gerar G-code:", error);
      // Simular G-code para demo
      simulateGCode();
    }
  }, [geometry, config]);

  // ═══════════════════════════════════════════════════════════════════════════════
  // SISTEMA DE CRIAÇÃO DE PEÇAS
  // ═══════════════════════════════════════════════════════════════════════════════

  // Criar nova peça
  const createNewPiece = useCallback((type: PieceType) => {
    const newPiece: PieceDefinition = {
      id: `piece_${Date.now()}`,
      type,
      name:
        type === "rectangle"
          ? "Retângulo"
          : type === "circle"
            ? "Círculo"
            : type === "L_shape"
              ? "Peça L"
              : type === "U_shape"
                ? "Peça U"
                : "Peça Personalizada",
      width: type === "circle" ? 100 : 200,
      height: type === "circle" ? 100 : 150,
      radius: type === "circle" ? 50 : undefined,
      legWidth: type === "L_shape" || type === "U_shape" ? 50 : undefined,
      legHeight: type === "L_shape" || type === "U_shape" ? 80 : undefined,
      holes: [],
      cutouts: [],
      quantity: 1,
      rotation: 0,
    };
    setEditingPiece(newPiece);
    setShowPieceEditor(true);
  }, []);

  // Adicionar furo à peça
  const addHoleToPiece = useCallback(
    (diameter: number = 10) => {
      if (!editingPiece) return;
      const newHole: HoleDefinition = {
        id: `hole_${Date.now()}`,
        x: editingPiece.width / 2,
        y: editingPiece.height / 2,
        diameter,
      };
      setEditingPiece((prev) =>
        prev ? { ...prev, holes: [...prev.holes, newHole] } : null,
      );
    },
    [editingPiece],
  );

  // Adicionar recorte à peça
  const addCutoutToPiece = useCallback(
    (type: "rectangle" | "circle" | "slot") => {
      if (!editingPiece) return;
      const newCutout: CutoutDefinition = {
        id: `cutout_${Date.now()}`,
        type,
        x: editingPiece.width / 4,
        y: editingPiece.height / 4,
        width: type === "rectangle" ? 50 : undefined,
        height: type === "rectangle" ? 30 : undefined,
        diameter: type === "circle" ? 30 : undefined,
        length: type === "slot" ? 50 : undefined,
      };
      setEditingPiece((prev) =>
        prev ? { ...prev, cutouts: [...prev.cutouts, newCutout] } : null,
      );
    },
    [editingPiece],
  );

  // Salvar peça editada
  const savePiece = useCallback(() => {
    if (!editingPiece) return;
    setPieces((prev) => {
      const existingIndex = prev.findIndex((p) => p.id === editingPiece.id);
      if (existingIndex >= 0) {
        const updated = [...prev];
        updated[existingIndex] = editingPiece;
        return updated;
      }
      return [...prev, editingPiece];
    });
    setShowPieceEditor(false);
    setEditingPiece(null);

    // Atualizar sugestões da IA
    updateAISuggestions();
  }, [editingPiece]);

  // Remover peça
  const removePiece = useCallback((pieceId: string) => {
    setPieces((prev) => prev.filter((p) => p.id !== pieceId));
  }, []);

  // Converter peças para geometria
  const piecesToGeometry = useCallback(
    (pieceDefs: PieceDefinition[]): Geometry => {
      const entities: GeometryEntity[] = [];
      let totalLength = 0;
      let lines = 0,
        circles = 0,
        arcs = 0,
        polylines = 0;

      let offsetX = 0;
      let offsetY = 0;

      for (const piece of pieceDefs) {
        for (let i = 0; i < piece.quantity; i++) {
          const px = offsetX;
          const py = offsetY;

          // Contorno da peça
          if (piece.type === "rectangle") {
            entities.push({
              type: "line",
              points: [
                { x: px, y: py },
                { x: px + piece.width, y: py },
              ],
            });
            entities.push({
              type: "line",
              points: [
                { x: px + piece.width, y: py },
                { x: px + piece.width, y: py + piece.height },
              ],
            });
            entities.push({
              type: "line",
              points: [
                { x: px + piece.width, y: py + piece.height },
                { x: px, y: py + piece.height },
              ],
            });
            entities.push({
              type: "line",
              points: [
                { x: px, y: py + piece.height },
                { x: px, y: py },
              ],
            });
            totalLength += (piece.width + piece.height) * 2;
            lines += 4;
          } else if (piece.type === "circle" && piece.radius) {
            entities.push({
              type: "circle",
              center: { x: px + piece.radius, y: py + piece.radius },
              radius: piece.radius,
            });
            totalLength += 2 * Math.PI * piece.radius;
            circles += 1;
          } else if (
            piece.type === "L_shape" &&
            piece.legWidth &&
            piece.legHeight
          ) {
            // Forma de L
            const lw = piece.legWidth;
            const lh = piece.legHeight;
            entities.push({
              type: "line",
              points: [
                { x: px, y: py },
                { x: px + piece.width, y: py },
              ],
            });
            entities.push({
              type: "line",
              points: [
                { x: px + piece.width, y: py },
                { x: px + piece.width, y: py + lh },
              ],
            });
            entities.push({
              type: "line",
              points: [
                { x: px + piece.width, y: py + lh },
                { x: px + lw, y: py + lh },
              ],
            });
            entities.push({
              type: "line",
              points: [
                { x: px + lw, y: py + lh },
                { x: px + lw, y: py + piece.height },
              ],
            });
            entities.push({
              type: "line",
              points: [
                { x: px + lw, y: py + piece.height },
                { x: px, y: py + piece.height },
              ],
            });
            entities.push({
              type: "line",
              points: [
                { x: px, y: py + piece.height },
                { x: px, y: py },
              ],
            });
            lines += 6;
          }

          // Furos
          for (const hole of piece.holes) {
            entities.push({
              type: "circle",
              center: { x: px + hole.x, y: py + hole.y },
              radius: hole.diameter / 2,
            });
            totalLength += Math.PI * hole.diameter;
            circles += 1;
          }

          // Recortes
          for (const cutout of piece.cutouts) {
            if (cutout.type === "circle" && cutout.diameter) {
              entities.push({
                type: "circle",
                center: { x: px + cutout.x, y: py + cutout.y },
                radius: cutout.diameter / 2,
              });
              totalLength += Math.PI * cutout.diameter;
              circles += 1;
            } else if (
              cutout.type === "rectangle" &&
              cutout.width &&
              cutout.height
            ) {
              entities.push({
                type: "line",
                points: [
                  { x: px + cutout.x, y: py + cutout.y },
                  { x: px + cutout.x + cutout.width, y: py + cutout.y },
                ],
              });
              entities.push({
                type: "line",
                points: [
                  { x: px + cutout.x + cutout.width, y: py + cutout.y },
                  {
                    x: px + cutout.x + cutout.width,
                    y: py + cutout.y + cutout.height,
                  },
                ],
              });
              entities.push({
                type: "line",
                points: [
                  {
                    x: px + cutout.x + cutout.width,
                    y: py + cutout.y + cutout.height,
                  },
                  { x: px + cutout.x, y: py + cutout.y + cutout.height },
                ],
              });
              entities.push({
                type: "line",
                points: [
                  { x: px + cutout.x, y: py + cutout.y + cutout.height },
                  { x: px + cutout.x, y: py + cutout.y },
                ],
              });
              totalLength += (cutout.width + cutout.height) * 2;
              lines += 4;
            }
          }

          offsetX += piece.width + sheetConfig.spacing;
          if (offsetX > sheetConfig.width - piece.width) {
            offsetX = 0;
            offsetY += piece.height + sheetConfig.spacing;
          }
        }
      }

      return {
        entities,
        boundingBox: {
          min: { x: 0, y: 0 },
          max: { x: sheetConfig.width, y: sheetConfig.height },
        },
        stats: { lines, arcs, circles, polylines, totalLength },
      };
    },
    [sheetConfig],
  );

  // ═══════════════════════════════════════════════════════════════════════════════
  // SISTEMA DE NESTING (OTIMIZAÇÃO DE CHAPA)
  // ═══════════════════════════════════════════════════════════════════════════════

  const runNesting = useCallback(async () => {
    if (pieces.length === 0) return;

    setIsNesting(true);

    // Tentar usar API do backend para nesting avançado
    try {
      const token = localStorage.getItem("token");
      const headers: Record<string, string> = {
        "Content-Type": "application/json",
      };
      if (token) headers["Authorization"] = `Bearer ${token}`;

      // Converter peças para o formato da API
      const apiPieces = pieces.map((piece) => ({
        name: piece.name,
        type: piece.type,
        width: piece.width,
        height: piece.height,
        diameter:
          piece.type === "circle"
            ? Math.min(piece.width, piece.height)
            : undefined,
        quantity: piece.quantity,
        allow_rotation: true,
      }));

      const response = await fetch(`${API_BASE_URL}/api/cam/nesting/run`, {
        method: "POST",
        headers,
        body: JSON.stringify({
          pieces: apiPieces,
          sheet: {
            width: sheetConfig.width,
            height: sheetConfig.height,
            margin: sheetConfig.margin,
          },
          algorithm: nestingAlgorithm,
          priority: nestingPriority,
          spacing: sheetConfig.spacing,
          rotation_mode: "orthogonal",
        }),
      });

      if (response.ok) {
        const result = await response.json();
        const apiResult = result.result || result;

        setNestingResult({
          placements: apiResult.placements || [],
          efficiency: apiResult.efficiency || 0,
          wasteArea: apiResult.waste_area || 0,
          usedArea: apiResult.used_area || 0,
          totalPieces: apiResult.total_pieces || 0,
          unplacedPieces: apiResult.unplaced_pieces || 0,
        });

        // Converter para geometria
        const geo = piecesToGeometry(pieces);
        setGeometry(geo);
        setFileName("nesting_otimizado.dxf");

        // Sugestões baseadas na eficiência
        const efficiency = apiResult.efficiency || 0;
        setAiSuggestions((prev) => [
          {
            id: `sug_${Date.now()}`,
            type:
              efficiency > 75 ? "info" : efficiency > 60 ? "warning" : "error",
            title: `${NESTING_ALGORITHMS[nestingAlgorithm].name}: ${efficiency.toFixed(1)}%`,
            message:
              efficiency > 75
                ? "Excelente aproveitamento de material!"
                : efficiency > 60
                  ? "Considere testar outro algoritmo para melhorar."
                  : "Tente o algoritmo Genético para melhor otimização.",
            action: efficiency < 75 ? "Testar algoritmo Genético" : undefined,
            priority: efficiency < 60 ? 1 : 3,
          },
          ...prev,
        ]);

        setIsNesting(false);
        return;
      }
    } catch {
      // Fallback para algoritmo local se a API falhar
      console.log("API nesting unavailable, using local algorithm");
    }

    // Algoritmo local de fallback (Bottom-Left)
    setTimeout(() => {
      const placements: NestingResult["placements"] = [];
      let usedArea = 0;
      let unplacedPieces = 0;

      // Expandir peças por quantidade
      const allPieces: PieceDefinition[] = [];
      for (const piece of pieces) {
        for (let i = 0; i < piece.quantity; i++) {
          allPieces.push({ ...piece, id: `${piece.id}_${i}` });
        }
      }

      // Ordenar por área (maior primeiro)
      allPieces.sort((a, b) => b.width * b.height - a.width * a.height);

      // Grid para ocupação
      const gridSize = 10;
      const gridW = Math.ceil(sheetConfig.width / gridSize);
      const gridH = Math.ceil(sheetConfig.height / gridSize);
      const occupied: boolean[][] = Array(gridH)
        .fill(null)
        .map(() => Array(gridW).fill(false));

      const canPlace = (
        x: number,
        y: number,
        w: number,
        h: number,
      ): boolean => {
        const startX = Math.floor(x / gridSize);
        const startY = Math.floor(y / gridSize);
        const endX = Math.ceil((x + w) / gridSize);
        const endY = Math.ceil((y + h) / gridSize);

        if (endX > gridW || endY > gridH) return false;

        for (let gy = startY; gy < endY; gy++) {
          for (let gx = startX; gx < endX; gx++) {
            if (occupied[gy][gx]) return false;
          }
        }
        return true;
      };

      const markOccupied = (x: number, y: number, w: number, h: number) => {
        const startX = Math.floor(x / gridSize);
        const startY = Math.floor(y / gridSize);
        const endX = Math.ceil((x + w) / gridSize);
        const endY = Math.ceil((y + h) / gridSize);

        for (let gy = startY; gy < endY; gy++) {
          for (let gx = startX; gx < endX; gx++) {
            occupied[gy][gx] = true;
          }
        }
      };

      // Posicionar peças
      for (const piece of allPieces) {
        let placed = false;
        const margin = sheetConfig.margin;
        const spacing = sheetConfig.spacing;

        // Tentar posicionar (canto inferior esquerdo primeiro)
        for (
          let y = margin;
          y < sheetConfig.height - piece.height - margin && !placed;
          y += gridSize
        ) {
          for (
            let x = margin;
            x < sheetConfig.width - piece.width - margin && !placed;
            x += gridSize
          ) {
            if (canPlace(x, y, piece.width + spacing, piece.height + spacing)) {
              placements.push({
                pieceId: piece.id,
                x,
                y,
                rotation: 0,
              });
              markOccupied(x, y, piece.width + spacing, piece.height + spacing);
              usedArea += piece.width * piece.height;
              placed = true;
            }
          }
        }

        // Tentar rotacionado 90°
        if (!placed && piece.type !== "circle") {
          for (
            let y = margin;
            y < sheetConfig.height - piece.width - margin && !placed;
            y += gridSize
          ) {
            for (
              let x = margin;
              x < sheetConfig.width - piece.height - margin && !placed;
              x += gridSize
            ) {
              if (
                canPlace(x, y, piece.height + spacing, piece.width + spacing)
              ) {
                placements.push({
                  pieceId: piece.id,
                  x,
                  y,
                  rotation: 90,
                });
                markOccupied(
                  x,
                  y,
                  piece.height + spacing,
                  piece.width + spacing,
                );
                usedArea += piece.width * piece.height;
                placed = true;
              }
            }
          }
        }

        if (!placed) {
          unplacedPieces++;
        }
      }

      const sheetArea = sheetConfig.width * sheetConfig.height;
      const efficiency = (usedArea / sheetArea) * 100;

      setNestingResult({
        placements,
        efficiency,
        wasteArea: sheetArea - usedArea,
        usedArea,
        totalPieces: placements.length,
        unplacedPieces,
      });

      // Converter para geometria
      const geo = piecesToGeometry(pieces);
      setGeometry(geo);
      setFileName("nesting_otimizado.dxf");

      setIsNesting(false);

      // Adicionar sugestão da IA
      setAiSuggestions((prev) => [
        {
          id: `sug_${Date.now()}`,
          type: efficiency > 70 ? "info" : "warning",
          title:
            efficiency > 70 ? "Aproveitamento Bom!" : "Aproveitamento Baixo",
          message: `Eficiência de ${efficiency.toFixed(1)}%. ${efficiency < 70 ? "Considere reorganizar ou adicionar peças menores." : ""}`,
          priority: efficiency < 70 ? 1 : 3,
        },
        ...prev,
      ]);
    }, 1500);
  }, [
    pieces,
    sheetConfig,
    piecesToGeometry,
    nestingAlgorithm,
    nestingPriority,
  ]);

  // ═══════════════════════════════════════════════════════════════════════════════
  // SISTEMA DE IA ASSISTENTE
  // ═══════════════════════════════════════════════════════════════════════════════

  const updateAISuggestions = useCallback(() => {
    const suggestions: AISuggestion[] = [];

    // Verificar problemas comuns
    if (pieces.length === 0) {
      suggestions.push({
        id: "no_pieces",
        type: "info",
        title: "Nenhuma peça definida",
        message:
          "Adicione peças clicando em 'Criar Peça' ou importe um arquivo DXF.",
        priority: 1,
      });
    }

    // Verificar espessura vs amperagem
    if (config.thickness > 12 && config.amperage < 80) {
      suggestions.push({
        id: "low_amperage",
        type: "warning",
        title: "Amperagem Baixa",
        message: `Para ${config.thickness}mm de espessura, recomenda-se pelo menos 80A. Atual: ${config.amperage}A`,
        action: "Ajustar para 80A",
        priority: 1,
      });
    }

    // Verificar furos pequenos
    for (const piece of pieces) {
      for (const hole of piece.holes) {
        if (hole.diameter < config.thickness * 1.5) {
          suggestions.push({
            id: `small_hole_${hole.id}`,
            type: "warning",
            title: "Furo Muito Pequeno",
            message: `Furo de ${hole.diameter}mm em material de ${config.thickness}mm pode ter qualidade ruim. Mínimo recomendado: ${(config.thickness * 1.5).toFixed(1)}mm`,
            priority: 2,
          });
        }
      }
    }

    // Verificar kerf
    if (config.kerfWidth < 1.0) {
      suggestions.push({
        id: "low_kerf",
        type: "warning",
        title: "Kerf Muito Baixo",
        message: "Kerf abaixo de 1.0mm pode causar compensação insuficiente.",
        priority: 2,
      });
    }

    // Sugestão de otimização
    if (pieces.length > 0 && !nestingResult) {
      suggestions.push({
        id: "run_nesting",
        type: "optimization",
        title: "Otimizar Corte",
        message:
          "Execute o algoritmo de nesting para minimizar desperdício de material.",
        action: "Executar Nesting",
        priority: 3,
      });
    }

    setAiSuggestions(suggestions);
  }, [pieces, config, nestingResult]);

  // Chat com IA
  const sendAIMessage = useCallback(async () => {
    if (!aiInput.trim()) return;

    const userMessage = aiInput;
    setAiInput("");
    setAiChatMessages((prev) => [
      ...prev,
      { role: "user", content: userMessage },
    ]);
    setIsAiThinking(true);

    // Simular resposta da IA (em produção, chamar API)
    setTimeout(() => {
      let response = "";
      const lower = userMessage.toLowerCase();

      if (lower.includes("furo") || lower.includes("hole")) {
        response = `Para adicionar furos:\n1. Clique em "Criar Peça"\n2. Na peça, clique em "Adicionar Furo"\n3. Defina diâmetro e posição\n\n💡 Dica: Para material de ${config.thickness}mm, furos devem ter no mínimo ${(config.thickness * 1.5).toFixed(1)}mm de diâmetro.`;
      } else if (
        lower.includes("material") ||
        lower.includes("aço") ||
        lower.includes("alumínio")
      ) {
        response = `Materiais disponíveis:\n• Aço Carbono (até 50mm)\n• Aço Inox (até 25mm)\n• Alumínio (até 20mm)\n• Cobre (até 12mm)\n• Latão (até 10mm)\n• Galvanizado (até 6mm)\n\nAtual: ${MATERIAL_PRESETS[config.material].name} ${config.thickness}mm`;
      } else if (
        lower.includes("nesting") ||
        lower.includes("otimizar") ||
        lower.includes("desperdício")
      ) {
        response = `O sistema de nesting organiza suas peças na chapa para minimizar desperdício.\n\n📊 Chapa atual: ${sheetConfig.width}x${sheetConfig.height}mm\n📐 Margem: ${sheetConfig.margin}mm\n📏 Espaçamento: ${sheetConfig.spacing}mm\n\nClique em "Executar Nesting" para otimizar!`;
      } else if (lower.includes("g-code") || lower.includes("gcode")) {
        response = `O G-code é gerado automaticamente com:\n• Ordem otimizada de corte (internos primeiro)\n• Lead-in/Lead-out para entrada suave\n• Pierce delay adequado ao material\n• Compensação de kerf\n\nApós criar/importar peças e configurar, clique em "Gerar G-code".`;
      } else if (lower.includes("velocidade") || lower.includes("speed")) {
        response = `Velocidade de corte recomendada para ${MATERIAL_PRESETS[config.material].name}:\n\n${Object.entries(
          CUTTING_TABLES[config.material] || {},
        )
          .map(([t, p]) => `• ${t}mm: ${p.speed} mm/min`)
          .join("\n")}\n\nVelocidade atual: ${config.cuttingSpeed} mm/min`;
      } else if (lower.includes("qualidade") || lower.includes("problema")) {
        response = `Dicas para melhor qualidade:\n\n✅ Verifique:\n• Altura de corte (${config.cutHeight}mm atual)\n• Pierce delay (${config.pierceDelay}s atual)\n• THC ${config.thcEnabled ? "ativado ✓" : "desativado ⚠️"}\n\n⚠️ Evite:\n• Velocidade muito alta (causa rebarbas)\n• Amperagem baixa (corte incompleto)\n• Furos menores que 1.5x espessura`;
      } else {
        response = `Posso ajudar com:\n\n🔧 **Criação de Peças**: Defina dimensões, furos e recortes\n📐 **Nesting**: Otimize o uso da chapa\n⚙️ **Parâmetros**: Configure material, velocidade, amperagem\n📄 **G-code**: Gere código para sua máquina CNC\n\nQual desses tópicos você precisa de ajuda?`;
      }

      setAiChatMessages((prev) => [...prev, { role: "ai", content: response }]);
      setIsAiThinking(false);
    }, 1000);
  }, [aiInput, config, sheetConfig]);

  // Aplicar sugestão da IA
  const applyAISuggestion = useCallback(
    (suggestion: AISuggestion) => {
      if (suggestion.id === "low_amperage") {
        updateConfig({ amperage: 80 });
      } else if (suggestion.id === "run_nesting") {
        runNesting();
      }
      setAiSuggestions((prev) => prev.filter((s) => s.id !== suggestion.id));
    },
    [updateConfig, runNesting],
  );

  // Atualizar sugestões quando configuração mudar
  useEffect(() => {
    updateAISuggestions();
  }, [pieces, config, updateAISuggestions]);

  // ── Carregar geometria de demonstração ──
  const loadDemoGeometry = useCallback(() => {
    // Geometria de demonstração: peça com furos e recorte
    const demoGeometry: Geometry = {
      entities: [
        // Contorno externo (retângulo 300x200)
        {
          type: "line",
          points: [
            { x: 0, y: 0 },
            { x: 300, y: 0 },
          ],
        },
        {
          type: "line",
          points: [
            { x: 300, y: 0 },
            { x: 300, y: 200 },
          ],
        },
        {
          type: "line",
          points: [
            { x: 300, y: 200 },
            { x: 0, y: 200 },
          ],
        },
        {
          type: "line",
          points: [
            { x: 0, y: 200 },
            { x: 0, y: 0 },
          ],
        },
        // Furo 1 (círculo r=15)
        { type: "circle", center: { x: 75, y: 100 }, radius: 15 },
        // Furo 2 (círculo r=15)
        { type: "circle", center: { x: 150, y: 100 }, radius: 15 },
        // Furo 3 (círculo r=15)
        { type: "circle", center: { x: 225, y: 100 }, radius: 15 },
        // Recorte retangular interno
        {
          type: "line",
          points: [
            { x: 100, y: 30 },
            { x: 200, y: 30 },
          ],
        },
        {
          type: "line",
          points: [
            { x: 200, y: 30 },
            { x: 200, y: 70 },
          ],
        },
        {
          type: "line",
          points: [
            { x: 200, y: 70 },
            { x: 100, y: 70 },
          ],
        },
        {
          type: "line",
          points: [
            { x: 100, y: 70 },
            { x: 100, y: 30 },
          ],
        },
        // Recorte retangular superior
        {
          type: "line",
          points: [
            { x: 100, y: 130 },
            { x: 200, y: 130 },
          ],
        },
        {
          type: "line",
          points: [
            { x: 200, y: 130 },
            { x: 200, y: 170 },
          ],
        },
        {
          type: "line",
          points: [
            { x: 200, y: 170 },
            { x: 100, y: 170 },
          ],
        },
        {
          type: "line",
          points: [
            { x: 100, y: 170 },
            { x: 100, y: 130 },
          ],
        },
      ],
      boundingBox: {
        min: { x: 0, y: 0 },
        max: { x: 300, y: 200 },
      },
      stats: {
        lines: 12,
        arcs: 0,
        circles: 3,
        polylines: 0,
        totalLength: 1094.2,
      },
    };

    setGeometry(demoGeometry);
    setFileName("demo_peca_exemplo.dxf");
    setStep("complete");
    setActiveTab("config");
    setShowTutorial(false);
  }, []);

  const simulateGCode = () => {
    const demoGCode: GCodeResult = {
      code: `(===================================================)
(  ENGENHARIA CAD - CORTE PLASMA CNC)
(===================================================)
(  Gerado em: ${new Date().toLocaleString("pt-BR")})
(  Material: ${MATERIAL_PRESETS[config.material].name})
(  Espessura: ${config.thickness}mm)
(  Amperagem: ${config.amperage}A)
(  Velocidade: ${config.cuttingSpeed}mm/min)
(  Kerf: ${config.kerfWidth}mm)
(===================================================)
(  Cortes: 4)
(  Comprimento de corte: 628.3mm)
(  Deslocamento rapido: 150.0mm)
(  Tempo estimado: 2.5 min)
(===================================================)

G21 (Unidades: milimetros)
G90 (Coordenadas absolutas)
G17 (Plano XY)
G54 (Sistema de coordenadas da peca)
M05 (Plasma desligado)
G00 Z${config.safeHeight.toFixed(1)} (Altura segura)

(=== CORTE 1/4 - INTERNO ===)
G00 X85.000 Y100.000 (Movimento rapido)
G00 Z${config.pierceHeight.toFixed(1)} (Altura de pierce)
M03 (Plasma ON)
G04 P${Math.round(config.pierceDelay * 1000)} (Pierce delay: ${config.pierceDelay}s)
G01 Z${config.cutHeight.toFixed(1)} F500 (Altura de corte)
G02 X85.000 Y100.000 I15.000 J0.000 F${config.cuttingSpeed}
M05 (Plasma OFF)
G00 Z${config.safeHeight.toFixed(1)}

(=== CORTE 2/4 - INTERNO ===)
G00 X235.000 Y100.000
G00 Z${config.pierceHeight.toFixed(1)}
M03
G04 P${Math.round(config.pierceDelay * 1000)}
G01 Z${config.cutHeight.toFixed(1)} F500
G02 X235.000 Y100.000 I15.000 J0.000 F${config.cuttingSpeed}
M05
G00 Z${config.safeHeight.toFixed(1)}

(=== CORTE 3/4 - EXTERNO ===)
G00 X55.000 Y100.000
G00 Z${config.pierceHeight.toFixed(1)}
M03
G04 P${Math.round(config.pierceDelay * 1000)}
G01 Z${config.cutHeight.toFixed(1)} F500
G02 X55.000 Y100.000 I45.000 J0.000 F${config.cuttingSpeed}
M05
G00 Z${config.safeHeight.toFixed(1)}

(=== CORTE 4/4 - EXTERNO ===)
G00 X200.000 Y50.000
G00 Z${config.pierceHeight.toFixed(1)}
M03
G04 P${Math.round(config.pierceDelay * 1000)}
G01 Z${config.cutHeight.toFixed(1)} F500
G01 X300.000 Y50.000 F${config.cuttingSpeed}
G01 X300.000 Y150.000
G01 X200.000 Y150.000
G01 X200.000 Y50.000
M05
G00 Z${config.safeHeight.toFixed(1)}

(=== FIM DO PROGRAMA ===)
M05 (Plasma OFF)
G00 Z${config.safeHeight.toFixed(1)} (Altura segura)
G00 X0 Y0 (Retorno ao zero)
M02 (Fim do programa)
%`,
      stats: {
        totalCuts: 4,
        cuttingLength: 628.3,
        rapidLength: 150.0,
        estimatedTime: 150,
        internalContours: 2,
        externalContours: 2,
      },
      costEstimate: {
        materialCost: 45.5,
        cuttingTimeCost: 37.75,
        totalCost: 83.25,
        scrapPercentage: 8.5,
      },
      warnings: [
        {
          level: "info",
          message: "THC habilitado para melhor qualidade de corte",
        },
      ],
    };

    setGcode(demoGCode);
    setStep("complete");
    setActiveTab("gcode");
  };

  // ── Download G-code ──
  const handleDownload = useCallback(
    (extension: string) => {
      if (!gcode) return;

      const blob = new Blob([gcode.code], { type: "text/plain" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${fileName.replace(/\.[^.]+$/, "") || "corte"}.${extension}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    },
    [gcode, fileName],
  );

  // ── Copiar G-code para clipboard ──
  const handleCopy = useCallback(async () => {
    if (!gcode) return;

    try {
      await navigator.clipboard.writeText(gcode.code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error("Erro ao copiar:", err);
      setError("Não foi possível copiar para a área de transferência");
      setTimeout(() => setError(null), 3000);
    }
  }, [gcode]);

  // ── Canvas preview rendering ──
  useEffect(() => {
    if (!canvasRef.current || !geometry) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    // Limpar canvas
    ctx.fillStyle = theme.background;
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Calcular escala e offset
    const bbox = geometry.boundingBox;
    const padding = 40;
    const scaleX = (canvas.width - padding * 2) / (bbox.max.x - bbox.min.x);
    const scaleY = (canvas.height - padding * 2) / (bbox.max.y - bbox.min.y);
    const scale = Math.min(scaleX, scaleY);

    const offsetX =
      padding +
      (canvas.width - padding * 2 - (bbox.max.x - bbox.min.x) * scale) / 2;
    const offsetY =
      padding +
      (canvas.height - padding * 2 - (bbox.max.y - bbox.min.y) * scale) / 2;

    const transform = (p: Point): Point => ({
      x: offsetX + (p.x - bbox.min.x) * scale,
      y: canvas.height - (offsetY + (p.y - bbox.min.y) * scale),
    });

    // Desenhar grid
    ctx.strokeStyle = theme.border;
    ctx.lineWidth = 0.5;
    const gridSize = 50 * scale;
    for (let x = offsetX; x < canvas.width - padding; x += gridSize) {
      ctx.beginPath();
      ctx.moveTo(x, padding);
      ctx.lineTo(x, canvas.height - padding);
      ctx.stroke();
    }
    for (let y = padding; y < canvas.height - padding; y += gridSize) {
      ctx.beginPath();
      ctx.moveTo(padding, y);
      ctx.lineTo(canvas.width - padding, y);
      ctx.stroke();
    }

    // Desenhar entidades
    ctx.strokeStyle = theme.accentPrimary;
    ctx.lineWidth = 2;

    for (const entity of geometry.entities) {
      ctx.beginPath();

      if (entity.type === "circle" && entity.center && entity.radius) {
        const center = transform(entity.center);
        ctx.arc(center.x, center.y, entity.radius * scale, 0, Math.PI * 2);
      } else if (entity.type === "polyline" && entity.points) {
        const points = entity.points.map(transform);
        ctx.moveTo(points[0].x, points[0].y);
        for (let i = 1; i < points.length; i++) {
          ctx.lineTo(points[i].x, points[i].y);
        }
        if (entity.closed) {
          ctx.closePath();
        }
      } else if (
        entity.type === "line" &&
        entity.points &&
        entity.points.length >= 2
      ) {
        const p1 = transform(entity.points[0]);
        const p2 = transform(entity.points[1]);
        ctx.moveTo(p1.x, p1.y);
        ctx.lineTo(p2.x, p2.y);
      }

      ctx.stroke();
    }

    // Marcar pontos de entrada (lead-in) se G-code gerado
    if (gcode) {
      ctx.fillStyle = theme.success;
      for (const entity of geometry.entities) {
        let entryPoint: Point | null = null;

        if (entity.type === "circle" && entity.center && entity.radius) {
          entryPoint = {
            x: entity.center.x + entity.radius,
            y: entity.center.y,
          };
        } else if (
          entity.type === "polyline" &&
          entity.points &&
          entity.points.length > 0
        ) {
          entryPoint = entity.points[0];
        }

        if (entryPoint) {
          const tp = transform(entryPoint);
          ctx.beginPath();
          ctx.arc(tp.x, tp.y, 4, 0, Math.PI * 2);
          ctx.fill();
        }
      }
    }
  }, [geometry, gcode, theme]);

  // ── Styles ──
  const containerStyle: React.CSSProperties = {
    minHeight: "100vh",
    backgroundColor: theme.background,
    padding: "24px",
    color: theme.textPrimary,
  };

  const cardStyle: React.CSSProperties = {
    backgroundColor: theme.surface,
    border: `1px solid ${theme.border}`,
    borderRadius: "12px",
    padding: "20px",
  };

  const inputStyle: React.CSSProperties = {
    backgroundColor: theme.inputBackground,
    border: `1px solid ${theme.inputBorder}`,
    borderRadius: "6px",
    padding: "10px 12px",
    color: theme.textPrimary,
    fontSize: "14px",
    width: "100%",
    outline: "none",
  };

  const labelStyle: React.CSSProperties = {
    fontSize: "12px",
    color: theme.textSecondary,
    fontWeight: 600,
    textTransform: "uppercase",
    letterSpacing: "0.5px",
    marginBottom: "6px",
    display: "block",
  };

  const btnPrimary: React.CSSProperties = {
    backgroundColor: theme.accentPrimary,
    color: "#FFFFFF",
    border: "none",
    borderRadius: "8px",
    padding: "12px 24px",
    fontWeight: 600,
    cursor: "pointer",
    display: "flex",
    alignItems: "center",
    gap: "8px",
    fontSize: "14px",
  };

  const btnSecondary: React.CSSProperties = {
    backgroundColor: "transparent",
    color: theme.textPrimary,
    border: `1px solid ${theme.border}`,
    borderRadius: "8px",
    padding: "10px 16px",
    fontWeight: 500,
    cursor: "pointer",
    display: "flex",
    alignItems: "center",
    gap: "8px",
    fontSize: "13px",
  };

  const tabStyle = (active: boolean): React.CSSProperties => ({
    padding: "12px 20px",
    backgroundColor: active ? theme.accentPrimary + "20" : "transparent",
    color: active ? theme.accentPrimary : theme.textSecondary,
    border: "none",
    borderBottom: active
      ? `2px solid ${theme.accentPrimary}`
      : "2px solid transparent",
    cursor: "pointer",
    fontWeight: active ? 600 : 500,
    fontSize: "14px",
    display: "flex",
    alignItems: "center",
    gap: "8px",
  });

  // ── Feature gate: CNC requires paid plan ──
  if (!canUse("cnc")) {
    return (
      <div
        style={{
          minHeight: "100vh",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          background: theme.gradientPage || theme.background,
          gap: "24px",
          padding: "32px",
          textAlign: "center",
        }}
      >
        <div style={{ fontSize: "64px" }}>🔒</div>
        <h2
          style={{
            color: theme.textPrimary,
            fontSize: "24px",
            fontWeight: 700,
            margin: 0,
          }}
        >
          CNC Plasma Otimizado
        </h2>
        <p
          style={{
            color: theme.textSecondary,
            fontSize: "15px",
            maxWidth: "480px",
            lineHeight: 1.6,
            margin: 0,
          }}
        >
          Este módulo está disponível nos planos{" "}
          <strong style={{ color: theme.accentPrimary }}>Professional</strong> e{" "}
          <strong style={{ color: theme.accentInfo || theme.accentPrimary }}>
            Enterprise
          </strong>
          . Gere G-code otimizado, aninhamento inteligente e controle de corte
          plasma com IA.
        </p>
        <div
          style={{
            display: "flex",
            gap: "12px",
            flexWrap: "wrap",
            justifyContent: "center",
          }}
        >
          <button
            onClick={() =>
              triggerUpgrade(
                "Módulo CNC Plasma está disponível nos planos Professional e Enterprise.",
              )
            }
            style={{
              padding: "14px 32px",
              background: theme.gradientAccent || theme.accentPrimary,
              color: "#fff",
              border: "none",
              borderRadius: "10px",
              fontSize: "15px",
              fontWeight: 700,
              cursor: "pointer",
              letterSpacing: "0.5px",
            }}
          >
            🚀 Ver Planos
          </button>
          <button
            onClick={() => {
              const t = encodeURIComponent(
                "Olá! Quero saber mais sobre o módulo CNC do Engenharia CAD.",
              );
              window.open(`https://wa.me/5531992681231?text=${t}`, "_blank");
            }}
            style={{
              padding: "14px 32px",
              background: "#25D366",
              color: "#fff",
              border: "none",
              borderRadius: "10px",
              fontSize: "15px",
              fontWeight: 700,
              cursor: "pointer",
            }}
          >
            💬 Falar com Consultor
          </button>
        </div>
        <div
          style={{
            display: "flex",
            gap: "16px",
            flexWrap: "wrap",
            justifyContent: "center",
            marginTop: "8px",
          }}
        >
          {[
            "G-code automático",
            "Nesting IA",
            "Corte plasma otimizado",
            "Controle multi-máquina",
          ].map((f) => (
            <div
              key={f}
              style={{
                background: "#111827",
                border: "1px solid #1e3050",
                borderRadius: "8px",
                padding: "8px 16px",
                color: "#a0b0c0",
                fontSize: "13px",
                opacity: 0.6,
                filter: "blur(0.5px)",
              }}
            >
              🔒 {f}
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div style={containerStyle}>
      {/* Header */}
      <div style={{ marginBottom: "24px" }}>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            marginBottom: "8px",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            <div
              style={{
                width: "48px",
                height: "48px",
                borderRadius: "12px",
                backgroundColor: `${theme.warning}20`,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <Flame size={28} color={theme.warning} />
            </div>
            <div>
              <h1
                style={{
                  fontSize: "24px",
                  fontWeight: 700,
                  margin: 0,
                  color: theme.textPrimary,
                }}
              >
                Controle CNC / Geração de Corte
              </h1>
              <p
                style={{
                  fontSize: "14px",
                  color: theme.textSecondary,
                  margin: 0,
                }}
              >
                Transforme desenhos CAD em arquivos G-code otimizados para corte
                plasma
              </p>
            </div>
          </div>

          {/* Botões de ajuda */}
          <div style={{ display: "flex", gap: "8px" }}>
            <button
              onClick={() => setShowTutorial(!showTutorial)}
              style={{
                ...btnSecondary,
                backgroundColor: showTutorial
                  ? theme.accentPrimary
                  : btnSecondary.backgroundColor,
                color: showTutorial ? "#fff" : btnSecondary.color,
              }}
            >
              <HelpCircle size={16} /> Como Usar
            </button>
            <button
              onClick={() => setShowAutoCADGuide(!showAutoCADGuide)}
              style={{
                ...btnSecondary,
                backgroundColor: showAutoCADGuide
                  ? theme.success
                  : btnSecondary.backgroundColor,
                color: showAutoCADGuide ? "#fff" : btnSecondary.color,
              }}
            >
              <Monitor size={16} /> Guia AutoCAD
            </button>
            <button
              onClick={loadDemoGeometry}
              style={{
                ...btnSecondary,
                backgroundColor: `${theme.warning}20`,
                color: theme.warning,
                border: `1px solid ${theme.warning}40`,
              }}
            >
              <Sparkles size={16} /> Carregar Demo
            </button>
            <button
              onClick={() => setShowStatisticsPanel(!showStatisticsPanel)}
              style={{
                ...btnSecondary,
                backgroundColor: showStatisticsPanel
                  ? `${theme.success}20`
                  : btnSecondary.backgroundColor,
                color: showStatisticsPanel ? theme.success : btnSecondary.color,
                border: showStatisticsPanel
                  ? `1px solid ${theme.success}40`
                  : undefined,
              }}
            >
              <TrendingUp size={16} /> Estatísticas
            </button>
          </div>
        </div>
      </div>

      {/* Tutorial Passo-a-Passo */}
      <AnimatePresence>
        {showTutorial && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            style={{
              ...cardStyle,
              marginBottom: "24px",
              background: `linear-gradient(135deg, ${theme.accentPrimary}10, ${theme.panel})`,
              border: `1px solid ${theme.accentPrimary}30`,
            }}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                marginBottom: "20px",
              }}
            >
              <h3
                style={{
                  fontSize: "16px",
                  fontWeight: 600,
                  color: theme.textPrimary,
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                }}
              >
                <BookOpen size={20} color={theme.accentPrimary} /> Tutorial:
                Como Gerar G-code para Corte Plasma
              </h3>
              <button
                onClick={() => setShowTutorial(false)}
                style={{
                  background: "none",
                  border: "none",
                  cursor: "pointer",
                  padding: "4px",
                }}
              >
                <X size={18} color={theme.textSecondary} />
              </button>
            </div>

            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(4, 1fr)",
                gap: "16px",
              }}
            >
              {/* Passo 1 */}
              <div
                style={{
                  padding: "16px",
                  backgroundColor: theme.panel,
                  borderRadius: "12px",
                  border: `1px solid ${theme.border}`,
                  textAlign: "center",
                }}
              >
                <div
                  style={{
                    width: "40px",
                    height: "40px",
                    borderRadius: "50%",
                    backgroundColor: `${theme.accentPrimary}20`,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    margin: "0 auto 12px",
                    fontSize: "18px",
                    fontWeight: 700,
                    color: theme.accentPrimary,
                  }}
                >
                  1
                </div>
                <FileUp
                  size={24}
                  color={theme.accentPrimary}
                  style={{ marginBottom: "8px" }}
                />
                <h4
                  style={{
                    fontSize: "14px",
                    fontWeight: 600,
                    color: theme.textPrimary,
                    marginBottom: "4px",
                  }}
                >
                  Importar Desenho
                </h4>
                <p
                  style={{
                    fontSize: "12px",
                    color: theme.textSecondary,
                    margin: 0,
                  }}
                >
                  Arraste um arquivo DXF ou SVG exportado do AutoCAD
                </p>
              </div>

              {/* Passo 2 */}
              <div
                style={{
                  padding: "16px",
                  backgroundColor: theme.panel,
                  borderRadius: "12px",
                  border: `1px solid ${theme.border}`,
                  textAlign: "center",
                }}
              >
                <div
                  style={{
                    width: "40px",
                    height: "40px",
                    borderRadius: "50%",
                    backgroundColor: `${theme.warning}20`,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    margin: "0 auto 12px",
                    fontSize: "18px",
                    fontWeight: 700,
                    color: theme.warning,
                  }}
                >
                  2
                </div>
                <Cog
                  size={24}
                  color={theme.warning}
                  style={{ marginBottom: "8px" }}
                />
                <h4
                  style={{
                    fontSize: "14px",
                    fontWeight: 600,
                    color: theme.textPrimary,
                    marginBottom: "4px",
                  }}
                >
                  Configurar Corte
                </h4>
                <p
                  style={{
                    fontSize: "12px",
                    color: theme.textSecondary,
                    margin: 0,
                  }}
                >
                  Selecione material, espessura e ajuste parâmetros
                </p>
              </div>

              {/* Passo 3 */}
              <div
                style={{
                  padding: "16px",
                  backgroundColor: theme.panel,
                  borderRadius: "12px",
                  border: `1px solid ${theme.border}`,
                  textAlign: "center",
                }}
              >
                <div
                  style={{
                    width: "40px",
                    height: "40px",
                    borderRadius: "50%",
                    backgroundColor: `${theme.success}20`,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    margin: "0 auto 12px",
                    fontSize: "18px",
                    fontWeight: 700,
                    color: theme.success,
                  }}
                >
                  3
                </div>
                <Play
                  size={24}
                  color={theme.success}
                  style={{ marginBottom: "8px" }}
                />
                <h4
                  style={{
                    fontSize: "14px",
                    fontWeight: 600,
                    color: theme.textPrimary,
                    marginBottom: "4px",
                  }}
                >
                  Gerar G-code
                </h4>
                <p
                  style={{
                    fontSize: "12px",
                    color: theme.textSecondary,
                    margin: 0,
                  }}
                >
                  Clique em "Gerar G-code" para processar
                </p>
              </div>

              {/* Passo 4 */}
              <div
                style={{
                  padding: "16px",
                  backgroundColor: theme.panel,
                  borderRadius: "12px",
                  border: `1px solid ${theme.border}`,
                  textAlign: "center",
                }}
              >
                <div
                  style={{
                    width: "40px",
                    height: "40px",
                    borderRadius: "50%",
                    backgroundColor: `${theme.danger}20`,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    margin: "0 auto 12px",
                    fontSize: "18px",
                    fontWeight: 700,
                    color: theme.danger,
                  }}
                >
                  4
                </div>
                <Send
                  size={24}
                  color={theme.danger}
                  style={{ marginBottom: "8px" }}
                />
                <h4
                  style={{
                    fontSize: "14px",
                    fontWeight: 600,
                    color: theme.textPrimary,
                    marginBottom: "4px",
                  }}
                >
                  Enviar p/ Máquina
                </h4>
                <p
                  style={{
                    fontSize: "12px",
                    color: theme.textSecondary,
                    margin: 0,
                  }}
                >
                  Baixe .NC/.TAP ou copie para a máquina CNC
                </p>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Guia de Integração AutoCAD */}
      <AnimatePresence>
        {showAutoCADGuide && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            style={{
              ...cardStyle,
              marginBottom: "24px",
              background: `linear-gradient(135deg, ${theme.success}10, ${theme.panel})`,
              border: `1px solid ${theme.success}30`,
            }}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                marginBottom: "20px",
              }}
            >
              <h3
                style={{
                  fontSize: "16px",
                  fontWeight: 600,
                  color: theme.textPrimary,
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                }}
              >
                <Monitor size={20} color={theme.success} /> Integração com
                AutoCAD
              </h3>
              <button
                onClick={() => setShowAutoCADGuide(false)}
                style={{
                  background: "none",
                  border: "none",
                  cursor: "pointer",
                  padding: "4px",
                }}
              >
                <X size={18} color={theme.textSecondary} />
              </button>
            </div>

            <div
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 1fr",
                gap: "24px",
              }}
            >
              {/* Método 1 */}
              <div
                style={{
                  padding: "20px",
                  backgroundColor: theme.panel,
                  borderRadius: "12px",
                  border: `1px solid ${theme.border}`,
                }}
              >
                <h4
                  style={{
                    fontSize: "14px",
                    fontWeight: 600,
                    color: theme.success,
                    marginBottom: "12px",
                    display: "flex",
                    alignItems: "center",
                    gap: "6px",
                  }}
                >
                  <FileText size={16} /> Método Manual (Exportar DXF)
                </h4>
                <ol
                  style={{
                    fontSize: "13px",
                    color: theme.textSecondary,
                    paddingLeft: "20px",
                    margin: 0,
                    lineHeight: "1.8",
                  }}
                >
                  <li>
                    Abra seu desenho no <strong>AutoCAD</strong>
                  </li>
                  <li>Selecione os contornos para corte</li>
                  <li>
                    Digite{" "}
                    <code
                      style={{
                        backgroundColor: theme.inputBackground,
                        padding: "2px 6px",
                        borderRadius: "4px",
                      }}
                    >
                      SAVEAS
                    </code>{" "}
                    ou{" "}
                    <code
                      style={{
                        backgroundColor: theme.inputBackground,
                        padding: "2px 6px",
                        borderRadius: "4px",
                      }}
                    >
                      EXPORT
                    </code>
                  </li>
                  <li>
                    Escolha formato <strong>DXF</strong>
                  </li>
                  <li>Arraste o arquivo aqui ou clique para importar</li>
                </ol>
              </div>

              {/* Método 2 */}
              <div
                style={{
                  padding: "20px",
                  backgroundColor: theme.panel,
                  borderRadius: "12px",
                  border: `1px solid ${theme.border}`,
                }}
              >
                <h4
                  style={{
                    fontSize: "14px",
                    fontWeight: 600,
                    color: theme.accentPrimary,
                    marginBottom: "12px",
                    display: "flex",
                    alignItems: "center",
                    gap: "6px",
                  }}
                >
                  <Zap size={16} /> Método Automático (Plugin)
                </h4>
                <ol
                  style={{
                    fontSize: "13px",
                    color: theme.textSecondary,
                    paddingLeft: "20px",
                    margin: 0,
                    lineHeight: "1.8",
                  }}
                >
                  <li>
                    Copie{" "}
                    <code
                      style={{
                        backgroundColor: theme.inputBackground,
                        padding: "2px 6px",
                        borderRadius: "4px",
                      }}
                    >
                      forge_vigilante.lsp
                    </code>{" "}
                    para pasta do AutoCAD
                  </li>
                  <li>
                    No AutoCAD, digite{" "}
                    <code
                      style={{
                        backgroundColor: theme.inputBackground,
                        padding: "2px 6px",
                        borderRadius: "4px",
                      }}
                    >
                      APPLOAD
                    </code>
                  </li>
                  <li>Carregue o arquivo LSP</li>
                  <li>
                    Digite{" "}
                    <code
                      style={{
                        backgroundColor: theme.inputBackground,
                        padding: "2px 6px",
                        borderRadius: "4px",
                      }}
                    >
                      FORGE-SYNC
                    </code>{" "}
                    para sincronizar automaticamente
                  </li>
                  <li>O desenho será enviado direto para este sistema!</li>
                </ol>
                <div
                  style={{
                    marginTop: "12px",
                    padding: "8px 12px",
                    backgroundColor: `${theme.warning}15`,
                    borderRadius: "6px",
                    fontSize: "12px",
                    color: theme.warning,
                  }}
                >
                  💡 Dica: O plugin sincroniza automaticamente sempre que você
                  salvar o desenho!
                </div>
              </div>
            </div>

            {/* Compatibilidade */}
            <div
              style={{
                marginTop: "16px",
                padding: "12px 16px",
                backgroundColor: theme.inputBackground,
                borderRadius: "8px",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
              }}
            >
              <span style={{ fontSize: "13px", color: theme.textSecondary }}>
                <strong>Compatível com:</strong> AutoCAD 2018+, Mach3, LinuxCNC,
                Plasma Edge, UCCNC
              </span>
              <span style={{ fontSize: "12px", color: theme.textTertiary }}>
                Formatos: DXF R12/R14/2000+, SVG
              </span>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Abas de Modo de Operação */}
      <div
        style={{
          display: "flex",
          gap: "4px",
          marginBottom: "16px",
          padding: "4px",
          backgroundColor: theme.inputBackground,
          borderRadius: "12px",
          width: "fit-content",
        }}
      >
        <button
          onClick={() => setOperationMode("import")}
          style={{
            padding: "10px 20px",
            borderRadius: "8px",
            border: "none",
            backgroundColor:
              operationMode === "import" ? theme.accentPrimary : "transparent",
            color: operationMode === "import" ? "#fff" : theme.textSecondary,
            fontWeight: 600,
            fontSize: "13px",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            gap: "8px",
            transition: "all 0.2s",
          }}
        >
          <Upload size={16} /> Importar DXF/SVG
        </button>
        <button
          onClick={() => setOperationMode("create")}
          style={{
            padding: "10px 20px",
            borderRadius: "8px",
            border: "none",
            backgroundColor:
              operationMode === "create" ? theme.success : "transparent",
            color: operationMode === "create" ? "#fff" : theme.textSecondary,
            fontWeight: 600,
            fontSize: "13px",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            gap: "8px",
            transition: "all 0.2s",
          }}
        >
          <PenTool size={16} /> Criar Peças
        </button>
        <button
          onClick={() => setOperationMode("nesting")}
          style={{
            padding: "10px 20px",
            borderRadius: "8px",
            border: "none",
            backgroundColor:
              operationMode === "nesting" ? theme.warning : "transparent",
            color: operationMode === "nesting" ? "#fff" : theme.textSecondary,
            fontWeight: 600,
            fontSize: "13px",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            gap: "8px",
            transition: "all 0.2s",
          }}
        >
          <LayoutGrid size={16} /> Nesting (Otimizar Chapa)
        </button>
      </div>

      {/* Main content */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: showAIAssistant
            ? "1fr 400px 320px"
            : "1fr 400px",
          gap: "24px",
        }}
      >
        {/* Left panel - Preview and G-code */}
        <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          {/* ═══════════════════════════════════════════════════════════════════════════════ */}
          {/* MODO: CRIAR PEÇAS */}
          {/* ═══════════════════════════════════════════════════════════════════════════════ */}
          {operationMode === "create" && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              style={cardStyle}
            >
              <h3
                style={{
                  fontSize: "16px",
                  fontWeight: 600,
                  marginBottom: "16px",
                  color: theme.textPrimary,
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                }}
              >
                <PenTool size={20} color={theme.success} /> Criar Peças para
                Corte
              </h3>

              {/* Tipos de peça */}
              <p
                style={{
                  fontSize: "13px",
                  color: theme.textSecondary,
                  marginBottom: "12px",
                }}
              >
                Selecione o tipo de peça:
              </p>
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(4, 1fr)",
                  gap: "12px",
                  marginBottom: "20px",
                }}
              >
                <button
                  onClick={() => createNewPiece("rectangle")}
                  style={{
                    padding: "20px 12px",
                    borderRadius: "12px",
                    border: `2px solid ${theme.border}`,
                    backgroundColor: theme.inputBackground,
                    cursor: "pointer",
                    display: "flex",
                    flexDirection: "column",
                    alignItems: "center",
                    gap: "8px",
                    transition: "all 0.2s",
                  }}
                >
                  <RectangleHorizontal size={32} color={theme.accentPrimary} />
                  <span
                    style={{
                      fontSize: "12px",
                      fontWeight: 600,
                      color: theme.textPrimary,
                    }}
                  >
                    Retângulo
                  </span>
                </button>
                <button
                  onClick={() => createNewPiece("circle")}
                  style={{
                    padding: "20px 12px",
                    borderRadius: "12px",
                    border: `2px solid ${theme.border}`,
                    backgroundColor: theme.inputBackground,
                    cursor: "pointer",
                    display: "flex",
                    flexDirection: "column",
                    alignItems: "center",
                    gap: "8px",
                    transition: "all 0.2s",
                  }}
                >
                  <Circle size={32} color={theme.warning} />
                  <span
                    style={{
                      fontSize: "12px",
                      fontWeight: 600,
                      color: theme.textPrimary,
                    }}
                  >
                    Círculo
                  </span>
                </button>
                <button
                  onClick={() => createNewPiece("L_shape")}
                  style={{
                    padding: "20px 12px",
                    borderRadius: "12px",
                    border: `2px solid ${theme.border}`,
                    backgroundColor: theme.inputBackground,
                    cursor: "pointer",
                    display: "flex",
                    flexDirection: "column",
                    alignItems: "center",
                    gap: "8px",
                    transition: "all 0.2s",
                  }}
                >
                  <CornerDownRight size={32} color={theme.success} />
                  <span
                    style={{
                      fontSize: "12px",
                      fontWeight: 600,
                      color: theme.textPrimary,
                    }}
                  >
                    Forma L
                  </span>
                </button>
                <button
                  onClick={() => createNewPiece("U_shape")}
                  style={{
                    padding: "20px 12px",
                    borderRadius: "12px",
                    border: `2px solid ${theme.border}`,
                    backgroundColor: theme.inputBackground,
                    cursor: "pointer",
                    display: "flex",
                    flexDirection: "column",
                    alignItems: "center",
                    gap: "8px",
                    transition: "all 0.2s",
                  }}
                >
                  <Package size={32} color={theme.danger} />
                  <span
                    style={{
                      fontSize: "12px",
                      fontWeight: 600,
                      color: theme.textPrimary,
                    }}
                  >
                    Forma U
                  </span>
                </button>
              </div>

              {/* Lista de peças criadas */}
              {pieces.length > 0 && (
                <>
                  <h4
                    style={{
                      fontSize: "14px",
                      fontWeight: 600,
                      marginBottom: "12px",
                      color: theme.textPrimary,
                    }}
                  >
                    Peças Criadas (
                    {pieces.reduce((acc, p) => acc + p.quantity, 0)} total)
                  </h4>
                  <div
                    style={{
                      display: "flex",
                      flexDirection: "column",
                      gap: "8px",
                      maxHeight: "300px",
                      overflowY: "auto",
                    }}
                  >
                    {pieces.map((piece) => (
                      <div
                        key={piece.id}
                        style={{
                          padding: "12px 16px",
                          backgroundColor: theme.inputBackground,
                          borderRadius: "8px",
                          display: "flex",
                          justifyContent: "space-between",
                          alignItems: "center",
                        }}
                      >
                        <div
                          style={{
                            display: "flex",
                            alignItems: "center",
                            gap: "12px",
                          }}
                        >
                          {piece.type === "rectangle" && (
                            <RectangleHorizontal
                              size={20}
                              color={theme.accentPrimary}
                            />
                          )}
                          {piece.type === "circle" && (
                            <Circle size={20} color={theme.warning} />
                          )}
                          {piece.type === "L_shape" && (
                            <CornerDownRight size={20} color={theme.success} />
                          )}
                          {piece.type === "U_shape" && (
                            <Package size={20} color={theme.danger} />
                          )}
                          <div>
                            <div
                              style={{
                                fontSize: "14px",
                                fontWeight: 600,
                                color: theme.textPrimary,
                              }}
                            >
                              {piece.name}
                            </div>
                            <div
                              style={{
                                fontSize: "12px",
                                color: theme.textSecondary,
                              }}
                            >
                              {piece.width}x{piece.height}mm •{" "}
                              {piece.holes.length} furos • Qtd: {piece.quantity}
                            </div>
                          </div>
                        </div>
                        <div style={{ display: "flex", gap: "8px" }}>
                          <button
                            onClick={() => {
                              setEditingPiece(piece);
                              setShowPieceEditor(true);
                            }}
                            style={{
                              ...btnSecondary,
                              padding: "6px 12px",
                              fontSize: "12px",
                            }}
                          >
                            <Cog size={14} /> Editar
                          </button>
                          <button
                            onClick={() => removePiece(piece.id)}
                            style={{
                              ...btnSecondary,
                              padding: "6px 12px",
                              fontSize: "12px",
                              color: theme.danger,
                            }}
                          >
                            <Trash2 size={14} />
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Ações */}
                  <div
                    style={{ display: "flex", gap: "12px", marginTop: "16px" }}
                  >
                    <button
                      onClick={() => {
                        const geo = piecesToGeometry(pieces);
                        setGeometry(geo);
                        setFileName(`pecas_${pieces.length}_itens.dxf`);
                        setOperationMode("import");
                      }}
                      style={{
                        ...btnPrimary,
                        flex: 1,
                        justifyContent: "center",
                      }}
                    >
                      <CheckCircle2 size={16} /> Usar Essas Peças
                    </button>
                    <button
                      onClick={() => setOperationMode("nesting")}
                      style={{
                        ...btnSecondary,
                        flex: 1,
                        justifyContent: "center",
                        backgroundColor: `${theme.warning}20`,
                        color: theme.warning,
                      }}
                    >
                      <LayoutGrid size={16} /> Otimizar na Chapa
                    </button>
                  </div>
                </>
              )}
            </motion.div>
          )}

          {/* ═══════════════════════════════════════════════════════════════════════════════ */}
          {/* MODO: NESTING */}
          {/* ═══════════════════════════════════════════════════════════════════════════════ */}
          {operationMode === "nesting" && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              style={cardStyle}
            >
              <h3
                style={{
                  fontSize: "16px",
                  fontWeight: 600,
                  marginBottom: "16px",
                  color: theme.textPrimary,
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                }}
              >
                <LayoutGrid size={20} color={theme.warning} /> Nesting -
                Otimização de Chapa
              </h3>

              {/* Configuração da chapa */}
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "1fr 1fr",
                  gap: "16px",
                  marginBottom: "20px",
                }}
              >
                <div>
                  <label
                    style={{
                      fontSize: "12px",
                      fontWeight: 600,
                      color: theme.textSecondary,
                      marginBottom: "4px",
                      display: "block",
                    }}
                  >
                    Largura da Chapa (mm)
                  </label>
                  <input
                    type="number"
                    value={sheetConfig.width}
                    onChange={(e) =>
                      setSheetConfig((prev) => ({
                        ...prev,
                        width: Number(e.target.value),
                      }))
                    }
                    style={{
                      width: "100%",
                      padding: "10px 12px",
                      borderRadius: "8px",
                      border: `1px solid ${theme.border}`,
                      backgroundColor: theme.inputBackground,
                      color: theme.textPrimary,
                      fontSize: "14px",
                    }}
                  />
                </div>
                <div>
                  <label
                    style={{
                      fontSize: "12px",
                      fontWeight: 600,
                      color: theme.textSecondary,
                      marginBottom: "4px",
                      display: "block",
                    }}
                  >
                    Altura da Chapa (mm)
                  </label>
                  <input
                    type="number"
                    value={sheetConfig.height}
                    onChange={(e) =>
                      setSheetConfig((prev) => ({
                        ...prev,
                        height: Number(e.target.value),
                      }))
                    }
                    style={{
                      width: "100%",
                      padding: "10px 12px",
                      borderRadius: "8px",
                      border: `1px solid ${theme.border}`,
                      backgroundColor: theme.inputBackground,
                      color: theme.textPrimary,
                      fontSize: "14px",
                    }}
                  />
                </div>
                <div>
                  <label
                    style={{
                      fontSize: "12px",
                      fontWeight: 600,
                      color: theme.textSecondary,
                      marginBottom: "4px",
                      display: "block",
                    }}
                  >
                    Margem (mm)
                  </label>
                  <input
                    type="number"
                    value={sheetConfig.margin}
                    onChange={(e) =>
                      setSheetConfig((prev) => ({
                        ...prev,
                        margin: Number(e.target.value),
                      }))
                    }
                    style={{
                      width: "100%",
                      padding: "10px 12px",
                      borderRadius: "8px",
                      border: `1px solid ${theme.border}`,
                      backgroundColor: theme.inputBackground,
                      color: theme.textPrimary,
                      fontSize: "14px",
                    }}
                  />
                </div>
                <div>
                  <label
                    style={{
                      fontSize: "12px",
                      fontWeight: 600,
                      color: theme.textSecondary,
                      marginBottom: "4px",
                      display: "block",
                    }}
                  >
                    Espaçamento entre Peças (mm)
                  </label>
                  <input
                    type="number"
                    value={sheetConfig.spacing}
                    onChange={(e) =>
                      setSheetConfig((prev) => ({
                        ...prev,
                        spacing: Number(e.target.value),
                      }))
                    }
                    style={{
                      width: "100%",
                      padding: "10px 12px",
                      borderRadius: "8px",
                      border: `1px solid ${theme.border}`,
                      backgroundColor: theme.inputBackground,
                      color: theme.textPrimary,
                      fontSize: "14px",
                    }}
                  />
                </div>
              </div>

              {/* Resumo das peças */}
              <div
                style={{
                  padding: "16px",
                  backgroundColor: theme.inputBackground,
                  borderRadius: "12px",
                  marginBottom: "16px",
                }}
              >
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    marginBottom: "8px",
                  }}
                >
                  <span
                    style={{ fontSize: "13px", color: theme.textSecondary }}
                  >
                    Peças para posicionar:
                  </span>
                  <span
                    style={{
                      fontSize: "14px",
                      fontWeight: 600,
                      color: theme.textPrimary,
                    }}
                  >
                    {pieces.reduce((acc, p) => acc + p.quantity, 0)} peças
                  </span>
                </div>
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    marginBottom: "8px",
                  }}
                >
                  <span
                    style={{ fontSize: "13px", color: theme.textSecondary }}
                  >
                    Área da chapa:
                  </span>
                  <span
                    style={{
                      fontSize: "14px",
                      fontWeight: 600,
                      color: theme.textPrimary,
                    }}
                  >
                    {(
                      (sheetConfig.width * sheetConfig.height) /
                      1000000
                    ).toFixed(2)}{" "}
                    m²
                  </span>
                </div>
                {nestingResult && (
                  <>
                    <div
                      style={{
                        height: "1px",
                        backgroundColor: theme.border,
                        margin: "12px 0",
                      }}
                    />
                    <div
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        marginBottom: "8px",
                      }}
                    >
                      <span
                        style={{ fontSize: "13px", color: theme.textSecondary }}
                      >
                        Eficiência:
                      </span>
                      <span
                        style={{
                          fontSize: "14px",
                          fontWeight: 700,
                          color:
                            nestingResult.efficiency > 70
                              ? theme.success
                              : theme.warning,
                        }}
                      >
                        {nestingResult.efficiency.toFixed(1)}%
                      </span>
                    </div>
                    <div
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        marginBottom: "8px",
                      }}
                    >
                      <span
                        style={{ fontSize: "13px", color: theme.textSecondary }}
                      >
                        Peças posicionadas:
                      </span>
                      <span
                        style={{
                          fontSize: "14px",
                          fontWeight: 600,
                          color: theme.success,
                        }}
                      >
                        {nestingResult.totalPieces}
                      </span>
                    </div>
                    {nestingResult.unplacedPieces > 0 && (
                      <div
                        style={{
                          display: "flex",
                          justifyContent: "space-between",
                        }}
                      >
                        <span style={{ fontSize: "13px", color: theme.danger }}>
                          Não couberam:
                        </span>
                        <span
                          style={{
                            fontSize: "14px",
                            fontWeight: 600,
                            color: theme.danger,
                          }}
                        >
                          {nestingResult.unplacedPieces}
                        </span>
                      </div>
                    )}
                  </>
                )}
              </div>

              {/* Seletor de Algoritmo de Nesting */}
              <div
                style={{
                  backgroundColor: theme.inputBackground,
                  borderRadius: "12px",
                  padding: "16px",
                  marginBottom: "16px",
                }}
              >
                <label
                  style={{
                    fontSize: "12px",
                    fontWeight: 600,
                    color: theme.textSecondary,
                    marginBottom: "8px",
                    display: "block",
                  }}
                >
                  🧠 Algoritmo de Otimização
                </label>
                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "1fr 1fr",
                    gap: "8px",
                    marginBottom: "12px",
                  }}
                >
                  {(
                    Object.entries(NESTING_ALGORITHMS) as [
                      typeof nestingAlgorithm,
                      { name: string; description: string; icon: string },
                    ][]
                  ).map(([key, algo]) => (
                    <button
                      key={key}
                      onClick={() => setNestingAlgorithm(key)}
                      style={{
                        padding: "10px 12px",
                        borderRadius: "8px",
                        border:
                          nestingAlgorithm === key
                            ? `2px solid ${theme.warning}`
                            : `1px solid ${theme.border}`,
                        backgroundColor:
                          nestingAlgorithm === key
                            ? `${theme.warning}15`
                            : "transparent",
                        color:
                          nestingAlgorithm === key
                            ? theme.warning
                            : theme.textSecondary,
                        cursor: "pointer",
                        textAlign: "left",
                        transition: "all 0.2s",
                      }}
                    >
                      <div
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: "8px",
                        }}
                      >
                        <span style={{ fontSize: "16px" }}>{algo.icon}</span>
                        <div>
                          <div style={{ fontSize: "12px", fontWeight: 600 }}>
                            {algo.name}
                          </div>
                          <div style={{ fontSize: "10px", opacity: 0.7 }}>
                            {algo.description}
                          </div>
                        </div>
                      </div>
                    </button>
                  ))}
                </div>
                <div style={{ display: "flex", gap: "8px" }}>
                  {(["speed", "balanced", "efficiency"] as const).map(
                    (priority) => (
                      <button
                        key={priority}
                        onClick={() => setNestingPriority(priority)}
                        style={{
                          flex: 1,
                          padding: "8px",
                          borderRadius: "6px",
                          border:
                            nestingPriority === priority
                              ? `2px solid ${theme.accent}`
                              : `1px solid ${theme.border}`,
                          backgroundColor:
                            nestingPriority === priority
                              ? `${theme.accent}15`
                              : "transparent",
                          color:
                            nestingPriority === priority
                              ? theme.accent
                              : theme.textSecondary,
                          cursor: "pointer",
                          fontSize: "11px",
                          fontWeight: 600,
                        }}
                      >
                        {priority === "speed"
                          ? "⚡ Velocidade"
                          : priority === "balanced"
                            ? "⚖️ Equilibrado"
                            : "📊 Eficiência"}
                      </button>
                    ),
                  )}
                </div>
              </div>

              {/* Botão de executar */}
              <button
                onClick={runNesting}
                disabled={pieces.length === 0 || isNesting}
                style={{
                  ...btnPrimary,
                  width: "100%",
                  justifyContent: "center",
                  padding: "14px",
                  backgroundColor:
                    pieces.length === 0 ? theme.textTertiary : theme.warning,
                  opacity: isNesting ? 0.7 : 1,
                }}
              >
                {isNesting ? (
                  <>
                    <motion.div
                      animate={{ rotate: 360 }}
                      transition={{
                        duration: 1,
                        repeat: Infinity,
                        ease: "linear",
                      }}
                    >
                      <RefreshCw size={18} />
                    </motion.div>
                    Otimizando...
                  </>
                ) : (
                  <>
                    <Scissors size={18} /> Executar Nesting
                  </>
                )}
              </button>

              {pieces.length === 0 && (
                <p
                  style={{
                    fontSize: "12px",
                    color: theme.textTertiary,
                    textAlign: "center",
                    marginTop: "12px",
                  }}
                >
                  Crie peças primeiro ou importe um arquivo DXF
                </p>
              )}
            </motion.div>
          )}

          {/* ═══════════════════════════════════════════════════════════════════════════════ */}
          {/* MODO: IMPORTAR (Original) */}
          {/* ═══════════════════════════════════════════════════════════════════════════════ */}

          {/* Upload area */}
          {operationMode === "import" && !geometry && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              style={{
                ...cardStyle,
                border: `2px dashed ${theme.border}`,
                textAlign: "center",
                padding: "60px 40px",
                cursor: "pointer",
              }}
              onClick={() => fileInputRef.current?.click()}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".dxf,.svg"
                onChange={handleFileSelect}
                style={{ display: "none" }}
              />
              <Upload
                size={48}
                color={theme.textTertiary}
                style={{ marginBottom: "16px" }}
              />
              <h3
                style={{
                  fontSize: "18px",
                  fontWeight: 600,
                  marginBottom: "8px",
                  color: theme.textPrimary,
                }}
              >
                Importar Desenho
              </h3>
              <p
                style={{
                  fontSize: "14px",
                  color: theme.textSecondary,
                  marginBottom: "16px",
                }}
              >
                Arraste um arquivo DXF ou SVG, ou clique para selecionar
              </p>
              <div
                style={{
                  display: "flex",
                  gap: "8px",
                  justifyContent: "center",
                  marginBottom: "20px",
                }}
              >
                <span
                  style={{
                    padding: "4px 12px",
                    backgroundColor: theme.inputBackground,
                    borderRadius: "4px",
                    fontSize: "12px",
                    color: theme.textSecondary,
                  }}
                >
                  DXF
                </span>
                <span
                  style={{
                    padding: "4px 12px",
                    backgroundColor: theme.inputBackground,
                    borderRadius: "4px",
                    fontSize: "12px",
                    color: theme.textSecondary,
                  }}
                >
                  SVG
                </span>
              </div>

              {/* Botões de ação rápida */}
              <div
                style={{
                  display: "flex",
                  gap: "12px",
                  justifyContent: "center",
                }}
              >
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setShowTutorial(true);
                  }}
                  style={{
                    ...btnSecondary,
                    fontSize: "12px",
                    padding: "8px 16px",
                  }}
                >
                  <HelpCircle size={14} /> Ver Tutorial
                </button>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    loadDemoGeometry();
                  }}
                  style={{
                    background: `linear-gradient(135deg, ${theme.warning}, ${theme.danger})`,
                    border: "none",
                    borderRadius: "8px",
                    color: "#fff",
                    padding: "8px 16px",
                    fontSize: "12px",
                    fontWeight: 600,
                    cursor: "pointer",
                    display: "flex",
                    alignItems: "center",
                    gap: "6px",
                  }}
                >
                  <Sparkles size={14} /> Testar com Demo
                </button>
              </div>
            </motion.div>
          )}

          {/* Tabs and content */}
          {geometry && (
            <div style={cardStyle}>
              {/* Tabs */}
              <div
                style={{
                  display: "flex",
                  borderBottom: `1px solid ${theme.border}`,
                  marginBottom: "16px",
                  marginTop: "-4px",
                }}
              >
                <button
                  style={tabStyle(activeTab === "config")}
                  onClick={() => setActiveTab("config")}
                >
                  <Settings2 size={16} /> Configuração
                </button>
                <button
                  style={tabStyle(activeTab === "preview")}
                  onClick={() => setActiveTab("preview")}
                >
                  <Eye size={16} /> Preview
                </button>
                <button
                  style={tabStyle(activeTab === "gcode")}
                  onClick={() => setActiveTab("gcode")}
                  disabled={!gcode}
                >
                  <FileCode size={16} /> G-Code
                </button>
              </div>

              {/* Config tab */}
              <AnimatePresence mode="wait">
                {activeTab === "config" && (
                  <motion.div
                    key="config"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                  >
                    {/* Material */}
                    <div style={{ marginBottom: "20px" }}>
                      <label style={labelStyle}>Material</label>
                      <div
                        style={{
                          display: "grid",
                          gridTemplateColumns: "repeat(4, 1fr)",
                          gap: "8px",
                        }}
                      >
                        {Object.entries(MATERIAL_PRESETS).map(
                          ([key, preset]) => (
                            <button
                              key={key}
                              onClick={() =>
                                updateConfig({
                                  material: key as CuttingConfig["material"],
                                })
                              }
                              style={{
                                padding: "12px 8px",
                                backgroundColor:
                                  config.material === key
                                    ? `${theme.accentPrimary}15`
                                    : theme.inputBackground,
                                border: `2px solid ${config.material === key ? theme.accentPrimary : theme.border}`,
                                borderRadius: "8px",
                                cursor: "pointer",
                                textAlign: "center",
                              }}
                            >
                              <div
                                style={{
                                  width: "24px",
                                  height: "24px",
                                  borderRadius: "50%",
                                  backgroundColor: preset.color,
                                  margin: "0 auto 8px",
                                  border: `2px solid ${theme.border}`,
                                }}
                              />
                              <span
                                style={{
                                  fontSize: "12px",
                                  fontWeight: 600,
                                  color:
                                    config.material === key
                                      ? theme.accentPrimary
                                      : theme.textSecondary,
                                }}
                              >
                                {preset.name}
                              </span>
                            </button>
                          ),
                        )}
                      </div>
                    </div>

                    {/* Thickness and basic params */}
                    <div
                      style={{
                        display: "grid",
                        gridTemplateColumns: "repeat(3, 1fr)",
                        gap: "16px",
                        marginBottom: "20px",
                      }}
                    >
                      <div>
                        <label style={labelStyle}>Espessura (mm)</label>
                        <input
                          type="number"
                          value={config.thickness}
                          onChange={(e) =>
                            updateConfig({
                              thickness: parseFloat(e.target.value) || 0,
                            })
                          }
                          min={1}
                          max={50}
                          step={0.5}
                          style={inputStyle}
                        />
                      </div>
                      <div>
                        <label style={labelStyle}>Amperagem (A)</label>
                        <input
                          type="number"
                          value={config.amperage}
                          onChange={(e) =>
                            updateConfig({
                              amperage: parseInt(e.target.value) || 0,
                            })
                          }
                          min={20}
                          max={400}
                          style={inputStyle}
                        />
                      </div>
                      <div>
                        <label style={labelStyle}>Velocidade (mm/min)</label>
                        <input
                          type="number"
                          value={config.cuttingSpeed}
                          onChange={(e) =>
                            updateConfig({
                              cuttingSpeed: parseInt(e.target.value) || 0,
                            })
                          }
                          min={100}
                          max={10000}
                          style={inputStyle}
                        />
                      </div>
                    </div>

                    {/* Advanced toggle */}
                    <button
                      onClick={() => setShowAdvanced(!showAdvanced)}
                      style={{
                        ...btnSecondary,
                        width: "100%",
                        justifyContent: "center",
                        marginBottom: showAdvanced ? "16px" : "0",
                      }}
                    >
                      <Settings2 size={16} />
                      Parâmetros Avançados
                      <ChevronRight
                        size={16}
                        style={{
                          transform: showAdvanced
                            ? "rotate(90deg)"
                            : "rotate(0deg)",
                          transition: "transform 0.2s",
                        }}
                      />
                    </button>

                    {/* Advanced params */}
                    <AnimatePresence>
                      {showAdvanced && (
                        <motion.div
                          initial={{ height: 0, opacity: 0 }}
                          animate={{ height: "auto", opacity: 1 }}
                          exit={{ height: 0, opacity: 0 }}
                          style={{ overflow: "hidden" }}
                        >
                          <div
                            style={{
                              backgroundColor: theme.inputBackground,
                              borderRadius: "8px",
                              padding: "16px",
                              display: "grid",
                              gridTemplateColumns: "repeat(2, 1fr)",
                              gap: "16px",
                            }}
                          >
                            <div>
                              <label style={labelStyle}>
                                Altura de Pierce (mm)
                              </label>
                              <input
                                type="number"
                                value={config.pierceHeight}
                                onChange={(e) =>
                                  updateConfig({
                                    pierceHeight:
                                      parseFloat(e.target.value) || 0,
                                  })
                                }
                                step={0.1}
                                style={inputStyle}
                              />
                            </div>
                            <div>
                              <label style={labelStyle}>
                                Altura de Corte (mm)
                              </label>
                              <input
                                type="number"
                                value={config.cutHeight}
                                onChange={(e) =>
                                  updateConfig({
                                    cutHeight: parseFloat(e.target.value) || 0,
                                  })
                                }
                                step={0.1}
                                style={inputStyle}
                              />
                            </div>
                            <div>
                              <label style={labelStyle}>
                                Delay de Pierce (s)
                              </label>
                              <input
                                type="number"
                                value={config.pierceDelay}
                                onChange={(e) =>
                                  updateConfig({
                                    pierceDelay:
                                      parseFloat(e.target.value) || 0,
                                  })
                                }
                                step={0.1}
                                style={inputStyle}
                              />
                            </div>
                            <div>
                              <label style={labelStyle}>
                                Altura Segura (mm)
                              </label>
                              <input
                                type="number"
                                value={config.safeHeight}
                                onChange={(e) =>
                                  updateConfig({
                                    safeHeight: parseFloat(e.target.value) || 0,
                                  })
                                }
                                step={0.5}
                                style={inputStyle}
                              />
                            </div>
                            <div>
                              <label style={labelStyle}>
                                Kerf / Largura Corte (mm)
                              </label>
                              <input
                                type="number"
                                value={config.kerfWidth}
                                onChange={(e) =>
                                  updateConfig({
                                    kerfWidth: parseFloat(e.target.value) || 0,
                                  })
                                }
                                step={0.1}
                                style={inputStyle}
                              />
                            </div>
                            <div>
                              <label style={labelStyle}>
                                Tensão do Arco (V)
                              </label>
                              <input
                                type="number"
                                value={config.arcVoltage}
                                onChange={(e) =>
                                  updateConfig({
                                    arcVoltage: parseFloat(e.target.value) || 0,
                                  })
                                }
                                style={inputStyle}
                              />
                            </div>
                            <div>
                              <label style={labelStyle}>Lead-In (mm)</label>
                              <input
                                type="number"
                                value={config.leadInLength}
                                onChange={(e) =>
                                  updateConfig({
                                    leadInLength:
                                      parseFloat(e.target.value) || 0,
                                  })
                                }
                                step={0.5}
                                style={inputStyle}
                              />
                            </div>
                            <div>
                              <label style={labelStyle}>Lead-Out (mm)</label>
                              <input
                                type="number"
                                value={config.leadOutLength}
                                onChange={(e) =>
                                  updateConfig({
                                    leadOutLength:
                                      parseFloat(e.target.value) || 0,
                                  })
                                }
                                step={0.5}
                                style={inputStyle}
                              />
                            </div>
                            <div>
                              <label style={labelStyle}>Tipo Lead-In/Out</label>
                              <select
                                value={config.leadType}
                                onChange={(e) =>
                                  updateConfig({
                                    leadType: e.target.value as "arc" | "line",
                                  })
                                }
                                style={inputStyle}
                              >
                                <option value="arc">Arco (Recomendado)</option>
                                <option value="line">Linear</option>
                              </select>
                            </div>
                            <div
                              style={{
                                display: "flex",
                                alignItems: "center",
                                gap: "8px",
                              }}
                            >
                              <input
                                type="checkbox"
                                id="thc"
                                checked={config.thcEnabled}
                                onChange={(e) =>
                                  updateConfig({ thcEnabled: e.target.checked })
                                }
                                style={{ width: "18px", height: "18px" }}
                              />
                              <label
                                htmlFor="thc"
                                style={{ ...labelStyle, marginBottom: 0 }}
                              >
                                THC (Controle de Altura)
                              </label>
                            </div>
                          </div>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </motion.div>
                )}

                {/* Preview tab */}
                {activeTab === "preview" && (
                  <motion.div
                    key="preview"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                  >
                    <CncCanvas
                      geometry={geometry}
                      placements={nestingResult?.placements || []}
                      sheetWidth={sheetConfig.width}
                      sheetHeight={sheetConfig.height}
                      theme={{
                        background: theme.background,
                        grid: theme.border,
                        gridText: theme.textTertiary,
                        sheetFill: `${theme.surface}80`,
                        sheetStroke: theme.accentPrimary,
                        geometryStroke: theme.warning,
                        piercePoint: theme.success,
                        toolpath: theme.danger,
                        selectedStroke: theme.accentPrimary,
                        hoverStroke: theme.success,
                        textPrimary: theme.textPrimary,
                        textSecondary: theme.textSecondary,
                        surface: theme.surface,
                        border: theme.border,
                      }}
                    />
                    <div
                      style={{
                        display: "flex",
                        gap: "16px",
                        marginTop: "12px",
                        justifyContent: "center",
                      }}
                    >
                      <div
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: "6px",
                        }}
                      >
                        <div
                          style={{
                            width: "12px",
                            height: "3px",
                            backgroundColor: theme.warning,
                          }}
                        />
                        <span
                          style={{
                            fontSize: "12px",
                            color: theme.textSecondary,
                          }}
                        >
                          Geometria
                        </span>
                      </div>
                      <div
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: "6px",
                        }}
                      >
                        <div
                          style={{
                            width: "8px",
                            height: "8px",
                            borderRadius: "50%",
                            backgroundColor: theme.success,
                          }}
                        />
                        <span
                          style={{
                            fontSize: "12px",
                            color: theme.textSecondary,
                          }}
                        >
                          Ponto de Pierce
                        </span>
                      </div>
                      {gcode && (
                        <div
                          style={{
                            display: "flex",
                            alignItems: "center",
                            gap: "6px",
                          }}
                        >
                          <div
                            style={{
                              width: "12px",
                              height: "2px",
                              backgroundColor: theme.danger,
                            }}
                          />
                          <span
                            style={{
                              fontSize: "12px",
                              color: theme.textSecondary,
                            }}
                          >
                            Toolpath
                          </span>
                        </div>
                      )}
                    </div>

                    {/* ── Simulação CNC — Timeline interativa ── */}
                    <div
                      style={{
                        marginTop: "18px",
                        padding: "14px 16px",
                        background: `${theme.surface}cc`,
                        border: `1px solid ${theme.border}`,
                        borderRadius: "10px",
                      }}
                    >
                      <div
                        style={{
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "space-between",
                          gap: 12,
                          marginBottom: 12,
                          flexWrap: "wrap",
                        }}
                      >
                        <div>
                          <div
                            style={{
                              fontSize: "11px",
                              color: theme.textTertiary,
                              textTransform: "uppercase",
                              letterSpacing: "0.08em",
                            }}
                          >
                            Timeline interativa
                          </div>
                          <div
                            style={{
                              fontSize: "14px",
                              color: theme.textPrimary,
                              fontWeight: 700,
                            }}
                          >
                            Etapa atual: {currentSimulationStage}
                          </div>
                        </div>
                        <div
                          style={{
                            fontSize: "12px",
                            color: theme.textSecondary,
                          }}
                        >
                          {simPlaying
                            ? "Simulação em andamento"
                            : "Simulação pronta para inspeção"}
                        </div>
                      </div>

                      {/* Barra de progresso */}
                      <div
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: "10px",
                          marginBottom: "10px",
                        }}
                      >
                        <span
                          style={{
                            fontSize: "11px",
                            color: theme.textTertiary,
                            minWidth: "28px",
                          }}
                        >
                          {Math.round(simProgress)}%
                        </span>
                        <div
                          style={{
                            flex: 1,
                            height: "6px",
                            background: theme.border,
                            borderRadius: "3px",
                            cursor: "pointer",
                            position: "relative",
                          }}
                          onClick={(e) => {
                            const rect = (
                              e.currentTarget as HTMLElement
                            ).getBoundingClientRect();
                            const pct = Math.max(
                              0,
                              Math.min(
                                100,
                                ((e.clientX - rect.left) / rect.width) * 100,
                              ),
                            );
                            setSimProgress(pct);
                          }}
                        >
                          <div
                            style={{
                              width: `${simProgress}%`,
                              height: "100%",
                              background: `linear-gradient(90deg, ${theme.accentPrimary}, ${theme.success})`,
                              borderRadius: "3px",
                              transition: "width 0.05s linear",
                            }}
                          />
                        </div>
                        {gcode && (
                          <span
                            style={{
                              fontSize: "11px",
                              color: theme.textTertiary,
                              minWidth: "36px",
                              textAlign: "right",
                            }}
                          >
                            {(
                              (simProgress / 100) *
                              (gcode.estimatedTime || 2.5)
                            ).toFixed(1)}
                            min
                          </span>
                        )}
                      </div>

                      <div
                        style={{
                          display: "grid",
                          gridTemplateColumns: "repeat(4, minmax(0, 1fr))",
                          gap: 8,
                          marginBottom: 12,
                        }}
                      >
                        {simulationMilestones.map((milestone) => {
                          const active = simProgress >= milestone.threshold;
                          return (
                            <div
                              key={milestone.id}
                              style={{
                                padding: "8px 10px",
                                borderRadius: 8,
                                border: `1px solid ${active ? `${theme.accentPrimary}55` : theme.border}`,
                                background: active
                                  ? `${theme.accentPrimary}12`
                                  : "transparent",
                              }}
                            >
                              <div
                                style={{
                                  fontSize: "11px",
                                  color: active
                                    ? theme.accentPrimary
                                    : theme.textTertiary,
                                  fontWeight: 700,
                                }}
                              >
                                {milestone.label}
                              </div>
                              <div
                                style={{
                                  fontSize: "10px",
                                  color: theme.textSecondary,
                                  marginTop: 4,
                                }}
                              >
                                {milestone.threshold}%
                              </div>
                            </div>
                          );
                        })}
                      </div>

                      {/* Controles */}
                      <div
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: "10px",
                        }}
                      >
                        {/* Retroceder */}
                        <button
                          onClick={() => setSimProgress(0)}
                          title="Reiniciar"
                          style={{
                            background: "transparent",
                            border: `1px solid ${theme.border}`,
                            borderRadius: "6px",
                            color: theme.textSecondary,
                            padding: "5px 8px",
                            cursor: "pointer",
                            fontSize: "13px",
                          }}
                        >
                          ⏮
                        </button>

                        {/* Play / Pause */}
                        <button
                          onClick={() => {
                            if (simProgress >= 100) setSimProgress(0);
                            setSimPlaying((v) => !v);
                          }}
                          style={{
                            background: simPlaying
                              ? `linear-gradient(135deg, ${theme.warning}, #d97706)`
                              : `linear-gradient(135deg, ${theme.accentPrimary}, ${theme.success})`,
                            border: "none",
                            borderRadius: "8px",
                            color: "#fff",
                            padding: "7px 16px",
                            cursor: "pointer",
                            fontWeight: 700,
                            fontSize: "13px",
                            display: "flex",
                            alignItems: "center",
                            gap: "6px",
                          }}
                        >
                          {simPlaying ? "⏸ Pausar" : "▶ Simular"}
                        </button>

                        {/* Velocidade */}
                        <span
                          style={{
                            fontSize: "11px",
                            color: theme.textSecondary,
                            marginLeft: "auto",
                          }}
                        >
                          Velocidade:
                        </span>
                        {[0.5, 1, 2, 4].map((s) => (
                          <button
                            key={s}
                            onClick={() => setSimSpeed(s)}
                            style={{
                              padding: "4px 8px",
                              borderRadius: "5px",
                              border: `1px solid ${simSpeed === s ? theme.accentPrimary : theme.border}`,
                              background:
                                simSpeed === s
                                  ? `${theme.accentPrimary}22`
                                  : "transparent",
                              color:
                                simSpeed === s
                                  ? theme.accentPrimary
                                  : theme.textSecondary,
                              cursor: "pointer",
                              fontSize: "11px",
                              fontWeight: simSpeed === s ? 700 : 400,
                            }}
                          >
                            {s}x
                          </button>
                        ))}
                      </div>
                    </div>
                  </motion.div>
                )}

                {/* G-code tab */}
                {activeTab === "gcode" && gcode && (
                  <motion.div
                    key="gcode"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                  >
                    <pre
                      style={{
                        backgroundColor: theme.background,
                        border: `1px solid ${theme.border}`,
                        borderRadius: "8px",
                        padding: "16px",
                        maxHeight: "400px",
                        overflow: "auto",
                        fontSize: "12px",
                        fontFamily: "'Fira Code', 'Consolas', monospace",
                        color: theme.textSecondary,
                        margin: 0,
                        whiteSpace: "pre-wrap",
                      }}
                    >
                      {gcode.code}
                    </pre>

                    {/* Download buttons */}
                    <div
                      style={{ display: "flex", gap: "8px", marginTop: "16px" }}
                    >
                      <button
                        onClick={() => handleDownload("nc")}
                        style={{
                          ...btnSecondary,
                          flex: 1,
                          justifyContent: "center",
                        }}
                      >
                        <Download size={16} /> .NC
                      </button>
                      <button
                        onClick={() => handleDownload("tap")}
                        style={{
                          ...btnSecondary,
                          flex: 1,
                          justifyContent: "center",
                        }}
                      >
                        <Download size={16} /> .TAP
                      </button>
                      <button
                        onClick={() => handleDownload("gcode")}
                        style={{
                          ...btnSecondary,
                          flex: 1,
                          justifyContent: "center",
                        }}
                      >
                        <Download size={16} /> .GCODE
                      </button>
                    </div>

                    {/* Copy button */}
                    <button
                      onClick={handleCopy}
                      style={{
                        ...btnSecondary,
                        width: "100%",
                        marginTop: "8px",
                        justifyContent: "center",
                        backgroundColor: copied
                          ? "#22c55e"
                          : btnSecondary.backgroundColor,
                        color: copied ? "#fff" : btnSecondary.color,
                      }}
                    >
                      <Copy size={16} />{" "}
                      {copied
                        ? "Copiado!"
                        : "Copiar para Área de Transferência"}
                    </button>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          )}
        </div>

        {/* Right panel - Stats and actions */}
        <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          {/* File info */}
          {geometry && (
            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              style={cardStyle}
            >
              <h3
                style={{
                  fontSize: "14px",
                  fontWeight: 600,
                  marginBottom: "16px",
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                  color: theme.textPrimary,
                }}
              >
                <FileText size={18} /> Arquivo Importado
              </h3>

              <div
                style={{
                  padding: "12px",
                  backgroundColor: theme.inputBackground,
                  borderRadius: "8px",
                  marginBottom: "16px",
                }}
              >
                <div
                  style={{
                    fontSize: "14px",
                    fontWeight: 600,
                    color: theme.textPrimary,
                    marginBottom: "4px",
                  }}
                >
                  {fileName || "demo_geometria.dxf"}
                </div>
                <div style={{ fontSize: "12px", color: theme.textSecondary }}>
                  {geometry.stats.totalLength.toFixed(1)} mm de perímetro total
                </div>
              </div>

              {/* Geometry stats */}
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(2, 1fr)",
                  gap: "8px",
                }}
              >
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "8px",
                    padding: "8px",
                    backgroundColor: theme.inputBackground,
                    borderRadius: "6px",
                  }}
                >
                  <Minus size={16} color={theme.textTertiary} />
                  <div>
                    <div
                      style={{
                        fontSize: "16px",
                        fontWeight: 700,
                        color: theme.textPrimary,
                      }}
                    >
                      {geometry.stats.lines}
                    </div>
                    <div
                      style={{ fontSize: "11px", color: theme.textSecondary }}
                    >
                      Linhas
                    </div>
                  </div>
                </div>
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "8px",
                    padding: "8px",
                    backgroundColor: theme.inputBackground,
                    borderRadius: "6px",
                  }}
                >
                  <Circle size={16} color={theme.textTertiary} />
                  <div>
                    <div
                      style={{
                        fontSize: "16px",
                        fontWeight: 700,
                        color: theme.textPrimary,
                      }}
                    >
                      {geometry.stats.circles}
                    </div>
                    <div
                      style={{ fontSize: "11px", color: theme.textSecondary }}
                    >
                      Círculos
                    </div>
                  </div>
                </div>
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "8px",
                    padding: "8px",
                    backgroundColor: theme.inputBackground,
                    borderRadius: "6px",
                  }}
                >
                  <Square size={16} color={theme.textTertiary} />
                  <div>
                    <div
                      style={{
                        fontSize: "16px",
                        fontWeight: 700,
                        color: theme.textPrimary,
                      }}
                    >
                      {geometry.stats.polylines}
                    </div>
                    <div
                      style={{ fontSize: "11px", color: theme.textSecondary }}
                    >
                      Polilinhas
                    </div>
                  </div>
                </div>
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "8px",
                    padding: "8px",
                    backgroundColor: theme.inputBackground,
                    borderRadius: "6px",
                  }}
                >
                  <RotateCcw size={16} color={theme.textTertiary} />
                  <div>
                    <div
                      style={{
                        fontSize: "16px",
                        fontWeight: 700,
                        color: theme.textPrimary,
                      }}
                    >
                      {geometry.stats.arcs}
                    </div>
                    <div
                      style={{ fontSize: "11px", color: theme.textSecondary }}
                    >
                      Arcos
                    </div>
                  </div>
                </div>
              </div>

              {/* New file button */}
              <button
                onClick={() => {
                  setGeometry(null);
                  setGcode(null);
                  setFileName("");
                  setStep("idle");
                }}
                style={{
                  ...btnSecondary,
                  width: "100%",
                  justifyContent: "center",
                  marginTop: "16px",
                }}
              >
                <Upload size={16} /> Importar Outro Arquivo
              </button>
            </motion.div>
          )}

          {/* Cutting summary */}
          {gcode && (
            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.1 }}
              style={cardStyle}
            >
              <h3
                style={{
                  fontSize: "14px",
                  fontWeight: 600,
                  marginBottom: "16px",
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                  color: theme.textPrimary,
                }}
              >
                <Target size={18} /> Resumo do Corte
              </h3>

              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  gap: "12px",
                }}
              >
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                  }}
                >
                  <span
                    style={{ fontSize: "13px", color: theme.textSecondary }}
                  >
                    Total de Cortes
                  </span>
                  <span
                    style={{
                      fontSize: "14px",
                      fontWeight: 600,
                      color: theme.textPrimary,
                    }}
                  >
                    {gcode.stats.totalCuts}
                  </span>
                </div>
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                  }}
                >
                  <span
                    style={{ fontSize: "13px", color: theme.textSecondary }}
                  >
                    Contornos Internos
                  </span>
                  <span
                    style={{
                      fontSize: "14px",
                      fontWeight: 600,
                      color: theme.warning,
                    }}
                  >
                    {gcode.stats.internalContours}
                  </span>
                </div>
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                  }}
                >
                  <span
                    style={{ fontSize: "13px", color: theme.textSecondary }}
                  >
                    Contornos Externos
                  </span>
                  <span
                    style={{
                      fontSize: "14px",
                      fontWeight: 600,
                      color: theme.accentPrimary,
                    }}
                  >
                    {gcode.stats.externalContours}
                  </span>
                </div>
                <div style={{ height: "1px", backgroundColor: theme.border }} />
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                  }}
                >
                  <span
                    style={{ fontSize: "13px", color: theme.textSecondary }}
                  >
                    Comprimento de Corte
                  </span>
                  <span
                    style={{
                      fontSize: "14px",
                      fontWeight: 600,
                      color: theme.textPrimary,
                    }}
                  >
                    {gcode.stats.cuttingLength.toFixed(1)} mm
                  </span>
                </div>
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                  }}
                >
                  <span
                    style={{ fontSize: "13px", color: theme.textSecondary }}
                  >
                    Deslocamento Rápido
                  </span>
                  <span
                    style={{
                      fontSize: "14px",
                      fontWeight: 600,
                      color: theme.textPrimary,
                    }}
                  >
                    {gcode.stats.rapidLength.toFixed(1)} mm
                  </span>
                </div>
                <div style={{ height: "1px", backgroundColor: theme.border }} />
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    padding: "12px",
                    backgroundColor: `${theme.success}15`,
                    borderRadius: "8px",
                  }}
                >
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "8px",
                    }}
                  >
                    <Clock size={18} color={theme.success} />
                    <span
                      style={{ fontSize: "13px", color: theme.textSecondary }}
                    >
                      Tempo Estimado
                    </span>
                  </div>
                  <span
                    style={{
                      fontSize: "16px",
                      fontWeight: 700,
                      color: theme.success,
                    }}
                  >
                    {Math.floor(gcode.stats.estimatedTime / 60)}:
                    {String(gcode.stats.estimatedTime % 60).padStart(2, "0")}{" "}
                    min
                  </span>
                </div>
              </div>
            </motion.div>
          )}

          {/* Cost Estimate */}
          {gcode && gcode.costEstimate && (
            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.15 }}
              style={cardStyle}
            >
              <h3
                style={{
                  fontSize: "14px",
                  fontWeight: 600,
                  marginBottom: "16px",
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                  color: theme.textPrimary,
                }}
              >
                <DollarSign size={18} /> Estimativa de Custo
              </h3>

              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  gap: "12px",
                }}
              >
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                  }}
                >
                  <span
                    style={{ fontSize: "13px", color: theme.textSecondary }}
                  >
                    Custo do Material
                  </span>
                  <span
                    style={{
                      fontSize: "14px",
                      fontWeight: 600,
                      color: theme.textPrimary,
                    }}
                  >
                    R$ {gcode.costEstimate.materialCost.toFixed(2)}
                  </span>
                </div>
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                  }}
                >
                  <span
                    style={{ fontSize: "13px", color: theme.textSecondary }}
                  >
                    Custo de Corte (Tempo)
                  </span>
                  <span
                    style={{
                      fontSize: "14px",
                      fontWeight: 600,
                      color: theme.textPrimary,
                    }}
                  >
                    R$ {gcode.costEstimate.cuttingTimeCost.toFixed(2)}
                  </span>
                </div>
                <div style={{ height: "1px", backgroundColor: theme.border }} />
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    padding: "12px",
                    backgroundColor: `${theme.accentPrimary}15`,
                    borderRadius: "8px",
                  }}
                >
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "8px",
                    }}
                  >
                    <DollarSign size={18} color={theme.accentPrimary} />
                    <span
                      style={{ fontSize: "13px", color: theme.textSecondary }}
                    >
                      Custo Total
                    </span>
                  </div>
                  <span
                    style={{
                      fontSize: "18px",
                      fontWeight: 700,
                      color: theme.accentPrimary,
                    }}
                  >
                    R$ {gcode.costEstimate.totalCost.toFixed(2)}
                  </span>
                </div>
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    padding: "8px",
                    backgroundColor: `${theme.warning}10`,
                    borderRadius: "6px",
                  }}
                >
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "8px",
                    }}
                  >
                    <Percent size={14} color={theme.warning} />
                    <span
                      style={{ fontSize: "12px", color: theme.textSecondary }}
                    >
                      Perda Estimada
                    </span>
                  </div>
                  <span
                    style={{
                      fontSize: "14px",
                      fontWeight: 600,
                      color: theme.warning,
                    }}
                  >
                    {gcode.costEstimate.scrapPercentage.toFixed(1)}%
                  </span>
                </div>
              </div>
            </motion.div>
          )}

          {/* Warnings */}
          {gcode && gcode.warnings.length > 0 && (
            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.2 }}
              style={cardStyle}
            >
              <h3
                style={{
                  fontSize: "14px",
                  fontWeight: 600,
                  marginBottom: "12px",
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                  color: theme.textPrimary,
                }}
              >
                <Info size={18} /> Informações
              </h3>

              {gcode.warnings.map((warning, idx) => (
                <div
                  key={idx}
                  style={{
                    display: "flex",
                    alignItems: "flex-start",
                    gap: "8px",
                    padding: "10px",
                    backgroundColor:
                      warning.level === "error"
                        ? `${theme.danger}15`
                        : warning.level === "warning"
                          ? `${theme.warning}15`
                          : `${theme.accentPrimary}15`,
                    borderRadius: "6px",
                    marginBottom: idx < gcode.warnings.length - 1 ? "8px" : 0,
                  }}
                >
                  {warning.level === "error" ? (
                    <AlertTriangle
                      size={16}
                      color={theme.danger}
                      style={{ flexShrink: 0, marginTop: "2px" }}
                    />
                  ) : warning.level === "warning" ? (
                    <AlertTriangle
                      size={16}
                      color={theme.warning}
                      style={{ flexShrink: 0, marginTop: "2px" }}
                    />
                  ) : (
                    <CheckCircle2
                      size={16}
                      color={theme.accentPrimary}
                      style={{ flexShrink: 0, marginTop: "2px" }}
                    />
                  )}
                  <div>
                    <div style={{ fontSize: "13px", color: theme.textPrimary }}>
                      {warning.message}
                    </div>
                    {warning.suggestion && (
                      <div
                        style={{
                          fontSize: "12px",
                          color: theme.textSecondary,
                          marginTop: "4px",
                        }}
                      >
                        {warning.suggestion}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </motion.div>
          )}

          {/* Generate button */}
          {geometry && (
            <motion.button
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={handleGenerate}
              disabled={step === "generating"}
              style={{
                ...btnPrimary,
                width: "100%",
                justifyContent: "center",
                padding: "16px",
                fontSize: "16px",
                backgroundColor:
                  step === "generating" ? theme.textTertiary : theme.success,
              }}
            >
              {step === "generating" ? (
                <>
                  <motion.div
                    animate={{ rotate: 360 }}
                    transition={{
                      duration: 1,
                      repeat: Infinity,
                      ease: "linear",
                    }}
                  >
                    <RotateCcw size={20} />
                  </motion.div>
                  Gerando G-Code...
                </>
              ) : gcode ? (
                <>
                  <RotateCcw size={20} />
                  Regenerar G-Code
                </>
              ) : (
                <>
                  <Play size={20} />
                  Gerar G-Code
                </>
              )}
            </motion.button>
          )}

          {/* Info card */}
          <div
            style={{
              ...cardStyle,
              backgroundColor: `${theme.accentPrimary}08`,
              border: `1px solid ${theme.accentPrimary}30`,
            }}
          >
            <h4
              style={{
                fontSize: "13px",
                fontWeight: 600,
                marginBottom: "12px",
                color: theme.accentPrimary,
                display: "flex",
                alignItems: "center",
                gap: "8px",
              }}
            >
              <Zap size={16} /> Otimizações Aplicadas
            </h4>
            <ul
              style={{
                fontSize: "12px",
                color: theme.textSecondary,
                margin: 0,
                paddingLeft: "20px",
                lineHeight: "1.8",
              }}
            >
              <li>Compensação de kerf automática</li>
              <li>Lead-in/out para entrada suave</li>
              <li>Cortes internos primeiro</li>
              <li>Sequência otimizada (menos deslocamento)</li>
              <li>Compatível com Plasma Edge</li>
            </ul>
          </div>

          {/* ═══════════════════════════════════════════════════════════════════════════════ */}
          {/* PAINEL DE ESTATÍSTICAS E VALIDAÇÕES */}
          {/* ═══════════════════════════════════════════════════════════════════════════════ */}
          {geometry && showStatisticsPanel && (
            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.1 }}
            >
              <CncStatisticsPanel
                config={{
                  material: config.material,
                  thickness: config.thickness,
                  amperage: config.amperage,
                  cuttingSpeed: config.cuttingSpeed,
                }}
                stats={gcode?.stats}
                costEstimate={gcode?.costEstimate}
                nestingResult={
                  nestingResult
                    ? {
                        efficiency: nestingResult.efficiency,
                        totalPieces: nestingResult.totalPieces,
                        unplacedPieces: nestingResult.unplacedPieces,
                        usedArea: nestingResult.usedArea,
                        wasteArea: nestingResult.wasteArea,
                      }
                    : undefined
                }
                sheetWidth={sheetConfig.width}
                sheetHeight={sheetConfig.height}
                theme={panelTheme}
              />
            </motion.div>
          )}

          {/* Painel de Validações */}
          {geometry && validationIssues.length > 0 && (
            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.15 }}
            >
              <CncValidationPanel
                issues={validationIssues}
                isValidating={isValidating}
                onRefresh={runValidation}
                onAutoFix={(issueId) => {
                  // Auto-fix logic based on issue
                  const issue = validationIssues.find((i) => i.id === issueId);
                  if (issue?.code === "MAT-001") {
                    updateConfig({ amperage: 100 });
                  } else if (issue?.code === "MAC-001") {
                    updateConfig({ cuttingSpeed: 4000 });
                  }
                  runValidation();
                }}
                onHighlightIssue={(issue) => {
                  console.log("Highlight issue:", issue);
                  // Could highlight on canvas
                }}
                theme={panelTheme}
              />
            </motion.div>
          )}
        </div>

        {/* ═══════════════════════════════════════════════════════════════════════════════ */}
        {/* PAINEL IA ASSISTENTE */}
        {/* ═══════════════════════════════════════════════════════════════════════════════ */}
        {showAIAssistant && (
          <div
            style={{ display: "flex", flexDirection: "column", gap: "16px" }}
          >
            {/* Header */}
            <div
              style={{
                ...cardStyle,
                background: `linear-gradient(135deg, ${theme.accentPrimary}15, ${theme.panel})`,
                border: `1px solid ${theme.accentPrimary}30`,
              }}
            >
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  marginBottom: "16px",
                }}
              >
                <h3
                  style={{
                    fontSize: "14px",
                    fontWeight: 600,
                    color: theme.textPrimary,
                    display: "flex",
                    alignItems: "center",
                    gap: "8px",
                  }}
                >
                  <Brain size={18} color={theme.accentPrimary} /> IA Assistente
                </h3>
                <button
                  onClick={() => setShowAIAssistant(false)}
                  style={{
                    background: "none",
                    border: "none",
                    cursor: "pointer",
                    padding: "4px",
                  }}
                >
                  <X size={16} color={theme.textSecondary} />
                </button>
              </div>

              {/* Sugestões da IA */}
              {aiSuggestions.length > 0 && (
                <div style={{ marginBottom: "16px" }}>
                  <h4
                    style={{
                      fontSize: "12px",
                      fontWeight: 600,
                      color: theme.textSecondary,
                      marginBottom: "8px",
                    }}
                  >
                    <Lightbulb
                      size={14}
                      style={{ marginRight: "4px", verticalAlign: "middle" }}
                    />
                    Sugestões
                  </h4>
                  <div
                    style={{
                      display: "flex",
                      flexDirection: "column",
                      gap: "8px",
                    }}
                  >
                    {aiSuggestions.slice(0, 3).map((suggestion) => (
                      <div
                        key={suggestion.id}
                        style={{
                          padding: "10px 12px",
                          borderRadius: "8px",
                          backgroundColor:
                            suggestion.type === "error"
                              ? `${theme.danger}15`
                              : suggestion.type === "warning"
                                ? `${theme.warning}15`
                                : suggestion.type === "optimization"
                                  ? `${theme.success}15`
                                  : `${theme.accentPrimary}10`,
                          border: `1px solid ${
                            suggestion.type === "error"
                              ? theme.danger
                              : suggestion.type === "warning"
                                ? theme.warning
                                : suggestion.type === "optimization"
                                  ? theme.success
                                  : theme.accentPrimary
                          }30`,
                        }}
                      >
                        <div
                          style={{
                            fontSize: "12px",
                            fontWeight: 600,
                            color: theme.textPrimary,
                            marginBottom: "4px",
                          }}
                        >
                          {suggestion.type === "error" && (
                            <AlertTriangle
                              size={12}
                              style={{
                                marginRight: "4px",
                                color: theme.danger,
                              }}
                            />
                          )}
                          {suggestion.type === "warning" && (
                            <AlertTriangle
                              size={12}
                              style={{
                                marginRight: "4px",
                                color: theme.warning,
                              }}
                            />
                          )}
                          {suggestion.type === "optimization" && (
                            <TrendingUp
                              size={12}
                              style={{
                                marginRight: "4px",
                                color: theme.success,
                              }}
                            />
                          )}
                          {suggestion.type === "info" && (
                            <Info
                              size={12}
                              style={{
                                marginRight: "4px",
                                color: theme.accentPrimary,
                              }}
                            />
                          )}
                          {suggestion.title}
                        </div>
                        <div
                          style={{
                            fontSize: "11px",
                            color: theme.textSecondary,
                            marginBottom: suggestion.action ? "8px" : 0,
                          }}
                        >
                          {suggestion.message}
                        </div>
                        {suggestion.action && (
                          <button
                            onClick={() => applyAISuggestion(suggestion)}
                            style={{
                              padding: "4px 10px",
                              borderRadius: "4px",
                              border: "none",
                              backgroundColor: theme.accentPrimary,
                              color: "#fff",
                              fontSize: "11px",
                              fontWeight: 600,
                              cursor: "pointer",
                            }}
                          >
                            {suggestion.action}
                          </button>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Chat */}
              <div
                style={{
                  height: "280px",
                  overflowY: "auto",
                  marginBottom: "12px",
                  padding: "12px",
                  backgroundColor: theme.inputBackground,
                  borderRadius: "8px",
                }}
              >
                {aiChatMessages.map((msg, idx) => (
                  <div
                    key={idx}
                    style={{
                      marginBottom: "12px",
                      display: "flex",
                      flexDirection: "column",
                      alignItems:
                        msg.role === "user" ? "flex-end" : "flex-start",
                    }}
                  >
                    <div
                      style={{
                        padding: "10px 14px",
                        borderRadius:
                          msg.role === "user"
                            ? "12px 12px 4px 12px"
                            : "12px 12px 12px 4px",
                        backgroundColor:
                          msg.role === "user"
                            ? theme.accentPrimary
                            : theme.panel,
                        color: msg.role === "user" ? "#fff" : theme.textPrimary,
                        maxWidth: "90%",
                        fontSize: "12px",
                        lineHeight: "1.5",
                        whiteSpace: "pre-wrap",
                      }}
                    >
                      {msg.content}
                    </div>
                  </div>
                ))}
                {isAiThinking && (
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "8px",
                    }}
                  >
                    <motion.div
                      animate={{ opacity: [0.5, 1, 0.5] }}
                      transition={{ duration: 1.5, repeat: Infinity }}
                      style={{ fontSize: "12px", color: theme.textSecondary }}
                    >
                      IA pensando...
                    </motion.div>
                  </div>
                )}
              </div>

              {/* Input */}
              <div style={{ display: "flex", gap: "8px" }}>
                <input
                  type="text"
                  value={aiInput}
                  onChange={(e) => setAiInput(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && sendAIMessage()}
                  placeholder="Pergunte algo..."
                  style={{
                    flex: 1,
                    padding: "10px 14px",
                    borderRadius: "8px",
                    border: `1px solid ${theme.border}`,
                    backgroundColor: theme.panel,
                    color: theme.textPrimary,
                    fontSize: "13px",
                  }}
                />
                <button
                  onClick={sendAIMessage}
                  style={{
                    padding: "10px 14px",
                    borderRadius: "8px",
                    border: "none",
                    backgroundColor: theme.accentPrimary,
                    color: "#fff",
                    cursor: "pointer",
                  }}
                >
                  <Send size={16} />
                </button>
              </div>
            </div>

            {/* Atalhos rápidos */}
            <div style={cardStyle}>
              <h4
                style={{
                  fontSize: "12px",
                  fontWeight: 600,
                  color: theme.textSecondary,
                  marginBottom: "12px",
                }}
              >
                Perguntas Rápidas
              </h4>
              <div
                style={{ display: "flex", flexDirection: "column", gap: "6px" }}
              >
                {[
                  "Como adicionar furos?",
                  "Qual velocidade usar?",
                  "Como otimizar o nesting?",
                  "Dicas de qualidade",
                ].map((q, idx) => (
                  <button
                    key={idx}
                    onClick={() => {
                      setAiInput(q);
                      sendAIMessage();
                    }}
                    style={{
                      padding: "8px 12px",
                      borderRadius: "6px",
                      border: `1px solid ${theme.border}`,
                      backgroundColor: "transparent",
                      color: theme.textSecondary,
                      fontSize: "11px",
                      cursor: "pointer",
                      textAlign: "left",
                      transition: "all 0.2s",
                    }}
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Botão para reabrir IA se fechada */}
      {!showAIAssistant && (
        <button
          onClick={() => setShowAIAssistant(true)}
          style={{
            position: "fixed",
            bottom: "24px",
            right: "24px",
            width: "56px",
            height: "56px",
            borderRadius: "50%",
            border: "none",
            backgroundColor: theme.accentPrimary,
            color: "#fff",
            boxShadow: theme.shadowMedium,
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 100,
          }}
        >
          <Bot size={24} />
        </button>
      )}

      {/* ═══════════════════════════════════════════════════════════════════════════════ */}
      {/* MODAL: Editor de Peças */}
      {/* ═══════════════════════════════════════════════════════════════════════════════ */}
      <AnimatePresence>
        {showPieceEditor && editingPiece && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            style={{
              position: "fixed",
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              backgroundColor: "rgba(0,0,0,0.6)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              zIndex: 1000,
            }}
            onClick={() => setShowPieceEditor(false)}
          >
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              style={{
                backgroundColor: theme.panel,
                borderRadius: "16px",
                padding: "24px",
                width: "600px",
                maxHeight: "80vh",
                overflowY: "auto",
                boxShadow: theme.shadowMedium,
              }}
              onClick={(e) => e.stopPropagation()}
            >
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  marginBottom: "24px",
                }}
              >
                <h2
                  style={{
                    fontSize: "18px",
                    fontWeight: 700,
                    color: theme.textPrimary,
                  }}
                >
                  {editingPiece.type === "rectangle" && (
                    <RectangleHorizontal
                      size={24}
                      style={{ marginRight: "8px", verticalAlign: "middle" }}
                    />
                  )}
                  {editingPiece.type === "circle" && (
                    <Circle
                      size={24}
                      style={{ marginRight: "8px", verticalAlign: "middle" }}
                    />
                  )}
                  Editar Peça: {editingPiece.name}
                </h2>
                <button
                  onClick={() => setShowPieceEditor(false)}
                  style={{
                    background: "none",
                    border: "none",
                    cursor: "pointer",
                  }}
                >
                  <X size={24} color={theme.textSecondary} />
                </button>
              </div>

              {/* Nome da peça */}
              <div style={{ marginBottom: "20px" }}>
                <label
                  style={{
                    fontSize: "13px",
                    fontWeight: 600,
                    color: theme.textSecondary,
                    marginBottom: "6px",
                    display: "block",
                  }}
                >
                  Nome da Peça
                </label>
                <input
                  type="text"
                  value={editingPiece.name}
                  onChange={(e) =>
                    setEditingPiece((prev) =>
                      prev ? { ...prev, name: e.target.value } : null,
                    )
                  }
                  style={{
                    width: "100%",
                    padding: "12px 14px",
                    borderRadius: "8px",
                    border: `1px solid ${theme.border}`,
                    backgroundColor: theme.inputBackground,
                    color: theme.textPrimary,
                    fontSize: "14px",
                  }}
                />
              </div>

              {/* Dimensões */}
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "1fr 1fr 1fr",
                  gap: "16px",
                  marginBottom: "20px",
                }}
              >
                <div>
                  <label
                    style={{
                      fontSize: "13px",
                      fontWeight: 600,
                      color: theme.textSecondary,
                      marginBottom: "6px",
                      display: "block",
                    }}
                  >
                    {editingPiece.type === "circle"
                      ? "Diâmetro (mm)"
                      : "Largura (mm)"}
                  </label>
                  <input
                    type="number"
                    value={editingPiece.width}
                    onChange={(e) =>
                      setEditingPiece((prev) =>
                        prev
                          ? {
                              ...prev,
                              width: Number(e.target.value),
                              radius:
                                prev.type === "circle"
                                  ? Number(e.target.value) / 2
                                  : prev.radius,
                            }
                          : null,
                      )
                    }
                    style={{
                      width: "100%",
                      padding: "12px 14px",
                      borderRadius: "8px",
                      border: `1px solid ${theme.border}`,
                      backgroundColor: theme.inputBackground,
                      color: theme.textPrimary,
                      fontSize: "14px",
                    }}
                  />
                </div>
                {editingPiece.type !== "circle" && (
                  <div>
                    <label
                      style={{
                        fontSize: "13px",
                        fontWeight: 600,
                        color: theme.textSecondary,
                        marginBottom: "6px",
                        display: "block",
                      }}
                    >
                      Altura (mm)
                    </label>
                    <input
                      type="number"
                      value={editingPiece.height}
                      onChange={(e) =>
                        setEditingPiece((prev) =>
                          prev
                            ? { ...prev, height: Number(e.target.value) }
                            : null,
                        )
                      }
                      style={{
                        width: "100%",
                        padding: "12px 14px",
                        borderRadius: "8px",
                        border: `1px solid ${theme.border}`,
                        backgroundColor: theme.inputBackground,
                        color: theme.textPrimary,
                        fontSize: "14px",
                      }}
                    />
                  </div>
                )}
                <div>
                  <label
                    style={{
                      fontSize: "13px",
                      fontWeight: 600,
                      color: theme.textSecondary,
                      marginBottom: "6px",
                      display: "block",
                    }}
                  >
                    Quantidade
                  </label>
                  <input
                    type="number"
                    min={1}
                    value={editingPiece.quantity}
                    onChange={(e) =>
                      setEditingPiece((prev) =>
                        prev
                          ? {
                              ...prev,
                              quantity: Math.max(1, Number(e.target.value)),
                            }
                          : null,
                      )
                    }
                    style={{
                      width: "100%",
                      padding: "12px 14px",
                      borderRadius: "8px",
                      border: `1px solid ${theme.border}`,
                      backgroundColor: theme.inputBackground,
                      color: theme.textPrimary,
                      fontSize: "14px",
                    }}
                  />
                </div>
              </div>

              {/* Furos */}
              <div style={{ marginBottom: "20px" }}>
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    marginBottom: "12px",
                  }}
                >
                  <h4
                    style={{
                      fontSize: "14px",
                      fontWeight: 600,
                      color: theme.textPrimary,
                    }}
                  >
                    <CircleDot
                      size={16}
                      style={{ marginRight: "8px", verticalAlign: "middle" }}
                    />
                    Furos ({editingPiece.holes.length})
                  </h4>
                  <button
                    onClick={() => addHoleToPiece(10)}
                    style={{
                      ...btnSecondary,
                      padding: "6px 12px",
                      fontSize: "12px",
                    }}
                  >
                    <Plus size={14} /> Adicionar Furo
                  </button>
                </div>

                {editingPiece.holes.length > 0 && (
                  <div
                    style={{
                      display: "flex",
                      flexDirection: "column",
                      gap: "8px",
                    }}
                  >
                    {editingPiece.holes.map((hole, idx) => (
                      <div
                        key={hole.id}
                        style={{
                          display: "grid",
                          gridTemplateColumns: "1fr 1fr 1fr auto",
                          gap: "12px",
                          padding: "12px",
                          backgroundColor: theme.inputBackground,
                          borderRadius: "8px",
                          alignItems: "end",
                        }}
                      >
                        <div>
                          <label
                            style={{
                              fontSize: "11px",
                              color: theme.textTertiary,
                            }}
                          >
                            X (mm)
                          </label>
                          <input
                            type="number"
                            value={hole.x}
                            onChange={(e) => {
                              const newHoles = [...editingPiece.holes];
                              newHoles[idx] = {
                                ...hole,
                                x: Number(e.target.value),
                              };
                              setEditingPiece((prev) =>
                                prev ? { ...prev, holes: newHoles } : null,
                              );
                            }}
                            style={{
                              width: "100%",
                              padding: "8px",
                              borderRadius: "6px",
                              border: `1px solid ${theme.border}`,
                              backgroundColor: theme.panel,
                              color: theme.textPrimary,
                              fontSize: "13px",
                            }}
                          />
                        </div>
                        <div>
                          <label
                            style={{
                              fontSize: "11px",
                              color: theme.textTertiary,
                            }}
                          >
                            Y (mm)
                          </label>
                          <input
                            type="number"
                            value={hole.y}
                            onChange={(e) => {
                              const newHoles = [...editingPiece.holes];
                              newHoles[idx] = {
                                ...hole,
                                y: Number(e.target.value),
                              };
                              setEditingPiece((prev) =>
                                prev ? { ...prev, holes: newHoles } : null,
                              );
                            }}
                            style={{
                              width: "100%",
                              padding: "8px",
                              borderRadius: "6px",
                              border: `1px solid ${theme.border}`,
                              backgroundColor: theme.panel,
                              color: theme.textPrimary,
                              fontSize: "13px",
                            }}
                          />
                        </div>
                        <div>
                          <label
                            style={{
                              fontSize: "11px",
                              color: theme.textTertiary,
                            }}
                          >
                            Diâmetro (mm)
                          </label>
                          <input
                            type="number"
                            value={hole.diameter}
                            onChange={(e) => {
                              const newHoles = [...editingPiece.holes];
                              newHoles[idx] = {
                                ...hole,
                                diameter: Number(e.target.value),
                              };
                              setEditingPiece((prev) =>
                                prev ? { ...prev, holes: newHoles } : null,
                              );
                            }}
                            style={{
                              width: "100%",
                              padding: "8px",
                              borderRadius: "6px",
                              border: `1px solid ${theme.border}`,
                              backgroundColor: theme.panel,
                              color: theme.textPrimary,
                              fontSize: "13px",
                            }}
                          />
                        </div>
                        <button
                          onClick={() => {
                            const newHoles = editingPiece.holes.filter(
                              (h) => h.id !== hole.id,
                            );
                            setEditingPiece((prev) =>
                              prev ? { ...prev, holes: newHoles } : null,
                            );
                          }}
                          style={{
                            padding: "8px",
                            background: "none",
                            border: "none",
                            cursor: "pointer",
                          }}
                        >
                          <Trash2 size={16} color={theme.danger} />
                        </button>
                      </div>
                    ))}
                  </div>
                )}

                {editingPiece.holes.length === 0 && (
                  <p
                    style={{
                      fontSize: "12px",
                      color: theme.textTertiary,
                      textAlign: "center",
                      padding: "20px",
                    }}
                  >
                    Nenhum furo adicionado. Clique em "Adicionar Furo" para
                    começar.
                  </p>
                )}
              </div>

              {/* Recortes */}
              <div style={{ marginBottom: "24px" }}>
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    marginBottom: "12px",
                  }}
                >
                  <h4
                    style={{
                      fontSize: "14px",
                      fontWeight: 600,
                      color: theme.textPrimary,
                    }}
                  >
                    <Scissors
                      size={16}
                      style={{ marginRight: "8px", verticalAlign: "middle" }}
                    />
                    Recortes ({editingPiece.cutouts.length})
                  </h4>
                  <div style={{ display: "flex", gap: "8px" }}>
                    <button
                      onClick={() => addCutoutToPiece("rectangle")}
                      style={{
                        ...btnSecondary,
                        padding: "6px 12px",
                        fontSize: "12px",
                      }}
                    >
                      <Square size={14} /> Retangular
                    </button>
                    <button
                      onClick={() => addCutoutToPiece("circle")}
                      style={{
                        ...btnSecondary,
                        padding: "6px 12px",
                        fontSize: "12px",
                      }}
                    >
                      <Circle size={14} /> Circular
                    </button>
                  </div>
                </div>

                {editingPiece.cutouts.length > 0 && (
                  <div
                    style={{
                      display: "flex",
                      flexDirection: "column",
                      gap: "8px",
                    }}
                  >
                    {editingPiece.cutouts.map((cutout, idx) => (
                      <div
                        key={cutout.id}
                        style={{
                          display: "flex",
                          gap: "12px",
                          padding: "12px",
                          backgroundColor: theme.inputBackground,
                          borderRadius: "8px",
                          alignItems: "center",
                        }}
                      >
                        <span
                          style={{
                            fontSize: "12px",
                            color: theme.textSecondary,
                            width: "80px",
                          }}
                        >
                          {cutout.type === "rectangle"
                            ? "Retângulo"
                            : "Círculo"}
                        </span>
                        <input
                          type="number"
                          placeholder="X"
                          value={cutout.x}
                          onChange={(e) => {
                            const newCutouts = [...editingPiece.cutouts];
                            newCutouts[idx] = {
                              ...cutout,
                              x: Number(e.target.value),
                            };
                            setEditingPiece((prev) =>
                              prev ? { ...prev, cutouts: newCutouts } : null,
                            );
                          }}
                          style={{
                            width: "70px",
                            padding: "8px",
                            borderRadius: "6px",
                            border: `1px solid ${theme.border}`,
                            backgroundColor: theme.panel,
                            color: theme.textPrimary,
                            fontSize: "12px",
                          }}
                        />
                        <input
                          type="number"
                          placeholder="Y"
                          value={cutout.y}
                          onChange={(e) => {
                            const newCutouts = [...editingPiece.cutouts];
                            newCutouts[idx] = {
                              ...cutout,
                              y: Number(e.target.value),
                            };
                            setEditingPiece((prev) =>
                              prev ? { ...prev, cutouts: newCutouts } : null,
                            );
                          }}
                          style={{
                            width: "70px",
                            padding: "8px",
                            borderRadius: "6px",
                            border: `1px solid ${theme.border}`,
                            backgroundColor: theme.panel,
                            color: theme.textPrimary,
                            fontSize: "12px",
                          }}
                        />
                        {cutout.type === "rectangle" && (
                          <>
                            <input
                              type="number"
                              placeholder="Larg"
                              value={cutout.width || 0}
                              onChange={(e) => {
                                const newCutouts = [...editingPiece.cutouts];
                                newCutouts[idx] = {
                                  ...cutout,
                                  width: Number(e.target.value),
                                };
                                setEditingPiece((prev) =>
                                  prev
                                    ? { ...prev, cutouts: newCutouts }
                                    : null,
                                );
                              }}
                              style={{
                                width: "70px",
                                padding: "8px",
                                borderRadius: "6px",
                                border: `1px solid ${theme.border}`,
                                backgroundColor: theme.panel,
                                color: theme.textPrimary,
                                fontSize: "12px",
                              }}
                            />
                            <input
                              type="number"
                              placeholder="Alt"
                              value={cutout.height || 0}
                              onChange={(e) => {
                                const newCutouts = [...editingPiece.cutouts];
                                newCutouts[idx] = {
                                  ...cutout,
                                  height: Number(e.target.value),
                                };
                                setEditingPiece((prev) =>
                                  prev
                                    ? { ...prev, cutouts: newCutouts }
                                    : null,
                                );
                              }}
                              style={{
                                width: "70px",
                                padding: "8px",
                                borderRadius: "6px",
                                border: `1px solid ${theme.border}`,
                                backgroundColor: theme.panel,
                                color: theme.textPrimary,
                                fontSize: "12px",
                              }}
                            />
                          </>
                        )}
                        {cutout.type === "circle" && (
                          <input
                            type="number"
                            placeholder="Diâm"
                            value={cutout.diameter || 0}
                            onChange={(e) => {
                              const newCutouts = [...editingPiece.cutouts];
                              newCutouts[idx] = {
                                ...cutout,
                                diameter: Number(e.target.value),
                              };
                              setEditingPiece((prev) =>
                                prev ? { ...prev, cutouts: newCutouts } : null,
                              );
                            }}
                            style={{
                              width: "70px",
                              padding: "8px",
                              borderRadius: "6px",
                              border: `1px solid ${theme.border}`,
                              backgroundColor: theme.panel,
                              color: theme.textPrimary,
                              fontSize: "12px",
                            }}
                          />
                        )}
                        <button
                          onClick={() => {
                            const newCutouts = editingPiece.cutouts.filter(
                              (c) => c.id !== cutout.id,
                            );
                            setEditingPiece((prev) =>
                              prev ? { ...prev, cutouts: newCutouts } : null,
                            );
                          }}
                          style={{
                            padding: "8px",
                            background: "none",
                            border: "none",
                            cursor: "pointer",
                            marginLeft: "auto",
                          }}
                        >
                          <Trash2 size={16} color={theme.danger} />
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Botões de ação */}
              <div style={{ display: "flex", gap: "12px" }}>
                <button
                  onClick={() => setShowPieceEditor(false)}
                  style={{ ...btnSecondary, flex: 1, justifyContent: "center" }}
                >
                  Cancelar
                </button>
                <button
                  onClick={savePiece}
                  style={{ ...btnPrimary, flex: 1, justifyContent: "center" }}
                >
                  <Save size={16} /> Salvar Peça
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default CncControl;
