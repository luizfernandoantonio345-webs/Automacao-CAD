import React, { useState } from 'react';
import Swal from 'sweetalert2';
import axios from 'axios';
import { LICENSING_BASE_URL } from '../services/endpoints';

const licensingApi = axios.create({ baseURL: LICENSING_BASE_URL, timeout: 10000 });

export default function License({ onSuccess }: { onSuccess: () => void }) {
  const [licenseKey, setLicenseKey] = useState('');
  const [machineId, setMachineId] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleActivate = async () => {
    const normalizedLicenseKey = licenseKey.trim().toUpperCase();
    const normalizedMachineId = machineId.trim();
    if (!/^[A-Z0-9-]{6,64}$/.test(normalizedLicenseKey)) {
      Swal.fire('Erro', 'Formato de chave de licenca invalido', 'error');
      return;
    }
    if (!/^[A-Za-z0-9_.:-]{3,128}$/.test(normalizedMachineId)) {
      Swal.fire('Erro', 'Formato de machine ID invalido', 'error');
      return;
    }

    setLoading(true);
    setError('');
    try {
      const response = await licensingApi.post('/activate', {
        license_key: normalizedLicenseKey,
        machine_id: normalizedMachineId,
      });
      if (response.data.status === 'active') {
        Swal.fire('Sucesso', 'Licenca ativada', 'success');
        window.localStorage.setItem(
          'license',
          JSON.stringify({ licenseKey: normalizedLicenseKey, machineId: normalizedMachineId })
        );
        onSuccess();
      } else {
        const msg = response.data?.detail || 'Resposta invalida do servidor de licenca';
        setError(msg);
        Swal.fire('Erro', msg, 'error');
      }
    } catch (err: any) {
      const msg = err?.response?.data?.detail || 'Falha ao ativar licenca';
      setError(msg);
      Swal.fire('Erro', msg, 'error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4">
      <div className="relative w-full max-w-md bg-slate-900 border border-slate-700 rounded-xl shadow-2xl p-8">
        <div className="text-center mb-6">
          <h2 className="text-2xl font-bold text-slate-100">Ativação de Licença</h2>
          <p className="text-sm text-slate-400">Conecte seu dispositivo e ative o acesso.</p>
        </div>

        <div className="space-y-4">
          <input
            value={licenseKey}
            onChange={(e) => setLicenseKey(e.target.value)}
            placeholder="Chave de licença"
            className="w-full bg-slate-800 border border-slate-700 rounded-lg p-3 text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition"
            maxLength={64}
          />

          <input
            value={machineId}
            onChange={(e) => setMachineId(e.target.value)}
            placeholder="Machine ID"
            className="w-full bg-slate-800 border border-slate-700 rounded-lg p-3 text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition"
            maxLength={128}
          />

          {error && (
            <div className="text-red-300 bg-red-950/20 border border-red-900 rounded-lg p-2 text-sm">{error}</div>
          )}

          <button
            onClick={handleActivate}
            disabled={loading}
            className="w-full bg-indigo-600 hover:bg-indigo-500 disabled:opacity-60 text-white rounded-lg p-3 font-semibold transition"
          >
            {loading ? 'Ativando...' : 'Ativar'}
          </button>
        </div>

        <div className="mt-6 text-xs text-slate-400 text-center">
          Depois de ativar, o sistema redirecionará para login automaticamente.
        </div>
      </div>
    </div>
  );
}
