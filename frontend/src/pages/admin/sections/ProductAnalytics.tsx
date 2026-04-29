import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { BarChart3, Users, Search, TrendingDown, Loader2 } from 'lucide-react';
import api from '../../../services/api';

const barColors = ['#0D7A7F','#3b82f6','#8b5cf6','#f59e0b','#ef4444','#22c55e'];

const ProductAnalytics: React.FC = () => {
  const { data, isLoading } = useQuery({
    queryKey: ['admin-product-analytics'],
    queryFn: () => api.get('/api/admin/product-analytics').then(r => r.data),
  });

  if (isLoading) return (
    <div className="flex items-center justify-center p-16">
      <Loader2 size={28} className="animate-spin text-teal-600" />
    </div>
  );

  const featureUsage: any[]     = data?.feature_usage     || [];
  const searchQueries: any[]    = data?.search_queries     || [];
  const conversionFunnel: any[] = data?.conversion_funnel  || [];
  const cohortData: any[]       = data?.cohort_data        || [];

  return (
    <div className="space-y-6">
      {/* Feature Usage */}
      <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
        <h3 className="font-black text-gray-900 text-lg flex items-center gap-2 mb-5">
          <BarChart3 size={18} className="text-teal-600" /> Feature Usage Analytics
        </h3>
        {featureUsage.length === 0 ? (
          <p className="text-sm text-gray-400 text-center py-6">No feature usage data yet</p>
        ) : (
          <div className="space-y-3 mb-5">
            {featureUsage.map((f: any, i: number) => (
              <div key={f.feature} className="flex items-center gap-3">
                <span className="text-xs font-bold text-gray-500 w-36 shrink-0">{f.feature}</span>
                <div className="flex-1 h-7 bg-gray-100 rounded-xl overflow-hidden">
                  <div className="h-full rounded-xl flex items-center px-3 transition-all"
                    style={{ width: `${(f.sessions / (featureUsage[0]?.sessions || 1)) * 100}%`, backgroundColor: barColors[i % barColors.length] }}>
                    <span className="text-white text-xs font-black">{f.sessions.toLocaleString()}</span>
                  </div>
                </div>
                <span className="text-xs text-gray-400 w-16 shrink-0 text-right">{f.avg_time}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Conversion Funnel */}
      <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
        <h3 className="font-black text-gray-900 text-lg mb-5">Conversion Funnel — Search → Booking</h3>
        {conversionFunnel.length === 0 ? (
          <p className="text-sm text-gray-400 text-center py-6">No funnel data yet</p>
        ) : (
          <div className="space-y-3">
            {conversionFunnel.map((step: any, i: number) => (
              <div key={step.step} className="flex items-center gap-4">
                <span className="text-xs font-bold text-gray-500 w-36 shrink-0">{step.step}</span>
                <div className="flex-1 h-8 bg-gray-100 rounded-xl overflow-hidden">
                  <div className="h-full rounded-xl flex items-center px-3 transition-all"
                    style={{ width: `${step.pct}%`, backgroundColor: barColors[i % barColors.length] }}>
                    <span className="text-white text-xs font-black">{step.count.toLocaleString()}</span>
                  </div>
                </div>
                <span className="font-black text-gray-700 text-sm w-10 text-right">{step.pct}%</span>
                {i > 0 && (
                  <span className="text-xs text-red-500 font-bold w-16">
                    -{(conversionFunnel[i - 1].pct - step.pct)}pts
                  </span>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Search Queries */}
      <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
        <h3 className="font-black text-gray-900 text-lg flex items-center gap-2 mb-4">
          <Search size={18} className="text-orange-600" /> Top Search Queries
        </h3>
        {searchQueries.length === 0 ? (
          <p className="text-sm text-gray-400 text-center py-6">No search data yet</p>
        ) : (
          <div className="space-y-3">
            {searchQueries.map((q: any) => (
              <div key={q.query} className={`flex items-center justify-between p-4 rounded-xl ${q.zero_result ? 'bg-red-50 border border-red-100' : 'bg-gray-50'}`}>
                <div className="flex items-center gap-3">
                  <div className={`w-2.5 h-2.5 rounded-full ${q.zero_result ? 'bg-red-500' : 'bg-green-500'}`} />
                  <p className="font-bold text-gray-900 text-sm">{q.query}</p>
                </div>
                <div className="flex items-center gap-3">
                  <span className="font-black text-gray-700 text-sm">{q.count.toLocaleString()}</span>
                  <span className={`text-xs font-black px-2.5 py-1 rounded-full ${q.zero_result ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700'}`}>
                    {q.zero_result ? '0 results' : 'found'}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
        {searchQueries.filter((q: any) => q.zero_result).length > 0 && (
          <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded-xl flex items-center gap-2">
            <TrendingDown size={14} className="text-red-500 shrink-0" />
            <p className="text-xs font-bold text-red-700">
              {searchQueries.filter((q: any) => q.zero_result).length} zero-result queries detected — consider adding these service categories
            </p>
          </div>
        )}
      </div>

      {/* Cohort Retention */}
      {cohortData.length > 0 && (
        <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
          <h3 className="font-black text-gray-900 text-lg flex items-center gap-2 mb-4">
            <Users size={18} className="text-purple-600" /> Provider Retention Cohorts
          </h3>
          <p className="text-xs text-gray-400 mb-4">% of providers still active by month after signup</p>
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="bg-gray-50">
                  <th className="text-left py-2.5 px-3 font-black text-gray-400">Cohort</th>
                  {['M0','M1','M2','M3'].map(m => (
                    <th key={m} className="py-2.5 px-3 font-black text-gray-400">{m}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {cohortData.map((row: any) => (
                  <tr key={row.month} className="border-t border-gray-50">
                    <td className="py-2.5 px-3 font-bold text-gray-700">{row.month}</td>
                    {[row.m0, row.m1, row.m2, row.m3].map((v: any, i: number) => (
                      <td key={i} className="py-2.5 px-3 text-center">
                        {v != null ? (
                          <span className="inline-block w-12 py-1 rounded-lg font-black text-white text-[10px]"
                            style={{ backgroundColor: v >= 70 ? '#22c55e' : v >= 50 ? '#3b82f6' : v >= 30 ? '#f59e0b' : '#ef4444' }}>
                            {v}%
                          </span>
                        ) : <span className="text-gray-200">—</span>}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};

export default ProductAnalytics;
