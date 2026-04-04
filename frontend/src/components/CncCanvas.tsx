/**
 * ═══════════════════════════════════════════════════════════════════════════════
 * CncCanvas - Canvas Interativo 2D para Visualização de Corte CNC
 * ═══════════════════════════════════════════════════════════════════════════════
 *
 * Recursos:
 * - Zoom com scroll do mouse
 * - Pan (arrastar) com mouse
 * - Grid de referência com escala
 * - Visualização de nesting
 * - Preview de toolpath
 * - Seleção de peças
 * - Mini-mapa de navegação
 */

import React, { useRef, useEffect, useState, useCallback } from "react";
import {
  ZoomIn,
  ZoomOut,
  Maximize2,
  Move,
  Crosshair,
  Grid,
  Eye,
} from "lucide-react";

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
  layer?: string;
}

interface Placement {
  pieceId: string;
  pieceName?: string;
  x: number;
  y: number;
  rotation: number;
  width?: number;
  height?: number;
  contour?: Point[];
}

interface CncCanvasProps {
  width: number;
  height: number;
  geometry?: {
    entities: GeometryEntity[];
    boundingBox: { min: Point; max: Point };
  };
  placements?: Placement[];
  sheetWidth?: number;
  sheetHeight?: number;
  sheetMargin?: number;
  showGrid?: boolean;
  showToolpath?: boolean;
  showPiercePoints?: boolean;
  onPieceSelect?: (pieceId: string | null) => void;
  selectedPieceId?: string | null;
  theme: {
    background: string;
    surface: string;
    border: string;
    accentPrimary: string;
    success: string;
    warning: string;
    danger: string;
    textPrimary: string;
    textSecondary: string;
  };
}

const CncCanvas: React.FC<CncCanvasProps> = ({
  width,
  height,
  geometry,
  placements,
  sheetWidth = 3000,
  sheetHeight = 1500,
  sheetMargin = 10,
  showGrid = true,
  showToolpath = false,
  showPiercePoints = true,
  onPieceSelect,
  selectedPieceId,
  theme,
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const minimapRef = useRef<HTMLCanvasElement>(null);

  // Estado de visualização
  const [zoom, setZoom] = useState(1);
  const [panOffset, setPanOffset] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [hoveredPiece, setHoveredPiece] = useState<string | null>(null);
  const [showMinimap, setShowMinimap] = useState(true);

  // Constantes
  const GRID_SIZE = 50; // mm
  const MIN_ZOOM = 0.1;
  const MAX_ZOOM = 10;

  // Calcular escala base para caber a chapa no canvas
  const baseScale = Math.min(
    (width - 100) / sheetWidth,
    (height - 100) / sheetHeight,
  );

  // Transformação de coordenadas
  const worldToScreen = useCallback(
    (point: Point): Point => {
      const scale = baseScale * zoom;
      return {
        x: point.x * scale + panOffset.x + 50,
        y: height - (point.y * scale + panOffset.y + 50), // Y invertido
      };
    },
    [baseScale, zoom, panOffset, height],
  );

  const screenToWorld = useCallback(
    (point: Point): Point => {
      const scale = baseScale * zoom;
      return {
        x: (point.x - panOffset.x - 50) / scale,
        y: (height - point.y - panOffset.y - 50) / scale,
      };
    },
    [baseScale, zoom, panOffset, height],
  );

  // Desenhar grid
  const drawGrid = useCallback(
    (ctx: CanvasRenderingContext2D) => {
      if (!showGrid) return;

      const scale = baseScale * zoom;
      const gridStep = GRID_SIZE * scale;

      // Limitar grid se zoom muito baixo
      if (gridStep < 10) return;

      ctx.strokeStyle = theme.border;
      ctx.lineWidth = 0.5;
      ctx.setLineDash([]);

      // Calcular limites visíveis
      const startWorld = screenToWorld({ x: 0, y: height });
      const endWorld = screenToWorld({ x: width, y: 0 });

      const startX = Math.floor(startWorld.x / GRID_SIZE) * GRID_SIZE;
      const startY = Math.floor(startWorld.y / GRID_SIZE) * GRID_SIZE;

      // Linhas verticais
      for (let x = startX; x <= endWorld.x; x += GRID_SIZE) {
        const screenX = worldToScreen({ x, y: 0 }).x;
        if (screenX >= 0 && screenX <= width) {
          ctx.beginPath();
          ctx.moveTo(screenX, 0);
          ctx.lineTo(screenX, height);
          ctx.stroke();

          // Labels a cada 100mm
          if (x % 100 === 0 && zoom > 0.3) {
            ctx.fillStyle = theme.textSecondary;
            ctx.font = "10px monospace";
            ctx.fillText(`${x}`, screenX + 2, height - 5);
          }
        }
      }

      // Linhas horizontais
      for (let y = startY; y <= endWorld.y; y += GRID_SIZE) {
        const screenY = worldToScreen({ x: 0, y }).y;
        if (screenY >= 0 && screenY <= height) {
          ctx.beginPath();
          ctx.moveTo(0, screenY);
          ctx.lineTo(width, screenY);
          ctx.stroke();

          // Labels a cada 100mm
          if (y % 100 === 0 && zoom > 0.3) {
            ctx.fillStyle = theme.textSecondary;
            ctx.font = "10px monospace";
            ctx.fillText(`${y}`, 5, screenY - 2);
          }
        }
      }
    },
    [
      showGrid,
      baseScale,
      zoom,
      theme,
      width,
      height,
      worldToScreen,
      screenToWorld,
    ],
  );

  // Desenhar chapa
  const drawSheet = useCallback(
    (ctx: CanvasRenderingContext2D) => {
      const topLeft = worldToScreen({ x: 0, y: sheetHeight });
      const bottomRight = worldToScreen({ x: sheetWidth, y: 0 });

      // Área da chapa
      ctx.fillStyle = theme.surface;
      ctx.fillRect(
        topLeft.x,
        topLeft.y,
        bottomRight.x - topLeft.x,
        bottomRight.y - topLeft.y,
      );

      // Borda da chapa
      ctx.strokeStyle = theme.danger;
      ctx.lineWidth = 2;
      ctx.strokeRect(
        topLeft.x,
        topLeft.y,
        bottomRight.x - topLeft.x,
        bottomRight.y - topLeft.y,
      );

      // Margem de segurança
      if (sheetMargin > 0) {
        const marginTL = worldToScreen({
          x: sheetMargin,
          y: sheetHeight - sheetMargin,
        });
        const marginBR = worldToScreen({
          x: sheetWidth - sheetMargin,
          y: sheetMargin,
        });

        ctx.strokeStyle = theme.warning;
        ctx.lineWidth = 1;
        ctx.setLineDash([5, 5]);
        ctx.strokeRect(
          marginTL.x,
          marginTL.y,
          marginBR.x - marginTL.x,
          marginBR.y - marginTL.y,
        );
        ctx.setLineDash([]);
      }

      // Dimensões da chapa
      ctx.fillStyle = theme.textSecondary;
      ctx.font = "12px monospace";
      ctx.fillText(
        `${sheetWidth} x ${sheetHeight}mm`,
        topLeft.x + 5,
        topLeft.y + 15,
      );
    },
    [worldToScreen, sheetWidth, sheetHeight, sheetMargin, theme],
  );

  // Desenhar geometria
  const drawGeometry = useCallback(
    (ctx: CanvasRenderingContext2D) => {
      if (!geometry) return;

      const scale = baseScale * zoom;

      for (const entity of geometry.entities) {
        ctx.beginPath();
        ctx.strokeStyle = theme.accentPrimary;
        ctx.lineWidth = 2;

        if (entity.type === "circle" && entity.center && entity.radius) {
          const center = worldToScreen(entity.center);
          ctx.arc(center.x, center.y, entity.radius * scale, 0, Math.PI * 2);
        } else if (
          entity.type === "polyline" &&
          entity.points &&
          entity.points.length > 0
        ) {
          const firstPoint = worldToScreen(entity.points[0]);
          ctx.moveTo(firstPoint.x, firstPoint.y);

          for (let i = 1; i < entity.points.length; i++) {
            const point = worldToScreen(entity.points[i]);
            ctx.lineTo(point.x, point.y);
          }

          if (entity.closed) {
            ctx.closePath();
          }
        } else if (
          entity.type === "line" &&
          entity.points &&
          entity.points.length >= 2
        ) {
          const p1 = worldToScreen(entity.points[0]);
          const p2 = worldToScreen(entity.points[1]);
          ctx.moveTo(p1.x, p1.y);
          ctx.lineTo(p2.x, p2.y);
        } else if (entity.type === "arc" && entity.center && entity.radius) {
          const center = worldToScreen(entity.center);
          const startAngle = ((entity.startAngle || 0) * Math.PI) / 180;
          const endAngle = ((entity.endAngle || 360) * Math.PI) / 180;
          ctx.arc(
            center.x,
            center.y,
            entity.radius * scale,
            -endAngle,
            -startAngle,
          );
        }

        ctx.stroke();

        // Marcar pontos de pierce
        if (showPiercePoints) {
          let piercePoint: Point | null = null;

          if (entity.type === "circle" && entity.center && entity.radius) {
            piercePoint = {
              x: entity.center.x + entity.radius,
              y: entity.center.y,
            };
          } else if (
            entity.type === "polyline" &&
            entity.points &&
            entity.points.length > 0
          ) {
            piercePoint = entity.points[0];
          } else if (
            entity.type === "line" &&
            entity.points &&
            entity.points.length > 0
          ) {
            piercePoint = entity.points[0];
          }

          if (piercePoint) {
            const screenPoint = worldToScreen(piercePoint);
            ctx.fillStyle = theme.success;
            ctx.beginPath();
            ctx.arc(screenPoint.x, screenPoint.y, 4, 0, Math.PI * 2);
            ctx.fill();
          }
        }
      }
    },
    [geometry, baseScale, zoom, worldToScreen, showPiercePoints, theme],
  );

  // Desenhar placements (nesting)
  const drawPlacements = useCallback(
    (ctx: CanvasRenderingContext2D) => {
      if (!placements) return;

      const scale = baseScale * zoom;

      for (const placement of placements) {
        const isSelected = placement.pieceId === selectedPieceId;
        const isHovered = placement.pieceId === hoveredPiece;

        ctx.save();

        // Transformar para posição e rotação
        const origin = worldToScreen({ x: placement.x, y: placement.y });
        ctx.translate(origin.x, origin.y);
        ctx.rotate((-placement.rotation * Math.PI) / 180);

        // Contorno da peça
        ctx.beginPath();

        if (placement.contour && placement.contour.length > 0) {
          ctx.moveTo(
            placement.contour[0].x * scale,
            -placement.contour[0].y * scale,
          );
          for (let i = 1; i < placement.contour.length; i++) {
            ctx.lineTo(
              placement.contour[i].x * scale,
              -placement.contour[i].y * scale,
            );
          }
          ctx.closePath();
        } else if (placement.width && placement.height) {
          ctx.rect(0, 0, placement.width * scale, -placement.height * scale);
        }

        // Preenchimento
        if (isSelected) {
          ctx.fillStyle = `${theme.accentPrimary}40`;
        } else if (isHovered) {
          ctx.fillStyle = `${theme.success}30`;
        } else {
          ctx.fillStyle = `${theme.accentPrimary}15`;
        }
        ctx.fill();

        // Borda
        ctx.strokeStyle = isSelected
          ? theme.accentPrimary
          : isHovered
            ? theme.success
            : theme.border;
        ctx.lineWidth = isSelected ? 3 : isHovered ? 2 : 1;
        ctx.stroke();

        // Label da peça
        if (zoom > 0.3 && placement.pieceName) {
          ctx.fillStyle = theme.textPrimary;
          ctx.font = `${Math.max(10, 12 * zoom)}px sans-serif`;
          ctx.textAlign = "center";
          ctx.textBaseline = "middle";

          const labelX = ((placement.width || 100) / 2) * scale;
          const labelY = (-(placement.height || 100) / 2) * scale;
          ctx.fillText(placement.pieceName, labelX, labelY);
        }

        ctx.restore();
      }
    },
    [
      placements,
      baseScale,
      zoom,
      worldToScreen,
      selectedPieceId,
      hoveredPiece,
      theme,
    ],
  );

  // Desenhar mini-mapa
  const drawMinimap = useCallback(() => {
    if (!minimapRef.current || !showMinimap) return;

    const ctx = minimapRef.current.getContext("2d");
    if (!ctx) return;

    const mapWidth = 150;
    const mapHeight = 100;
    const mapScale =
      Math.min(mapWidth / sheetWidth, mapHeight / sheetHeight) * 0.9;

    // Background
    ctx.fillStyle = theme.background;
    ctx.fillRect(0, 0, mapWidth, mapHeight);

    // Chapa
    ctx.fillStyle = theme.surface;
    ctx.strokeStyle = theme.border;
    ctx.lineWidth = 1;
    ctx.fillRect(5, 5, sheetWidth * mapScale, sheetHeight * mapScale);
    ctx.strokeRect(5, 5, sheetWidth * mapScale, sheetHeight * mapScale);

    // Placements
    if (placements) {
      ctx.fillStyle = theme.accentPrimary;
      for (const p of placements) {
        const px = 5 + p.x * mapScale;
        const py = 5 + (sheetHeight - p.y - (p.height || 50)) * mapScale;
        const pw = (p.width || 50) * mapScale;
        const ph = (p.height || 50) * mapScale;
        ctx.fillRect(px, py, pw, ph);
      }
    }

    // Viewport
    const viewportWorld = {
      x: -panOffset.x / (baseScale * zoom),
      y: -panOffset.y / (baseScale * zoom),
      width: width / (baseScale * zoom),
      height: height / (baseScale * zoom),
    };

    ctx.strokeStyle = theme.danger;
    ctx.lineWidth = 2;
    ctx.strokeRect(
      5 + viewportWorld.x * mapScale,
      5 + (sheetHeight - viewportWorld.y - viewportWorld.height) * mapScale,
      viewportWorld.width * mapScale,
      viewportWorld.height * mapScale,
    );
  }, [
    showMinimap,
    sheetWidth,
    sheetHeight,
    placements,
    panOffset,
    baseScale,
    zoom,
    width,
    height,
    theme,
  ]);

  // Render principal
  useEffect(() => {
    if (!canvasRef.current) return;

    const ctx = canvasRef.current.getContext("2d");
    if (!ctx) return;

    // Clear
    ctx.fillStyle = theme.background;
    ctx.fillRect(0, 0, width, height);

    // Draw layers
    drawGrid(ctx);
    drawSheet(ctx);
    drawPlacements(ctx);
    drawGeometry(ctx);

    // Minimap
    drawMinimap();
  }, [
    width,
    height,
    theme,
    drawGrid,
    drawSheet,
    drawPlacements,
    drawGeometry,
    drawMinimap,
  ]);

  // Event handlers
  const handleWheel = useCallback(
    (e: React.WheelEvent) => {
      e.preventDefault();

      const delta = e.deltaY > 0 ? 0.9 : 1.1;
      const newZoom = Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, zoom * delta));

      // Zoom centrado no mouse
      const rect = canvasRef.current?.getBoundingClientRect();
      if (rect) {
        const mouseX = e.clientX - rect.left;
        const mouseY = e.clientY - rect.top;

        const worldBefore = screenToWorld({ x: mouseX, y: mouseY });
        setZoom(newZoom);

        // Ajustar pan para manter mouse sobre mesmo ponto world
        const scale = baseScale * newZoom;
        const newPanX = mouseX - 50 - worldBefore.x * scale;
        const newPanY = height - mouseY - 50 - worldBefore.y * scale;
        setPanOffset({ x: newPanX, y: newPanY });
      }
    },
    [zoom, baseScale, height, screenToWorld],
  );

  const handleMouseDown = useCallback(
    (e: React.MouseEvent) => {
      if (e.button === 0) {
        // Left click
        setIsDragging(true);
        setDragStart({
          x: e.clientX - panOffset.x,
          y: e.clientY + panOffset.y,
        });
      }
    },
    [panOffset],
  );

  const handleMouseMove = useCallback(
    (e: React.MouseEvent) => {
      if (isDragging) {
        setPanOffset({
          x: e.clientX - dragStart.x,
          y: dragStart.y - e.clientY,
        });
      } else if (placements && onPieceSelect) {
        // Check hover
        const rect = canvasRef.current?.getBoundingClientRect();
        if (rect) {
          const mouseWorld = screenToWorld({
            x: e.clientX - rect.left,
            y: e.clientY - rect.top,
          });

          let foundPiece: string | null = null;
          for (const p of placements) {
            const pw = p.width || 100;
            const ph = p.height || 100;
            if (
              mouseWorld.x >= p.x &&
              mouseWorld.x <= p.x + pw &&
              mouseWorld.y >= p.y &&
              mouseWorld.y <= p.y + ph
            ) {
              foundPiece = p.pieceId;
              break;
            }
          }
          setHoveredPiece(foundPiece);
        }
      }
    },
    [isDragging, dragStart, placements, onPieceSelect, screenToWorld],
  );

  const handleMouseUp = useCallback(() => {
    if (isDragging && hoveredPiece && onPieceSelect) {
      onPieceSelect(hoveredPiece);
    }
    setIsDragging(false);
  }, [isDragging, hoveredPiece, onPieceSelect]);

  const handleDoubleClick = useCallback(() => {
    // Reset view
    setZoom(1);
    setPanOffset({ x: 0, y: 0 });
  }, []);

  // Toolbar
  const toolbarBtnStyle: React.CSSProperties = {
    width: 32,
    height: 32,
    border: `1px solid ${theme.border}`,
    backgroundColor: theme.surface,
    borderRadius: 6,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    cursor: "pointer",
    color: theme.textPrimary,
  };

  return (
    <div style={{ position: "relative", width, height }}>
      <canvas
        ref={canvasRef}
        width={width}
        height={height}
        style={{
          borderRadius: 8,
          cursor: isDragging ? "grabbing" : "grab",
        }}
        onWheel={handleWheel}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        onDoubleClick={handleDoubleClick}
      />

      {/* Toolbar */}
      <div
        style={{
          position: "absolute",
          top: 10,
          right: 10,
          display: "flex",
          flexDirection: "column",
          gap: 4,
          backgroundColor: `${theme.background}E0`,
          padding: 8,
          borderRadius: 8,
          border: `1px solid ${theme.border}`,
        }}
      >
        <button
          style={toolbarBtnStyle}
          onClick={() => setZoom((z) => Math.min(MAX_ZOOM, z * 1.2))}
          title="Zoom In"
        >
          <ZoomIn size={16} />
        </button>
        <button
          style={toolbarBtnStyle}
          onClick={() => setZoom((z) => Math.max(MIN_ZOOM, z / 1.2))}
          title="Zoom Out"
        >
          <ZoomOut size={16} />
        </button>
        <button
          style={toolbarBtnStyle}
          onClick={handleDoubleClick}
          title="Fit to View"
        >
          <Maximize2 size={16} />
        </button>
        <div
          style={{ height: 1, backgroundColor: theme.border, margin: "4px 0" }}
        />
        <button
          style={{
            ...toolbarBtnStyle,
            backgroundColor: showMinimap ? theme.accentPrimary : theme.surface,
          }}
          onClick={() => setShowMinimap(!showMinimap)}
          title="Toggle Minimap"
        >
          <Eye size={16} color={showMinimap ? "#fff" : theme.textPrimary} />
        </button>
      </div>

      {/* Zoom indicator */}
      <div
        style={{
          position: "absolute",
          bottom: 10,
          left: 10,
          padding: "4px 8px",
          backgroundColor: `${theme.background}E0`,
          borderRadius: 4,
          fontSize: 12,
          color: theme.textSecondary,
          fontFamily: "monospace",
        }}
      >
        {Math.round(zoom * 100)}%
      </div>

      {/* Minimap */}
      {showMinimap && (
        <canvas
          ref={minimapRef}
          width={150}
          height={100}
          style={{
            position: "absolute",
            bottom: 10,
            right: 10,
            borderRadius: 6,
            border: `1px solid ${theme.border}`,
            backgroundColor: theme.background,
          }}
        />
      )}

      {/* Crosshair cursor indicator */}
      <div
        style={{
          position: "absolute",
          top: 10,
          left: 10,
          display: "flex",
          alignItems: "center",
          gap: 4,
          padding: "4px 8px",
          backgroundColor: `${theme.background}E0`,
          borderRadius: 4,
          fontSize: 11,
          color: theme.textSecondary,
        }}
      >
        <Crosshair size={12} />
        <span>Scroll: Zoom | Drag: Pan | DblClick: Reset</span>
      </div>
    </div>
  );
};

export default CncCanvas;
