import React, { useState } from 'react';
import {
  AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, RadarChart, Radar, PolarGrid,
  PolarAngleAxis, PolarRadiusAxis
} from 'recharts';
import { TrendingUp, MapPin, Star, Zap } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import api from '../../../services/api';

type Period = 'daily' | 'weekly' | 'monthly';

const fmt = (n: number) => `₹${n.toLocaleString('en-IN')}`;


const BusinessIntelligence: React.FC = () => {
  const [period, setPeriod] = useState<Period>('daily');

  const { data: pulseData } = useQuery({
    queryKey: ['earnings-pulse', period],
    queryFn: () => api.get(`/api/provider/analytics/earnings-pulse?period=${period}`).then(r => r.data),
    retry: 1,
  });

  const { data: heatmapData } = useQuery({
    queryKey: ['demand-heatmap'],
    queryFn: () => api.get('/api/provider/territory/demand-heatmap').then(r => r.data),
    retry: 1,
  });

  const { data: advancedData } = useQuery({
    queryKey: ['advanced-analytics'],
    queryFn: () => api.get('/api/provider/analytics/advanced').then(r => r.data),
    retry: 1,
  });

  const chartData = (pulseData?.data || []).slice().reverse();
  const xKey = 'date';

  const totalEarnings = chartData.reduce((s: number, d: any) => s + (d.revenue ?? 0), 0);
  const totalJobs     = chartData.reduce((s: number, d: any) => s + (d.jobs ?? 0), 0);
  const avgJob        = totalJobs ? Math.round(totalEarnings / totalJobs) : 0;
  const profitPerHour = pulseData?.overall?.avg_profit_per_hour ?? 0;
  const marketPos     = pulseData?.overall ? 'Top Provider' : 'N/A';

  const heatmapZones = advancedData?.heatmap_zones || [];
  const peakHoursData = advancedData?.peak_hours || [];
  const radarData = advancedData?.radar_data || [];
  const routeEfficiencyData = advancedData?.route_efficiency_data || [];
  const competitorRankData = advancedData?.competitor_rank || [];

  const heatmapPoints: any[] = heatmapData?.heatmap || [];

  return (
    <div className="space-y-6">
      {/* KPI Row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label:'Total Revenue',    value: fmt(totalEarnings),  sub:`${period} period`,  color:'text-green-600',  bg:'bg-green-50',  icon:'💰' },
          { label:'Total Jobs',       value: totalJobs,           sub:`avg ${fmt(avgJob)}/job`, color:'text-blue-600', bg:'bg-blue-50',   icon:'🔧' },
          { label:'Profit / Hour',    value: fmt(profitPerHour),  sub:'blended rate',      color:'text-purple-600', bg:'bg-purple-50', icon:'⏱️' },
          { label:'Market Rank',      value: marketPos,           sub:'Based on earnings', color:'text-teal-600',   bg:'bg-teal-50',   icon:'🏆' },
        ].map(s => (
          <div key={s.label} className="bg-white rounded-2xl p-5 shadow-sm border border-gray-100 hover:shadow-md hover:-translate-y-0.5 transition-all duration-200">
            <div className={`w-10 h-10 ${s.bg} rounded-xl flex items-center justify-center text-lg mb-3`}>{s.icon}</div>
            <p className="text-2xl font-black text-gray-900">{s.value}</p>
            <p className="text-sm font-bold text-gray-500 mt-0.5">{s.label}</p>
            <p className="text-xs text-gray-400 mt-0.5">{s.sub}</p>
          </div>
        ))}
      </div>

      {/* Earnings Chart */}
      <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
        <div className="flex items-center justify-between mb-5">
          <div>
            <h3 className="font-black text-gray-900 text-lg">Earnings Analytics</h3>
            <p className="text-sm text-gray-500">Revenue · Jobs · Profit trend</p>
          </div>
          <div className="flex gap-1 bg-gray-100 rounded-xl p-1">
            {(['daily','weekly','monthly'] as Period[]).map(p => (
              <button key={p} onClick={() => setPeriod(p)}
                className={`px-4 py-1.5 rounded-lg text-xs font-black capitalize transition-all ${period === p ? 'bg-teal-600 text-white shadow' : 'text-gray-500 hover:text-gray-800'}`}>
                {p}
              </button>
            ))}
          </div>
        </div>
        <ResponsiveContainer width="100%" height={220}>
          <AreaChart data={chartData}>
            <defs>
              <linearGradient id="biGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%"  stopColor="#0D7A7F" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#0D7A7F" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#F0F4F8" />
            <XAxis dataKey={xKey} tick={{ fontSize: 11, fontWeight: 700 }} />
            <YAxis tick={{ fontSize: 11 }} tickFormatter={v => `₹${(v/1000).toFixed(0)}k`} />
            <Tooltip formatter={(v: any) => [fmt(v as number), 'Earnings']} />
            <Area type="monotone" dataKey="revenue" stroke="#0D7A7F" strokeWidth={2.5} fill="url(#biGrad)" />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        {/* Peak Hours */}
        <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
          <div className="flex items-center gap-2 mb-5">
            <Zap size={18} className="text-yellow-500" />
            <h3 className="font-black text-gray-900 text-lg">Peak Hours Analysis</h3>
          </div>
          <p className="text-xs text-gray-400 mb-4 bg-yellow-50 text-yellow-700 px-3 py-2 rounded-xl font-bold">
            🤖 AI Insight: Best booking windows — 10 AM and 4–6 PM. Avoid 7–9 PM (low conversion).
          </p>
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={peakHoursData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#F0F4F8" />
              <XAxis dataKey="hour" tick={{ fontSize: 10, fontWeight: 700 }} />
              <YAxis tick={{ fontSize: 10 }} />
              <Tooltip />
              <Bar dataKey="requests" fill="#0D7A7F" radius={[6,6,0,0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Route Efficiency Radar */}
        <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
          <div className="flex items-center gap-2 mb-4">
            <MapPin size={18} className="text-blue-500" />
            <h3 className="font-black text-gray-900 text-lg">Route Efficiency Score</h3>
          </div>
          <ResponsiveContainer width="100%" height={200}>
            <RadarChart data={radarData}>
              <PolarGrid stroke="#E2E8F0" />
              <PolarAngleAxis dataKey="subject" tick={{ fontSize: 11, fontWeight: 700 }} />
              <PolarRadiusAxis domain={[0,100]} tick={{ fontSize: 9 }} />
              <Radar dataKey="score" stroke="#0D7A7F" fill="#0D7A7F" fillOpacity={0.2} strokeWidth={2} />
              <Tooltip />
            </RadarChart>
          </ResponsiveContainer>
          <div className="mt-2 space-y-1.5">
            {routeEfficiencyData.map(r => (
              <div key={r.zone} className="flex items-center justify-between text-xs">
                <span className="text-gray-500 font-medium">{r.zone}</span>
                <div className="flex items-center gap-2">
                  <div className="w-24 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                    <div className="h-full rounded-full bg-teal-500" style={{ width:`${r.effScore}%` }} />
                  </div>
                  <span className="font-black text-gray-700 w-8">{r.effScore}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Competitor Rank + Demand Heatmap */}
      <div className="grid lg:grid-cols-2 gap-6">
        {/* Competitor Rank */}
        <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
          <div className="flex items-center gap-2 mb-4">
            <Star size={18} className="text-yellow-500" />
            <h3 className="font-black text-gray-900 text-lg">Local Market Position</h3>
          </div>
          <p className="text-xs text-gray-400 mb-4">Electricians in Bangalore ranked by performance</p>
          <div className="space-y-3">
            {competitorRankData.map((c, i) => {
              const isYou = c.name === 'You';
              return (
                <div key={c.name} className={`flex items-center justify-between p-3 rounded-xl transition-colors ${isYou ? 'bg-teal-50 border-2 border-teal-400' : 'bg-gray-50 hover:bg-gray-100'}`}>
                  <div className="flex items-center gap-3">
                    <span className={`w-8 h-8 rounded-full flex items-center justify-center font-black text-sm ${i===0?'bg-yellow-400 text-white':i===1?'bg-gray-300 text-gray-700':isYou?'bg-teal-600 text-white':'bg-gray-200 text-gray-600'}`}>
                      {i+1}
                    </span>
                    <div>
                      <p className={`font-bold text-sm ${isYou?'text-teal-700':'text-gray-800'}`}>{c.name}</p>
                      <p className="text-xs text-gray-400">{c.jobs} jobs · ₹{c.price}/hr</p>
                    </div>
                  </div>
                  <span className={`font-black text-sm ${c.rating>=4.8?'text-green-600':c.rating>=4.5?'text-yellow-600':'text-red-500'}`}>{c.rating} ★</span>
                </div>
              );
            })}
          </div>
          <div className="mt-4 p-3 bg-green-50 rounded-xl border border-green-200">
            <p className="text-xs font-bold text-green-700">💡 Tip: Add 2 more job categories to climb to #1 within 60 days.</p>
          </div>
        </div>

        {/* Demand Heatmap */}
        <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
          <div className="flex items-center gap-2 mb-4">
            <TrendingUp size={18} className="text-red-500" />
            <h3 className="font-black text-gray-900 text-lg">Demand Heatmap</h3>
          </div>
          <p className="text-xs text-gray-400 mb-4">Service request concentration in your area</p>
          <div className="space-y-2.5">
            {heatmapZones.map(z => (
              <div key={z.zone} className="flex items-center gap-3">
                <div className="w-3 h-3 rounded-full shrink-0" style={{ backgroundColor: z.color }} />
                <div className="flex-1">
                  <div className="flex items-center justify-between mb-0.5">
                    <span className="text-xs font-bold text-gray-700">{z.zone}</span>
                    <span className="text-xs font-black text-gray-500">{z.demand}%</span>
                  </div>
                  <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                    <div className="h-full rounded-full transition-all" style={{ width:`${z.demand}%`, backgroundColor: z.color }} />
                  </div>
                </div>
              </div>
            ))}
          </div>
          <div className="mt-4 flex items-center gap-3 flex-wrap text-xs">
            {[['#ef4444','Crisis (80%+)'],['#f97316','High (60-79%)'],['#eab308','Medium (40-59%)'],['#22c55e','Low (<40%)']].map(([c,l]) => (
              <div key={l} className="flex items-center gap-1.5">
                <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: c }} />
                <span className="text-gray-500">{l}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default BusinessIntelligence;
