import React, { useState, useEffect } from 'react';
import { Users, FileText, MapPin, MessageSquare, ThumbsUp } from 'lucide-react';
import api from '../../../services/api';
import toast from 'react-hot-toast';

const CommunityGovernance: React.FC = () => {
  const [juryPool, setJuryPool] = useState<any[]>([]);
  const [ambassadors, setAmbassadors] = useState<any[]>([]);
  const [featureRequests, setFeatureRequests] = useState<any[]>([]);
  const [policies, setPolicies] = useState<any[]>([]);
  const [activeSection, setActiveSection] = useState<'jury'|'policy'|'ambassadors'|'feedback'>('jury');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await api.get('/api/admin/community-governance').then(r => r.data);
        setJuryPool(res.jury || []);
        setAmbassadors(res.ambassadors || []);
        setFeatureRequests(res.feature_requests || []);
        setPolicies(res.policy_broadcasts || []);
      } catch (err) {
        console.error('Failed to load community data', err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  const sections = [
    { key:'jury',        label:'Jury Pool',    icon:'⚖️' },
    { key:'policy',      label:'Policy',       icon:'📜' },
    { key:'ambassadors', label:'Ambassadors',  icon:'🏘️' },
    { key:'feedback',    label:'Feedback',     icon:'💡' },
  ] as const;

  if (loading) return <div className="p-10 text-center font-bold text-gray-400">Loading community data...</div>;

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

      {activeSection === 'jury' && (
        <div className="space-y-4">
          <div className="grid grid-cols-3 gap-4">
            {[
              { label:'Active Jurors',  value:juryPool.filter(j=>j.status!=='inactive').length, color:'text-blue-600', bg:'bg-blue-50' },
              { label:'Cases Pending',  value:3,  color:'text-yellow-600', bg:'bg-yellow-50' },
              { label:'Avg Accuracy',   value:juryPool.length ? `${Math.round(juryPool.reduce((s,j)=>s+j.accuracy,0)/juryPool.length)}%` : '0%', color:'text-green-600', bg:'bg-green-50' },
            ].map(s => (
              <div key={s.label} className={`${s.bg} rounded-2xl p-4 text-center`}>
                <p className={`text-2xl font-black ${s.color}`}>{s.value}</p>
                <p className="text-xs font-bold text-gray-500 mt-0.5">{s.label}</p>
              </div>
            ))}
          </div>
          <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
              <h3 className="font-black text-gray-900 text-lg flex items-center gap-2"><Users size={18} className="text-blue-600" /> Jury Pool Management</h3>
              <button onClick={() => toast.success('Jury invitation sent to top providers!')} className="text-xs bg-blue-600 text-white font-black px-4 py-2 rounded-xl hover:bg-blue-700 transition-all">+ Recruit Jurors</button>
            </div>
            <div className="divide-y divide-gray-50">
              {juryPool.map(j => (
                <div key={j.id} className="flex items-center justify-between px-6 py-4 hover:bg-gray-50 transition-colors">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-blue-100 rounded-xl flex items-center justify-center font-black text-blue-700 text-sm">
                      {j.name.split(' ').map((n: string)=>n[0]).join('')}
                    </div>
                    <div>
                      <p className="font-bold text-gray-900 text-sm">{j.name}</p>
                      <p className="text-xs text-gray-400">{j.tier} · {j.cases} cases · {j.accuracy}% accuracy</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="text-center">
                      <p className="font-black text-green-600 text-sm">{j.reward}</p>
                      <span className={`text-[10px] font-black px-2 py-0.5 rounded-full ${j.status==='available'?'bg-green-100 text-green-700':j.status==='on_case'?'bg-blue-100 text-blue-700':'bg-gray-100 text-gray-500'}`}>{j.status.replace('_',' ')}</span>
                    </div>
                    {j.status === 'available' && (
                      <button onClick={() => toast.success(`Case assigned to ${j.name}`)} className="text-xs bg-blue-600 hover:bg-blue-700 text-white px-3 py-1.5 rounded-xl font-black transition-all">Assign Case</button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {activeSection === 'policy' && (
        <div className="space-y-4">
          <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
            <h3 className="font-black text-gray-900 text-lg flex items-center gap-2 mb-5"><FileText size={18} className="text-gray-700" /> Policy Broadcasts</h3>
            <div className="space-y-4">
              {policies.map(p => (
                <div key={p.id} className="flex items-center justify-between p-4 bg-gray-50 rounded-xl">
                  <div>
                    <p className="font-bold text-gray-900 text-sm">{p.title}</p>
                    <p className="text-[10px] text-gray-400 mt-0.5">Reach: {p.reach} · Date: {p.date}</p>
                  </div>
                  <span className={`text-[10px] font-black px-2 py-1 rounded-full ${p.status==='sent'?'bg-green-100 text-green-700':'bg-yellow-100 text-yellow-700'}`}>{p.status}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {activeSection === 'ambassadors' && (
        <div className="grid grid-cols-2 gap-4">
          {ambassadors.map(a => (
            <div key={a.name} className="bg-white p-5 rounded-2xl shadow-sm border border-gray-100 hover:shadow-md transition-all">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <MapPin size={16} className="text-teal-600" />
                  <span className="font-black text-gray-900">{a.name}</span>
                </div>
                <span className={`text-[10px] font-black px-2 py-1 rounded-full ${a.status==='active'?'bg-green-100 text-green-700':'bg-orange-100 text-orange-700'}`}>{a.status}</span>
              </div>
              <div className="grid grid-cols-2 gap-4 mb-4">
                <div className="text-center">
                  <p className="text-lg font-black text-gray-900">{a.providers}</p>
                  <p className="text-[10px] text-gray-400 font-bold">Providers</p>
                </div>
                <div className="text-center">
                  <p className="text-lg font-black text-gray-900">{a.customers}</p>
                  <p className="text-[10px] text-gray-400 font-bold">Customers</p>
                </div>
              </div>
              <div className="flex items-center justify-between pt-4 border-t border-gray-50">
                <p className="text-xs text-gray-500 font-bold">Captain: <span className="text-gray-900">{a.captain}</span></p>
                <span className="text-xs font-black text-green-600">{a.growth} growth</span>
              </div>
            </div>
          ))}
        </div>
      )}

      {activeSection === 'feedback' && (
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-100">
            <h3 className="font-black text-gray-900 text-lg flex items-center gap-2"><ThumbsUp size={18} className="text-yellow-600" /> Top Feature Requests</h3>
          </div>
          <div className="divide-y divide-gray-50">
            {featureRequests.map(r => (
              <div key={r.id} className="flex items-center justify-between px-6 py-4">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-teal-50 rounded-xl flex items-center justify-center font-black text-teal-700 text-sm">
                    {r.votes}
                  </div>
                  <div>
                    <p className="font-bold text-gray-900 text-sm">{r.title}</p>
                    <p className="text-[10px] text-gray-400 uppercase tracking-wider font-black">{r.category} · {r.status}</p>
                  </div>
                </div>
                <button className="text-xs text-teal-600 font-black px-3 py-1.5 rounded-lg hover:bg-teal-50 transition-all">Support</button>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default CommunityGovernance;
