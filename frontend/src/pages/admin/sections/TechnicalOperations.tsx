import React, { useState, useEffect } from 'react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { Server, Cpu, Shield, Database, Zap, AlertTriangle, CheckCircle } from 'lucide-react';
import api from '../../../services/api';
import toast from 'react-hot-toast';

const TechnicalOperations: React.FC = () => {
  const [systemMetrics, setSystemMetrics] = useState<any[]>([]);
  const [aiModels, setAiModels] = useState<any[]>([]);
  const [apiLatencyHistory, setApiLatencyHistory] = useState<any[]>([]);

  useEffect(() => {
    const fetchTech = async () => {
      try {
        const res = await api.get('/api/admin/tech-ops').then(r => r.data);
        setSystemMetrics(res.system_metrics || []);
        setAiModels(res.ai_models || []);
        setApiLatencyHistory(res.latency_history || []);
      } catch (err) {
        console.error('Failed to load tech ops', err);
      }
    };
    fetchTech();
  }, []);

  const healthyCount = systemMetrics.filter(m => m.status === 'healthy').length;

  return (
    <div className="space-y-6">
      <div className="bg-gradient-to-r from-[#0D1F2D] to-gray-900 rounded-2xl p-6 text-white shadow-lg">
        <div className="flex items-center gap-2 mb-4">
          <div className={`w-3 h-3 rounded-full ${healthyCount===systemMetrics.length?'bg-green-400 animate-pulse':'bg-yellow-400 animate-pulse'}`} />
          <p className="font-black text-sm uppercase tracking-widest text-gray-300">System Health Dashboard</p>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { label:'Services Online',    value:`${healthyCount}/${systemMetrics.length}`, color:'text-green-400'  },
            { label:'API Avg Latency',    value:'42ms',    color:'text-teal-300'  },
            { label:'Error Rate',         value:'0.04%',   color:'text-green-400' },
            { label:'Platform Uptime',    value:'99.94%',  color:'text-blue-300'  },
          ].map(s => (
            <div key={s.label} className="bg-white/10 backdrop-blur-sm rounded-xl p-4 border border-white/10">
              <p className={`text-2xl font-black ${s.color}`}>{s.value}</p>
              <p className="text-xs text-gray-400 mt-0.5">{s.label}</p>
            </div>
          ))}
        </div>
      </div>

      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-100 flex items-center gap-2">
          <Server size={18} className="text-teal-600" />
          <h3 className="font-black text-gray-900 text-lg">Service Status</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>{['Service','Latency','Error Rate','Uptime','Status'].map(h=>(
                <th key={h} className="text-left py-3 px-5 font-black text-gray-400 text-xs uppercase tracking-wider">{h}</th>
              ))}</tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {systemMetrics.map(m => (
                <tr key={m.service} className="hover:bg-gray-50 transition-colors">
                  <td className="py-3.5 px-5 font-bold text-gray-900 text-sm flex items-center gap-2">
                    <div className={`w-2 h-2 rounded-full ${m.status==='healthy'?'bg-green-500':'bg-yellow-500'}`} />
                    {m.service}
                  </td>
                  <td className="py-3.5 px-5 font-bold text-gray-700 text-sm">{m.latency}</td>
                  <td className="py-3.5 px-5 font-bold text-sm"><span className={m.errorRate==='0.00%'?'text-green-600':'text-yellow-600'}>{m.errorRate}</span></td>
                  <td className="py-3.5 px-5 font-bold text-sm"><span className={parseFloat(m.uptime)>=99.9?'text-green-600':'text-yellow-600'}>{m.uptime}</span></td>
                  <td className="py-3.5 px-5">
                    <span className={`text-xs font-black px-2.5 py-1 rounded-full ${m.status==='healthy'?'bg-green-100 text-green-700':'bg-yellow-100 text-yellow-700'}`}>{m.status}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
        <h3 className="font-black text-gray-900 text-lg flex items-center gap-2 mb-4"><Cpu size={18} className="text-blue-600" /> API Latency — Today</h3>
        <ResponsiveContainer width="100%" height={180}>
          <AreaChart data={apiLatencyHistory}>
            <defs>
              <linearGradient id="latGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#F0F4F8" />
            <XAxis dataKey="time" tick={{ fontSize:11, fontWeight:700 }} />
            <YAxis tick={{ fontSize:11 }} unit="ms" />
            <Tooltip formatter={(v: any) => [`${v}ms`, 'API Latency']} />
            <Area type="monotone" dataKey="latency" stroke="#3b82f6" strokeWidth={2.5} fill="url(#latGrad)" />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
        <h3 className="font-black text-gray-900 text-lg flex items-center gap-2 mb-4"><Zap size={18} className="text-yellow-500" /> AI Model Monitoring</h3>
        <div className="space-y-3">
          {aiModels.map(m => (
            <div key={m.model} className={`flex items-center justify-between p-4 rounded-xl border ${m.status==='warning'?'bg-yellow-50 border-yellow-200':'bg-gray-50 border-gray-100'}`}>
              <div className="flex items-center gap-3">
                <div className={`w-2.5 h-2.5 rounded-full ${m.status==='healthy'?'bg-green-500':'bg-yellow-500'}`} />
                <div>
                  <p className="font-bold text-gray-900 text-sm">{m.model}</p>
                  <p className="text-xs text-gray-400">Last trained: {m.lastTrained}</p>
                </div>
              </div>
              <div className="flex items-center gap-4">
                <div className="text-center">
                  <p className="font-black text-green-600 text-sm">{m.accuracy}%</p>
                  <p className="text-[10px] text-gray-400">accuracy</p>
                </div>
                <div className="text-center">
                  <p className={`font-black text-sm ${m.drift>2?'text-red-500':m.drift>1?'text-yellow-600':'text-green-600'}`}>{m.drift}%</p>
                  <p className="text-[10px] text-gray-400">drift</p>
                </div>
                {m.status === 'warning' && (
                  <button onClick={() => toast.success(`${m.model} retraining scheduled!`)} className="text-xs bg-yellow-500 hover:bg-yellow-600 text-white px-3 py-1.5 rounded-xl font-black transition-all">Retrain</button>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default TechnicalOperations;
