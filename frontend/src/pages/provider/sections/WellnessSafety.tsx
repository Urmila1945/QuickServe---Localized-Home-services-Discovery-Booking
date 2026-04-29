import React, { useState } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts';
import { Shield, Heart, Phone, MapPin, AlertTriangle, CheckCircle } from 'lucide-react';
import { workloadData, safetyScores } from '../../../data/mockDashboardData';
import toast from 'react-hot-toast';

const safetyLevel = (s: number) =>
  s >= 80 ? { label:'Safe', color:'text-green-600', bg:'bg-green-100' } :
  s >= 60 ? { label:'Moderate', color:'text-yellow-600', bg:'bg-yellow-100' } :
            { label:'Caution', color:'text-red-600', bg:'bg-red-100' };

const WellnessSafety: React.FC = () => {
  const [safetyCheckIn, setSafetyCheckIn] = useState(false);
  const [emergencyContact, setEmergencyContact] = useState({ name:'Sunita Sharma (Wife)', phone:'+91 98765 00000' });
  const [editContact, setEditContact] = useState(false);

  const lastWeekHours = workloadData[workloadData.length-1].hours;
  const burnoutRisk = lastWeekHours >= 60 ? 'high' : lastWeekHours >= 50 ? 'medium' : 'low';
  const burnoutColor = burnoutRisk === 'high' ? 'text-red-600' : burnoutRisk === 'medium' ? 'text-yellow-600' : 'text-green-600';
  const burnoutBg    = burnoutRisk === 'high' ? 'bg-red-50 border-red-200' : burnoutRisk === 'medium' ? 'bg-yellow-50 border-yellow-200' : 'bg-green-50 border-green-200';

  return (
    <div className="space-y-6">
      {/* Burnout Warning Banner */}
      <div className={`border-2 rounded-2xl p-5 ${burnoutBg}`}>
        <div className="flex items-start gap-4">
          <div className="text-4xl">{burnoutRisk==='high'?'🚨':burnoutRisk==='medium'?'⚠️':'✅'}</div>
          <div className="flex-1">
            <h3 className={`font-black text-lg ${burnoutColor}`}>
              Workload {burnoutRisk==='high'?'Alert — High Risk of Burnout!':burnoutRisk==='medium'?'Warning — Approaching Limit':'Healthy — Great Balance!'}
            </h3>
            <p className="text-sm text-gray-600 mt-1">
              {lastWeekHours >= 60
                ? `You worked ${lastWeekHours}h last week — 60h+ is associated with burnout. Take a break this Sunday!`
                : lastWeekHours >= 50
                ? `You worked ${lastWeekHours}h last week. Consider reducing to prevent fatigue. Rest days improve performance.`
                : `You worked ${lastWeekHours}h last week. Excellent balance. Keep it up!`}
            </p>
            {burnoutRisk !== 'low' && (
              <button onClick={() => toast.success('Recovery plan applied — auto-blocked next Sunday!')}
                className="mt-3 bg-red-600 hover:bg-red-700 text-white px-5 py-2 rounded-xl font-black text-sm transition-all active:scale-95">
                Apply Recovery Plan
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Workload Chart */}
      <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
        <h3 className="font-black text-gray-900 text-lg flex items-center gap-2 mb-5">
          <Heart size={18} className="text-red-500" /> Weekly Hours — Workload Tracker
        </h3>
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={workloadData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#F0F4F8" />
            <XAxis dataKey="week" tick={{ fontSize:10, fontWeight:700 }} />
            <YAxis domain={[0,80]} tick={{ fontSize:10 }} />
            <Tooltip formatter={(v: any) => [`${v}h`, 'Hours Worked']} />
            <ReferenceLine y={60} stroke="#ef4444" strokeDasharray="4 2" label={{ value:'Burnout Threshold (60h)', position:'insideTopRight', fill:'#ef4444', fontSize:10, fontWeight:700 }} />
            <ReferenceLine y={50} stroke="#f59e0b" strokeDasharray="4 2" label={{ value:'Warning (50h)', position:'insideTopRight', fill:'#f59e0b', fontSize:10, fontWeight:700 }} />
            <Bar dataKey="hours" radius={[6,6,0,0]} fill="#0D7A7F" />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        {/* Safety Check-In */}
        <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
          <h3 className="font-black text-gray-900 text-lg flex items-center gap-2 mb-4">
            <Phone size={18} className="text-blue-600" /> Safety Check-In
          </h3>
          <p className="text-xs text-gray-400 mb-4">If you don't check out within 2 hours of scheduled job end, an alert is sent to your emergency contact.</p>

          <div className="flex items-center justify-between p-4 bg-blue-50 border border-blue-200 rounded-xl mb-4">
            <div>
              <p className="font-black text-gray-900 text-sm">Check-In Status</p>
              <p className="text-xs text-gray-400 mt-0.5">Job ends 6:00 PM · Alert at 8:00 PM</p>
            </div>
            <button onClick={() => { setSafetyCheckIn(p=>!p); toast.success(safetyCheckIn?'Safety check-out recorded!':'Safety check-in active!'); }}
              className={`px-4 py-2 rounded-xl font-black text-sm transition-all active:scale-95 ${safetyCheckIn?'bg-green-600 hover:bg-green-700 text-white':'bg-blue-600 hover:bg-blue-700 text-white'}`}>
              {safetyCheckIn ? '✓ Checked In' : 'Check In'}
            </button>
          </div>

          <div className="bg-gray-50 border border-gray-200 rounded-xl p-4">
            <p className="text-xs font-black text-gray-500 uppercase tracking-widest mb-2">Emergency Contact</p>
            {editContact ? (
              <div className="space-y-2">
                <input value={emergencyContact.name} onChange={e=>setEmergencyContact(p=>({...p,name:e.target.value}))}
                  className="w-full px-3 py-2 text-sm border border-gray-200 rounded-xl focus:outline-none focus:border-teal-400 font-medium" />
                <input value={emergencyContact.phone} onChange={e=>setEmergencyContact(p=>({...p,phone:e.target.value}))}
                  className="w-full px-3 py-2 text-sm border border-gray-200 rounded-xl focus:outline-none focus:border-teal-400 font-medium" />
                <button onClick={() => { setEditContact(false); toast.success('Contact saved!'); }} className="bg-teal-600 text-white px-4 py-2 rounded-xl font-black text-xs">Save</button>
              </div>
            ) : (
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-bold text-gray-900 text-sm">{emergencyContact.name}</p>
                  <p className="text-xs text-gray-400">{emergencyContact.phone}</p>
                </div>
                <button onClick={() => setEditContact(true)} className="text-xs text-teal-600 font-black hover:underline">Edit</button>
              </div>
            )}
          </div>
        </div>

        {/* Neighborhood Safety Scores */}
        <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
          <h3 className="font-black text-gray-900 text-lg flex items-center gap-2 mb-4">
            <MapPin size={18} className="text-orange-500" /> Neighborhood Safety Scores
          </h3>
          <div className="space-y-3">
            {safetyScores.map(z => {
              const sl = safetyLevel(z.score);
              return (
                <div key={z.zone} className="flex items-center gap-3">
                  <div className={`w-10 h-10 ${sl.bg} rounded-xl flex items-center justify-center font-black text-xs ${sl.color} shrink-0`}>{z.score}</div>
                  <div className="flex-1">
                    <div className="flex items-center justify-between mb-1">
                      <p className="text-sm font-bold text-gray-800">{z.zone}</p>
                      <span className={`text-[10px] font-black px-2 py-0.5 rounded-full ${sl.bg} ${sl.color}`}>{sl.label}</span>
                    </div>
                    <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
                      <div className="h-full rounded-full" style={{ width:`${z.score}%`, backgroundColor: z.score>=80?'#22c55e':z.score>=60?'#f59e0b':'#ef4444' }} />
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Insurance */}
      <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
        <h3 className="font-black text-gray-900 text-lg flex items-center gap-2 mb-4">
          <Shield size={18} className="text-teal-600" /> Insurance Integration
        </h3>
        <div className="grid sm:grid-cols-3 gap-4">
          {[
            { name:'Professional Liability Insurance', provider:'HDFC ERGO', coverage:'₹25L', expires:'Mar 2026', status:'active' },
            { name:'Tool & Equipment Cover',           provider:'Bajaj Allianz', coverage:'₹5L', expires:'Sep 2025', status:'active' },
            { name:'Personal Accident Policy',         provider:'LIC',         coverage:'₹50L', expires:'Dec 2024', status:'expiring' },
          ].map(ins => (
            <div key={ins.name} className={`border-2 rounded-xl p-4 ${ins.status==='active'?'border-green-200 bg-green-50/30':'border-orange-200 bg-orange-50/30'}`}>
              <div className="flex items-center gap-2 mb-2">
                {ins.status==='active' ? <CheckCircle size={14} className="text-green-600" /> : <AlertTriangle size={14} className="text-orange-600" />}
                <span className={`text-[10px] font-black px-2 py-0.5 rounded-full ${ins.status==='active'?'bg-green-100 text-green-700':'bg-orange-100 text-orange-700'}`}>{ins.status}</span>
              </div>
              <p className="font-black text-gray-900 text-xs leading-tight">{ins.name}</p>
              <p className="text-[10px] text-gray-500 mt-1">{ins.provider}</p>
              <p className="text-[10px] font-bold text-teal-700 mt-1">Coverage: {ins.coverage}</p>
              <p className="text-[10px] text-gray-400">Expires: {ins.expires}</p>
              {ins.status==='expiring' && (
                <button onClick={() => toast.success('Renewal reminder set!')} className="mt-2 w-full text-[10px] bg-orange-600 hover:bg-orange-700 text-white font-black py-1.5 rounded-xl transition-all active:scale-95">Renew Now</button>
              )}
            </div>
          ))}
        </div>
        <button onClick={() => toast.success('Certificate uploaded!')}
          className="mt-4 w-full border-2 border-dashed border-teal-200 text-teal-600 font-bold text-sm py-3 rounded-xl hover:bg-teal-50 transition-colors">
          + Upload New Certificate
        </button>
      </div>
    </div>
  );
};

export default WellnessSafety;
