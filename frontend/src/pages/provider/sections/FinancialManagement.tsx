import React, { useState } from 'react';
import { AreaChart, Area, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { Target, TrendingUp, FileText, Wallet, Clock } from 'lucide-react';
import toast from 'react-hot-toast';

const fmt = (n: number) => `₹${n.toLocaleString('en-IN')}`;

const EARNINGS_MONTHLY = [
  { month: 'Jul', earnings: 180000, expenses: 42000 },
  { month: 'Aug', earnings: 210000, expenses: 48000 },
  { month: 'Sep', earnings: 195000, expenses: 45000 },
  { month: 'Oct', earnings: 240000, expenses: 52000 },
  { month: 'Nov', earnings: 265000, expenses: 58000 },
  { month: 'Dec', earnings: 286000, expenses: 61000 },
];

const CASH_FLOW_FORECAST = [
  { week: 'W1', projected: 68000, actual: 71000 },
  { week: 'W2', projected: 72000, actual: 69000 },
  { week: 'W3', projected: 75000, actual: 78000 },
  { week: 'W4', projected: 80000, actual: null  },
];

const payoutOptions = [
  { type: 'Instant', fee: '2%',  desc: 'Available within 2 hours', badge: 'bg-orange-100 text-orange-700' },
  { type: 'Weekly',  fee: 'Free', desc: 'Every Monday morning',     badge: 'bg-blue-100 text-blue-700'   },
  { type: 'Monthly', fee: 'Free', desc: '1st of each month',        badge: 'bg-green-100 text-green-700' },
];

const FinancialManagement: React.FC = () => {
  const [goalTarget, setGoalTarget] = useState(300000);
  const [selectedPayout, setSelectedPayout] = useState('Weekly');

  const currentMonthEarnings = 286000;
  const goalProgress = Math.min(100, Math.round((currentMonthEarnings / goalTarget) * 100));

  const plData = EARNINGS_MONTHLY.map(m => ({
    month: m.month,
    revenue: m.earnings,
    expenses: m.expenses,
    profit: m.earnings - m.expenses,
  }));

  const lastMonth = plData[plData.length - 1];
  const netProfit   = lastMonth?.profit ?? 0;
  const platformFees = Math.round(currentMonthEarnings * 0.1);
  const taxes        = Math.round(currentMonthEarnings * 0.18);

  return (
    <div className="space-y-6">
      {/* Top Financial Summary */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: 'This Month Revenue',  value: fmt(currentMonthEarnings), color: 'text-green-600',  bg: 'bg-green-50',  icon: '💰' },
          { label: 'Platform Fees (10%)', value: fmt(platformFees),         color: 'text-orange-600', bg: 'bg-orange-50', icon: '🏪' },
          { label: 'Est. Tax Liability',  value: fmt(taxes),                color: 'text-red-600',    bg: 'bg-red-50',    icon: '🧾' },
          { label: 'Net Profit',          value: fmt(netProfit),            color: 'text-teal-600',   bg: 'bg-teal-50',   icon: '📈' },
        ].map(s => (
          <div key={s.label} className="bg-white rounded-2xl p-5 shadow-sm border border-gray-100">
            <div className={`w-10 h-10 ${s.bg} rounded-xl flex items-center justify-center text-lg mb-3`}>{s.icon}</div>
            <p className={`text-xl font-black ${s.color}`}>{s.value}</p>
            <p className="text-xs font-bold text-gray-500 mt-0.5">{s.label}</p>
          </div>
        ))}
      </div>

      {/* P&L Chart */}
      <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
        <div className="flex items-center justify-between mb-5">
          <div>
            <h3 className="font-black text-gray-900 text-lg">Profit & Loss Dashboard</h3>
            <p className="text-xs text-gray-400">Revenue vs Expenses vs Net Profit</p>
          </div>
          <button onClick={() => toast.success('Full P&L report downloaded!')}
            className="text-xs bg-gray-100 hover:bg-gray-200 text-gray-700 font-black px-4 py-2 rounded-xl transition-all">Export PDF</button>
        </div>
        <ResponsiveContainer width="100%" height={220}>
          <AreaChart data={plData}>
            <defs>
              <linearGradient id="revGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%"  stopColor="#22c55e" stopOpacity={0.25} />
                <stop offset="95%" stopColor="#22c55e" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="profitGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%"  stopColor="#0D7A7F" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#0D7A7F" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#F0F4F8" />
            <XAxis dataKey="month" tick={{ fontSize: 11, fontWeight: 700 }} />
            <YAxis tick={{ fontSize: 11 }} tickFormatter={v => `₹${(v / 1000).toFixed(0)}k`} />
            <Tooltip formatter={(v: any, n: string) => [fmt(v), n.charAt(0).toUpperCase() + n.slice(1)]} />
            <Area type="monotone" dataKey="revenue"  stroke="#22c55e" strokeWidth={2}   fill="url(#revGrad)" />
            <Area type="monotone" dataKey="profit"   stroke="#0D7A7F" strokeWidth={2.5} fill="url(#profitGrad)" />
            <Area type="monotone" dataKey="expenses" stroke="#ef4444" strokeWidth={1.5} fill="none" strokeDasharray="4 2" />
          </AreaChart>
        </ResponsiveContainer>
        <div className="flex items-center gap-5 mt-3 text-xs">
          {[['#22c55e', 'Revenue'], ['#0D7A7F', 'Net Profit'], ['#ef4444', 'Expenses']].map(([c, l]) => (
            <div key={l} className="flex items-center gap-1.5">
              <div className="w-3 h-1.5 rounded-full" style={{ backgroundColor: c }} />
              <span className="text-gray-500">{l}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        {/* Goal Setting */}
        <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
          <h3 className="font-black text-gray-900 text-lg flex items-center gap-2 mb-4">
            <Target size={18} className="text-purple-600" /> Monthly Earnings Goal
          </h3>
          <div className="mb-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-bold text-gray-500">Progress</span>
              <span className="text-sm font-black text-teal-700">{fmt(currentMonthEarnings)} / {fmt(goalTarget)}</span>
            </div>
            <div className="h-4 bg-gray-100 rounded-full overflow-hidden">
              <div className={`h-full rounded-full transition-all ${goalProgress >= 100 ? 'bg-green-500' : goalProgress >= 75 ? 'bg-teal-500' : 'bg-blue-500'}`}
                style={{ width: `${goalProgress}%` }} />
            </div>
            <p className={`text-xs font-black mt-1.5 ${goalProgress >= 100 ? 'text-green-600' : 'text-teal-600'}`}>
              {goalProgress >= 100 ? '🎉 Goal achieved!' : goalProgress >= 75 ? '🔥 Almost there!' : ''} {goalProgress}% complete
            </p>
          </div>
          <label className="text-xs font-black text-gray-400 uppercase tracking-widest mb-2 block">Set New Goal</label>
          <div className="flex gap-2">
            <input type="number" value={goalTarget} onChange={e => setGoalTarget(Number(e.target.value))}
              className="flex-1 px-4 py-2.5 rounded-xl border-2 border-gray-100 focus:border-teal-400 focus:outline-none text-sm font-bold" />
            <button onClick={() => toast.success('Goal updated!')} className="bg-purple-600 hover:bg-purple-700 text-white px-5 py-2.5 rounded-xl font-black text-sm transition-all active:scale-95">Set</button>
          </div>
          <div className="mt-4 grid grid-cols-3 gap-2">
            {[200000, 300000, 500000].map(g => (
              <button key={g} onClick={() => setGoalTarget(g)}
                className={`text-xs font-black py-2 rounded-xl transition-all ${goalTarget === g ? 'bg-purple-600 text-white' : 'bg-purple-50 text-purple-700 hover:bg-purple-100'}`}>
                ₹{(g / 1000).toFixed(0)}k
              </button>
            ))}
          </div>
        </div>

        {/* Payout Schedule */}
        <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
          <h3 className="font-black text-gray-900 text-lg flex items-center gap-2 mb-4">
            <Wallet size={18} className="text-green-600" /> Payout Schedule
          </h3>
          <div className="space-y-3 mb-5">
            {payoutOptions.map(p => (
              <div key={p.type} onClick={() => setSelectedPayout(p.type)}
                className={`flex items-center justify-between p-4 rounded-xl border-2 cursor-pointer transition-all ${selectedPayout === p.type ? 'border-teal-400 bg-teal-50' : 'border-gray-100 hover:border-gray-200'}`}>
                <div className="flex items-center gap-3">
                  <div className={`w-4 h-4 rounded-full border-2 ${selectedPayout === p.type ? 'border-teal-600 bg-teal-600' : 'border-gray-300'} flex items-center justify-center`}>
                    {selectedPayout === p.type && <div className="w-1.5 h-1.5 rounded-full bg-white" />}
                  </div>
                  <div>
                    <p className="font-black text-gray-900 text-sm">{p.type} Payout</p>
                    <p className="text-xs text-gray-400">{p.desc}</p>
                  </div>
                </div>
                <span className={`text-xs font-black px-2.5 py-1 rounded-full ${p.badge}`}>{p.fee}</span>
              </div>
            ))}
          </div>
          <div className="bg-green-50 border border-green-200 rounded-xl p-4 flex items-center justify-between">
            <div>
              <p className="font-black text-green-700 text-sm">Available Balance</p>
              <p className="text-2xl font-black text-green-800">₹1,02,800</p>
            </div>
            <button onClick={() => toast.success('Withdrawal initiated!')}
              className="bg-green-600 hover:bg-green-700 text-white px-5 py-3 rounded-xl font-black text-sm transition-all active:scale-95">
              Withdraw
            </button>
          </div>
        </div>
      </div>

      {/* Cash Flow Forecast */}
      <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
        <h3 className="font-black text-gray-900 text-lg flex items-center gap-2 mb-2">
          <TrendingUp size={18} className="text-blue-600" /> Cash Flow Forecast
        </h3>
        <p className="text-xs text-gray-400 mb-5 bg-blue-50 text-blue-700 px-3 py-2 rounded-xl font-bold">
          🤖 AI predicts next 30-day income based on confirmed bookings and seasonal patterns
        </p>
        <ResponsiveContainer width="100%" height={180}>
          <LineChart data={CASH_FLOW_FORECAST}>
            <CartesianGrid strokeDasharray="3 3" stroke="#F0F4F8" />
            <XAxis dataKey="week" tick={{ fontSize: 11, fontWeight: 700 }} />
            <YAxis tick={{ fontSize: 11 }} tickFormatter={v => `₹${(v / 1000).toFixed(0)}k`} />
            <Tooltip formatter={(v: any, n: string) => [fmt(v as number), n === 'projected' ? 'AI Forecast' : 'Actual']} />
            <Line type="monotone" dataKey="projected" stroke="#3b82f6" strokeWidth={2} strokeDasharray="5 3" dot={{ fill: '#3b82f6', r: 4 }} />
            <Line type="monotone" dataKey="actual"    stroke="#0D7A7F" strokeWidth={2.5} dot={{ fill: '#0D7A7F', r: 4 }} connectNulls={false} />
          </LineChart>
        </ResponsiveContainer>
        <div className="flex items-center gap-5 mt-3 text-xs">
          <div className="flex items-center gap-1.5"><div className="w-6 h-0.5 bg-blue-500" /><span className="text-gray-500">AI Forecast</span></div>
          <div className="flex items-center gap-1.5"><div className="w-6 h-0.5 bg-teal-600" /><span className="text-gray-500">Actual</span></div>
        </div>
      </div>

      {/* Tax Documents */}
      <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
        <h3 className="font-black text-gray-900 text-lg flex items-center gap-2 mb-4">
          <FileText size={18} className="text-orange-600" /> Tax Documents
        </h3>
        <div className="grid sm:grid-cols-3 gap-4">
          {[
            { name: 'GST Returns Q3 FY2025',  date: 'Generated Dec 1', status: 'ready'   },
            { name: 'Annual Income Statement', date: 'FY 2024-25',      status: 'pending' },
            { name: 'Quarterly Tax Estimate',  date: 'Q4 (Dec–Mar)',    status: 'ready'   },
          ].map(doc => (
            <div key={doc.name} className="border border-gray-100 rounded-xl p-4 hover:border-teal-300 hover:bg-teal-50/20 transition-all">
              <div className="text-3xl mb-2">📄</div>
              <p className="font-bold text-gray-900 text-sm">{doc.name}</p>
              <p className="text-xs text-gray-400 mt-0.5">{doc.date}</p>
              <div className="flex items-center justify-between mt-3">
                <span className={`text-[10px] font-black px-2 py-0.5 rounded-full ${doc.status === 'ready' ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'}`}>{doc.status}</span>
                <button onClick={() => toast.success('Document downloaded!')}
                  className="text-xs text-teal-600 font-black hover:underline">Download</button>
              </div>
            </div>
          ))}
        </div>
        <div className="mt-4 p-4 bg-orange-50 border border-orange-200 rounded-xl flex items-center gap-3">
          <Clock size={16} className="text-orange-500 shrink-0" />
          <p className="text-xs font-bold text-orange-700">Quarterly estimated tax due Jan 15, 2025 · Estimated: ₹28,600</p>
        </div>
      </div>
    </div>
  );
};

export default FinancialManagement;
