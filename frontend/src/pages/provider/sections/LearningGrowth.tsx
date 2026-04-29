import React, { useState } from 'react';
import { BookOpen, Award, Video, Lightbulb, ChevronRight, CheckCircle, AlertCircle } from 'lucide-react';
import { skillGapAlerts, certifications } from '../../../data/mockDashboardData';
import toast from 'react-hot-toast';

const webinars = [
  { id:'w1', title:'Pricing Strategies for Service Providers',   date:'Dec 20', time:'6:00 PM IST', speaker:'Raj Mehta (IIM-A)', registered:false, category:'Business' },
  { id:'w2', title:'Customer Communication Excellence',          date:'Dec 22', time:'4:00 PM IST', speaker:'Priya Sharma',      registered:true,  category:'Soft Skills' },
  { id:'w3', title:'Smart Home Technology Basics',               date:'Jan 5',  time:'5:00 PM IST', speaker:'Tech Team',         registered:false, category:'Technical' },
  { id:'w4', title:'Building Your 5-Star Reputation Online',     date:'Jan 10', time:'7:00 PM IST', speaker:'Digital Coach',     registered:false, category:'Marketing' },
];

const arModules = [
  { id:'ar1', name:'Solar Panel Mounting',       duration:'15 min', difficulty:'Medium', completed:false },
  { id:'ar2', name:'Smart Switch Wiring',        duration:'10 min', difficulty:'Easy',   completed:true  },
  { id:'ar3', name:'EV Charger Installation',    duration:'25 min', difficulty:'Hard',   completed:false },
  { id:'ar4', name:'Generator Connection',       duration:'20 min', difficulty:'Medium', completed:false },
];

const LearningGrowth: React.FC = () => {
  const [webinarList, setWebinarList] = useState(webinars);

  const toggleRegister = (id: string) => {
    setWebinarList(prev => prev.map(w => w.id===id ? {...w, registered:!w.registered} : w));
    const w = webinarList.find(x=>x.id===id);
    toast.success(w?.registered ? 'Registration cancelled' : 'Registered! Reminder set.');
  };

  const certStatus = (s: string) => s==='active' ? 'bg-green-100 text-green-700' : s==='expiring' ? 'bg-yellow-100 text-yellow-700' : 'bg-red-100 text-red-700';
  const certIcon   = (s: string) => s==='active' ? <CheckCircle size={14} className="text-green-600" /> : s==='expiring' ? <AlertCircle size={14} className="text-yellow-600" /> : <AlertCircle size={14} className="text-red-600" />;

  return (
    <div className="space-y-6">
      {/* Skill Gap Alerts */}
      <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
        <h3 className="font-black text-gray-900 text-lg flex items-center gap-2 mb-4">
          <Lightbulb size={18} className="text-yellow-500" /> Skill Gap Alerts
        </h3>
        <p className="text-xs text-gray-400 mb-4 bg-yellow-50 text-yellow-700 px-3 py-2 rounded-xl font-bold">
          🤖 AI identified high-demand skills in your area you don't currently offer
        </p>
        <div className="grid sm:grid-cols-2 gap-4">
          {skillGapAlerts.map(s => (
            <div key={s.skill} className="border border-gray-100 rounded-xl p-4 hover:border-teal-400 hover:bg-teal-50/30 transition-all group">
              <div className="flex items-start justify-between mb-2">
                <p className="font-black text-gray-900 text-sm">{s.skill}</p>
                <span className={`text-[10px] font-black px-2 py-0.5 rounded-full ${s.roi==='Very High'?'bg-purple-100 text-purple-700':s.roi==='High'?'bg-green-100 text-green-700':'bg-blue-100 text-blue-700'}`}>
                  {s.roi} ROI
                </span>
              </div>
              <div className="flex items-center justify-between text-xs text-gray-500 mb-3">
                <span>Avg ticket: <strong className="text-green-600">₹{s.avgTicket.toLocaleString()}</strong></span>
                <span>{s.unmetRequests} unmet requests nearby</span>
              </div>
              <div className="flex items-center justify-between">
                <span className={`text-[10px] font-black px-2 py-1 rounded-full ${s.difficulty==='Easy'?'bg-green-100 text-green-700':s.difficulty==='Medium'?'bg-yellow-100 text-yellow-700':'bg-red-100 text-red-700'}`}>
                  {s.difficulty}
                </span>
                <button onClick={() => toast.success(`Training module for ${s.skill} started!`)}
                  className="text-xs bg-teal-600 hover:bg-teal-700 text-white px-3 py-1.5 rounded-xl font-black transition-all active:scale-95 flex items-center gap-1">
                  Start Training <ChevronRight size={11} />
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* AR Training Modules */}
      <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
        <h3 className="font-black text-gray-900 text-lg flex items-center gap-2 mb-4">
          <Video size={18} className="text-purple-600" /> AR Training Modules
        </h3>
        <p className="text-xs text-gray-400 mb-4">Practice new services using your phone camera overlay</p>
        <div className="grid sm:grid-cols-2 gap-3">
          {arModules.map(m => (
            <div key={m.id} className={`border-2 rounded-xl p-4 transition-all ${m.completed?'border-green-200 bg-green-50':'border-gray-100 hover:border-purple-300 hover:bg-purple-50/20'}`}>
              <div className="flex items-center justify-between mb-2">
                <p className="font-bold text-gray-900 text-sm">{m.name}</p>
                {m.completed && <CheckCircle size={16} className="text-green-600" />}
              </div>
              <div className="flex items-center justify-between text-xs text-gray-400 mb-3">
                <span>{m.duration}</span>
                <span className={`font-bold ${m.difficulty==='Easy'?'text-green-600':m.difficulty==='Medium'?'text-yellow-600':'text-red-600'}`}>{m.difficulty}</span>
              </div>
              <button onClick={() => toast.success(m.completed ? 'Module replayed!' : `AR Training for "${m.name}" started!`)}
                className={`w-full text-xs font-black py-2 rounded-xl transition-all active:scale-95 ${m.completed?'bg-green-100 text-green-700 hover:bg-green-200':'bg-purple-600 hover:bg-purple-700 text-white'}`}>
                {m.completed ? '✓ Replay Module' : '📱 Start AR Training'}
              </button>
            </div>
          ))}
        </div>
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        {/* Certification Tracker */}
        <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
          <h3 className="font-black text-gray-900 text-lg flex items-center gap-2 mb-4">
            <Award size={18} className="text-teal-600" /> Certification Tracker
          </h3>
          <div className="space-y-3">
            {certifications.map(c => (
              <div key={c.name} className="flex items-center justify-between p-3 bg-gray-50 rounded-xl">
                <div className="flex items-center gap-3">
                  {certIcon(c.status)}
                  <div>
                    <p className="font-bold text-gray-900 text-xs">{c.name}</p>
                    <p className="text-[10px] text-gray-400">{c.issuer} · Expires {c.expires}</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`text-[10px] font-black px-2 py-0.5 rounded-full ${certStatus(c.status)}`}>{c.status}</span>
                  {c.status !== 'active' && (
                    <button onClick={() => toast.success('Renewal reminder set!')} className="text-[10px] bg-orange-100 text-orange-700 font-black px-2 py-1 rounded-xl hover:bg-orange-200">Renew</button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Webinars */}
        <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
          <h3 className="font-black text-gray-900 text-lg flex items-center gap-2 mb-4">
            <BookOpen size={18} className="text-blue-600" /> Upcoming Webinars
          </h3>
          <div className="space-y-3">
            {webinarList.map(w => (
              <div key={w.id} className={`border rounded-xl p-3 transition-all ${w.registered?'border-green-200 bg-green-50':'border-gray-100 hover:border-blue-200'}`}>
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <p className="font-bold text-gray-900 text-xs leading-tight">{w.title}</p>
                    <p className="text-[10px] text-gray-400 mt-0.5">{w.date} · {w.time} · {w.speaker}</p>
                    <span className="text-[10px] font-black text-blue-600 bg-blue-50 px-2 py-0.5 rounded-full mt-1 inline-block">{w.category}</span>
                  </div>
                  <button onClick={() => toggleRegister(w.id)}
                    className={`text-[10px] font-black px-2.5 py-1.5 rounded-xl whitespace-nowrap transition-all active:scale-95 shrink-0 ${w.registered?'bg-green-600 text-white':'bg-blue-600 hover:bg-blue-700 text-white'}`}>
                    {w.registered?'✓ Registered':'Register'}
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default LearningGrowth;
