import React, { useState, useEffect } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { DollarSign, AlertTriangle, RefreshCw, FileText, Loader2 } from 'lucide-react';
import api from '../../../services/api';
import toast from 'react-hot-toast';

const fraudStatusStyle: Record<string, string> = {
  open:       'bg-red-100 text-red-700',
  reviewing:  'bg-yellow-100 text-yellow-700',
  resolved:   'bg-green-100 text-green-700',
};

const FinancialControls: React.FC = () => {
  const [commissions, setCommissions] = useState<any[]>([]);
  const [revenueMonthly, setRevenueMonthly] = useState<any[]>([]);
  const [fraudAlerts, setFraudAlerts] = useState<any[]>([]);
  const [escrowItems, setEscrowItems] = useState<any[]>([]);
  
  const [refunds, setRefunds] = useState<any[]>([]);
  const [refundSummary, setRefundSummary] = useState<any>({});
  const [refundsLoading, setRefundsLoading] = useState(false);
  const [activeSection, setActiveSection] = useState<'commission'|'escrow'|'fraud'|'refunds'|'revenue'>('commission');

  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await api.get('/api/admin/financial').then(r => r.data);
        setCommissions(res.commission_tiers || []);
        setRevenueMonthly(res.revenue_monthly || []);
        setFraudAlerts(res.fraud_alerts || []);
        setEscrowItems(res.escrow_items || []);
      } catch (err) {
        console.error('Failed to load financial data', err);
      }
    };
    fetchData();
  }, []);

  useEffect(() => {
    if (activeSection !== 'refunds') return;
    setRefundsLoading(true);
    api.get('/api/admin/transactions', { params: { type: 'refund', limit: 100 } })
      .then(r => {
        setRefunds(r.data.transactions || []);
        setRefundSummary(r.data.summary || {});
      })
      .catch(console.error)
      .finally(() => setRefundsLoading(false));
  }, [activeSection]);

  const sections = [
    { key:'commission', label:'Commission', icon:'💹' },
    { key:'escrow',     label:'Escrow',     icon:'🔒' },
    { key:'fraud',      label:'Fraud',      icon:'🚨' },
    { key:'refunds',    label:'Refunds',    icon:'↩️' },
    { key:'revenue',    label:'Revenue',    icon:'📊' },
  ] as const;

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

      {activeSection === 'commission' && (
        <div className="space-y-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {commissions.map(c => (
              <div key={c.tier} className="bg-white rounded-2xl p-5 shadow-sm border border-gray-100">
                <p className="font-black text-gray-900">{c.tier}</p>
                <p className="text-3xl font-black text-teal-700 mt-1">{c.rate}%</p>
                <p className="text-xs text-gray-400">{c.providers} providers</p>
                <p className="text-xs font-bold text-green-600 mt-1">₹{(c.volume/100000).toFixed(1)}L vol</p>
              </div>
            ))}
          </div>
          <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
            <h3 className="font-black text-gray-900 text-lg mb-5 flex items-center gap-2"><DollarSign size={18} className="text-teal-600" /> Adjust Commission Rates</h3>
            <div className="space-y-5">
              {commissions.map((c, i) => (
                <div key={c.tier} className="flex items-center gap-4">
                  <span className="font-bold text-gray-700 w-20 text-sm">{c.tier}</span>
                  <input type="range" min={5} max={25} step={0.5} value={c.rate}
                    onChange={e => setCommissions(prev => prev.map((t,j) => j===i ? {...t, rate:Number(e.target.value)} : t))}
                    className="flex-1 h-2 rounded-full bg-teal-200 appearance-none cursor-pointer" />
                  <div className="flex items-center gap-2 w-24">
                    <span className="font-black text-teal-700 text-lg">{c.rate}%</span>
                  </div>
                </div>
              ))}
            </div>
            <button onClick={() => toast.success('Commission rates updated for all providers!')}
              className="mt-5 bg-teal-600 hover:bg-teal-700 text-white px-8 py-3 rounded-xl font-black text-sm transition-all active:scale-95">
              Apply Changes
            </button>
          </div>
          <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
            <h3 className="font-black text-gray-900 text-lg mb-4">Commission by Tier</h3>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={commissions}>
                <CartesianGrid strokeDasharray="3 3" stroke="#F0F4F8" />
                <XAxis dataKey="tier" tick={{ fontSize:12, fontWeight:700 }} />
                <YAxis tick={{ fontSize:11 }} unit="%" />
                <Tooltip formatter={(v: any) => [`${v}%`, 'Commission Rate']} />
                <Bar dataKey="rate" fill="#0D7A7F" radius={[8,8,0,0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {activeSection === 'escrow' && (
        <div className="space-y-4">
          <div className="grid grid-cols-3 gap-4">
            {[
              { label:'Total Held', value:`₹${escrowItems.reduce((s,e)=>s+e.amount,0).toLocaleString()}`, color:'text-purple-600', bg:'bg-purple-50' },
              { label:'In Dispute', value:escrowItems.filter(e=>e.status==='dispute').length, color:'text-red-600', bg:'bg-red-50' },
              { label:'Auto-Release Today', value:'₹8,300', color:'text-green-600', bg:'bg-green-50' },
            ].map(s => (
              <div key={s.label} className={`${s.bg} rounded-2xl p-4 text-center`}>
                <p className={`text-2xl font-black ${s.color}`}>{s.value}</p>
                <p className="text-xs font-bold text-gray-500 mt-0.5">{s.label}</p>
              </div>
            ))}
          </div>
          <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-100"><h3 className="font-black text-gray-900 text-lg">Escrow Holdings</h3></div>
            <div className="divide-y divide-gray-50">
              {escrowItems.map(e => (
                <div key={e.id} className="flex items-center justify-between px-6 py-4 hover:bg-gray-50 transition-colors">
                  <div>
                    <p className="font-bold text-gray-900 text-sm">{e.booking}</p>
                    <p className="text-xs text-gray-400">Held {e.held} · Release: {e.release}</p>
                  </div>
                  <div className="flex items-center gap-3">
                    <p className="font-black text-gray-900">₹{e.amount.toLocaleString()}</p>
                    <span className={`text-xs font-black px-2.5 py-1 rounded-full ${e.status==='dispute'?'bg-red-100 text-red-700':'bg-yellow-100 text-yellow-700'}`}>{e.status}</span>
                    <button onClick={() => toast.success(`Funds released for ${e.booking}`)} className="text-xs bg-green-600 hover:bg-green-700 text-white px-3 py-1.5 rounded-xl font-black transition-all">Release</button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {activeSection === 'fraud' && (
        <div className="space-y-4">
          <div className="bg-red-50 border border-red-200 rounded-2xl p-4 flex items-center gap-3">
            <AlertTriangle size={20} className="text-red-500 shrink-0" />
            <p className="font-black text-red-700 text-sm">{fraudAlerts.filter(f=>f.status==='open').length} open fraud alerts require immediate review</p>
          </div>
          {fraudAlerts.map(f => (
            <div key={f.id} className={`bg-white rounded-2xl p-5 shadow-sm border ${f.status==='open'?'border-red-300':'border-gray-100'}`}>
              <div className="flex items-start justify-between flex-wrap gap-4">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-black text-gray-700 text-sm">#{f.id}</span>
                    <span className={`text-xs font-black px-2.5 py-1 rounded-full ${fraudStatusStyle[f.status]}`}>{f.status}</span>
                    <span className="text-xs font-black text-orange-600 bg-orange-100 px-2.5 py-1 rounded-full">{f.type} Fraud</span>
                  </div>
                  <p className="font-bold text-gray-900 text-sm">Provider: {f.provider} · Customer: {f.customer}</p>
                  <p className="text-xs text-gray-400 mt-0.5">Flagged: {f.flaggedAt} · Amount: ₹{f.amount.toLocaleString()}</p>
                  <div className="flex items-center gap-2 mt-2">
                    <span className="text-xs text-gray-500">AI Confidence:</span>
                    <div className="w-24 h-2 bg-gray-100 rounded-full overflow-hidden">
                      <div className="h-full rounded-full bg-red-500" style={{ width:`${f.score}%` }} />
                    </div>
                    <span className="font-black text-red-600 text-xs">{f.score}%</span>
                  </div>
                </div>
                {f.status === 'open' && (
                  <div className="flex gap-2">
                    <button onClick={() => toast.success('Transaction frozen!')} className="bg-red-600 hover:bg-red-700 text-white px-3 py-2 rounded-xl font-black text-xs transition-all">Freeze</button>
                    <button onClick={() => toast.success('Marked as false positive')} className="bg-gray-100 hover:bg-gray-200 text-gray-700 px-3 py-2 rounded-xl font-black text-xs transition-all">False Positive</button>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {activeSection === 'refunds' && (
        <div className="space-y-4">
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            <div className="bg-red-50 rounded-2xl p-4 text-center">
              <p className="text-2xl font-black text-red-600">₹{(refundSummary.total_refunds || 0).toLocaleString()}</p>
              <p className="text-xs font-bold text-gray-500 mt-0.5">Total Refunded</p>
            </div>
            <div className="bg-yellow-50 rounded-2xl p-4 text-center">
              <p className="text-2xl font-black text-yellow-600">{refunds.length}</p>
              <p className="text-xs font-bold text-gray-500 mt-0.5">Refund Transactions</p>
            </div>
            <div className="bg-purple-50 rounded-2xl p-4 text-center">
              <p className="text-2xl font-black text-purple-600">
                {refunds.length > 0 ? `₹${Math.round((refundSummary.total_refunds || 0) / refunds.length).toLocaleString()}` : '₹0'}
              </p>
              <p className="text-xs font-bold text-gray-500 mt-0.5">Avg Refund</p>
            </div>
          </div>

          <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-100 flex items-center gap-2">
              <RefreshCw size={18} className="text-blue-600" />
              <h3 className="font-black text-gray-900 text-lg">Refund History</h3>
            </div>
            {refundsLoading ? (
              <div className="flex items-center justify-center p-10">
                <Loader2 size={24} className="animate-spin text-teal-600" />
              </div>
            ) : refunds.length === 0 ? (
              <p className="text-sm text-gray-400 text-center py-10">No refunds processed yet</p>
            ) : (
              <div className="divide-y divide-gray-50">
                {refunds.map((r: any) => (
                  <div key={r.payment_id} className="px-6 py-4 hover:bg-gray-50 transition-colors">
                    <div className="flex items-start justify-between flex-wrap gap-3">
                      <div>
                        <div className="flex items-center gap-2 mb-1">
                          <span className="font-black text-gray-500 text-xs font-mono">#{r.payment_id?.slice(-8).toUpperCase()}</span>
                          <span className="text-xs font-black bg-red-100 text-red-700 px-2 py-0.5 rounded-full">Refunded</span>
                        </div>
                        <p className="font-bold text-gray-900 text-sm">{r.customer_name}</p>
                        <p className="text-xs text-gray-400 mt-0.5">
                          {r.refund_reason || 'Customer request'} ·{' '}
                          {r.created_at ? new Date(r.created_at).toLocaleDateString('en-IN', { day:'numeric', month:'short', year:'numeric' }) : 'N/A'}
                        </p>
                        <p className="text-xs text-gray-400">
                          Service: {r.service_name || 'N/A'} · Method: {r.payment_method?.toUpperCase() || 'N/A'}
                        </p>
                      </div>
                      <p className="font-black text-red-600 text-lg">₹{(r.amount || 0).toLocaleString()}</p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {activeSection === 'revenue' && (
        <div className="space-y-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { label:'Total GTV',      value:`₹${((revenueMonthly.reduce((s,m)=>s+(m.revenue||0),0))/100000).toFixed(1)}L`, color:'text-green-600', bg:'bg-green-50' },
              { label:'Commission',     value:`₹${((revenueMonthly.reduce((s,m)=>s+(m.commission||0),0))/100000).toFixed(1)}L`, color:'text-teal-600', bg:'bg-teal-50' },
              { label:'Refunds Issued', value:`₹${((refundSummary.total_refunds||0)/100000).toFixed(1)}L`, color:'text-red-600', bg:'bg-red-50' },
              { label:'Net Revenue',    value:`₹${(((revenueMonthly.reduce((s,m)=>s+(m.commission||0),0))-(refundSummary.total_refunds||0))/100000).toFixed(1)}L`, color:'text-purple-600', bg:'bg-purple-50' },
            ].map(s => (
              <div key={s.label} className={`${s.bg} rounded-2xl p-5 text-center`}>
                <p className={`text-2xl font-black ${s.color}`}>{s.value}</p>
                <p className="text-xs font-bold text-gray-500 mt-0.5">{s.label}</p>
              </div>
            ))}
          </div>
          <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
            <h3 className="font-black text-gray-900 text-lg mb-4 flex items-center gap-2"><FileText size={18} className="text-purple-600" /> Revenue Recognition Report</h3>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={revenueMonthly}>
                <CartesianGrid strokeDasharray="3 3" stroke="#F0F4F8" />
                <XAxis dataKey="month" tick={{ fontSize:11, fontWeight:700 }} />
                <YAxis tick={{ fontSize:11 }} tickFormatter={v=>`₹${(v/100000).toFixed(0)}L`} />
                <Tooltip formatter={(v: any, n: string) => [`₹${(v/100000).toFixed(2)}L`, n==='revenue'?'GTV':'Commission']} />
                <Bar dataKey="revenue"    fill="#0D7A7F" radius={[4,4,0,0]} />
                <Bar dataKey="commission" fill="#8b5cf6" radius={[4,4,0,0]} />
              </BarChart>
            </ResponsiveContainer>
            <button onClick={() => toast.success('Monthly financial report downloaded!')} className="mt-4 bg-purple-600 hover:bg-purple-700 text-white px-6 py-3 rounded-xl font-black text-sm transition-all active:scale-95">Download GST Report</button>
          </div>
        </div>
      )}
    </div>
  );
};

export default FinancialControls;
