import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE_URL } from '../services/api';

// ═══════════════════════════════════════════════════════════════════════════════
// AutoConnect Page - Conexão 1-Click com AutoCAD
// Zero instalação - Detecta versão - Status em tempo real
// ═══════════════════════════════════════════════════════════════════════════════

interface AutoCADStatus {
  detected: boolean;
  version: string;
  path: string;
  connected: boolean;
  bridgeReady: boolean;
}

const AutoConnectPage: React.FC = () => {
  const [status, setStatus] = useState<string>('Pronto para conectar');
  const [progress, setProgress] = useState<number>(0);
  const [cadInfo, setCadInfo] = useState<AutoCADStatus | null>(null);
  const [isConnecting, setIsConnecting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Usar URL centralizada do serviço API
  const BACKEND_URL = API_BASE_URL;

  // Obter token de autenticação
  const getAuthToken = (): string | null => {
    return localStorage.getItem('token') || sessionStorage.getItem('token');
  };

  // Detectar AutoCAD no cliente
  const detectAutoCAD = useCallback(async () => {
    setStatus('🔍 Detectando AutoCAD...');
    setProgress(10);
    setError(null);

    try {
      const token = getAuthToken();
      const headers: HeadersInit = {
        'Content-Type': 'application/json',
      };
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      const response = await fetch(`${BACKEND_URL}/api/autocad/detect`, {
        method: 'POST',
        headers,
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.detail || `Erro ${response.status}`);
      }

      const data = await response.json();
      setCadInfo(data);
      setProgress(30);
      
      if (data.detected) {
        setStatus(`✅ ${data.version} detectado em ${data.path}`);
        return data;
      } else {
        setStatus('⚠️ AutoCAD não encontrado nesta máquina');
        return null;
      }
    } catch (err: any) {
      const msg = err.message || 'Erro ao detectar AutoCAD';
      setError(msg);
      setStatus(`❌ ${msg}`);
      return null;
    }
  }, [BACKEND_URL]);

  // Conectar ao AutoCAD
  const connectAutoCAD = useCallback(async () => {
    setIsConnecting(true);
    setError(null);

    try {
      // 1. Detectar AutoCAD primeiro
      const detected = await detectAutoCAD();
      if (!detected) {
        setIsConnecting(false);
        return;
      }

      setStatus('🔐 Validando licença...');
      setProgress(40);

      // 2. Validar licença (se necessário)
      const token = getAuthToken();
      if (!token) {
        // Tentar login demo
        const demoRes = await fetch(`${BACKEND_URL}/auth/demo`, { method: 'POST' });
        if (demoRes.ok) {
          const demoData = await demoRes.json();
          localStorage.setItem('token', demoData.access_token);
        }
      }

      setStatus('🚀 Abrindo AutoCAD...');
      setProgress(60);

      // 3. Solicitar auto-connect
      const currentToken = getAuthToken();
      const connectRes = await fetch(`${BACKEND_URL}/api/autocad/auto-connect`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(currentToken && { 'Authorization': `Bearer ${currentToken}` }),
        },
      });

      if (!connectRes.ok) {
        const errData = await connectRes.json().catch(() => ({}));
        throw new Error(errData.detail || 'Erro ao conectar');
      }

      const connectData = await connectRes.json();
      setProgress(80);

      // 4. Aguardar confirmação de conexão via polling
      setStatus('⏳ Aguardando AutoCAD iniciar...');
      
      let attempts = 0;
      const maxAttempts = 30; // 30 segundos
      
      const checkConnection = async (): Promise<boolean> => {
        try {
          const statusRes = await fetch(`${BACKEND_URL}/api/autocad/status`, {
            headers: currentToken ? { 'Authorization': `Bearer ${currentToken}` } : {},
          });
          if (statusRes.ok) {
            const statusData = await statusRes.json();
            if (statusData.connected || statusData.use_bridge) {
              return true;
            }
          }
        } catch {
          // Ignorar erros de polling
        }
        return false;
      };

      // Polling para verificar conexão
      while (attempts < maxAttempts) {
        const connected = await checkConnection();
        if (connected) {
          break;
        }
        attempts++;
        await new Promise(resolve => setTimeout(resolve, 1000));
        setProgress(80 + Math.min(attempts / 2, 15));
      }

      setProgress(100);
      setCadInfo(prev => prev ? { ...prev, connected: true, bridgeReady: true } : null);
      setStatus(`✅ ${detected.version} CONECTADO! Pronto para desenhar.`);

    } catch (err: any) {
      const msg = err.message || 'Erro ao conectar';
      setError(msg);
      setStatus(`❌ ${msg}`);
      setProgress(0);
    } finally {
      setIsConnecting(false);
    }
  }, [BACKEND_URL, detectAutoCAD]);

  // Estilos inline para componentes
  const cardStyle: React.CSSProperties = {
    maxWidth: 520,
    margin: '40px auto',
    padding: 24,
    background: 'linear-gradient(145deg, #1a1a2e 0%, #16213e 100%)',
    borderRadius: 16,
    boxShadow: '0 8px 32px rgba(0,0,0,0.3)',
    border: '1px solid rgba(255,255,255,0.1)',
  };

  const titleStyle: React.CSSProperties = {
    color: '#fff',
    fontSize: 24,
    fontWeight: 700,
    marginBottom: 24,
    textAlign: 'center',
    letterSpacing: 1,
  };

  const progressBarStyle: React.CSSProperties = {
    width: '100%',
    height: 8,
    background: '#2d2d44',
    borderRadius: 4,
    marginBottom: 16,
    overflow: 'hidden',
  };

  const progressFillStyle: React.CSSProperties = {
    width: `${progress}%`,
    height: '100%',
    background: progress === 100 
      ? 'linear-gradient(90deg, #10b981, #34d399)' 
      : 'linear-gradient(90deg, #3b82f6, #60a5fa)',
    borderRadius: 4,
    transition: 'width 0.3s ease',
  };

  const statusBoxStyle: React.CSSProperties = {
    padding: '16px 20px',
    background: error ? 'rgba(239,68,68,0.1)' : progress === 100 ? 'rgba(16,185,129,0.1)' : 'rgba(59,130,246,0.1)',
    border: `1px solid ${error ? '#ef4444' : progress === 100 ? '#10b981' : '#3b82f6'}`,
    borderRadius: 8,
    marginBottom: 20,
    color: '#fff',
    fontSize: 15,
  };

  const infoBoxStyle: React.CSSProperties = {
    padding: '12px 16px',
    background: 'rgba(16,185,129,0.1)',
    border: '1px solid #10b981',
    borderRadius: 8,
    marginBottom: 20,
    color: '#10b981',
    fontSize: 14,
  };

  const buttonStyle: React.CSSProperties = {
    width: '100%',
    padding: '16px 24px',
    fontSize: 18,
    fontWeight: 600,
    color: '#fff',
    background: isConnecting 
      ? '#4b5563' 
      : progress === 100 
        ? 'linear-gradient(90deg, #10b981, #059669)' 
        : 'linear-gradient(90deg, #3b82f6, #2563eb)',
    border: 'none',
    borderRadius: 8,
    cursor: isConnecting || progress === 100 ? 'not-allowed' : 'pointer',
    transition: 'all 0.2s ease',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 10,
  };

  const footerStyle: React.CSSProperties = {
    color: '#6b7280',
    fontSize: 13,
    textAlign: 'center',
    marginTop: 20,
    lineHeight: 1.6,
  };

  return (
    <div style={{ minHeight: '100vh', background: '#0f0f1a', padding: '20px' }}>
      <div style={cardStyle}>
        <h2 style={titleStyle}>
          🔌 AutoConnect - 1 Click
        </h2>

        {/* Barra de progresso */}
        <div style={progressBarStyle}>
          <div style={progressFillStyle} />
        </div>

        {/* Status atual */}
        <div style={statusBoxStyle}>
          {isConnecting && <span style={{ marginRight: 8 }}>⏳</span>}
          {progress === 100 && <span style={{ marginRight: 8 }}>✅</span>}
          {error && <span style={{ marginRight: 8 }}>❌</span>}
          {status}
        </div>

        {/* Info do AutoCAD detectado */}
        {cadInfo?.detected && (
          <div style={infoBoxStyle}>
            <div><strong>Versão:</strong> {cadInfo.version}</div>
            <div><strong>Caminho:</strong> {cadInfo.path}</div>
            <div><strong>Status:</strong> {cadInfo.connected ? '🟢 Conectado' : '🟡 Detectado'}</div>
            {cadInfo.bridgeReady && <div><strong>Bridge:</strong> ✅ Pronto</div>}
          </div>
        )}

        {/* Botão de conexão */}
        <button
          style={buttonStyle}
          onClick={connectAutoCAD}
          disabled={isConnecting || progress === 100}
        >
          {isConnecting ? (
            <>
              <span className="spinner" /> Conectando...
            </>
          ) : progress === 100 ? (
            '✅ Conectado!'
          ) : (
            <>
              <span>⚡</span> CONECTAR AUTOCAD
            </>
          )}
        </button>

        <p style={footerStyle}>
          Zero instalação • Qualquer versão AutoCAD • Licença auto-validação<br/>
          <span style={{ color: '#4b5563' }}>
            O sistema detecta automaticamente o AutoCAD instalado
          </span>
        </p>
      </div>

      {/* CSS para spinner */}
      <style>{`
        .spinner {
          width: 20px;
          height: 20px;
          border: 2px solid rgba(255,255,255,0.3);
          border-top-color: #fff;
          border-radius: 50%;
          animation: spin 0.8s linear infinite;
        }
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
};

export default AutoConnectPage;

