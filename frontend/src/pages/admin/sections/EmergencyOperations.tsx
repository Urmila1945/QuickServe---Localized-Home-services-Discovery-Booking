import React, { useState } from 'react';
import { AlertTriangle, Zap, Shield, Bell, TrendingUp } from 'lucide-react';
import toast from 'react-hot-toast';

const priceSpikeAlerts = [
  { provider:'QuickFix Electricals', service:'Emergency Wiring', normal:996,  current:4150,  spike:317, area:'Koramangala', flagged:true  },
  { provider:'RapidPlumb Services',  service:'Pipe Burst Fix',   normal:830,  current:2905,  spike:250, area:'Indiranagar', flagged:true  },
  { provider:'AquaFix Pro',          service:'Water Leakage',    normal:747,  current:1660,  spike:122, area:'Whitefield',  flagged:false },
];

const outageTemplates = [
  { title:'Payment Gateway Down',    msg:'We\'re experiencing payment issues. Cash payments accepted temporarily.' },
  { title:'App Performance Slow',    msg:'Our team is working to restore normal speed. Thank you for your patience.' },
  { title:'Provider App Outage',     msg:'Provider app is being updated. Bookings continue via customer app.' },
];

const EmergencyOperations: React.FC = () => {
  const [disasterMode, setDisasterMode] = useState(false);
  const [activeSection, setActiveSection] = useState<'disaster'|'outage'|'pricing'|'workers'>('disaster');

  const sections = [
    { key:'disaster', label:'Disaster Mode',     icon:'🚨' },
    { key:'outage',   label:'Service Outage',    icon:'⚠️' },
    { key:'pricing',  label:'Price Gouging',     icon:'💰' },
    { key:'workers',  label:'Essential Workers', icon:'🔧' },
  ] as const;

  return (
    <div className="space-y-6">
      {disasterMode && (
        <div className="bg-red-600 rounded-2xl p-4 text-white flex items-center gap-3 animate-pulse">
          <AlertTriangle size={24} />
          <div>
            <p className="font-black text-lg">DISASTER RESPONSE MODE ACTIVE</p>
            <p className="text-red-200 text-sm">Commission reduced to 5% · All providers alerted · Support team mobilized</p>
          </div>
          <button onClick={() => { setDisasterMode(false); toast.success('Disaster mode deactivated'); }}
            className="ml-auto bg-white text-red-600 px-4 py-2 rounded-xl font-black text-sm">Deactivate</button>
        </div>
      )}

      <div className="flex gap-2 bg-white rounded-2xl p-1.5 shadow-sm border border-gray-100 overflow-x-auto">
        {sections.map(s => (
          <button key={s.key} onClick={() => setActiveSection(s.key)}
            className={`flex items-center gap-1.5 px-4 py-2 rounded-xl font-bold text-sm whitespace-nowrap transition-all ${activeSection===s.key?'bg-teal-600 text-white shadow':'text-gray-500 hover:text-gray-800 hover:bg-gray-50'}`}>
            {s.icon} {s.label}
          </button>
        ))}
      </div>

      {activeSection === 'disaster' && (
        <div className="space-y-4">
          <div className={`rounded-2xl p-6 border-2 ${disasterMode?'bg-red-50 border-red-300':'bg-white border-gray-100 shadow-sm'}`}>
            <div className="flex items-start gap-4">
              <div className={`w-14 h-14 rounded-2xl flex items-center justify-center text-3xl ${disasterMode?'bg-red-100':'bg-gray-100'}`}>🚨</div>
              <div className="flex-1">
                <h3 className="font-black text-gray-900 text-xl">Disaster Response Mode</h3>
                <p className="text-sm text-gray-500 mt-1">One-click emergency protocol: reduces commission to 5%, sends mass provider alert, notifies media team, activates support surge.</p>
                <div className="mt-4 grid sm:grid-cols-2 gap-3 text-xs">
                  {[
                    '✅ Commission auto-reduces to 5%',
                    '✅ SMS blast to all 1,284 providers',
                    '✅ Emergency hotline activated',
                    '✅ Media & PR team notified',
                    '✅ Government helpline linkup',
                    '✅ Real-time tracking enabled',
                  ].map(a => <p key={a} className="font-bold text-gray-700">{a}</p>)}
                </div>
              </div>
            </div>
            <div className="mt-5 flex gap-3">
              <button
                onClick={() => { setDisasterMode(true); toast.success('Disaster Response Mode activated!', {icon:'🚨', duration:5000}); }}
                disabled={disasterMode}
                className={`flex items-center gap-2 px-6 py-3 rounded-xl font-black text-sm transition-all active:scale-95 ${disasterMode?'bg-gray-200 text-gray-400 cursor-not-allowed':'bg-red-600 hover:bg-red-700 text-white shadow-lg shadow-red-200'}`}>
                <Zap size={16} /> Activate Disaster Mode
              </button>
              <button onClick={() => toast.success('Status page updated!')} className="bg-gray-100 hover:bg-gray-200 text-gray-700 px-5 py-3 rounded-xl font-black text-sm transition-all">Update Status Page</button>
            </div>
          </div>

          <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
            <h4 className="font-black text-gray-900 text-sm mb-4 flex items-center gap-2"><Bell size={15} className="text-orange-500" /> Mass Provider Alert</h4>
            <textarea placeholder="Type emergency message to all providers..." rows={3}
              className="w-full px-4 py-3 rounded-xl border-2 border-gray-100 focus:border-red-400 focus:outline-none text-sm font-medium mb-3 resize-none" />
            <div className="flex gap-3">
              <button onClick={() => toast.success('SMS sent to 1,284 providers!')} className="bg-orange-600 hover:bg-orange-700 text-white px-5 py-2.5 rounded-xl font-black text-sm transition-all">Send SMS</button>
              <button onClick={() => toast.success('Push notification sent!')} className="bg-blue-600 hover:bg-blue-700 text-white px-5 py-2.5 rounded-xl font-black text-sm transition-all">Send Push</button>
              <button onClick={() => toast.success('Email campaign sent!')} className="bg-gray-600 hover:bg-gray-700 text-white px-5 py-2.5 rounded-xl font-black text-sm transition-all">Send Email</button>
            </div>
          </div>
        </div>
      )}

      {activeSection === 'outage' && (
        <div className="space-y-4">
          <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
            <h3 className="font-black text-gray-900 text-lg flex items-center gap-2 mb-4"><AlertTriangle size={18} className="text-yellow-500" /> Service Outage Management</h3>
            <div className="grid sm:grid-cols-3 gap-4 mb-5">
              {[{label:'System Status',value:'Operational',color:'text-green-600',bg:'bg-green-50'},{label:'Active Incidents',value:0,color:'text-gray-500',bg:'bg-gray-50'},{label:'Uptime (30d)',value:'99.94%',color:'text-blue-600',bg:'bg-blue-50'}].map(s=>(
                <div key={s.label} className={`${s.bg} rounded-xl p-4 text-center`}>
                  <p className={`text-xl font-black ${s.color}`}>{s.value}</p>
                  <p className="text-xs text-gray-500 mt-0.5">{s.label}</p>
                </div>
              ))}
            </div>
            <h4 className="font-black text-gray-900 text-sm mb-3">Communication Templates</h4>
            <div className="space-y-3">
              {outageTemplates.map(t => (
                <div key={t.title} className="border border-gray-100 rounded-xl p-4 hover:border-yellow-300 hover:bg-yellow-50/20 transition-all">
                  <p className="font-black text-gray-900 text-sm mb-1">{t.title}</p>
                  <p className="text-xs text-gray-500 italic mb-3">"{t.msg}"</p>
                  <button onClick={() => toast.success(`${t.title} template sent to all users!`)} className="text-xs bg-yellow-500 hover:bg-yellow-600 text-white px-4 py-2 rounded-xl font-black transition-all">Broadcast</button>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {activeSection === 'pricing' && (
        <div className="space-y-4">
          <div className="bg-red-50 border border-red-200 rounded-2xl p-4 flex items-center gap-3">
            <TrendingUp size={20} className="text-red-500 shrink-0" />
            <p className="font-black text-red-700 text-sm">{priceSpikeAlerts.filter(p=>p.flagged).length} providers flagged for price gouging during peak demand</p>
          </div>
          {priceSpikeAlerts.map(p => (
            <div key={p.provider} className={`bg-white rounded-2xl p-5 shadow-sm border ${p.flagged?'border-red-300':'border-gray-100'}`}>
              <div className="flex items-start justify-between flex-wrap gap-4">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <p className="font-black text-gray-900">{p.provider}</p>
                    {p.flagged && <span className="text-xs font-black bg-red-100 text-red-700 px-2.5 py-1 rounded-full">⚠️ Flagged</span>}
                  </div>
                  <p className="text-sm text-gray-500">{p.service} · {p.area}</p>
                  <div className="flex items-center gap-3 mt-2">
                    <span className="text-xs text-gray-400">Normal: <strong>₹{p.normal}</strong></span>
                    <span className="text-xs text-red-600 font-black">Current: ₹{p.current} ({p.spike}% over normal)</span>
                  </div>
                </div>
                {p.flagged && (
                  <div className="flex gap-2 shrink-0">
                    <button onClick={() => toast.success(`Price capped for ${p.provider}`)} className="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-xl font-black text-sm transition-all">Cap Price</button>
                    <button onClick={() => toast.success('Provider warned')} className="bg-yellow-500 hover:bg-yellow-600 text-white px-4 py-2 rounded-xl font-black text-sm transition-all">Warn</button>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {activeSection === 'workers' && (
        <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
          <h3 className="font-black text-gray-900 text-lg flex items-center gap-2 mb-5"><Shield size={18} className="text-blue-600" /> Essential Worker Fast-Track</h3>
          <p className="text-sm text-gray-500 mb-4">Expedited verification for critical service providers during emergencies</p>
          {[
            { name:'Sanjay Electricals', service:'Electrician',  city:'Mumbai', reason:'Cyclone relief',  docs:'Complete', priority:'High'   },
            { name:'AquaFix Emergency',  service:'Plumber',      city:'Chennai', reason:'Flood response', docs:'Partial',  priority:'High'   },
            { name:'MedTech Repair',     service:'Medical Equip',city:'Delhi',  reason:'Hospital support',docs:'Complete', priority:'Critical'},
          ].map(w => (
            <div key={w.name} className="border border-blue-100 rounded-xl p-4 mb-3 bg-blue-50/30">
              <div className="flex items-center justify-between flex-wrap gap-3">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <p className="font-black text-gray-900">{w.name}</p>
                    <span className={`text-[10px] font-black px-2 py-0.5 rounded-full ${w.priority==='Critical'?'bg-red-100 text-red-700':'bg-orange-100 text-orange-700'}`}>{w.priority}</span>
                  </div>
                  <p className="text-xs text-gray-500">{w.service} · {w.city} · {w.reason}</p>
                  <p className="text-xs font-bold text-gray-600 mt-0.5">Docs: {w.docs}</p>
                </div>
                <button onClick={() => toast.success(`${w.name} fast-track approved!`)} className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-xl font-black text-sm transition-all">Fast-Track Approve</button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default EmergencyOperations;
