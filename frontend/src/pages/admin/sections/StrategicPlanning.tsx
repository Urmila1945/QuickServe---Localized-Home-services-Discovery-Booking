import React from 'react';
import { AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { Map, TrendingUp, Target, DollarSign, Globe } from 'lucide-react';
import toast from 'react-hot-toast';

const expansionCities = [
  { city:'Pune',       state:'Maharashtra', demand:18400, gap:12800, score:92 },
  { city:'Ahmedabad',  state:'Gujarat',     demand:14200, gap:10600, score:87 },
  { city:'Jaipur',     state:'Rajasthan',   demand:9800,  gap:7400,  score:81 },
  { city:'Kochi',      state:'Kerala',      demand:8200,  gap:6100,  score:78 },
  { city:'Chandigarh', state:'Punjab',      demand:6400,  gap:5200,  score:74 },
];

const fiveYearForecast = [
  { year:'FY25', users:305764,  revenue:57_60_00_000,  cities:8  },
  { year:'FY26', users:620000,  revenue:142_00_00_000, cities:18 },
  { year:'FY27', users:1100000, revenue:310_00_00_000, cities:35 },
  { year:'FY28', users:1900000, revenue:620_00_00_000, cities:60 },
  { year:'FY29', users:3200000, revenue:1200_00_00_000,cities:100},
];

const categoryExpansion = [
  { category:'EV Charging Install',     demand:4820, providers:0,   gap:4820, revenue:'₹5.9L', priority:'Critical' },
  { category:'Smart Home Automation',   demand:3640, providers:12,  gap:3628, revenue:'₹9.1L', priority:'Critical' },
  { category:'Pest Control',            demand:6210, providers:45,  gap:6165, revenue:'₹3.1L', priority:'High'     },
  { category:'Interior Design Consult', demand:2180, providers:8,   gap:2172, revenue:'₹7.2L', priority:'High'     },
  { category:'Private Tutoring',        demand:8940, providers:120, gap:8820, revenue:'₹2.2L', priority:'Medium'   },
];

const competitorIntel = [
  { competitor:'Urban Company',  city:'Bangalore', priceΔ:'+8%',  feature:'AI-match launch',    threat:'High'   },
  { competitor:'Housejoy',       city:'Mumbai',    priceΔ:'-5%',  feature:'Subscription plans', threat:'Medium' },
  { competitor:'Zimmber',        city:'Delhi',     priceΔ:'0%',   feature:'New AC category',    threat:'Low'    },
];

const investmentROI = [
  { initiative:'AI Scheduling Feature',    invest:828000,  revenue:4980000,  roi:501, months:6  },
  { initiative:'AR Training Modules',      invest:414000,  revenue:1826000,  roi:341, months:9  },
  { initiative:'Bangalore City Launch',    invest:2490000, revenue:9960000,  roi:300, months:12 },
  { initiative:'WhatsApp Integration',     invest:207000,  revenue:1245000,  roi:501, months:3  },
];

const StrategicPlanning: React.FC = () => {
  const formatLarge = (n: number) => n >= 10000000 ? `₹${(n/10000000).toFixed(1)}Cr` : n >= 100000 ? `₹${(n/100000).toFixed(1)}L` : `₹${n.toLocaleString()}`;

  return (
    <div className="space-y-6">
      {/* 5-Year Forecast */}
      <div className="bg-gradient-to-r from-[#0D1F2D] to-indigo-900 rounded-2xl p-6 text-white shadow-lg">
        <div className="flex items-center gap-2 mb-5">
          <TrendingUp size={20} className="text-indigo-300" />
          <h3 className="font-black text-lg">5-Year Platform Forecast</h3>
          <span className="ml-auto text-xs text-indigo-300">ML-based projections</span>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-5">
          {fiveYearForecast.map(f => (
            <div key={f.year} className="bg-white/10 backdrop-blur-sm rounded-xl p-3 border border-white/10 text-center">
              <p className="font-black text-indigo-300 text-xs mb-1">{f.year}</p>
              <p className="font-black text-lg">{(f.users/1000).toFixed(0)}k</p>
              <p className="text-[10px] text-white/50">users</p>
              <p className="font-black text-green-400 text-sm mt-1">{formatLarge(f.revenue)}</p>
              <p className="text-[10px] text-white/50">{f.cities} cities</p>
            </div>
          ))}
        </div>
        <ResponsiveContainer width="100%" height={160}>
          <AreaChart data={fiveYearForecast}>
            <defs>
              <linearGradient id="foreGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#6366f1" stopOpacity={0.4} />
                <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
              </linearGradient>
            </defs>
            <XAxis dataKey="year" tick={{ fontSize:11, fontWeight:700, fill:'#a5b4fc' }} />
            <YAxis tick={{ fontSize:10, fill:'#a5b4fc' }} tickFormatter={v=>`${(v/1000000).toFixed(0)}M`} />
            <Tooltip formatter={(v: any, n: string) => [formatLarge(v as number), n==='revenue'?'Revenue':'Users']} contentStyle={{ background:'#1e1b4b', border:'1px solid #4338ca', borderRadius:'12px', color:'white' }} />
            <Area type="monotone" dataKey="revenue" stroke="#6366f1" strokeWidth={2.5} fill="url(#foreGrad)" />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Expansion Planner */}
      <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
        <h3 className="font-black text-gray-900 text-lg flex items-center gap-2 mb-4">
          <Map size={18} className="text-teal-600" /> Expansion Planner
        </h3>
        <p className="text-xs text-gray-400 mb-4 bg-teal-50 text-teal-700 px-3 py-2 rounded-xl font-bold">
          🤖 AI ranked cities by demand-supply gap and growth potential
        </p>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>{['City','State','Demand','Providers Needed','Revenue Potential','Expansion Score','Action'].map(h=>(
                <th key={h} className="text-left py-3 px-4 font-black text-gray-400 text-xs uppercase tracking-wider">{h}</th>
              ))}</tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {expansionCities.map(c => (
                <tr key={c.city} className="hover:bg-gray-50 transition-colors">
                  <td className="py-3.5 px-4 font-black text-gray-900">{c.city}</td>
                  <td className="py-3.5 px-4 text-gray-500 text-sm">{c.state}</td>
                  <td className="py-3.5 px-4 font-bold text-gray-700 text-sm">{c.demand.toLocaleString()}</td>
                  <td className="py-3.5 px-4 font-bold text-red-600 text-sm">{c.gap.toLocaleString()}</td>
                  <td className="py-3.5 px-4 font-black text-green-600 text-sm">₹{(c.gap * 830 / 100000).toFixed(1)}L/mo</td>
                  <td className="py-3.5 px-4">
                    <div className="flex items-center gap-2">
                      <div className="w-16 h-2 bg-gray-100 rounded-full overflow-hidden">
                        <div className="h-full rounded-full bg-teal-500" style={{ width:`${c.score}%` }} />
                      </div>
                      <span className="font-black text-teal-700 text-sm">{c.score}</span>
                    </div>
                  </td>
                  <td className="py-3.5 px-4">
                    <button onClick={() => toast.success(`Expansion plan for ${c.city} initiated!`)} className="text-xs bg-teal-600 hover:bg-teal-700 text-white px-3 py-1.5 rounded-xl font-black transition-all">Plan Launch</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Category Expansion + Competitor Intel */}
      <div className="grid lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
          <h3 className="font-black text-gray-900 text-lg flex items-center gap-2 mb-4">
            <Target size={18} className="text-purple-600" /> Category Expansion Data
          </h3>
          <div className="space-y-3">
            {categoryExpansion.map(c => (
              <div key={c.category} className="flex items-center justify-between p-3 bg-gray-50 rounded-xl hover:bg-purple-50/30 transition-colors">
                <div>
                  <p className="font-bold text-gray-900 text-sm">{c.category}</p>
                  <p className="text-xs text-gray-400">{c.demand.toLocaleString()} unmet requests · {c.revenue}/mo potential</p>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <span className={`text-[10px] font-black px-2 py-0.5 rounded-full ${c.priority==='Critical'?'bg-red-100 text-red-700':c.priority==='High'?'bg-orange-100 text-orange-700':'bg-gray-100 text-gray-500'}`}>{c.priority}</span>
                  <button onClick={() => toast.success(`${c.category} category added to roadmap!`)} className="text-xs bg-purple-600 hover:bg-purple-700 text-white px-2.5 py-1.5 rounded-xl font-black transition-all">Add</button>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
          <h3 className="font-black text-gray-900 text-lg flex items-center gap-2 mb-4">
            <Globe size={18} className="text-blue-600" /> Competitive Intelligence
          </h3>
          <div className="space-y-3">
            {competitorIntel.map(c => (
              <div key={c.competitor} className={`p-4 rounded-xl border ${c.threat==='High'?'bg-red-50 border-red-200':c.threat==='Medium'?'bg-yellow-50 border-yellow-200':'bg-gray-50 border-gray-100'}`}>
                <div className="flex items-start justify-between">
                  <div>
                    <p className="font-black text-gray-900 text-sm">{c.competitor}</p>
                    <p className="text-xs text-gray-500">{c.city} · Price change: <strong className={c.priceΔ.startsWith('+')? 'text-red-600':'text-green-600'}>{c.priceΔ}</strong></p>
                    <p className="text-xs font-bold text-blue-700 mt-1">🆕 {c.feature}</p>
                  </div>
                  <span className={`text-[10px] font-black px-2.5 py-1 rounded-full shrink-0 ${c.threat==='High'?'bg-red-100 text-red-700':c.threat==='Medium'?'bg-yellow-100 text-yellow-700':'bg-gray-100 text-gray-500'}`}>{c.threat} Threat</span>
                </div>
              </div>
            ))}
          </div>

          <div className="mt-4">
            <h4 className="font-black text-gray-900 text-sm mb-3 flex items-center gap-2"><DollarSign size={14} className="text-green-600" /> Investment ROI Tracker</h4>
            <div className="space-y-2">
              {investmentROI.map(inv => (
                <div key={inv.initiative} className="flex items-center justify-between bg-green-50 border border-green-100 rounded-xl px-3 py-2.5">
                  <div>
                    <p className="font-bold text-gray-900 text-xs">{inv.initiative}</p>
                    <p className="text-[10px] text-gray-400">Payback: {inv.months} months</p>
                  </div>
                  <div className="text-right">
                    <p className="font-black text-green-700 text-sm">{inv.roi}% ROI</p>
                    <p className="text-[10px] text-gray-400">₹{(inv.invest/1000).toFixed(0)}k → ₹{(inv.revenue/1000).toFixed(0)}k</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default StrategicPlanning;
