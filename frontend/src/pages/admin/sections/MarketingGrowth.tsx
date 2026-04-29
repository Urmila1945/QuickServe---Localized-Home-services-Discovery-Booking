import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { Megaphone, Tag, Share2, Search, Handshake, Loader2 } from 'lucide-react';
import api from '../../../services/api';
import toast from 'react-hot-toast';

const MarketingGrowth: React.FC = () => {
  const [activeSection, setActiveSection] = useState<'campaigns'|'promos'|'referrals'|'seo'|'partners'>('campaigns');

  const { data, isLoading } = useQuery({
    queryKey: ['admin-marketing'],
    queryFn: () => api.get('/api/admin/marketing').then(r => r.data),
  });

  const sections = [
    { key:'campaigns',  label:'Campaigns',   icon:'📢' },
    { key:'promos',     label:'Promo Codes',  icon:'🏷️' },
    { key:'referrals',  label:'Referrals',   icon:'🔗' },
    { key:'seo',        label:'SEO',         icon:'🔍' },
    { key:'partners',   label:'Partners',    icon:'🤝' },
  ] as const;

  const campaigns: any[]    = data?.campaigns    || [];
  const promoCodes: any[]   = data?.promo_codes   || [];
  const referrals: any[]    = data?.top_referrers || [];
  const seoKeywords: any[]  = data?.seo_keywords  || [];
  const partners: any[]     = data?.partners      || [];
  const referralStats: any  = data?.referral_stats || {};

  if (isLoading) return (
    <div className="flex items-center justify-center p-16">
      <Loader2 size={28} className="animate-spin text-teal-600" />
    </div>
  );

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

      {activeSection === 'campaigns' && (
        <div className="space-y-4">
          <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
              <h3 className="font-black text-gray-900 text-lg flex items-center gap-2"><Megaphone size={18} className="text-teal-600" /> Campaign Manager</h3>
              <button onClick={() => toast.success('New campaign builder opened!')} className="bg-teal-600 hover:bg-teal-700 text-white px-4 py-2 rounded-xl font-black text-sm transition-all">+ New Campaign</button>
            </div>
            {campaigns.length === 0 ? (
              <p className="text-sm text-gray-400 text-center py-10">No campaigns yet</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gray-50">
                    <tr>{['Campaign','Type','Target','Sent','Opens','Conversions','ROI','Action'].map(h=>(
                      <th key={h} className="text-left py-3 px-4 font-black text-gray-400 text-xs uppercase tracking-wider">{h}</th>
                    ))}</tr>
                  </thead>
                  <tbody className="divide-y divide-gray-50">
                    {campaigns.map((c: any) => (
                      <tr key={c.id} className="hover:bg-gray-50 transition-colors">
                        <td className="py-3.5 px-4 font-bold text-gray-900 text-sm">{c.name}</td>
                        <td className="py-3.5 px-4"><span className="text-xs font-black bg-blue-100 text-blue-700 px-2.5 py-1 rounded-full">{c.type}</span></td>
                        <td className="py-3.5 px-4 text-gray-500 text-sm">{c.target}</td>
                        <td className="py-3.5 px-4 font-bold text-gray-700">{(c.sent||0).toLocaleString()}</td>
                        <td className="py-3.5 px-4 font-bold text-blue-600">{(c.opens||0).toLocaleString()}</td>
                        <td className="py-3.5 px-4 font-bold text-green-600">{(c.conversions||0).toLocaleString()}</td>
                        <td className="py-3.5 px-4 font-black text-purple-600">{c.roi}%</td>
                        <td className="py-3.5 px-4">
                          <button onClick={() => toast.success('Report exported')} className="text-xs bg-teal-100 hover:bg-teal-200 text-teal-700 px-2.5 py-1 rounded-xl font-black transition-all">Export</button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
          {campaigns.length > 0 && (
            <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
              <h4 className="font-black text-gray-900 text-sm mb-4">Campaign Performance</h4>
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={campaigns}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#F0F4F8" />
                  <XAxis dataKey="name" tick={{ fontSize:10, fontWeight:700 }} />
                  <YAxis tick={{ fontSize:10 }} />
                  <Tooltip />
                  <Bar dataKey="conversions" fill="#0D7A7F" radius={[6,6,0,0]} name="Conversions" />
                  <Bar dataKey="roi"         fill="#8b5cf6" radius={[6,6,0,0]} name="ROI %" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      )}

      {activeSection === 'promos' && (
        <div className="space-y-4">
          <div className="flex justify-end">
            <button onClick={() => toast.success('Promo code generator opened!')} className="bg-teal-600 hover:bg-teal-700 text-white px-5 py-2.5 rounded-xl font-black text-sm transition-all flex items-center gap-2"><Tag size={14} /> Generate Promo Codes</button>
          </div>
          {promoCodes.length === 0 ? (
            <div className="bg-white rounded-2xl p-10 text-center shadow-sm border border-gray-100">
              <p className="text-3xl mb-2">🏷️</p>
              <p className="text-sm font-bold text-gray-400">No promo codes yet</p>
            </div>
          ) : promoCodes.map((p: any) => (
            <div key={p.code} className="bg-white rounded-2xl p-5 shadow-sm border border-gray-100">
              <div className="flex items-start justify-between flex-wrap gap-4">
                <div className="flex items-center gap-4">
                  <div className="bg-teal-600 text-white font-black text-lg px-5 py-3 rounded-xl tracking-widest">{p.code}</div>
                  <div>
                    <p className="font-black text-gray-900">{p.discount} off</p>
                    <p className="text-xs text-gray-400">{(p.uses||0).toLocaleString()} uses · Expires {p.expires}</p>
                    <div className="flex items-center gap-2 mt-1">
                      <div className="w-32 h-2 bg-gray-100 rounded-full overflow-hidden">
                        <div className="h-full bg-teal-500 rounded-full" style={{ width:`${Math.min(100, Math.round((p.redeemed||0)/(p.budget||1)*100))}%` }} />
                      </div>
                      <span className="text-xs text-gray-400">{Math.round((p.redeemed||0)/(p.budget||1)*100)}% used</span>
                    </div>
                  </div>
                </div>
                <div className="grid grid-cols-3 gap-4 text-center">
                  {[
                    { label:'Budget',   value:`₹${((p.budget||0)/1000).toFixed(0)}k`   },
                    { label:'Redeemed', value:`₹${((p.redeemed||0)/1000).toFixed(0)}k` },
                    { label:'ROI',      value:`${p.roi||0}%`                            },
                  ].map(s => (
                    <div key={s.label}>
                      <p className="font-black text-gray-900 text-sm">{s.value}</p>
                      <p className="text-[10px] text-gray-400">{s.label}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {activeSection === 'referrals' && (
        <div className="space-y-4">
          <div className="grid grid-cols-3 gap-4">
            {[
              { label:'Total Referrals',  value: referralStats.total_referrals || 0,                                    color:'text-blue-600',   bg:'bg-blue-50'   },
              { label:'Revenue via Refs', value: `₹${((referralStats.revenue_from_referrals||0)/100).toFixed(0)}`,     color:'text-purple-600', bg:'bg-purple-50' },
              { label:'Conversion Rate',  value: `${referralStats.conversion_rate || 0}%`,                              color:'text-green-600',  bg:'bg-green-50'  },
            ].map(s => (
              <div key={s.label} className={`${s.bg} rounded-2xl p-4 text-center`}>
                <p className={`text-2xl font-black ${s.color}`}>{s.value}</p>
                <p className="text-xs font-bold text-gray-500 mt-0.5">{s.label}</p>
              </div>
            ))}
          </div>
          <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-100"><h3 className="font-black text-gray-900 text-lg flex items-center gap-2"><Share2 size={18} className="text-purple-600" /> Top Referrers</h3></div>
            {referrals.length === 0 ? (
              <p className="text-sm text-gray-400 text-center py-10">No referral data yet</p>
            ) : (
              <div className="divide-y divide-gray-50">
                {referrals.map((r: any, i: number) => (
                  <div key={r.user_id || i} className="flex items-center justify-between px-6 py-4 hover:bg-gray-50 transition-colors">
                    <div className="flex items-center gap-3">
                      <span className={`w-8 h-8 rounded-full flex items-center justify-center font-black text-sm ${i===0?'bg-yellow-400 text-white':i===1?'bg-gray-300 text-gray-700':'bg-gray-100 text-gray-600'}`}>{i+1}</span>
                      <p className="font-bold text-gray-900 text-sm">{r.name}</p>
                    </div>
                    <div className="flex items-center gap-4">
                      <div className="text-center">
                        <p className="font-black text-blue-600">{r.referrals}</p>
                        <p className="text-[10px] text-gray-400">referrals</p>
                      </div>
                      <div className="text-center">
                        <p className="font-black text-green-600">₹{(r.revenue||0).toLocaleString()}</p>
                        <p className="text-[10px] text-gray-400">revenue</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {activeSection === 'seo' && (
        <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
          <h3 className="font-black text-gray-900 text-lg flex items-center gap-2 mb-5"><Search size={18} className="text-blue-600" /> Top Search Queries</h3>
          {seoKeywords.length === 0 ? (
            <p className="text-sm text-gray-400 text-center py-10">No search query data yet</p>
          ) : (
            <div className="space-y-3">
              {seoKeywords.map((k: any, i: number) => (
                <div key={k.query || i} className="flex items-center gap-4 p-4 bg-gray-50 rounded-xl">
                  <div className="w-8 h-8 rounded-xl bg-teal-100 text-teal-700 flex items-center justify-center font-black text-sm shrink-0">
                    #{i+1}
                  </div>
                  <div className="flex-1">
                    <p className="font-bold text-gray-900 text-sm">{k.query}</p>
                    <p className="text-xs text-gray-400">{(k.count||0).toLocaleString()} searches</p>
                  </div>
                  <span className={`text-xs font-black px-2.5 py-1 rounded-full ${k.zero_result?'bg-red-100 text-red-700':'bg-green-100 text-green-700'}`}>
                    {k.zero_result ? '0 results' : 'found'}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {activeSection === 'partners' && (
        <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
          <h3 className="font-black text-gray-900 text-lg flex items-center gap-2 mb-5"><Handshake size={18} className="text-orange-600" /> Partnership Portal</h3>
          {partners.length === 0 ? (
            <p className="text-sm text-gray-400 text-center py-10">No partners configured yet</p>
          ) : (
            <div className="grid sm:grid-cols-2 gap-4">
              {partners.map((p: any) => (
                <div key={p.name} className={`border-2 rounded-xl p-4 ${p.status==='active'?'border-green-200 bg-green-50/30':'border-yellow-200 bg-yellow-50/30'}`}>
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="font-black text-gray-900">{p.name}</p>
                      <p className="text-xs text-gray-500">{p.type}</p>
                      <p className="text-xs font-bold text-teal-700 mt-1">{p.deal}</p>
                    </div>
                    <span className={`text-[10px] font-black px-2.5 py-1 rounded-full ${p.status==='active'?'bg-green-100 text-green-700':'bg-yellow-100 text-yellow-700'}`}>{p.status}</span>
                  </div>
                  <div className="flex items-center justify-between mt-3">
                    <span className="font-black text-green-600 text-sm">{p.value}</span>
                    <button onClick={() => toast.success(`Partnership details for ${p.name} opened`)} className="text-xs bg-gray-100 hover:bg-gray-200 text-gray-700 px-3 py-1.5 rounded-xl font-black transition-all">Manage</button>
                  </div>
                </div>
              ))}
            </div>
          )}
          <button onClick={() => toast.success('Partnership request form opened!')} className="mt-4 w-full border-2 border-dashed border-orange-200 text-orange-500 font-bold py-3 rounded-xl hover:bg-orange-50 transition-colors">+ Add New Partnership</button>
        </div>
      )}
    </div>
  );
};

export default MarketingGrowth;
