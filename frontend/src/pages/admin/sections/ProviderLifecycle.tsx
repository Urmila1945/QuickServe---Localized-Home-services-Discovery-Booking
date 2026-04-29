import React, { useState, useEffect } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { Shield, CheckCircle, XCircle, Clock, TrendingUp, Star } from 'lucide-react';
import api, { dashboardAPI } from '../../../services/api';
import toast from 'react-hot-toast';

const tierColor: Record<string, string> = {
  Platinum: 'bg-purple-100 text-purple-700 border border-purple-200',
  Gold:     'bg-yellow-100 text-yellow-700 border border-yellow-200',
  Silver:   'bg-gray-200 text-gray-700 border border-gray-300',
  Bronze:   'bg-orange-100 text-orange-700 border border-orange-200',
};

const ProviderLifecycle: React.FC = () => {
  const [queue, setQueue] = useState<any[]>([]);
  const [tiers, setTiers] = useState<any[]>([]);
  const [funnel, setFunnel] = useState<any[]>([]);
  const [nps, setNps] = useState<any>(null);
  const [activeSection, setActiveSection] = useState<'verification'|'tiers'|'funnel'|'nps'>('verification');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadData = async () => {
      try {
        setLoading(true);
        // Load basic admin dash data
        const data = await dashboardAPI.getAdmin();
        setQueue(data?.all_providers?.filter((p: any) => !p.verified_by_admin && !p.suspended) || []);

        const resolvedTiers = data?.all_providers?.slice(0, 10).map((p: any) => ({
          id: p._id,
          name: p.full_name,
          tier: p.rating > 4.5 ? 'Platinum' : p.rating > 4.0 ? 'Gold' : 'Silver',
          rating: p.rating || 0,
          bookings: p.analytics?.completed_bookings || 0,
          earnings: p.analytics?.total_earnings || 0,
          churnRisk: Math.max(5, 20 - (p.analytics?.completion_rate || 70)),
        }));
        setTiers(resolvedTiers);

        // Load specific performance stats
        const perf = await api.get('/api/admin/performance-analytics').then(r => r.data);
        setFunnel(perf.onboarding_funnel || []);
        setNps(perf.nps || null);
      } catch (error) {
        console.error('Failed to load provider lifecycle data', error);
      } finally {
        setLoading(false);
      }
    };
    loadData();
  }, []);

  const approve = async (id: string) => {
    try {
      await api.post(`/api/admin/providers/${id}/verify`);
      setQueue(prev => prev.filter(v => (v.id || v._id) !== id));
      toast.success('Provider approved & notified!');
    } catch (err) {
      toast.error('Failed to approve');
    }
  };

  const reject = async (id: string) => {
    try {
      await api.post(`/api/admin/providers/${id}/suspend`, null, { params: { reason: 'Rejected during verification' } });
      setQueue(prev => prev.filter(v => (v.id || v._id) !== id));
      toast.error('Provider application rejected.');
    } catch (err) {
      toast.error('Request failed');
    }
  };

  const sections = [
    { key:'verification', label:'Verification Queue', icon:'📋' },
    { key:'tiers',        label:'Performance Tiers',  icon:'🏆' },
    { key:'funnel',       label:'Onboarding Funnel',  icon:'📊' },
    { key:'nps',          label:'NPS & Satisfaction', icon:'💬' },
  ] as const;

  if (loading) return <div className="p-10 text-center font-bold text-gray-400 text-sm">Loading lifecycle data...</div>;

  return (
    <div className="space-y-6">
      <div className="flex gap-2 bg-white rounded-2xl p-1.5 shadow-sm border border-gray-100 overflow-x-auto">
        {sections.map(s => (
          <button key={s.key} onClick={() => setActiveSection(s.key)}
            className={`flex items-center gap-1.5 px-4 py-2 rounded-xl font-bold text-sm whitespace-nowrap transition-all ${activeSection===s.key?'bg-teal-600 text-white shadow':'text-gray-500 hover:text-gray-800 hover:bg-gray-50'}`}>
            {s.icon} {s.label}
          </button>
        ))}
      </div>

      {activeSection === 'verification' && (
        <div className="space-y-4">
          <div className="grid grid-cols-3 gap-4">
            {[
              { label:'Pending Review',  value:queue.length,                          color:'text-yellow-600', bg:'bg-yellow-50' },
              { label:'Approved Today',  value:8,                                     color:'text-green-600',  bg:'bg-green-50'  },
              { label:'Avg Review Time', value:'4.2h',                                color:'text-blue-600',   bg:'bg-blue-50'   },
            ].map(s => (
              <div key={s.label} className={`${s.bg} rounded-2xl p-4 text-center`}>
                <p className={`text-2xl font-black ${s.color}`}>{s.value}</p>
                <p className="text-xs font-bold text-gray-500 mt-0.5">{s.label}</p>
              </div>
            ))}
          </div>

          {queue.length === 0 && (
            <div className="bg-green-50 border border-green-200 rounded-2xl p-8 text-center">
              <CheckCircle size={32} className="mx-auto mb-2 text-green-500" />
              <p className="font-black text-green-700">All applications reviewed!</p>
            </div>
          )}

          {queue.map(v => (
            <div key={v._id} className="bg-white rounded-2xl p-5 shadow-sm border border-gray-100">
              <div className="flex items-start justify-between flex-wrap gap-4">
                <div className="flex items-start gap-4">
                  <div className="w-12 h-12 bg-teal-100 rounded-xl flex items-center justify-center font-black text-teal-700 text-lg shrink-0">
                    {v.full_name?.split(' ').map((n:any)=>n[0]).join('').slice(0,2)}
                  </div>
                  <div>
                    <p className="font-black text-gray-900">{v.full_name}</p>
                    <p className="text-sm text-gray-500">{v.email}</p>
                    <p className="text-xs text-gray-400 mt-0.5">{v.city || 'No city'}</p>
                  </div>
                </div>
                <div className="flex items-center gap-3 shrink-0">
                  <button onClick={() => approve(v._id)}
                    className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-xl font-black text-sm transition-all active:scale-95 flex items-center gap-1.5">
                    <CheckCircle size={14} /> Approve
                  </button>
                  <button onClick={() => reject(v._id)}
                    className="bg-red-500 hover:bg-red-600 text-white px-4 py-2 rounded-xl font-black text-sm transition-all active:scale-95 flex items-center gap-1.5">
                    <XCircle size={14} /> Reject
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {activeSection === 'tiers' && (
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-100">
            <h3 className="font-black text-gray-900 text-lg flex items-center gap-2"><Star size={18} className="text-yellow-500" /> Provider Performance Tiers</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>{['Provider','Tier','Rating','Jobs','Earnings','Churn Risk','Actions'].map(h=>(
                  <th key={h} className="text-left py-3 px-5 font-black text-gray-400 text-xs uppercase tracking-wider">{h}</th>
                ))}</tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {tiers.map(p => (
                  <tr key={p.id} className="hover:bg-gray-50 transition-colors">
                    <td className="py-4 px-5 font-bold text-gray-900">{p.name}</td>
                    <td className="py-4 px-5">
                      <span className={`text-xs font-black px-2.5 py-1 rounded-full ${tierColor[p.tier] || tierColor.Silver}`}>{p.tier}</span>
                    </td>
                    <td className="py-4 px-5 font-black text-yellow-600">{p.rating?.toFixed(1)} ★</td>
                    <td className="py-4 px-5 font-bold text-gray-700">{p.bookings}</td>
                    <td className="py-4 px-5 font-black text-green-600">₹{(p.earnings).toLocaleString()}</td>
                    <td className="py-4 px-5">
                      <div className="flex items-center gap-2">
                        <div className="w-16 h-2 bg-gray-100 rounded-full overflow-hidden">
                          <div className="h-full rounded-full" style={{ width:`${p.churnRisk}%`, backgroundColor: p.churnRisk>50?'#ef4444':p.churnRisk>25?'#f59e0b':'#22c55e' }} />
                        </div>
                        <span className={`text-xs font-black ${p.churnRisk>50?'text-red-600':p.churnRisk>25?'text-yellow-600':'text-green-600'}`}>{p.churnRisk}%</span>
                      </div>
                    </td>
                    <td className="py-4 px-5">
                      <div className="flex gap-2">
                        {p.churnRisk > 40 && <button onClick={() => toast.success(`Retention offer sent to ${p.name}`)} className="text-xs bg-orange-500 hover:bg-orange-600 text-white px-2.5 py-1.5 rounded-xl font-black transition-all">Retain</button>}
                        <button onClick={() => toast.success('Profile viewed')} className="text-xs bg-gray-100 hover:bg-gray-200 text-gray-700 px-2.5 py-1.5 rounded-xl font-black transition-all">View</button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {activeSection === 'funnel' && (
        <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
          <h3 className="font-black text-gray-900 text-lg flex items-center gap-2 mb-5">
            <TrendingUp size={18} className="text-teal-600" /> Onboarding Funnel Drop-off Analysis
          </h3>
          <div className="space-y-3 mb-6">
            {funnel.map((s, i) => (
              <div key={s.step} className="flex items-center gap-4">
                <div className="w-6 h-6 rounded-full bg-teal-600 text-white flex items-center justify-center font-black text-xs shrink-0">{i+1}</div>
                <div className="flex-1">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-bold text-gray-800">{s.step}</span>
                    <span className="text-sm font-black text-gray-700">{s.count.toLocaleString()} <span className="text-xs font-bold text-gray-400">({s.pct}%)</span></span>
                  </div>
                  <div className="h-5 bg-gray-100 rounded-xl overflow-hidden">
                    <div className="h-full rounded-xl flex items-center px-2 transition-all" style={{ width:`${s.pct}%`, backgroundColor: i<2?'#0D7A7F':i<4?'#3b82f6':'#8b5cf6' }}>
                      {s.pct > 15 && <span className="text-white text-[10px] font-black">{s.pct}%</span>}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {activeSection === 'nps' && nps && (
        <div className="space-y-4">
          <div className="grid grid-cols-3 gap-4">
            {[
              { label:'NPS Score', value:nps.score, sub:'Excellent (>50 is good)', color:'text-green-600', bg:'bg-green-50' },
              { label:'Promoters',  value:nps.promoters, sub:'Score 9-10',               color:'text-green-600', bg:'bg-green-50' },
              { label:'Detractors', value:nps.detractors,  sub:'Score 0-6',                color:'text-red-600',   bg:'bg-red-50'   },
            ].map(s => (
              <div key={s.label} className={`${s.bg} rounded-2xl p-5 text-center`}>
                <p className={`text-3xl font-black ${s.color}`}>{s.value}</p>
                <p className="text-xs font-bold text-gray-700 mt-1">{s.label}</p>
                <p className="text-[10px] text-gray-400 mt-0.5">{s.sub}</p>
              </div>
            ))}
          </div>
          <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
            <h4 className="font-black text-gray-900 text-sm mb-4">Recent Provider Feedback</h4>
            {nps.recent_feedback?.map((f:any, i:number) => (
              <div key={i} className={`border rounded-xl p-4 mb-3 ${f.score>=9?'border-green-200 bg-green-50/30':f.score>=7?'border-gray-100':' border-red-200 bg-red-50/30'}`}>
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-gray-900 text-sm">{f.name}</span>
                    <span className={`text-[10px] font-black px-2 py-0.5 rounded-full ${tierColor[f.tier] || tierColor.Silver}`}>{f.tier}</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <span className="ml-1 font-black text-xs text-gray-600">{f.score}/10</span>
                  </div>
                </div>
                <p className="text-xs text-gray-600 italic">"{f.comment}"</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default ProviderLifecycle;
