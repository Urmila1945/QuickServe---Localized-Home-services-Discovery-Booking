import React, { useState, useEffect } from 'react';
import { DollarSign, AlertTriangle, Map, Ban, TrendingUp, TrendingDown } from 'lucide-react';
import api, { providerAPI } from '../../../services/api';
import toast from 'react-hot-toast';

const DynamicPricing: React.FC = () => {
  const [zones, setZones] = useState<any[]>([]);
  const [newNoGo, setNewNoGo] = useState('');
  const [localNoGo, setLocalNoGo] = useState<any[]>([]);
  const [surgeEnabled, setSurgeEnabled] = useState(false);
  const [competitorAlerts, setCompetitorAlerts] = useState<any[]>([]);
  const [seasonalRules, setSeasonalRules] = useState<any[]>([]);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [pricing, adv, zonesResp] = await Promise.all([
          providerAPI.getSurgePricing(),
          api.get('/api/provider/analytics/advanced').then(r => r.data),
          api.get('/api/provider/territory/no-go-zones').then(r => r.data)
        ]);
        setSurgeEnabled(pricing.surge_active || false);
        setZones([{ zone: 'Local Zone', baseRate: 650, surgeMultiplier: pricing.surge_multiplier || 1.0, active: pricing.surge_active }]);
        setCompetitorAlerts(adv.competitor_alerts || []);
        setSeasonalRules(adv.seasonal_rules || []);
        setLocalNoGo(zonesResp.zones || []);
      } catch (err) {
        console.error('Failed to load pricing data', err);
      }
    };
    fetchData();
  }, []);

  const toggleZone = (idx: number) => {
    setZones(prev => prev.map((z,i) => i===idx ? {...z, active:!z.active} : z));
    toast.success(`Zone ${zones[idx]?.active ? 'deactivated' : 'activated'}`);
  };

  const addNoGo = async () => {
    if (!newNoGo.trim()) return;
    try {
      await api.post('/api/provider/territory/no-go-zones', { name: newNoGo, reason: 'Manually added' });
      setLocalNoGo(prev => [...prev, { id: `ng${Date.now()}`, name: newNoGo, reason: 'Manually added', added: 'Today' }]);
      setNewNoGo('');
      toast.success('No-go zone added');
    } catch (err) {
      toast.error('Failed to add no-go zone');
    }
  };

  const removeNoGo = async (zoneName: string) => {
    try {
      await api.delete(`/api/provider/territory/no-go-zones/${zoneName}`);
      setLocalNoGo(prev => prev.filter(n => n.name !== zoneName));
      toast.success('No-go zone removed');
    } catch (err) {
      toast.error('Failed to remove no-go zone');
    }
  };

  return (
    <div className="space-y-6">
      {/* Competitor Alerts */}
      <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
        <h3 className="font-black text-gray-900 text-lg flex items-center gap-2 mb-4">
          <AlertTriangle size={18} className="text-orange-500" /> Competitor Price Monitoring
        </h3>
        <p className="text-xs text-gray-400 mb-4 bg-blue-50 text-blue-700 px-3 py-2 rounded-xl font-bold">
          🤖 Real-time tracking of competitors in your service area
        </p>
        <div className="space-y-3">
          {competitorAlerts.map(a => (
            <div key={a.provider} className={`flex items-center justify-between p-4 rounded-xl border ${a.type==='up'?'bg-red-50 border-red-200':'bg-green-50 border-green-200'}`}>
              <div>
                <p className="font-bold text-gray-900 text-sm">{a.provider}</p>
                <p className="text-xs text-gray-500">{a.area} · New rate: {a.newRate}</p>
              </div>
              <div className="flex items-center gap-2">
                {a.type==='up' ? <TrendingUp size={16} className="text-red-500" /> : <TrendingDown size={16} className="text-green-500" />}
                <span className={`font-black text-sm ${a.type==='up'?'text-red-600':'text-green-600'}`}>{a.change}</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Territory Zones */}
      <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-black text-gray-900 text-lg flex items-center gap-2">
            <Map size={18} className="text-teal-600" /> Territory Heatmap Editor
          </h3>
          <button onClick={() => { setSurgeEnabled(p=>!p); toast(surgeEnabled?'Surge pricing disabled':'Surge pricing auto-enabled!',{icon:surgeEnabled?'📉':'⚡'}); }}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl font-black text-xs transition-all ${surgeEnabled?'bg-amber-500 text-white':'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}>
            <span className={`w-2 h-2 rounded-full ${surgeEnabled?'bg-white animate-pulse':'bg-gray-400'}`} />
            {surgeEnabled ? 'Surge ON' : 'Surge OFF'}
          </button>
        </div>

        <div className="space-y-3">
          {zones.map((z, i) => (
            <div key={z.zone} className={`border-2 rounded-xl p-4 transition-all ${z.active?'border-teal-400 bg-teal-50':'border-gray-200 bg-gray-50 opacity-60'}`}>
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-bold text-gray-900 text-sm">{z.zone}</p>
                  <p className="text-xs text-gray-500 mt-0.5">Base: ₹{z.baseRate}/hr · Surge: ₹{Math.round(z.baseRate * z.surgeMultiplier)}/hr ({z.surgeMultiplier}×)</p>
                </div>
                <div className="flex items-center gap-3">
                  <span className={`text-xs font-black px-2.5 py-1 rounded-full ${z.active?'bg-teal-600 text-white':'bg-gray-300 text-gray-600'}`}>
                    {z.active ? 'Active' : 'Inactive'}
                  </span>
                  <button onClick={() => toggleZone(i)}
                    className={`relative w-11 h-6 rounded-full transition-all ${z.active?'bg-teal-600':'bg-gray-200'}`}>
                    <div className={`absolute top-0.5 w-5 h-5 rounded-full bg-white shadow transition-all ${z.active?'left-5':'left-0.5'}`} />
                  </button>
                </div>
              </div>
              {z.active && (
                <div className="mt-3 flex items-center gap-3">
                  <label className="text-xs text-gray-500 font-medium w-20 shrink-0">Base Rate</label>
                  <input type="range" min={500} max={2000} step={50} defaultValue={z.baseRate}
                    className="flex-1 h-1.5 rounded-full bg-teal-200 appearance-none cursor-pointer" />
                  <span className="text-xs font-black text-teal-700 w-16 text-right">₹{z.baseRate}/hr</span>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Seasonal Rules */}
      <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
        <h3 className="font-black text-gray-900 text-lg flex items-center gap-2 mb-4">
          <DollarSign size={18} className="text-purple-600" /> Seasonal Pricing Rules
        </h3>
        <div className="space-y-3">
          {seasonalRules.map(r => (
            <div key={r.name} className="flex items-center justify-between p-4 bg-purple-50 border border-purple-100 rounded-xl">
              <div>
                <p className="font-bold text-gray-900 text-sm">{r.name}</p>
                <p className="text-xs text-gray-500">{r.category}</p>
              </div>
              <div className="flex items-center gap-3">
                <span className="font-black text-green-600 text-sm">{r.adjustment}</span>
                <span className={`text-xs font-black px-2.5 py-1 rounded-full ${r.status==='active'?'bg-green-100 text-green-700':'bg-blue-100 text-blue-700'}`}>
                  {r.status}
                </span>
              </div>
            </div>
          ))}
          <button onClick={() => toast.success('New seasonal rule created!')}
            className="w-full border-2 border-dashed border-purple-200 text-purple-500 font-bold text-sm py-3 rounded-xl hover:bg-purple-50 transition-colors">
            + Add Seasonal Rule
          </button>
        </div>
      </div>

      {/* No-Go Zones */}
      <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
        <h3 className="font-black text-gray-900 text-lg flex items-center gap-2 mb-4">
          <Ban size={18} className="text-red-500" /> No-Go Zone Blacklist
        </h3>
        <div className="flex gap-2 mb-4">
          <input value={newNoGo} onChange={e=>setNewNoGo(e.target.value)}
            onKeyDown={e=>e.key==='Enter'&&addNoGo()}
            placeholder="Enter address or area name…"
            className="flex-1 px-4 py-2.5 rounded-xl border-2 border-gray-100 focus:border-teal-400 focus:outline-none text-sm font-medium" />
          <button onClick={addNoGo} className="bg-red-500 hover:bg-red-600 text-white px-4 py-2.5 rounded-xl font-black text-sm transition-all active:scale-95">Add</button>
        </div>
        <div className="space-y-2">
          {localNoGo.map(z => (
            <div key={z.name} className="flex items-center justify-between bg-red-50 border border-red-100 rounded-xl p-3">
              <div>
                <p className="font-bold text-gray-900 text-sm">{z.name}</p>
                <p className="text-xs text-gray-500">{z.reason} · Added Today</p>
              </div>
              <button onClick={() => removeNoGo(z.name)}
                className="text-red-500 hover:text-red-700 text-xs font-black hover:bg-red-100 px-2 py-1 rounded-lg transition-all">
                Remove
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default DynamicPricing;
