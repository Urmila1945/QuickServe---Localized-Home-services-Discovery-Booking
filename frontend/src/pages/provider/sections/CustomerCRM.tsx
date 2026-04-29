import React, { useState } from 'react';
import { Bell, Share2, AlertTriangle, Search } from 'lucide-react';
import { crmCustomers } from '../../../data/mockDashboardData';
import toast from 'react-hot-toast';

const tagStyle: Record<string, string> = {
  'VIP':        'bg-yellow-100 text-yellow-700 border border-yellow-200',
  'High Tipper':'bg-green-100 text-green-700 border border-green-200',
  'Loyal':      'bg-blue-100 text-blue-700 border border-blue-200',
  'Referrer':   'bg-purple-100 text-purple-700 border border-purple-200',
  'Regular':    'bg-teal-100 text-teal-700 border border-teal-200',
  'At Risk':    'bg-red-100 text-red-700 border border-red-200',
};

const riskColor = (score: number) => score < 20 ? 'text-green-600' : score < 50 ? 'text-yellow-600' : 'text-red-600';
const riskBg    = (score: number) => score < 20 ? 'bg-green-50' : score < 50 ? 'bg-yellow-50' : 'bg-red-50';

const CustomerCRM: React.FC = () => {
  const [search, setSearch] = useState('');
  const [selected, setSelected] = useState<string|null>(null);
  const [customers, setCustomers] = useState(crmCustomers);
  const filtered = customers.filter(c =>
    !search || c.name.toLowerCase().includes(search.toLowerCase()) || c.phone.includes(search)
  );

  const addTag = (customerId: string, tag: string) => {
    setCustomers(prev => prev.map(c =>
      c.id === customerId && !c.tags.includes(tag) ? { ...c, tags: [...c.tags, tag] } : c
    ));
    toast.success(`Tagged as ${tag}`);
  };

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label:'Total Clients',    value:customers.length,                                      color:'text-blue-600',   bg:'bg-blue-50',   icon:'👥' },
          { label:'VIP Customers',    value:customers.filter(c=>c.tags.includes('VIP')).length,    color:'text-yellow-600', bg:'bg-yellow-50', icon:'⭐' },
          { label:'High Risk',        value:customers.filter(c=>c.riskScore>=50).length,           color:'text-red-600',    bg:'bg-red-50',    icon:'⚠️' },
          { label:'Avg Spend',        value:`₹${Math.round(customers.reduce((s,c)=>s+c.totalSpent,0)/customers.length).toLocaleString()}`, color:'text-green-600', bg:'bg-green-50', icon:'💰' },
        ].map(s => (
          <div key={s.label} className="bg-white rounded-2xl p-5 shadow-sm border border-gray-100">
            <div className={`w-10 h-10 ${s.bg} rounded-xl flex items-center justify-center text-lg mb-3`}>{s.icon}</div>
            <p className={`text-2xl font-black ${s.color}`}>{s.value}</p>
            <p className="text-xs font-bold text-gray-500 mt-0.5">{s.label}</p>
          </div>
        ))}
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        {/* Customer List */}
        <div className="lg:col-span-2 bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
          <div className="px-5 py-4 border-b border-gray-100 flex items-center gap-3">
            <div className="relative flex-1">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
              <input type="text" placeholder="Search customers…" value={search} onChange={e=>setSearch(e.target.value)}
                className="pl-8 pr-4 py-2 w-full text-sm border border-gray-200 rounded-xl focus:outline-none focus:border-teal-400 font-medium" />
            </div>
          </div>
          <div className="divide-y divide-gray-50">
            {filtered.map(c => (
              <div key={c.id} onClick={() => setSelected(selected===c.id ? null : c.id)}
                className={`px-5 py-4 cursor-pointer transition-all hover:bg-teal-50/30 ${selected===c.id?'bg-teal-50 border-l-4 border-teal-500 pl-4':''}`}>
                <div className="flex items-start justify-between">
                  <div className="flex items-start gap-3">
                    <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-teal-400 to-teal-600 flex items-center justify-center text-white font-black text-sm shrink-0">
                      {c.name.split(' ').map(n=>n[0]).join('').slice(0,2)}
                    </div>
                    <div>
                      <p className="font-bold text-gray-900 text-sm">{c.name}</p>
                      <p className="text-xs text-gray-500">{c.phone} · {c.bookings} bookings · ₹{c.totalSpent.toLocaleString()} total</p>
                      <p className="text-xs text-gray-400 mt-0.5">Last: {c.lastService}</p>
                      <div className="flex flex-wrap gap-1 mt-1.5">
                        {c.tags.map(tag => (
                          <span key={tag} className={`text-[10px] font-black px-2 py-0.5 rounded-full ${tagStyle[tag]||'bg-gray-100 text-gray-600'}`}>{tag}</span>
                        ))}
                      </div>
                    </div>
                  </div>
                  <div className={`w-10 h-10 ${riskBg(c.riskScore)} rounded-xl flex flex-col items-center justify-center shrink-0`}>
                    <span className={`text-xs font-black ${riskColor(c.riskScore)}`}>{c.riskScore}</span>
                    <span className="text-[9px] text-gray-400">risk</span>
                  </div>
                </div>

                {selected === c.id && (
                  <div className="mt-3 pt-3 border-t border-teal-100 space-y-3">
                    <p className="text-xs text-gray-500 italic">"{c.notes}"</p>
                    <div className="flex flex-wrap gap-2">
                      {['VIP','High Tipper','Referrer'].filter(t=>!c.tags.includes(t)).map(tag => (
                        <button key={tag} onClick={e=>{e.stopPropagation();addTag(c.id,tag);}}
                          className={`text-xs font-black px-2.5 py-1 rounded-full border-dashed border-2 ${tagStyle[tag]||'bg-gray-50 text-gray-500 border-gray-300'} hover:opacity-80 transition-all`}>
                          + {tag}
                        </button>
                      ))}
                    </div>
                    <div className="flex gap-2">
                      <button onClick={e=>{e.stopPropagation();toast.success(`Follow-up reminder set for ${c.name}!`);}}
                        className="flex items-center gap-1.5 bg-teal-600 hover:bg-teal-700 text-white px-3 py-1.5 rounded-xl text-xs font-black transition-all active:scale-95">
                        <Bell size={11} /> Set Reminder
                      </button>
                      <button onClick={e=>{e.stopPropagation();toast.success('Referral discount sent!');}}
                        className="flex items-center gap-1.5 bg-purple-600 hover:bg-purple-700 text-white px-3 py-1.5 rounded-xl text-xs font-black transition-all active:scale-95">
                        <Share2 size={11} /> Send Referral
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Sidebar Info */}
        <div className="space-y-4">
          {/* Upcoming Follow-ups */}
          <div className="bg-white rounded-2xl p-5 shadow-sm border border-gray-100">
            <h4 className="font-black text-gray-900 text-sm flex items-center gap-2 mb-3">
              <Bell size={15} className="text-orange-500" /> Follow-up Reminders
            </h4>
            <div className="space-y-2.5">
              {[
                { name:'Karan Sharma',  due:'Dec 20', service:'Post-service check' },
                { name:'Meera Nair',    due:'Jan 05', service:'AC maintenance due' },
                { name:'Ramesh Gupta',  due:'Jan 12', service:'Quarterly wiring'   },
              ].map(f => (
                <div key={f.name} className="bg-orange-50 border border-orange-100 rounded-xl p-3">
                  <p className="font-bold text-gray-900 text-xs">{f.name}</p>
                  <p className="text-[10px] text-gray-500">{f.service}</p>
                  <p className="text-[10px] font-black text-orange-600 mt-0.5">Due: {f.due}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Referral Tracking */}
          <div className="bg-white rounded-2xl p-5 shadow-sm border border-gray-100">
            <h4 className="font-black text-gray-900 text-sm flex items-center gap-2 mb-3">
              <Share2 size={15} className="text-purple-500" /> Referral Tracking
            </h4>
            <div className="space-y-2">
              {[
                { name:'Priya Mehta',  referrals:3, earned:1494 },
                { name:'Anjali Singh', referrals:2, earned:996  },
                { name:'Meera Nair',   referrals:1, earned:498  },
              ].map(r => (
                <div key={r.name} className="flex items-center justify-between bg-purple-50 rounded-xl p-3">
                  <div>
                    <p className="font-bold text-gray-900 text-xs">{r.name}</p>
                    <p className="text-[10px] text-purple-600">{r.referrals} referrals</p>
                  </div>
                  <span className="font-black text-green-600 text-xs">+₹{r.earned.toLocaleString()}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Dispute Risk */}
          <div className="bg-white rounded-2xl p-5 shadow-sm border border-gray-100">
            <h4 className="font-black text-gray-900 text-sm flex items-center gap-2 mb-3">
              <AlertTriangle size={15} className="text-red-500" /> Dispute Risk Flags
            </h4>
            {customers.filter(c=>c.riskScore>=45).map(c => (
              <div key={c.id} className="bg-red-50 border border-red-200 rounded-xl p-3 mb-2">
                <p className="font-bold text-red-800 text-xs">{c.name}</p>
                <p className="text-[10px] text-red-500">{c.notes.slice(0,60)}…</p>
                <div className="flex items-center justify-between mt-1">
                  <span className="text-[10px] font-black text-red-600">Risk Score: {c.riskScore}/100</span>
                  <button onClick={() => toast('Customer flagged for manual review', {icon:'⚠️'})}
                    className="text-[10px] font-black text-red-600 hover:underline">Flag</button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default CustomerCRM;
