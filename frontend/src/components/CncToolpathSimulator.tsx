/**
 * ═══════════════════════════════════════════════════════════════════════════════
 * CncToolpathSimulator - Simulação Animada do Toolpath de Corte Plasma
 * ═══════════════════════════════════════════════════════════════════════════════
 *
 * Melhoria #1: Simulação em tempo real do percurso de corte
 * - Animação do toolpath sendo executado
 * - Visualização do arco plasma "cortando"
 * - Timeline com pause/play/velocidade
 * - Indicadores de temperatura simulados
 */

import React, { useState, useEffect, useRef, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Play,
  Pause,
  RotateCcw,
  FastForward,
  Rewind,
  Flame,
  Thermometer,
  Clock,
  Zap,
  Settings,
  Maximize2,
  Volume2,
  VolumeX,
} from "lucide-react";

interface Point {
  x: number;
  y: number;
}

interface ToolpathSegment {
  type: "rapid" | "cut" | "pierce";
  start: Point;
  end: Point;
  duration: number; // ms
}

interface CncToolpathSimulatorProps {
  toolpath: ToolpathSegment[];
  width?: number;
  height?: number;
  theme: {
    surface: string;
    border: string;
    accentPrimary: string;
    success: string;
    warning: string;
    danger: string;
    textPrimary: string;
    textSecondary: string;
  };
  onComplete?: () => void;
}

const CncToolpathSimulator: React.FC<CncToolpathSimulatorProps> = ({
  toolpath,
  width = 800,
  height = 500,
  theme,
  onComplete,
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationRef = useRef<number | null>(null);

  // State
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentSegment, setCurrentSegment] = useState(0);
  const [progress, setProgress] = useState(0);
  const [speed, setSpeed] = useState(1);
  const [torchPosition, setTorchPosition] = useState<Point>({ x: 0, y: 0 });
  const [temperature, setTemperature] = useState(0);
  const [soundEnabled, setSoundEnabled] = useState(false);
  const [showHeatMap, setShowHeatMap] = useState(true);

  // Heat map data
  const heatMapRef = useRef<number[][]>([]);
  const cutPathRef = useRef<Point[]>([]);

  // Initialize heat map
  useEffect(() => {
    const gridSize = 20;
    heatMapRef.current = Array(Math.ceil(height / gridSize))
      .fill(null)
      .map(() => Array(Math.ceil(width / gridSize)).fill(0));
  }, [width, height]);

  // Calculate total duration
  const totalDuration = toolpath.reduce((sum, seg) => sum + seg.duration, 0);

  // Animation loop
  useEffect(() => {
    if (!isPlaying || !canvasRef.current) return;

    let startTime = performance.now();
    let accumulatedTime = 0;

    // Calculate start time offset
    for (let i = 0; i < currentSegment; i++) {
      accumulatedTime += toolpath[i].duration;
    }
    accumulatedTime +=
      (progress / 100) * (toolpath[currentSegment]?.duration || 0);

    const animate = (timestamp: number) => {
      const elapsed = (timestamp - startTime) * speed;
      let currentTime = accumulatedTime + elapsed;

      // Find current segment
      let segmentTime = 0;
      let segIdx = 0;
      for (let i = 0; i < toolpath.length; i++) {
        if (segmentTime + toolpath[i].duration > currentTime) {
          segIdx = i;
          break;
        }
        segmentTime += toolpath[i].duration;
        if (i === toolpath.length - 1) {
          segIdx = i;
          currentTime = totalDuration;
        }
      }

      const segment = toolpath[segIdx];
      if (!segment) return;

      const segmentProgress = Math.min(
        100,
        ((currentTime - segmentTime) / segment.duration) * 100,
      );

      // Update position
      const x =
        segment.start.x +
        (segment.end.x - segment.start.x) * (segmentProgress / 100);
      const y =
        segment.start.y +
        (segment.end.y - segment.start.y) * (segmentProgress / 100);
      setTorchPosition({ x, y });

      // Update temperature based on segment type
      if (segment.type === "cut") {
        setTemperature((prev) => Math.min(100, prev + 2));
        cutPathRef.current.push({ x, y });

        // Update heat map
        if (showHeatMap) {
          const gridX = Math.floor(x / 20);
          const gridY = Math.floor(y / 20);
          if (heatMapRef.current[gridY]?.[gridX] !== undefined) {
            heatMapRef.current[gridY][gridX] = Math.min(
              100,
              heatMapRef.current[gridY][gridX] + 5,
            );
          }
        }
      } else if (segment.type === "pierce") {
        setTemperature(100);
      } else {
        setTemperature((prev) => Math.max(0, prev - 5));
      }

      setCurrentSegment(segIdx);
      setProgress(segmentProgress);

      // Draw
      drawCanvas();

      // Check completion
      if (currentTime >= totalDuration) {
        setIsPlaying(false);
        onComplete?.();
        return;
      }

      animationRef.current = requestAnimationFrame(animate);
    };

    animationRef.current = requestAnimationFrame(animate);

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [isPlaying, speed, currentSegment, progress, toolpath, showHeatMap]);

  // Draw canvas
  const drawCanvas = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    // Clear
    ctx.fillStyle = "#0a0a0f";
    ctx.fillRect(0, 0, width, height);

    // Draw heat map
    if (showHeatMap) {
      const gridSize = 20;
      for (let y = 0; y < heatMapRef.current.length; y++) {
        for (let x = 0; x < heatMapRef.current[y].length; x++) {
          const heat = heatMapRef.current[y][x];
          if (heat > 0) {
            const alpha = heat / 100;
            ctx.fillStyle = `rgba(255, ${Math.max(0, 150 - heat * 1.5)}, 0, ${alpha * 0.3})`;
            ctx.fillRect(x * gridSize, y * gridSize, gridSize, gridSize);
          }
        }
      }
    }

    // Draw full toolpath (faded)
    ctx.strokeStyle = "rgba(100, 100, 100, 0.3)";
    ctx.lineWidth = 1;
    ctx.setLineDash([5, 5]);
    ctx.beginPath();
    toolpath.forEach((seg, i) => {
      if (i === 0) {
        ctx.moveTo(seg.start.x, seg.start.y);
      }
      ctx.lineTo(seg.end.x, seg.end.y);
    });
    ctx.stroke();
    ctx.setLineDash([]);

    // Draw completed cuts
    ctx.strokeStyle = "#FF6B35";
    ctx.lineWidth = 2;
    ctx.beginPath();
    cutPathRef.current.forEach((point, i) => {
      if (i === 0) {
        ctx.moveTo(point.x, point.y);
      } else {
        ctx.lineTo(point.x, point.y);
      }
    });
    ctx.stroke();

    // Draw torch
    const segment = toolpath[currentSegment];
    if (segment) {
      // Torch glow effect
      const gradient = ctx.createRadialGradient(
        torchPosition.x,
        torchPosition.y,
        0,
        torchPosition.x,
        torchPosition.y,
        segment.type === "cut" ? 30 : 15,
      );

      if (segment.type === "cut") {
        gradient.addColorStop(0, "rgba(255, 200, 100, 0.9)");
        gradient.addColorStop(0.3, "rgba(255, 100, 50, 0.6)");
        gradient.addColorStop(1, "rgba(255, 50, 0, 0)");
      } else if (segment.type === "pierce") {
        gradient.addColorStop(0, "rgba(255, 255, 200, 1)");
        gradient.addColorStop(0.5, "rgba(255, 150, 50, 0.8)");
        gradient.addColorStop(1, "rgba(255, 50, 0, 0)");
      } else {
        gradient.addColorStop(0, "rgba(100, 200, 255, 0.5)");
        gradient.addColorStop(1, "rgba(100, 200, 255, 0)");
      }

      ctx.fillStyle = gradient;
      ctx.beginPath();
      ctx.arc(
        torchPosition.x,
        torchPosition.y,
        segment.type === "cut" ? 30 : 15,
        0,
        Math.PI * 2,
      );
      ctx.fill();

      // Torch center
      ctx.fillStyle = segment.type === "rapid" ? "#00D4FF" : "#FFF";
      ctx.beginPath();
      ctx.arc(torchPosition.x, torchPosition.y, 4, 0, Math.PI * 2);
      ctx.fill();

      // Sparks effect for cutting
      if (segment.type === "cut") {
        for (let i = 0; i < 8; i++) {
          const angle = Math.random() * Math.PI * 2;
          const dist = 10 + Math.random() * 20;
          const sparkX = torchPosition.x + Math.cos(angle) * dist;
          const sparkY = torchPosition.y + Math.sin(angle) * dist;

          ctx.fillStyle = `rgba(255, ${150 + Math.random() * 100}, 50, ${Math.random()})`;
          ctx.beginPath();
          ctx.arc(sparkX, sparkY, 1 + Math.random() * 2, 0, Math.PI * 2);
          ctx.fill();
        }
      }
    }
  }, [toolpath, currentSegment, torchPosition, width, height, showHeatMap]);

  // Controls
  const handlePlayPause = () => setIsPlaying(!isPlaying);

  const handleReset = () => {
    setIsPlaying(false);
    setCurrentSegment(0);
    setProgress(0);
    setTemperature(0);
    cutPathRef.current = [];
    heatMapRef.current = heatMapRef.current.map((row) => row.map(() => 0));
    drawCanvas();
  };

  const handleSpeedChange = (newSpeed: number) => {
    setSpeed(newSpeed);
  };

  const formatTime = (ms: number) => {
    const seconds = Math.floor(ms / 1000);
    const minutes = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${minutes}:${secs.toString().padStart(2, "0")}`;
  };

  const currentTime =
    toolpath
      .slice(0, currentSegment)
      .reduce((sum, seg) => sum + seg.duration, 0) +
    (progress / 100) * (toolpath[currentSegment]?.duration || 0);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      style={{
        background: theme.surface,
        border: `1px solid ${theme.border}`,
        borderRadius: "12px",
        overflow: "hidden",
      }}
    >
      {/* Canvas */}
      <div style={{ position: "relative" }}>
        <canvas
          ref={canvasRef}
          width={width}
          height={height}
          style={{ display: "block" }}
        />

        {/* Status overlay */}
        <div
          style={{
            position: "absolute",
            top: 12,
            left: 12,
            display: "flex",
            gap: 12,
          }}
        >
          {/* Operation type */}
          <div
            style={{
              background: "rgba(0,0,0,0.7)",
              padding: "6px 12px",
              borderRadius: 6,
              display: "flex",
              alignItems: "center",
              gap: 6,
            }}
          >
            {toolpath[currentSegment]?.type === "cut" && (
              <>
                <Flame size={14} color="#FF6B35" />
                <span
                  style={{ color: "#FF6B35", fontSize: 12, fontWeight: 600 }}
                >
                  CORTANDO
                </span>
              </>
            )}
            {toolpath[currentSegment]?.type === "pierce" && (
              <>
                <Zap size={14} color="#FFD700" />
                <span
                  style={{ color: "#FFD700", fontSize: 12, fontWeight: 600 }}
                >
                  PERFURANDO
                </span>
              </>
            )}
            {toolpath[currentSegment]?.type === "rapid" && (
              <>
                <FastForward size={14} color="#00D4FF" />
                <span
                  style={{ color: "#00D4FF", fontSize: 12, fontWeight: 600 }}
                >
                  DESLOCAMENTO
                </span>
              </>
            )}
          </div>

          {/* Temperature */}
          <div
            style={{
              background: "rgba(0,0,0,0.7)",
              padding: "6px 12px",
              borderRadius: 6,
              display: "flex",
              alignItems: "center",
              gap: 6,
            }}
          >
            <Thermometer
              size={14}
              color={
                temperature > 70
                  ? "#FF4444"
                  : temperature > 40
                    ? "#FFD700"
                    : "#00D4FF"
              }
            />
            <div
              style={{
                width: 60,
                height: 6,
                background: "#333",
                borderRadius: 3,
                overflow: "hidden",
              }}
            >
              <div
                style={{
                  width: `${temperature}%`,
                  height: "100%",
                  background:
                    temperature > 70
                      ? "linear-gradient(90deg, #FF4444, #FF0000)"
                      : temperature > 40
                        ? "linear-gradient(90deg, #FFD700, #FF8800)"
                        : "linear-gradient(90deg, #00D4FF, #00FF88)",
                  transition: "width 0.1s",
                }}
              />
            </div>
          </div>
        </div>

        {/* Position overlay */}
        <div
          style={{
            position: "absolute",
            top: 12,
            right: 12,
            background: "rgba(0,0,0,0.7)",
            padding: "6px 12px",
            borderRadius: 6,
            fontFamily: "monospace",
            fontSize: 11,
            color: "#AAA",
          }}
        >
          X: {torchPosition.x.toFixed(1)} Y: {torchPosition.y.toFixed(1)}
        </div>
      </div>

      {/* Controls */}
      <div
        style={{
          padding: 16,
          borderTop: `1px solid ${theme.border}`,
          display: "flex",
          alignItems: "center",
          gap: 16,
        }}
      >
        {/* Play/Pause */}
        <button
          onClick={handlePlayPause}
          style={{
            width: 44,
            height: 44,
            borderRadius: "50%",
            border: "none",
            background: theme.accentPrimary,
            color: "#FFF",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          {isPlaying ? <Pause size={20} /> : <Play size={20} />}
        </button>

        {/* Reset */}
        <button
          onClick={handleReset}
          style={{
            width: 36,
            height: 36,
            borderRadius: "50%",
            border: `1px solid ${theme.border}`,
            background: "transparent",
            color: theme.textSecondary,
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <RotateCcw size={16} />
        </button>

        {/* Timeline */}
        <div
          style={{ flex: 1, display: "flex", alignItems: "center", gap: 12 }}
        >
          <span style={{ color: theme.textSecondary, fontSize: 12, width: 45 }}>
            {formatTime(currentTime)}
          </span>
          <div
            style={{
              flex: 1,
              height: 6,
              background: theme.border,
              borderRadius: 3,
              overflow: "hidden",
            }}
          >
            <div
              style={{
                width: `${(currentTime / totalDuration) * 100}%`,
                height: "100%",
                background: `linear-gradient(90deg, ${theme.accentPrimary}, ${theme.success})`,
                transition: "width 0.1s",
              }}
            />
          </div>
          <span style={{ color: theme.textSecondary, fontSize: 12, width: 45 }}>
            {formatTime(totalDuration)}
          </span>
        </div>

        {/* Speed controls */}
        <div style={{ display: "flex", gap: 4 }}>
          {[0.5, 1, 2, 4].map((s) => (
            <button
              key={s}
              onClick={() => handleSpeedChange(s)}
              style={{
                padding: "4px 8px",
                borderRadius: 4,
                border: `1px solid ${speed === s ? theme.accentPrimary : theme.border}`,
                background: speed === s ? theme.accentPrimary : "transparent",
                color: speed === s ? "#FFF" : theme.textSecondary,
                fontSize: 11,
                cursor: "pointer",
              }}
            >
              {s}x
            </button>
          ))}
        </div>

        {/* Toggle buttons */}
        <button
          onClick={() => setShowHeatMap(!showHeatMap)}
          style={{
            width: 36,
            height: 36,
            borderRadius: 6,
            border: `1px solid ${showHeatMap ? theme.warning : theme.border}`,
            background: showHeatMap ? `${theme.warning}20` : "transparent",
            color: showHeatMap ? theme.warning : theme.textSecondary,
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
          title="Mapa de calor"
        >
          <Thermometer size={16} />
        </button>

        <button
          onClick={() => setSoundEnabled(!soundEnabled)}
          style={{
            width: 36,
            height: 36,
            borderRadius: 6,
            border: `1px solid ${theme.border}`,
            background: "transparent",
            color: theme.textSecondary,
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          {soundEnabled ? <Volume2 size={16} /> : <VolumeX size={16} />}
        </button>
      </div>

      {/* Segment info */}
      <div
        style={{
          padding: "12px 16px",
          borderTop: `1px solid ${theme.border}`,
          display: "flex",
          justifyContent: "space-between",
          fontSize: 12,
          color: theme.textSecondary,
        }}
      >
        <span>
          Segmento: {currentSegment + 1} / {toolpath.length}
        </span>
        <span>Velocidade: {speed}x</span>
        <span>
          Progresso: {((currentTime / totalDuration) * 100).toFixed(1)}%
        </span>
      </div>
    </motion.div>
  );
};

export default CncToolpathSimulator;
