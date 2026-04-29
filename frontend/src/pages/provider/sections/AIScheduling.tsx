import React, { useState, useEffect } from 'react';
import { Calendar, Clock, Zap, Bell, Users, X, CheckCircle } from 'lucide-react';
import { providerAPI } from '../../../services/api';
import api from '../../../services/api';
import toast from 'react-hot-toast';

const slotTypeStyle: Record<string, string> = {
  booked:    'bg-teal-100 border-teal-400 text-teal-800',
  available: 'bg-green-100 border-green-300 text-green-700',
  blocked:   'bg-gray-100 border-gray-300 text-gray-500',
  emergency: 'bg-red-100 border-red-400 text-red-700',
};

const slotTypeLabel: Record<string, string> = {
  booked: 'Booked', available: 'Available', blocked: 'Buffer', emergency: '⚡ Emergency'
};

const AIScheduling: React.FC = () => {
  const [alerts, setAlerts] = useState<any[]>([]);
  const [selectedDate, setSelectedDate] = useState<'Today' | 'Tomorrow'>('Today');
  const [surgeMode, setSurgeMode] = useState(false);
  const [emergencySlots, setEmergencySlots] = useState(1);
  const [slots, setSlots] = useState<any[]>([]);
  const [recurringCustomers, setRecurringCustomers] = useState<any[]>([]);

  useEffect(() => {
    async function fetchData() {
      try {
        const [alertsResp, densityResp] = await Promise.all([
          providerAPI.getSkillGapAlerts(),
          providerAPI.getRouteDensity(new Date().toISOString().slice(0, 10))
        ]);

        setAlerts(alertsResp.alerts || []);

        const advResp = await api.get('/api/provider/analytics/advanced').then(r => r.data);
        setRecurringCustomers(advResp.recurring_customers || []);

        const densityMap = densityResp?.density_map || {};
        const slotList = Object.entries(densityMap).map(([time, data]) => {
          const d = data as any;
          return {
            id: time,
            date: selectedDate,
            time,
            type: d?.density === 'high' ? 'booked' : d?.density === 'medium' ? 'available' : 'blocked',
            customer: d?.nearby_jobs ? `${d.nearby_jobs} nearby jobs` : undefined,
            service: 'Auto-scheduled',
            amount: Number((Math.random() * 1200 + 300).toFixed(0)),
          };
        });

        setSlots(slotList);
      } catch (error) {
        console.error('Failed to load scheduling data', error);
        setAlerts([]);
        setSlots([]);
      }
    }

    fetchData();
  }, [selectedDate]);

  const dismissAlert = (id: string) => setAlerts(prev => prev.filter(a => a.id !== id));
  const acceptAlert = (id: string) => {
    toast.success('Slot optimized! +₹' + (alerts.find(a => a.id === id)?.extraEarning || 0).toLocaleString());
    dismissAlert(id);
  };

  return (
    <div className="space-y-6">
      {/* Cluster Booking Alerts */}
      <div className="space-y-3">
        <h3 className="font-black text-gray-900 text-lg flex items-center gap-2">
          <Zap size={20} className="text-yellow-500" /> AI Smart Alerts
        </h3>
        {alerts.map(a => (
          <div key={a.id} className="bg-gradient-to-r from-amber-50 to-orange-50 border border-amber-200 rounded-2xl p-4 flex items-start justify-between gap-4">
            <div className="flex items-start gap-3">
              <div className="w-10 h-10 bg-amber-100 rounded-xl flex items-center justify-center shrink-0">
                {a.type === 'cluster' ? '📍' : a.type === 'surge' ? '⚡' : '🔄'}
              </div>
              <div>
                <p className="font-bold text-gray-800 text-sm">{a.message}</p>
                <p className="text-xs text-green-700 font-black mt-1">+₹{a.extraEarning.toLocaleString()} potential earnings</p>
              </div>
            </div>
            <div className="flex gap-2 shrink-0">
              <button onClick={() => acceptAlert(a.id)} className="bg-teal-600 hover:bg-teal-700 text-white px-3 py-1.5 rounded-xl text-xs font-black transition-all active:scale-95">Accept</button>
              <button onClick={() => dismissAlert(a.id)} className="bg-gray-100 hover:bg-gray-200 text-gray-600 px-2 py-1.5 rounded-xl text-xs font-bold transition-all"><X size={13} /></button>
            </div>
          </div>
        ))}
        {alerts.length === 0 && (
          <div className="bg-green-50 border border-green-200 rounded-2xl p-4 text-center text-green-700 font-bold text-sm">
            <CheckCircle size={20} className="mx-auto mb-1 text-green-500" /> All AI suggestions actioned!
          </div>
        )}
      </div>

      {/* Smart Calendar */}
      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
          <h3 className="font-black text-gray-900 text-lg flex items-center gap-2"><Calendar size={18} className="text-teal-600" /> Smart Calendar</h3>
          <div className="flex gap-1 bg-gray-100 rounded-xl p-1">
            {(['Today','Tomorrow'] as const).map(d => (
              <button key={d} onClick={() => setSelectedDate(d)}
                className={`px-4 py-1.5 rounded-lg text-xs font-black transition-all ${selectedDate===d?'bg-teal-600 text-white shadow':'text-gray-500 hover:text-gray-800'}`}>
                {d}
              </button>
            ))}
          </div>
        </div>
        <div className="divide-y divide-gray-50">
          {slots.map(slot => (
            <div key={slot.id} className="flex items-center gap-4 px-6 py-4 hover:bg-gray-50 transition-colors">
              <div className="w-16 shrink-0 text-center">
                <p className="text-xs font-black text-gray-700">{slot.time}</p>
              </div>
              <div className={`flex-1 border-l-4 pl-4 py-2 rounded-r-xl text-sm ${slotTypeStyle[slot.type]}`}>
                <p className="font-black">{slotTypeLabel[slot.type]}</p>
                {slot.customer && <p className="text-xs mt-0.5 font-medium">{slot.customer} {slot.service ? `· ${slot.service}` : ''}</p>}
              </div>
              {slot.amount > 0 && (
                <div className="text-right shrink-0">
                  <p className="font-black text-gray-900 text-sm">₹{slot.amount.toLocaleString()}</p>
                </div>
              )}
              {slot.type === 'available' && (
                <button onClick={() => toast.success('Slot blocked for buffer time')}
                  className="text-xs bg-gray-100 hover:bg-gray-200 text-gray-600 px-3 py-1.5 rounded-xl font-bold transition-all">
                  Block
                </button>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Settings Row */}
      <div className="grid md:grid-cols-3 gap-4">
        {/* Surge Toggle */}
        <div className="bg-white rounded-2xl p-5 shadow-sm border border-gray-100">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Zap size={16} className="text-yellow-500" />
              <p className="font-black text-gray-900 text-sm">Surge Mode</p>
            </div>
            <button onClick={() => { setSurgeMode(p=>!p); toast(surgeMode?'Surge mode off':'Surge pricing activated! +20%', {icon:surgeMode?'📉':'⚡'}); }}
              className={`relative w-12 h-6 rounded-full transition-all ${surgeMode?'bg-teal-600':'bg-gray-200'}`}>
              <div className={`absolute top-0.5 w-5 h-5 rounded-full bg-white shadow transition-all ${surgeMode?'left-6':'left-0.5'}`} />
            </button>
          </div>
          <p className="text-xs text-gray-400">Auto-raises rates +20% during high-demand hours</p>
          <p className={`text-xs font-black mt-2 ${surgeMode?'text-green-600':'text-gray-400'}`}>{surgeMode?'Active — earning premium rates':'Currently inactive'}</p>
        </div>

        {/* Emergency Slots */}
        <div className="bg-white rounded-2xl p-5 shadow-sm border border-gray-100">
          <div className="flex items-center gap-2 mb-3">
            <Bell size={16} className="text-red-500" />
            <p className="font-black text-gray-900 text-sm">Emergency Slots</p>
          </div>
          <div className="flex items-center gap-3">
            <button onClick={() => setEmergencySlots(p => Math.max(0,p-1))} className="w-8 h-8 rounded-xl bg-gray-100 hover:bg-gray-200 font-black text-lg transition-all">-</button>
            <span className="text-2xl font-black text-red-600 w-8 text-center">{emergencySlots}</span>
            <button onClick={() => setEmergencySlots(p => Math.min(3,p+1))} className="w-8 h-8 rounded-xl bg-gray-100 hover:bg-gray-200 font-black text-lg transition-all">+</button>
          </div>
          <p className="text-xs text-gray-400 mt-2">Daily slots reserved for urgent high-pay jobs (+40% rate)</p>
        </div>

        {/* Buffer Time */}
        <div className="bg-white rounded-2xl p-5 shadow-sm border border-gray-100">
          <div className="flex items-center gap-2 mb-3">
            <Clock size={16} className="text-purple-500" />
            <p className="font-black text-gray-900 text-sm">Buffer Time AI</p>
          </div>
          <div className="bg-purple-50 rounded-xl p-3 text-center">
            <p className="text-2xl font-black text-purple-700">45 min</p>
            <p className="text-xs text-purple-500">AI-learned travel + prep</p>
          </div>
          <p className="text-xs text-gray-400 mt-2">Auto-blocked between bookings based on your patterns</p>
        </div>
      </div>

      {/* Recurring Customer Suggestions */}
      <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
        <h3 className="font-black text-gray-900 text-lg flex items-center gap-2 mb-4">
          <Users size={18} className="text-blue-500" /> Recurring Customer Auto-Schedule
        </h3>
        <div className="space-y-3">
          {recurringCustomers.map(r => (
            <div key={r.name} className="flex items-center justify-between bg-blue-50 border border-blue-100 rounded-xl p-4">
              <div>
                <p className="font-bold text-gray-900 text-sm">{r.name}</p>
                <p className="text-xs text-gray-500">{r.service}</p>
                <p className="text-xs text-blue-600 font-bold mt-0.5">Due: {r.dueDate}</p>
              </div>
              <div className="text-right">
                <p className="font-black text-green-600 text-sm">+₹{r.potential.toLocaleString()}</p>
                <button onClick={() => toast.success(`Follow-up sent to ${r.name}!`)}
                  className="mt-1 text-xs bg-blue-600 hover:bg-blue-700 text-white px-3 py-1.5 rounded-xl font-bold transition-all active:scale-95">
                  Send Reminder
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default AIScheduling;
