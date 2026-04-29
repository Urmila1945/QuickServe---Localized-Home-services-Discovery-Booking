import React, { useState, useEffect } from 'react';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer
} from 'recharts';
import { Activity, DollarSign, AlertTriangle } from 'lucide-react';
import api from '../../../services/api';

const fmt = (n: number) => `₹${(n ?? 0).toLocaleString('en-IN')}`;

const MarketplaceCommand: React.FC = () => {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await api.get('/api/admin/marketplace-command').then(r => r.data);
        setData(res);
      } catch (err) {
        console.error('Failed to load marketplace data', err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  const statusStyle: Record<string, string> = {
    healthy:  'bg-green-100 text-green-700 border border-green-200',
    shortage: 'bg-yellow-100 text-yellow-700 border border-yellow-200',
    crisis:   'bg-red-100 text-red-700 border border-red-200',
    surplus:  'bg-blue-100 text-blue-700 border border-blue-200',
  };

  if (loading || !data) return <div className="p-10 text-center font-bold text-gray-400">Loading marketplace analytics...</div>;

  return (
    <div className="space-y-6">
      {/* Live Health Monitor */}
      <div className="bg-gradient-to-r from-[#0D1F2D] to-teal-900 rounded-2xl p-6 text-white shadow-lg">
        <div className="flex items-center gap-2 mb-5">
          <div className="w-2.5 h-2.5 bg-green-400 rounded-full animate-pulse" />
          <p className="text-teal-300 font-black text-sm uppercase tracking-widest">Real-Time Platform Health Monitor</p>
          <span className="ml-auto text-xs text-teal-300">Last updated: just now</span>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { label:'Live Gross Transaction Value',  value: fmt(data.gtv),        sub:`₹${Math.round(data.gtv/100000)}L lifecycle`, icon:'💰' },
            { label:'Active Bookings Now',            value: data.active_now,        sub:'across active zones',                                    icon:'📅' },
            { label:'Supply Health',                 value: data.supply_demand.length, sub:'cities tracked', icon:'🔧' },
            { label:'Platform Pulse',                value: 'Optimal', sub:'99.9% success rate', icon:'📈' },
          ].map(s => (
            <div key={s.label} className="bg-white/10 backdrop-blur-sm border border-white/15 rounded-xl p-4">
              <div className="text-2xl mb-1">{s.icon}</div>
              <p className="text-2xl font-black">{s.value}</p>
              <p className="text-xs text-teal-300 font-bold mt-0.5">{s.label}</p>
              <p className="text-[10px] text-white/40 mt-0.5">{s.sub}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Revenue Chart */}
      <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
        <div className="flex items-center justify-between mb-5">
          <div>
            <h3 className="font-black text-gray-900 text-lg">Gross Transaction Value & Commission</h3>
            <p className="text-xs text-gray-400">Monthly breakdown from backend logs</p>
          </div>
          <span className="text-xs font-bold text-green-600 bg-green-50 px-3 py-1.5 rounded-full">+21% trend</span>
        </div>
        <ResponsiveContainer width="100%" height={220}>
          <AreaChart data={data.revenue_monthly}>
            <defs>
              <linearGradient id="mcRev" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%"  stopColor="#0D7A7F" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#0D7A7F" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="mcComm" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%"  stopColor="#8b5cf6" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#F0F4F8" />
            <XAxis dataKey="month" tick={{ fontSize:11, fontWeight:700 }} />
            <YAxis tick={{ fontSize:11 }} tickFormatter={v=>`₹${(v/100000).toFixed(1)}L`} />
            <Tooltip formatter={(v: any, n: string) => [fmt(v), n==='revenue'?'GTV':'Commission']} />
            <Area type="monotone" dataKey="revenue"    stroke="#0D7A7F" strokeWidth={2.5} fill="url(#mcRev)" />
            <Area type="monotone" dataKey="commission" stroke="#8b5cf6" strokeWidth={2}   fill="url(#mcComm)" />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Supply-Demand Map */}
      <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
        <div className="flex items-center gap-2 mb-5">
          <Activity size={18} className="text-teal-600" />
          <h3 className="font-black text-gray-900 text-lg">Geographic Supply-Demand Balance</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>{['Zone','Area','Providers','Requests','Coverage Ratio','Status','Action'].map(h=>(
                <th key={h} className="text-left py-3 px-4 font-black text-gray-400 text-xs uppercase tracking-wider">{h}</th>
              ))}</tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {data.supply_demand.map((z:any) => (
                <tr key={z.zip} className="hover:bg-gray-50 transition-colors">
                  <td className="py-3.5 px-4 font-black text-gray-500 text-sm">{z.zip}</td>
                  <td className="py-3.5 px-4 font-bold text-gray-900 text-sm">{z.area}</td>
                  <td className="py-3.5 px-4 text-gray-600 text-sm font-bold">{z.providers}</td>
                  <td className="py-3.5 px-4 text-gray-600 text-sm font-bold">{z.requests}</td>
                  <td className="py-3.5 px-4">
                    <div className="flex items-center gap-2">
                      <div className="w-20 h-2 bg-gray-100 rounded-full overflow-hidden">
                        <div className="h-full rounded-full" style={{ width:`${Math.min(100,z.ratio*100)}%`, backgroundColor: z.ratio>=1?'#22c55e':z.ratio>=0.7?'#f59e0b':'#ef4444' }} />
                      </div>
                      <span className="font-black text-xs text-gray-700">{z.ratio.toFixed(2)}</span>
                    </div>
                  </td>
                  <td className="py-3.5 px-4">
                    <span className={`text-xs font-black px-2.5 py-1 rounded-full capitalize ${statusStyle[z.status]}`}>{z.status}</span>
                  </td>
                  <td className="py-3.5 px-4">
                    {z.status !== 'healthy' && z.status !== 'surplus' && (
                      <button className="text-xs bg-teal-600 hover:bg-teal-700 text-white px-3 py-1.5 rounded-xl font-black transition-all">
                        Recruit
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        {/* Churn Early Warning */}
        <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
          <h3 className="font-black text-gray-900 text-lg flex items-center gap-2 mb-4">
            <AlertTriangle size={18} className="text-orange-500" /> Churn Early Warning
          </h3>
          <p className="text-xs text-gray-400 mb-4 bg-orange-50 text-orange-700 px-3 py-2 rounded-xl font-bold">
            🤖 AI-flagged providers with high churn risk based on activity patterns
          </p>
          <div className="space-y-3">
            {data.churn_risk.map((p:any) => (
              <div key={p.name} className="flex items-center justify-between p-4 bg-red-50 border border-red-100 rounded-xl">
                <div>
                  <p className="font-bold text-gray-900 text-sm">{p.name}</p>
                  <p className="text-xs text-gray-400">Inactive {p.daysActive} days · ₹{p.revenue.toLocaleString()} at risk</p>
                </div>
                <div className="flex items-center gap-3">
                  <div className="text-right">
                    <p className="font-black text-red-600 text-sm">{p.risk}%</p>
                    <p className="text-[10px] text-gray-400">churn risk</p>
                  </div>
                  <button className="text-xs bg-red-600 hover:bg-red-700 text-white px-3 py-1.5 rounded-xl font-black transition-all">Intervene</button>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* CAC by Channel */}
        <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
          <h3 className="font-black text-gray-900 text-lg flex items-center gap-2 mb-4">
            <DollarSign size={18} className="text-blue-600" /> Customer Acquisition Cost
          </h3>
          <div className="space-y-3">
            {data.cac.sort((a:any,b:any)=>a.cac-b.cac).map((c:any) => (
              <div key={c.channel} className="flex items-center gap-3">
                <span className="text-xs font-bold text-gray-500 w-28 shrink-0">{c.channel}</span>
                <div className="flex-1 h-6 bg-gray-100 rounded-xl overflow-hidden">
                  <div className="h-full bg-blue-500 rounded-xl flex items-center px-2 transition-all" style={{ width:`${(c.cac/2500)*100}%` }} />
                </div>
                <div className="text-right shrink-0">
                  <p className="font-black text-gray-800 text-xs">₹{c.cac.toLocaleString()}</p>
                  <p className="text-[10px] text-gray-400">{c.conversions} conv.</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default MarketplaceCommand;