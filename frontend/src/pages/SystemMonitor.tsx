import React, { useState, useEffect, useCallback, useRef } from "react";
import {
  Activity,
  Cpu,
  HardDrive,
  Database,
  Wifi,
  AlertTriangle,
  Server,
  Clock,
  Zap,
  BarChart3,
  RefreshCw,
} from "lucide-react";
import { api } from "../services/api";
import { wsService } from "../services/websocket";

interface SystemMetrics {
  cpu: { percent: number };
  memory: { percent: number; used_mb: number; total_mb: number };
  disk: { percent: number; used_gb: number; total_gb: number };
  process: { cpu_percent: number; memory_mb: number; threads: number };
  active_connections: number;
}

interface Alert {
  name: string;
  metric: string;
  value: number;
  threshold: number;
  severity: string;
  timestamp: string;
}

interface TaskQueueStats {
  total_submitted: number;
  total_completed: number;
  total_failed: number;
  active_tasks: number;
  queue_size: number;
  avg_duration_ms: number;
  peak_active: number;
}

interface RequestMetrics {
  total_requests: number;
  total_errors: number;
  error_rate_percent: number;
  response_times: {
    avg_ms: number;
    p50_ms: number;
    p95_ms: number;
    p99_ms: number;
  };
}

interface DashboardData {
  system?: {
    system?: SystemMetrics;
    alerts?: Alert[];
    requests?: RequestMetrics;
    top_endpoints?: Array<{
      endpoint: string;
      count: number;
      errors: number;
      avg_ms: number;
    }>;
  };
  task_queue?: TaskQueueStats;
  db_pool?: {
    total_connections: number;
    active_connections: number;
    peak_connections: number;
    total_queries: number;
    avg_query_time_ms: number;
  };
  cache?: {
    l1: {
      hits: number;
      misses: number;
      hit_rate_percent: number;
      size: number;
    };
    l2: {
      hits: number;
      misses: number;
      hit_rate_percent: number;
      available: boolean;
    };
  };
  websocket?: {
    active_connections: number;
    active_users: number;
    total_messages_sent: number;
    peak_connections: number;
  };
}

const MetricCard: React.FC<{
  title: string;
  value: string | number;
  subtitle?: string;
  icon: React.ReactNode;
  color?: string;
  trend?: "up" | "down" | "stable";
}> = ({ title, value, subtitle, icon, color = "blue" }) => (
  <div className="bg-white dark:bg-gray-800 rounded-xl p-4 shadow-sm border border-gray-200 dark:border-gray-700">
    <div className="flex items-center justify-between mb-2">
      <span className="text-sm text-gray-500 dark:text-gray-400">{title}</span>
      <span className={`text-${color}-500`}>{icon}</span>
    </div>
    <div className="text-2xl font-bold text-gray-900 dark:text-white">
      {value}
    </div>
    {subtitle && <div className="text-xs text-gray-400 mt-1">{subtitle}</div>}
  </div>
);

const ProgressBar: React.FC<{
  value: number;
  label: string;
  color?: string;
}> = ({ value, label, color = "blue" }) => {
  const c = value > 90 ? "red" : value > 75 ? "yellow" : color;
  return (
    <div className="mb-3">
      <div className="flex justify-between text-sm mb-1">
        <span className="text-gray-600 dark:text-gray-400">{label}</span>
        <span className="font-mono text-gray-900 dark:text-white">
          {value.toFixed(1)}%
        </span>
      </div>
      <div className="h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
        <div
          className={`h-full bg-${c}-500 rounded-full transition-all duration-500`}
          style={{ width: `${Math.min(value, 100)}%` }}
        />
      </div>
    </div>
  );
};

const SystemMonitorPage: React.FC = () => {
  const [data, setData] = useState<DashboardData>({});
  const [loading, setLoading] = useState(true);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());
  const intervalRef = useRef<ReturnType<typeof setInterval>>();

  const fetchData = useCallback(async () => {
    try {
      const response = await api.get("/api/monitoring/dashboard");
      setData(response.data);
      setLastUpdate(new Date());
    } catch (err) {
      console.error("Erro ao carregar dashboard:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    if (autoRefresh) {
      intervalRef.current = setInterval(fetchData, 5000);
    }
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [fetchData, autoRefresh]);

  // WebSocket real-time updates
  useEffect(() => {
    const unsub = wsService.on("system_update", (msg) => {
      setData((prev) => ({
        ...prev,
        system: {
          ...prev.system,
          system: msg as any,
        },
      }));
      setLastUpdate(new Date());
    });
    return unsub;
  }, []);

  const sys = data.system?.system;
  const alerts = data.system?.alerts || [];
  const requests = data.system?.requests;
  const tq = data.task_queue;
  const pool = data.db_pool;
  const cache = data.cache;
  const ws = data.websocket;
  const topEndpoints = data.system?.top_endpoints || [];

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <RefreshCw className="w-8 h-8 animate-spin text-blue-500" />
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <Activity className="w-6 h-6 text-blue-500" />
            Monitor do Sistema
          </h1>
          <p className="text-sm text-gray-500">
            Última atualização: {lastUpdate.toLocaleTimeString()}
          </p>
        </div>
        <button
          onClick={() => setAutoRefresh(!autoRefresh)}
          className={`px-4 py-2 rounded-lg text-sm font-medium ${
            autoRefresh
              ? "bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300"
              : "bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300"
          }`}
        >
          {autoRefresh ? "Auto ✓" : "Auto ✗"}
        </button>
      </div>

      {/* Alerts */}
      {alerts.length > 0 && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl p-4">
          <h3 className="text-red-800 dark:text-red-300 font-semibold flex items-center gap-2 mb-2">
            <AlertTriangle className="w-5 h-5" /> Alertas Ativos
          </h3>
          {alerts.slice(0, 5).map((alert, i) => (
            <div
              key={i}
              className="text-sm text-red-700 dark:text-red-400 py-1"
            >
              <span className="font-mono">
                [{alert.severity.toUpperCase()}]
              </span>{" "}
              {alert.name}: {alert.value} (limite: {alert.threshold})
            </div>
          ))}
        </div>
      )}

      {/* System Resources */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="CPU"
          value={`${sys?.cpu?.percent?.toFixed(1) || 0}%`}
          subtitle={`Processo: ${sys?.process?.cpu_percent?.toFixed(1) || 0}%`}
          icon={<Cpu className="w-5 h-5" />}
          color={sys?.cpu?.percent && sys.cpu.percent > 80 ? "red" : "blue"}
        />
        <MetricCard
          title="Memória"
          value={`${sys?.memory?.percent?.toFixed(1) || 0}%`}
          subtitle={`${sys?.memory?.used_mb?.toFixed(0) || 0} / ${sys?.memory?.total_mb?.toFixed(0) || 0} MB`}
          icon={<Server className="w-5 h-5" />}
          color={
            sys?.memory?.percent && sys.memory.percent > 85 ? "red" : "green"
          }
        />
        <MetricCard
          title="Disco"
          value={`${sys?.disk?.percent?.toFixed(1) || 0}%`}
          subtitle={`${sys?.disk?.used_gb?.toFixed(1) || 0} / ${sys?.disk?.total_gb?.toFixed(1) || 0} GB`}
          icon={<HardDrive className="w-5 h-5" />}
        />
        <MetricCard
          title="Conexões Ativas"
          value={sys?.active_connections || 0}
          subtitle={`Threads: ${sys?.process?.threads || 0}`}
          icon={<Wifi className="w-5 h-5" />}
        />
      </div>

      {/* Resource Bars */}
      {sys && (
        <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-gray-700">
          <h3 className="font-semibold mb-4 text-gray-900 dark:text-white">
            Uso de Recursos
          </h3>
          <ProgressBar value={sys.cpu?.percent || 0} label="CPU" color="blue" />
          <ProgressBar
            value={sys.memory?.percent || 0}
            label="Memória RAM"
            color="green"
          />
          <ProgressBar
            value={sys.disk?.percent || 0}
            label="Disco"
            color="purple"
          />
        </div>
      )}

      {/* Request Metrics + Task Queue */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* HTTP Requests */}
        {requests && (
          <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-gray-700">
            <h3 className="font-semibold mb-4 text-gray-900 dark:text-white flex items-center gap-2">
              <BarChart3 className="w-5 h-5 text-blue-500" />
              HTTP Requests
            </h3>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <div className="text-2xl font-bold">
                  {requests.total_requests.toLocaleString()}
                </div>
                <div className="text-xs text-gray-500">Total</div>
              </div>
              <div>
                <div className="text-2xl font-bold text-red-500">
                  {requests.error_rate_percent}%
                </div>
                <div className="text-xs text-gray-500">Taxa de Erro</div>
              </div>
              <div>
                <div className="text-lg font-mono">
                  {requests.response_times.avg_ms}ms
                </div>
                <div className="text-xs text-gray-500">Latência Média</div>
              </div>
              <div>
                <div className="text-lg font-mono">
                  {requests.response_times.p95_ms}ms
                </div>
                <div className="text-xs text-gray-500">P95</div>
              </div>
            </div>
          </div>
        )}

        {/* Task Queue */}
        {tq && (
          <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-gray-700">
            <h3 className="font-semibold mb-4 text-gray-900 dark:text-white flex items-center gap-2">
              <Zap className="w-5 h-5 text-yellow-500" />
              Fila de Tarefas
            </h3>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <div className="text-2xl font-bold">{tq.active_tasks}</div>
                <div className="text-xs text-gray-500">Ativas</div>
              </div>
              <div>
                <div className="text-2xl font-bold">{tq.queue_size}</div>
                <div className="text-xs text-gray-500">Na Fila</div>
              </div>
              <div>
                <div className="text-lg font-mono">
                  {tq.total_completed.toLocaleString()}
                </div>
                <div className="text-xs text-gray-500">Completadas</div>
              </div>
              <div>
                <div className="text-lg font-mono text-red-500">
                  {tq.total_failed}
                </div>
                <div className="text-xs text-gray-500">Falharam</div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* DB Pool + Cache + WebSocket */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {pool && (
          <div className="bg-white dark:bg-gray-800 rounded-xl p-4 shadow-sm border border-gray-200 dark:border-gray-700">
            <h3 className="font-semibold mb-3 text-gray-900 dark:text-white flex items-center gap-2">
              <Database className="w-4 h-4 text-green-500" /> DB Pool
            </h3>
            <div className="space-y-1 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-500">Ativas</span>
                <span>{pool.active_connections}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Pico</span>
                <span>{pool.peak_connections}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Queries</span>
                <span>{pool.total_queries?.toLocaleString()}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Latência</span>
                <span>{pool.avg_query_time_ms}ms</span>
              </div>
            </div>
          </div>
        )}

        {cache && (
          <div className="bg-white dark:bg-gray-800 rounded-xl p-4 shadow-sm border border-gray-200 dark:border-gray-700">
            <h3 className="font-semibold mb-3 text-gray-900 dark:text-white flex items-center gap-2">
              <Zap className="w-4 h-4 text-purple-500" /> Cache
            </h3>
            <div className="space-y-1 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-500">L1 Hit Rate</span>
                <span>{cache.l1?.hit_rate_percent}%</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">L1 Size</span>
                <span>{cache.l1?.size}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">L2 (Redis)</span>
                <span>{cache.l2?.available ? "✓" : "✗"}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">L2 Hit Rate</span>
                <span>{cache.l2?.hit_rate_percent}%</span>
              </div>
            </div>
          </div>
        )}

        {ws && (
          <div className="bg-white dark:bg-gray-800 rounded-xl p-4 shadow-sm border border-gray-200 dark:border-gray-700">
            <h3 className="font-semibold mb-3 text-gray-900 dark:text-white flex items-center gap-2">
              <Wifi className="w-4 h-4 text-blue-500" /> WebSocket
            </h3>
            <div className="space-y-1 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-500">Conexões</span>
                <span>{ws.active_connections}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Usuários</span>
                <span>{ws.active_users}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Msgs Enviadas</span>
                <span>{ws.total_messages_sent?.toLocaleString()}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">Pico</span>
                <span>{ws.peak_connections}</span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Top Endpoints */}
      {topEndpoints.length > 0 && (
        <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-sm border border-gray-200 dark:border-gray-700">
          <h3 className="font-semibold mb-4 text-gray-900 dark:text-white flex items-center gap-2">
            <Clock className="w-5 h-5 text-indigo-500" />
            Top Endpoints (por volume)
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200 dark:border-gray-700">
                  <th className="text-left py-2 text-gray-500">Endpoint</th>
                  <th className="text-right py-2 text-gray-500">Requests</th>
                  <th className="text-right py-2 text-gray-500">Erros</th>
                  <th className="text-right py-2 text-gray-500">
                    Latência Média
                  </th>
                </tr>
              </thead>
              <tbody>
                {topEndpoints.slice(0, 10).map((ep, i) => (
                  <tr
                    key={i}
                    className="border-b border-gray-100 dark:border-gray-700/50"
                  >
                    <td className="py-2 font-mono text-xs">{ep.endpoint}</td>
                    <td className="py-2 text-right">
                      {ep.count.toLocaleString()}
                    </td>
                    <td
                      className={`py-2 text-right ${ep.errors > 0 ? "text-red-500" : ""}`}
                    >
                      {ep.errors}
                    </td>
                    <td className="py-2 text-right font-mono">{ep.avg_ms}ms</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};

export default SystemMonitorPage;
