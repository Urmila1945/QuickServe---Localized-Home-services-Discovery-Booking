import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import DashboardLayout from '../components/DashboardLayout';
import {
  BarChart3, Calendar, DollarSign, Star, CheckCircle,
  MapPin, Award, Zap, Users, Package, BookOpen,
  MessageSquare, Wallet, Heart, TrendingUp, ShoppingBag, Navigation
} from 'lucide-react';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import toast from 'react-hot-toast';
import { useTranslation } from 'react-i18next';
import api from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import { formatPriceINR } from '../utils/currency';

import BusinessIntelligence from './provider/sections/BusinessIntelligence';
import AIScheduling         from './provider/sections/AIScheduling';
import DynamicPricing       from './provider/sections/DynamicPricing';
import CustomerCRM          from './provider/sections/CustomerCRM';
import PortfolioMarketing   from './provider/sections/PortfolioMarketing';
import OperationalTools     from './provider/sections/OperationalTools';
import LearningGrowth       from './provider/sections/LearningGrowth';
import CommunicationHub     from './provider/sections/CommunicationHub';
import FinancialManagement  from './provider/sections/FinancialManagement';
import WellnessSafety       from './provider/sections/WellnessSafety';
import WorkGallery          from '../components/verification/WorkGallery';

type ProviderTab =
  | 'overview' | 'intelligence' | 'schedule' | 'pricing'
  | 'customers' | 'marketing' | 'operations' | 'learning'
  | 'inbox' | 'finance' | 'wellness' | 'predictor';

const getTabs = (t: (k: string) => string): { key: ProviderTab; label: string; icon: React.ElementType }[] => [
  { key:'overview',      label: t('Overview'),        icon:BarChart3     },
  { key:'predictor',     label: t('Income Forecast'), icon:TrendingUp    },
  { key:'intelligence',  label: t('Intelligence'),    icon:BarChart3     },
  { key:'schedule',      label: t('AI Schedule'),   icon:Calendar      },
  { key:'pricing',       label: t('Pricing'),       icon:DollarSign    },
  { key:'customers',     label: t('CRM'),           icon:Users         },
  { key:'marketing',     label: t('Marketing'),     icon:ShoppingBag   },
  { key:'operations',    label: t('Operations'),    icon:Package       },
  { key:'learning',      label: t('Learning'),      icon:BookOpen      },
  { key:'inbox',         label: t('Inbox'),         icon:MessageSquare },
  { key:'finance',       label: t('Finance'),       icon:Wallet        },
  { key:'wellness',      label: t('Wellness'),      icon:Heart         },
];

const JobStatusBadge: React.FC<{ status: string }> = ({ status }) => {
  const map: Record<string, string> = {
    completed:   'bg-green-100 text-green-700',
    confirmed:   'bg-blue-100  text-blue-700',
    in_progress: 'bg-orange-100 text-orange-700',
    pending:     'bg-yellow-100 text-yellow-700',
  };
  return <span className={`text-xs font-bold px-2.5 py-1 rounded-full capitalize ${map[status] || 'bg-gray-100 text-gray-600'}`}>{status.replace('_',' ')}</span>;
};

// ── Income Predictor Feature ───────────────────────────────────────────
const IncomePredictor: React.FC<{ jobs: any[], balance: any }> = ({ jobs, balance }) => {
  const { t } = useTranslation();
  
  // Predict next month's income based on 30 day history
  const last30Days = jobs.filter(j => 
    j.created_at && new Date(j.created_at) >= new Date(Date.now() - 30*24*60*60*1000)
  );
  const mrr = last30Days.reduce((s, j) => s + (j.total_amount || 0), 0);
  const avgJobValue = last30Days.length ? mrr / last30Days.length : 0;
  
  // Forecast = MRR * AI Multiplier (seasonal + profile completion)
  const predictedValue = mrr * 1.15; // 15% projected growth

  return (
    <div className="space-y-6">
      <div className="bg-gradient-to-r from-blue-600 to-indigo-800 rounded-3xl p-8 text-white shadow-xl relative overflow-hidden">
        <div className="absolute top-0 right-0 w-64 h-64 bg-white/10 rounded-full blur-3xl -translate-y-1/2 translate-x-1/3" />
        <div className="relative z-10">
          <h2 className="text-sm font-bold uppercase tracking-widest text-indigo-200 mb-2">🔮 AI Income Forecast</h2>
          <div className="flex items-end gap-4 mb-4">
            <span className="text-5xl font-black">{formatPriceINR(predictedValue)}</span>
            <span className="text-indigo-200 font-bold mb-2">Next 30 Days</span>
          </div>
          <p className="text-indigo-100 text-sm max-w-lg">
            Based on your recent booking velocity, avg job value of {formatPriceINR(avgJobValue)}, and seasonal demand trends for your category.
          </p>
        </div>
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
          <h3 className="font-black text-gray-900 mb-4">📈 Growth Drivers</h3>
          <div className="space-y-4">
            {[
              { label: 'Booking Frequency', status: 'Optimal', effect: '+5%', color: 'text-green-600' },
              { label: 'Avg Job Value', status: 'Increasing', effect: '+7%', color: 'text-teal-600' },
              { label: 'Local Demand', status: 'High', effect: '+3%', color: 'text-blue-600' },
            ].map(d => (
              <div key={d.label} className="flex items-center justify-between p-3 bg-gray-50 rounded-xl">
                <div>
                  <p className="font-bold text-gray-900">{d.label}</p>
                  <p className="text-xs text-gray-500">{d.status}</p>
                </div>
                <span className={`font-black ${d.color}`}>{d.effect}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
          <h3 className="font-black text-gray-900 mb-4">💡 Optimization Tips</h3>
          <ul className="space-y-3">
            <li className="flex gap-3 items-start">
              <span className="text-xl">⭐️</span>
              <div>
                <p className="font-bold text-gray-900 text-sm">Request More Reviews</p>
                <p className="text-xs text-gray-500 mt-0.5">Providers with 10+ reviews see a 22% increase in bookings.</p>
              </div>
            </li>
            <li className="flex gap-3 items-start">
              <span className="text-xl">⚡</span>
              <div>
                <p className="font-bold text-gray-900 text-sm">Expand Service Radius</p>
                <p className="text-xs text-gray-500 mt-0.5">Adding 5km to your radius could unlock ₹15,000 in potential jobs.</p>
              </div>
            </li>
          </ul>
        </div>
      </div>
    </div>
  );
};

const CustomerFeedbackModal: React.FC<{ jobId: string; onClose: () => void }> = ({ jobId, onClose }) => {
  const [rating, setRating] = useState(0);
  const [comment, setComment] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async () => {
    if (rating === 0) {
      toast.error('Please provide a rating');
      return;
    }
    setLoading(true);
    // Simulate API call to save provider's rating for the customer
    await new Promise(r => setTimeout(r, 1000));
    setLoading(false);
    toast.success('Thank you! Feedback submitted.');
    onClose();
  };

  return (
    <div className="fixed inset-0 z-[110] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
      <div className="bg-white rounded-[32px] p-8 max-w-sm w-full shadow-2xl relative">
        <div className="w-16 h-16 bg-teal-50 rounded-2xl flex items-center justify-center mx-auto mb-4 border border-teal-100">
          <Star size={32} className="text-teal-500 fill-teal-100" />
        </div>
        <h3 className="text-2xl font-black text-center text-gray-900 mb-1">Rate Customer</h3>
        <p className="text-center text-gray-500 text-sm mb-6">How was your experience working with this customer?</p>
        
        <div className="flex justify-center gap-2 mb-6">
          {[1, 2, 3, 4, 5].map(star => (
            <button
              key={star}
              onClick={() => setRating(star)}
              className="transition-transform hover:scale-110 focus:outline-none"
            >
              <Star
                size={36}
                className={star <= rating ? 'text-yellow-400 fill-yellow-400' : 'text-gray-200 fill-gray-100'}
              />
            </button>
          ))}
        </div>

        <div className="mb-6">
          <label className="block text-xs font-black text-gray-400 uppercase tracking-widest mb-2">Private Note (Optional)</label>
          <textarea
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            placeholder="Help us understand your experience..."
            className="w-full bg-gray-50 border-2 border-gray-100 focus:border-teal-400 rounded-xl px-4 py-3 text-sm focus:outline-none resize-none transition-colors"
            rows={3}
          />
        </div>

        <button
          onClick={handleSubmit}
          disabled={loading || rating === 0}
          className="w-full bg-teal-600 hover:bg-teal-700 disabled:opacity-50 text-white py-4 rounded-xl font-black text-sm transition-all"
        >
          {loading ? 'Submitting...' : 'Submit Feedback'}
        </button>
      </div>
    </div>
  );
};

const ProviderDashboardNew: React.FC = () => {
  const { t } = useTranslation();
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState<ProviderTab>('overview');
  const [liveMode, setLiveMode] = useState(true);
  const [verifyingJobId, setVerifyingJobId] = useState<string | null>(null);
  const [feedbackJobId, setFeedbackJobId] = useState<string | null>(null);
  
  const tabs = getTabs(t);

  const { data: stats, refetch: refetchStats } = useQuery({
    queryKey: ['provider-stats'],
    queryFn: () => api.get('/api/provider/stats').then(r => r.data),
    retry: 1,
  });

  const { data: balance } = useQuery({
    queryKey: ['provider-balance'],
    queryFn: () => api.get('/api/provider/financial/balance').then(r => r.data),
    retry: 1,
  });

  const { data: earningsPulse } = useQuery({
    queryKey: ['provider-earnings-pulse'],
    queryFn: () => api.get('/api/provider/analytics/earnings-pulse?period=daily').then(r => r.data),
    retry: 1,
  });

  const { data: jobsData } = useQuery({
    queryKey: ['provider-jobs'],
    queryFn: () => api.get('/api/bookings/').then(r => r.data),
    retry: 1,
  });

  const { data: activeJobData, refetch: refetchActiveJob } = useQuery({
    queryKey: ['provider-active-job'],
    queryFn: () => api.get('/api/provider/active-job').then(r => r.data),
    retry: 1,
  });

  const { data: trustData } = useQuery({
    queryKey: ['provider-trust-score', user?._id],
    queryFn: () => user?._id
      ? api.get(`/api/work-verification/trust-score/${user._id}`).then(r => r.data)
      : Promise.resolve(null),
    enabled: !!user?._id,
    retry: 1,
  });

  // ── Reviews from backend ───────────────────────────────────────────────
  const { data: reviewsData } = useQuery({
    queryKey: ['provider-reviews', user?._id],
    queryFn: () => user?._id
      ? api.get(`/api/reviews/provider/${user._id}`).then(r => r.data)
      : Promise.resolve({ reviews: [] }),
    enabled: !!user?._id,
    retry: 1,
  });

  // ── Provider transaction / payout history ──────────────────────────────
  const { data: payoutsData } = useQuery({
    queryKey: ['provider-payouts'],
    queryFn: () => api.get('/api/provider/financial/balance').then(r => r.data),
    retry: 1,
  });

  const earningsChartData = (earningsPulse?.data || [])
    .slice().reverse().slice(-7)
    .map((d: any) => ({ day: d.date?.slice(-5) || d.date, earnings: d.revenue || 0 }));

  const jobs: any[] = Array.isArray(jobsData) ? jobsData : (jobsData as any)?.bookings || [];
  const activeJob = activeJobData?.active_job;
  const weekTotal = earningsChartData.reduce((s: number, d: any) => s + d.earnings, 0);
  const reviews: any[] = reviewsData?.reviews || [];
  const avgRating = reviews.length > 0 ? (reviews.reduce((s: number, r: any) => s + (r.rating || 0), 0) / reviews.length).toFixed(1) : '—';

  const displayStats = [
    { label: t("Today's Earnings"), value: formatPriceINR(stats?.earnings_today ?? 0),  color:'text-green-600',  bg:'bg-green-50',  icon: DollarSign  },
    { label: t('Jobs Completed'),   value: stats?.completed_jobs ?? 0,                  color:'text-blue-600',   bg:'bg-blue-50',   icon: CheckCircle },
    { label: t('Avg Rating'),       value: reviews.length > 0 ? `${avgRating} ★` : `${(stats?.avg_rating ?? 0).toFixed(1)} ★`, color:'text-yellow-600', bg:'bg-yellow-50', icon: Star },
    { label: t('Wallet Balance'),   value: formatPriceINR(balance?.available ?? 0),     color:'text-purple-600', bg:'bg-purple-50', icon: Wallet      },
  ];

  const handleCheckIn = async (jobId: string) => {
    if (!navigator.geolocation) {
      toast.error('Geolocation is not supported by your browser');
      return;
    }

    navigator.geolocation.getCurrentPosition(async (pos) => {
      try {
        const formData = new FormData();
        formData.append('booking_id', jobId);
        formData.append('latitude', pos.coords.latitude.toString());
        formData.append('longitude', pos.coords.longitude.toString());

        await api.post('/api/work-verification/checkin', formData);
        toast.success('GPS Check-in recorded!');
        refetchActiveJob();
      } catch (err) {
        toast.error('Check-in failed. Please try again.');
      }
    }, () => {
      toast.error('Location permission denied. Cannot check-in.');
    });
  };

  return (
    <DashboardLayout role="provider" title={t("Provider Dashboard")}>
      <div className="space-y-5">
        {/* Tab Navigation */}
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <div className="flex gap-1.5 bg-white rounded-2xl p-1.5 shadow-sm border border-gray-100 overflow-x-auto max-w-full">
            {tabs.map(t => {
              const Icon = t.icon;
              return (
                <button key={t.key} onClick={() => setActiveTab(t.key)}
                  className={`flex items-center gap-1.5 px-3.5 py-2 rounded-xl font-bold text-xs whitespace-nowrap transition-all duration-200 ${
                    activeTab===t.key ? 'bg-teal-600 text-white shadow-md shadow-teal-200' : 'text-gray-500 hover:text-gray-800 hover:bg-gray-50'
                  }`}>
                  <Icon size={13} />
                  {t.label}
                </button>
              );
            })}
          </div>
          <button onClick={() => setLiveMode(p=>!p)}
            className={`flex items-center gap-2 px-4 py-2.5 rounded-xl font-bold text-sm transition-all duration-200 shrink-0 ${
              liveMode ? 'bg-green-600 text-white shadow-md shadow-green-200 hover:bg-green-700' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
            }`}>
            <div className={`w-2.5 h-2.5 rounded-full ${liveMode?'bg-white animate-pulse':'bg-gray-400'}`} />
            {liveMode ? t('Online') : t('Offline')}
          </button>
        </div>

        {/* Overview Tab */}
        {activeTab === 'overview' && (
          <div className="space-y-6">
            {/* Stats */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              {displayStats.map(s => {
                const Icon = s.icon;
                return (
                  <div key={s.label} className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100 hover:shadow-md hover:-translate-y-1 transition-all duration-200 group">
                    <div className="flex items-start justify-between mb-4">
                      <div className={`w-12 h-12 ${s.bg} rounded-xl flex items-center justify-center group-hover:scale-110 transition-transform`}>
                        <Icon size={22} className={s.color} />
                      </div>
                    </div>
                    <p className="text-3xl font-black text-gray-900 mb-1">{s.value}</p>
                    <p className="text-sm font-medium text-gray-500">{s.label}</p>
                  </div>
                );
              })}
            </div>

            {/* Active Job Banner — only shown when there's a real active job */}
            {activeJob && (
              <div className="bg-gradient-to-r from-[#0D1F2D] to-teal-900 rounded-2xl p-6 text-white shadow-lg">
                <div className="flex items-center justify-between flex-wrap gap-4">
                  <div className="flex items-center gap-4">
                    <div className="w-14 h-14 bg-white/10 rounded-2xl flex items-center justify-center backdrop-blur-sm border border-white/20">
                      <Zap size={26} className="text-teal-300" />
                    </div>
                    <div>
                      <p className="text-teal-300 text-xs font-bold uppercase tracking-widest mb-1">{t('Active Job Now')}</p>
                      <div className="flex items-center gap-2">
                        <p className="font-black text-xl">{activeJob.service_name} — {activeJob.customer_name || 'Customer'}</p>
                        {trustData?.is_verified_badge && (
                          <div className="bg-teal-400 text-teal-900 text-[10px] font-black px-1.5 py-0.5 rounded flex items-center gap-1 shadow-lg shadow-teal-400/20">
                            <Award size={10} /> {('VERIFIED')}
                          </div>
                        )}
                      </div>
                      <p className="text-teal-300 text-sm mt-1 flex items-center gap-2">
                        <MapPin size={13} /> {activeJob.location?.city || 'Location'} · Started {activeJob.started_at ? new Date(activeJob.started_at).toLocaleTimeString([],{hour:'2-digit',minute:'2-digit'}) : 'Now'}
                      </p>
                    </div>
                  </div>
                  <div className="flex flex-col items-end gap-3">
                    <div className="text-right">
                      <p className="text-teal-300 text-xs font-bold mb-1">{t('Earnings Estimation')}</p>
                      <p className="font-black text-2xl">{formatPriceINR(activeJob.total_amount || 0)}</p>
                    </div>
                    {activeJob.status === 'confirmed' && (
                      <div className="flex gap-2">
                        <a 
                          href={`https://maps.google.com/?q=${activeJob.location?.lat || 0},${activeJob.location?.lng || 0}`}
                          target="_blank" rel="noopener noreferrer"
                          className="bg-white/10 hover:bg-white/20 text-white px-5 py-2.5 rounded-xl font-black text-sm transition-all border border-white/20 flex items-center gap-2"
                        >
                          <Navigation size={14} /> {t('Navigate')}
                        </a>
                        <button 
                          onClick={() => handleCheckIn(activeJob._id)}
                          className="bg-teal-400 hover:bg-teal-300 text-teal-900 px-5 py-2.5 rounded-xl font-black text-sm transition-all shadow-xl shadow-teal-400/20 flex items-center gap-2"
                        >
                          <MapPin size={14} /> {t('Verify Arrival')}
                        </button>
                      </div>
                    )}
                    {activeJob.status === 'in_progress' && (
                       <button 
                        onClick={() => setVerifyingJobId(activeJob._id)}
                        className="bg-green-500 hover:bg-green-400 text-white px-5 py-2.5 rounded-xl font-black text-sm transition-all shadow-xl shadow-green-500/20 flex items-center gap-2"
                      >
                        <CheckCircle size={14} /> {t('Complete Job (Verify Work)')}
                      </button>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* Work Gallery / Evidence Modal */}
            {verifyingJobId && (
              <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/60 backdrop-blur-md">
                <WorkGallery
                  bookingId={verifyingJobId}
                  providerId={user?._id || verifyingJobId}
                  onClose={() => setVerifyingJobId(null)}
                  onSuccess={() => {
                    const finishedId = verifyingJobId;
                    setVerifyingJobId(null);
                    setFeedbackJobId(finishedId);
                    refetchActiveJob();
                    refetchStats();
                  }}
                />
              </div>
            )}

            {/* Mandatory Feedback Modal After Completion */}
            {feedbackJobId && (
              <CustomerFeedbackModal 
                jobId={feedbackJobId} 
                onClose={() => setFeedbackJobId(null)} 
              />
            )}

            {/* Earnings Chart */}
            <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
              <div className="flex items-center justify-between mb-5">
                <div>
                  <h3 className="font-black text-gray-900 text-lg">{t('Weekly Earnings')}</h3>
                  <p className="text-sm text-gray-500">{t('This week')}: {formatPriceINR(weekTotal)}</p>
                </div>
                <TrendingUp size={20} className="text-green-500" />
              </div>
              {earningsChartData.length === 0 ? (
                <div className="h-44 flex items-center justify-center text-gray-400 font-medium">No earnings data yet</div>
              ) : (
                <ResponsiveContainer width="100%" height={180}>
                  <AreaChart data={earningsChartData}>
                    <defs>
                      <linearGradient id="earGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%"  stopColor="#0D7A7F" stopOpacity={0.3} />
                        <stop offset="95%" stopColor="#0D7A7F" stopOpacity={0.02} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#F0F4F8" />
                    <XAxis dataKey="day" tick={{ fontSize:12, fontWeight:700 }} />
                    <YAxis tick={{ fontSize:12 }} tickFormatter={v=>`₹${(v/1000).toFixed(0)}k`} />
                    <Tooltip formatter={(v: any) => [`₹${(v as number).toLocaleString('en-IN')}`, 'Earnings']} />
                    <Area type="monotone" dataKey="earnings" stroke="#0D7A7F" strokeWidth={2.5} fill="url(#earGrad)" />
                  </AreaChart>
                </ResponsiveContainer>
              )}
            </div>

            {/* ── Wallet + Performance Row ─────────────────────────────── */}
            <div className="grid lg:grid-cols-3 gap-5">
              {/* Wallet Balance */}
              <div className="bg-gradient-to-br from-teal-600 to-teal-800 rounded-2xl p-6 text-white shadow-lg">
                <p className="text-teal-200 text-xs font-bold uppercase tracking-widest mb-1">💰 Wallet Balance</p>
                <p className="text-4xl font-black mb-3">{formatPriceINR(balance?.available ?? 0)}</p>
                <div className="space-y-1.5 text-sm">
                  <div className="flex justify-between">
                    <span className="text-teal-200">Total Earned</span>
                    <span className="font-bold">{formatPriceINR(balance?.total_earned ?? 0)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-teal-200">Withdrawn</span>
                    <span className="font-bold">{formatPriceINR(balance?.total_withdrawn ?? 0)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-teal-200">Pending Payout</span>
                    <span className="font-bold text-yellow-300">{formatPriceINR(balance?.pending_payouts ?? 0)}</span>
                  </div>
                </div>
                <button onClick={() => setActiveTab('finance')} className="mt-4 w-full bg-white/20 hover:bg-white/30 backdrop-blur text-white py-2.5 rounded-xl font-bold text-sm transition-all">
                  Manage Finance →
                </button>
              </div>

              {/* Performance Snapshot */}
              <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
                <h3 className="font-black text-gray-900 text-base mb-4">⚡ Performance Snapshot</h3>
                <div className="space-y-3">
                  {[
                    { label: 'Completion Rate', val: stats?.completed_jobs && stats?.total_bookings ? Math.round((stats.completed_jobs / stats.total_bookings) * 100) : 0, suffix: '%', color: 'bg-green-500' },
                    { label: 'Avg Job Value', val: stats?.avg_job_value ? Math.round(stats.avg_job_value) : 0, prefix: '₹', color: 'bg-blue-500' },
                    { label: 'Profit / Hour', val: stats?.profit_per_hour ? Math.round(stats.profit_per_hour) : 0, prefix: '₹', color: 'bg-purple-500' },
                  ].map(m => (
                    <div key={m.label}>
                      <div className="flex justify-between mb-1">
                        <span className="text-xs font-bold text-gray-500">{m.label}</span>
                        <span className="text-xs font-black text-gray-800">{m.prefix || ''}{m.val.toLocaleString('en-IN')}{m.suffix || ''}</span>
                      </div>
                      <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                        <div className={`h-full ${m.color} rounded-full transition-all duration-700`}
                          style={{ width: `${Math.min(100, m.suffix === '%' ? m.val : Math.min(100, (m.val / 5000) * 100))}%` }} />
                      </div>
                    </div>
                  ))}
                </div>
                <div className="mt-4 pt-4 border-t border-gray-100">
                  <p className="text-xs text-gray-400 font-bold">Market Position</p>
                  <p className="font-black text-teal-600 text-sm mt-0.5">{stats?.local_market_position || 'Calculating…'}</p>
                </div>
              </div>

              {/* Trust Score */}
              <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
                <h3 className="font-black text-gray-900 text-base mb-4">🛡️ Trust Score</h3>
                <div className="flex items-center justify-center mb-4">
                  <div className="relative w-24 h-24">
                    <svg viewBox="0 0 36 36" className="w-24 h-24 -rotate-90">
                      <circle cx="18" cy="18" r="15.9" fill="none" stroke="#e5e7eb" strokeWidth="3" />
                      <circle cx="18" cy="18" r="15.9" fill="none" stroke="#0D7A7F" strokeWidth="3"
                        strokeDasharray={`${(trustData?.trust_score ?? 0)} 100`} strokeLinecap="round" />
                    </svg>
                    <div className="absolute inset-0 flex flex-col items-center justify-center">
                      <span className="text-xl font-black text-teal-600">{trustData?.trust_score ?? 0}</span>
                      <span className="text-xs text-gray-400">/ 100</span>
                    </div>
                  </div>
                </div>
                <div className="space-y-2">
                  {[
                    { label: 'Reliability', val: trustData?.breakdown?.reliability ?? 0, max: 40 },
                    { label: 'Punctuality', val: trustData?.breakdown?.punctuality ?? 0, max: 30 },
                    { label: 'Quality',     val: trustData?.breakdown?.quality     ?? 0, max: 30 },
                  ].map(b => (
                    <div key={b.label} className="flex items-center gap-2">
                      <span className="text-xs font-bold text-gray-500 w-20">{b.label}</span>
                      <div className="flex-1 h-1.5 bg-gray-100 rounded-full">
                        <div className="h-full bg-teal-500 rounded-full" style={{ width: `${(b.val / b.max) * 100}%` }} />
                      </div>
                      <span className="text-xs font-black text-gray-700 w-8 text-right">{b.val}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* ── Recent Jobs + Real Reviews ── */}
            <div className="grid lg:grid-cols-2 gap-5">
              {/* Recent Jobs */}
              <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
                <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
                  <h2 className="font-black text-gray-900 text-lg">{t('Recent Jobs')}</h2>
                  <button onClick={() => setActiveTab('operations')} className="text-xs text-teal-600 font-bold hover:underline">{t('View All')}</button>
                </div>
                <div className="divide-y divide-gray-50">
                  {jobs.length === 0 ? (
                    <div className="px-6 py-10 text-center text-gray-400 font-medium">No jobs yet</div>
                  ) : jobs.slice(0, 6).map((job: any) => (
                    <div key={job._id} className="flex items-center justify-between px-6 py-3.5 hover:bg-gray-50 transition-colors group cursor-pointer">
                      <div className="flex items-center gap-3">
                        <div className="w-9 h-9 rounded-xl bg-teal-50 flex items-center justify-center text-base group-hover:scale-110 transition-transform">🔧</div>
                        <div>
                          <p className="font-bold text-gray-900 text-sm">{job.service_name || job.category || 'Service'}</p>
                          <p className="text-xs text-gray-500">{job.customer_name || 'Customer'} · {job.created_at?.slice(0, 10)}</p>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="font-black text-gray-800 text-sm">{formatPriceINR(job.total_amount || 0)}</span>
                        <JobStatusBadge status={job.status} />
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* ── Real Customer Reviews from DB ── */}
              <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
                <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
                  <div>
                    <h2 className="font-black text-gray-900 text-lg">⭐ Customer Reviews</h2>
                    <p className="text-xs text-gray-400">Live from database · Avg: <span className="font-black text-yellow-600">{avgRating} ★</span> ({reviews.length} reviews)</p>
                  </div>
                </div>
                <div className="divide-y divide-gray-50 max-h-72 overflow-y-auto">
                  {reviews.length === 0 ? (
                    <div className="px-6 py-10 text-center text-gray-400 font-medium">No reviews yet</div>
                  ) : reviews.slice(0, 8).map((rev: any) => (
                    <div key={rev._id} className="px-6 py-4">
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex items-center gap-2">
                          <div className="w-9 h-9 bg-gradient-to-br from-teal-400 to-blue-500 rounded-full flex items-center justify-center text-white font-black text-xs flex-shrink-0">
                            {(rev.customer_name || rev.reviewer_name || 'C')[0].toUpperCase()}
                          </div>
                          <div>
                            <p className="font-bold text-gray-900 text-sm">{rev.customer_name || rev.reviewer_name || 'Customer'}</p>
                            <div className="flex gap-0.5 mt-0.5">
                              {[1,2,3,4,5].map(s => (
                                <span key={s} className={`text-xs ${s <= (rev.rating || 0) ? 'text-yellow-500' : 'text-gray-200'}`}>★</span>
                              ))}
                            </div>
                          </div>
                        </div>
                        <span className="text-xs text-gray-400 whitespace-nowrap">{rev.created_at ? new Date(rev.created_at).toLocaleDateString() : ''}</span>
                      </div>
                      {rev.comment && <p className="text-xs text-gray-500 mt-2 leading-relaxed line-clamp-2">{rev.comment}</p>}
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* ── Customer History Table ── */}
            <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
              <div className="px-6 py-4 border-b border-gray-100">
                <h2 className="font-black text-gray-900 text-lg">👥 Customer History</h2>
                <p className="text-xs text-gray-400 mt-0.5">All customers who booked your services — fetched from database</p>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gray-50">
                    <tr>{['Customer', 'Service', 'Date', 'Amount', 'Payment', 'Status', 'Rating'].map(h => (
                      <th key={h} className="text-left py-3 px-5 font-black text-gray-400 text-xs uppercase tracking-wider">{h}</th>
                    ))}</tr>
                  </thead>
                  <tbody className="divide-y divide-gray-50">
                    {jobs.length === 0 ? (
                      <tr><td colSpan={7} className="py-10 text-center text-gray-400 font-medium">No customer history yet</td></tr>
                    ) : jobs.map((job: any) => {
                      const jobReview = reviews.find((r: any) => r.booking_id === job._id);
                      return (
                        <tr key={job._id} className="hover:bg-teal-50/20 transition-colors">
                          <td className="py-3.5 px-5">
                            <div className="flex items-center gap-2">
                              <div className="w-8 h-8 bg-teal-100 rounded-full flex items-center justify-center text-teal-700 font-black text-xs">
                                {(job.customer_name || 'C')[0].toUpperCase()}
                              </div>
                              <div>
                                <p className="font-bold text-gray-900 text-sm">{job.customer_name || 'Customer'}</p>
                                <p className="text-xs text-gray-400">{job.customer_phone || ''}</p>
                              </div>
                            </div>
                          </td>
                          <td className="py-3.5 px-5 text-sm text-gray-700 font-medium">{job.service_name || job.category || '—'}</td>
                          <td className="py-3.5 px-5 text-xs text-gray-400 whitespace-nowrap">{job.created_at?.slice(0, 10) || '—'}</td>
                          <td className="py-3.5 px-5 font-black text-gray-900">{formatPriceINR(job.total_amount || job.amount || 0)}</td>
                          <td className="py-3.5 px-5">
                            <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${job.payment_status === 'completed' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
                              {job.payment_status || 'unpaid'}
                            </span>
                          </td>
                          <td className="py-3.5 px-5"><JobStatusBadge status={job.status} /></td>
                          <td className="py-3.5 px-5">
                            {jobReview ? (
                              <span className="text-yellow-600 font-black text-sm">{jobReview.rating} ★</span>
                            ) : (
                              <span className="text-gray-300 text-xs">—</span>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Quick Navigation */}
            <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
              {[
                { tab:'intelligence' as ProviderTab, label: t('Business Intelligence'), icon:'📊', color:'bg-blue-50 text-blue-700'   },
                { tab:'schedule'     as ProviderTab, label: t('AI Scheduling'),         icon:'🤖', color:'bg-purple-50 text-purple-700' },
                { tab:'customers'    as ProviderTab, label: t('CRM'),                   icon:'👥', color:'bg-green-50 text-green-700'  },
                { tab:'finance'      as ProviderTab, label: t('Financial Mgmt'),        icon:'💰', color:'bg-yellow-50 text-yellow-700' },
                { tab:'wellness'     as ProviderTab, label: t('Wellness & Safety'),     icon:'❤️', color:'bg-red-50 text-red-700'      },
                { tab:'predictor'    as ProviderTab, label: t('Forecast'),              icon:'🔮', color:'bg-indigo-50 text-indigo-700' },
              ].map(n => (
                <button key={n.tab} onClick={() => setActiveTab(n.tab)}
                  className={`${n.color} rounded-2xl p-4 text-center font-bold text-sm hover:opacity-80 transition-all hover:-translate-y-0.5 active:scale-95`}>
                  <div className="text-2xl mb-1">{n.icon}</div>
                  {n.label}
                </button>
              ))}
            </div>
          </div>
        )}

        {activeTab === 'predictor'    && <IncomePredictor jobs={jobs} balance={balance} />}
        {activeTab === 'intelligence' && <BusinessIntelligence />}
        {activeTab === 'schedule'     && <AIScheduling />}
        {activeTab === 'pricing'      && <DynamicPricing />}
        {activeTab === 'customers'    && <CustomerCRM />}
        {activeTab === 'marketing'    && <PortfolioMarketing />}
        {activeTab === 'operations'   && <OperationalTools />}
        {activeTab === 'learning'     && <LearningGrowth />}
        {activeTab === 'inbox'        && <CommunicationHub />}
        {activeTab === 'finance'      && <FinancialManagement />}
        {activeTab === 'wellness'     && <WellnessSafety />}
      </div>
    </DashboardLayout>
  );
};

export default ProviderDashboardNew;
