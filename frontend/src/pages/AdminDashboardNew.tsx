import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import DashboardLayout from '../components/DashboardLayout';
import {
  Users, DollarSign, Calendar, TrendingUp, Award,
  AlertTriangle, CheckCircle, XCircle, Gift,
  BarChart3, UserCheck, Search, Activity, Shield,
  Megaphone, BookOpen, Settings, Globe, LogIn,
  CreditCard, RefreshCw, Eye, X, Clock, Phone,
  Star, UserX, UserPlus, Filter, Download, ArrowUpRight,
  ArrowDownRight, Wallet, FileText
} from 'lucide-react';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, BarChart, Bar, PieChart, Pie, Cell
} from 'recharts';
import toast from 'react-hot-toast';
import api from '../services/api';

import MarketplaceCommand   from './admin/sections/MarketplaceCommand';
import ProviderLifecycle    from './admin/sections/ProviderLifecycle';
import FinancialControls    from './admin/sections/FinancialControls';
import TrustSafety          from './admin/sections/TrustSafety';
import MarketingGrowth      from './admin/sections/MarketingGrowth';
import ProductAnalytics     from './admin/sections/ProductAnalytics';
import EmergencyOperations  from './admin/sections/EmergencyOperations';
import CommunityGovernance  from './admin/sections/CommunityGovernance';
import TechnicalOperations  from './admin/sections/TechnicalOperations';
import StrategicPlanning    from './admin/sections/StrategicPlanning';

type AdminTab =
  | 'overview' | 'login-activity' | 'customers' | 'providers'
  | 'bookings' | 'transactions' | 'command' | 'providers-lifecycle'
  | 'finance' | 'trust' | 'marketing' | 'analytics' | 'emergency'
  | 'community' | 'tech' | 'strategy';

const COLORS = ['#0D7A7F', '#f59e0b', '#ef4444', '#8b5cf6', '#3b82f6'];

const StatusBadge: React.FC<{ status: string }> = ({ status }) => {
  const map: Record<string, string> = {
    completed: 'bg-green-100 text-green-700',
    success:   'bg-green-100 text-green-700',
    active:    'bg-teal-100 text-teal-700',
    pending:   'bg-yellow-100 text-yellow-700',
    in_progress:'bg-orange-100 text-orange-700',
    confirmed:  'bg-blue-100 text-blue-700',
    cancelled:  'bg-red-100 text-red-700',
    failed:     'bg-red-100 text-red-700',
    refunded:   'bg-purple-100 text-purple-700',
    unpaid:     'bg-gray-100 text-gray-600',
  };
  return (
    <span className={`text-xs font-bold px-2.5 py-1 rounded-full ${map[status] || 'bg-gray-100 text-gray-600'}`}>
      {status.replace(/_/g,' ')}
    </span>
  );
};

const StatCard: React.FC<{
  label: string; value: string | number; icon: any;
  color: string; bg: string; sub?: string; onClick?: () => void;
}> = ({ label, value, icon: Icon, color, bg, sub, onClick }) => (
  <div
    onClick={onClick}
    className={`bg-white rounded-2xl p-6 shadow-sm border border-gray-100 hover:shadow-md hover:-translate-y-0.5 transition-all duration-200 group ${onClick ? 'cursor-pointer' : ''}`}
  >
    <div className="flex items-start justify-between mb-4">
      <div className={`w-12 h-12 ${bg} rounded-xl flex items-center justify-center group-hover:scale-110 transition-transform`}>
        <Icon size={22} className={color} />
      </div>
    </div>
    <p className="text-3xl font-black text-gray-900 mb-1">{value}</p>
    <p className="text-sm font-bold text-gray-500">{label}</p>
    {sub && <p className="text-xs text-gray-400 mt-1">{sub}</p>}
  </div>
);

// ── User Detail Modal ───────────────────────────────────────────────────────
const UserDetailModal: React.FC<{ userId: string; onClose: () => void }> = ({ userId, onClose }) => {
  const { data, isLoading } = useQuery({
    queryKey: ['admin-user-full', userId],
    queryFn: () => api.get(`/api/admin/users/${userId}/full`).then(r => r.data),
  });

  if (isLoading) return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center">
      <div className="bg-white rounded-3xl p-10 flex items-center gap-4">
        <div className="w-8 h-8 border-4 border-teal-500/30 border-t-teal-500 rounded-full animate-spin" />
        <span className="font-bold text-gray-600">Loading profile…</span>
      </div>
    </div>
  );

  const user = data?.user || {};
  const bookings = data?.bookings || [];
  const payments = data?.payments || [];
  const loginHistory = data?.login_history || [];
  const stats = data?.stats || {};

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4 overflow-y-auto">
      <div className="bg-white rounded-3xl w-full max-w-4xl max-h-[90vh] overflow-y-auto shadow-2xl">
        {/* Header */}
        <div className="sticky top-0 bg-white border-b border-gray-100 px-8 py-5 flex items-center justify-between rounded-t-3xl z-10">
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 bg-gradient-to-br from-teal-500 to-teal-700 rounded-2xl flex items-center justify-center text-white font-black text-xl">
              {(user.full_name || 'U')[0].toUpperCase()}
            </div>
            <div>
              <h2 className="text-xl font-black text-gray-900">{user.full_name}</h2>
              <div className="flex items-center gap-2 mt-0.5">
                <span className="text-sm text-gray-500">{user.email}</span>
                <StatusBadge status={user.role || 'customer'} />
                {user.verified_by_admin && <span className="text-xs text-green-600 font-bold bg-green-50 px-2 py-0.5 rounded-full flex items-center gap-1"><CheckCircle size={10} /> Verified</span>}
                {user.suspended && <span className="text-xs text-red-600 font-bold bg-red-50 px-2 py-0.5 rounded-full flex items-center gap-1"><XCircle size={10} /> Suspended</span>}
              </div>
            </div>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-gray-100 rounded-xl transition-colors"><X size={20} /></button>
        </div>

        <div className="p-8 space-y-6">
          {/* Quick Stats */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { label: 'Total Bookings', value: stats.total_bookings || 0, color: 'text-blue-600', bg: 'bg-blue-50' },
              { label: 'Completed', value: stats.completed_bookings || 0, color: 'text-green-600', bg: 'bg-green-50' },
              { label: user.role === 'provider' ? 'Total Earned' : 'Total Spent', value: `₹${(stats.total_spent_earned || 0).toLocaleString('en-IN')}`, color: 'text-teal-600', bg: 'bg-teal-50' },
              { label: 'Logins', value: stats.login_count || 0, color: 'text-purple-600', bg: 'bg-purple-50' },
            ].map(s => (
              <div key={s.label} className={`${s.bg} rounded-2xl p-4`}>
                <p className={`text-2xl font-black ${s.color}`}>{s.value}</p>
                <p className="text-xs font-bold text-gray-500 mt-1">{s.label}</p>
              </div>
            ))}
          </div>

          {/* Profile Details */}
          <div className="bg-gray-50 rounded-2xl p-5">
            <h3 className="font-black text-gray-800 mb-3 text-sm uppercase tracking-wider">Profile Details</h3>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
              {[
                { label: 'Phone', value: user.phone },
                { label: 'City', value: user.city || user.base_location },
                { label: 'Joined', value: user.created_at ? new Date(user.created_at).toLocaleDateString() : 'N/A' },
                { label: 'Credits', value: `${user.quickserve_credits || 0} pts` },
                { label: 'Rating', value: user.rating ? `${user.rating} ★` : 'N/A' },
                { label: 'Experience', value: user.experience_years ? `${user.experience_years} yrs` : 'N/A' },
              ].filter(f => f.value).map(f => (
                <div key={f.label} className="bg-white rounded-xl p-3">
                  <p className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-0.5">{f.label}</p>
                  <p className="font-bold text-gray-900 text-sm">{f.value}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Bookings */}
          {bookings.length > 0 && (
            <div>
              <h3 className="font-black text-gray-800 mb-3 flex items-center gap-2"><Calendar size={16} /> Booking History ({bookings.length})</h3>
              <div className="space-y-2 max-h-48 overflow-y-auto">
                {bookings.map((b: any) => (
                  <div key={b._id} className="flex items-center justify-between bg-gray-50 rounded-xl p-3">
                    <div>
                      <p className="font-bold text-gray-900 text-sm">{b.service_name || b.category || 'Service'}</p>
                      <p className="text-xs text-gray-500">{b.created_at ? new Date(b.created_at).toLocaleDateString() : ''} · {b.provider_name || b.customer_name || ''}</p>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="font-black text-gray-800 text-sm">₹{(b.final_amount || b.amount || 0).toLocaleString('en-IN')}</span>
                      <StatusBadge status={b.status} />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Login History */}
          {loginHistory.length > 0 && (
            <div>
              <h3 className="font-black text-gray-800 mb-3 flex items-center gap-2"><LogIn size={16} /> Login History</h3>
              <div className="space-y-2 max-h-40 overflow-y-auto">
                {loginHistory.map((l: any) => (
                  <div key={l._id} className="flex items-center justify-between bg-gray-50 rounded-xl p-3">
                    <div className="flex items-center gap-2">
                      {l.status === 'success' ? <CheckCircle size={14} className="text-green-500" /> : <XCircle size={14} className="text-red-500" />}
                      <span className="text-sm font-bold text-gray-700">{l.method?.toUpperCase()} Login</span>
                    </div>
                    <span className="text-xs text-gray-400">{l.timestamp_str || l.timestamp}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

// ── Main Component ───────────────────────────────────────────────────────────
const AdminDashboardNew: React.FC = () => {
  const [activeTab, setActiveTab] = useState<AdminTab>('overview');
  const [searchQuery, setSearchQuery] = useState('');
  const [rewardForm, setRewardForm] = useState({ email: '', amount: 100, reason: '', type: 'credits' });
  const [selectedUserId, setSelectedUserId] = useState<string | null>(null);
  const [txFilter, setTxFilter] = useState('all');
  const [loginFilter, setLoginFilter] = useState('all');
  const [bookingFilter, setBookingFilter] = useState('all');
  const queryClient = useQueryClient();

  // ── All API calls ──────────────────────────────────────────────────────
  const { data: dashData } = useQuery({
    queryKey: ['admin-dashboard'],
    queryFn: () => api.get('/api/admin/dashboard').then(r => r.data),
    retry: 1,
  });

  const { data: usersData } = useQuery({
    queryKey: ['admin-users'],
    queryFn: () => api.get('/api/admin/users?limit=200').then(r => r.data),
    retry: 1,
  });

  const { data: revenueData } = useQuery({
    queryKey: ['admin-revenue'],
    queryFn: () => api.get('/api/admin/analytics/revenue?period=monthly').then(r => r.data),
    retry: 1,
  });

  const { data: topProvidersData } = useQuery({
    queryKey: ['admin-top-providers'],
    queryFn: () => api.get('/api/admin/analytics/top-providers?limit=5').then(r => r.data),
    retry: 1,
  });

  const { data: topCustomersData } = useQuery({
    queryKey: ['admin-top-customers'],
    queryFn: () => api.get('/api/admin/analytics/top-customers?limit=5').then(r => r.data),
    retry: 1,
  });

  const { data: disputesData } = useQuery({
    queryKey: ['admin-disputes'],
    queryFn: () => api.get('/api/admin/disputes').then(r => r.data),
    retry: 1,
  });

  const { data: loginData, refetch: refetchLogin } = useQuery({
    queryKey: ['admin-login-activity', loginFilter],
    queryFn: () => {
      const params: Record<string, string> = { limit: '100' };
      if (loginFilter !== 'all') params.role = loginFilter;
      return api.get('/api/admin/login-activity', { params }).then(r => r.data);
    },
    enabled: activeTab === 'login-activity' || activeTab === 'overview',
    retry: 1,
  });

  const { data: bookingsData } = useQuery({
    queryKey: ['admin-all-bookings', bookingFilter],
    queryFn: () => {
      const params: Record<string, string> = { limit: '100' };
      if (bookingFilter !== 'all') params.status = bookingFilter;
      return api.get('/api/admin/bookings', { params }).then(r => r.data);
    },
    enabled: activeTab === 'bookings',
    retry: 1,
  });

  const { data: txData, refetch: refetchTx } = useQuery({
    queryKey: ['admin-transactions', txFilter],
    queryFn: () => {
      const params: Record<string, string> = { limit: '100' };
      if (txFilter !== 'all') params.tx_type = txFilter;
      return api.get('/api/admin/transactions', { params }).then(r => r.data);
    },
    enabled: activeTab === 'transactions',
    retry: 1,
  });

  // ── Mutations ─────────────────────────────────────────────────────────
  const verifyMutation = useMutation({
    mutationFn: (id: string) => api.post(`/api/admin/providers/${id}/verify`),
    onSuccess: () => { toast.success('Provider verified!'); queryClient.invalidateQueries({ queryKey: ['admin-users'] }); },
    onError: () => toast.error('Verification failed'),
  });

  const suspendMutation = useMutation({
    mutationFn: ({ id, reason }: { id: string; reason: string }) =>
      api.post(`/api/admin/providers/${id}/suspend`, null, { params: { reason } }),
    onSuccess: () => { toast.success('Provider suspended.'); queryClient.invalidateQueries({ queryKey: ['admin-users'] }); },
    onError: () => toast.error('Suspension failed'),
  });

  const resolveMutation = useMutation({
    mutationFn: ({ id }: { id: string }) =>
      api.post(`/api/admin/disputes/${id}/resolve`, null, { params: { resolution: 'Resolved by admin', winner: 'customer' } }),
    onSuccess: () => { toast.success('Dispute resolved!'); queryClient.invalidateQueries({ queryKey: ['admin-disputes'] }); },
    onError: () => toast.error('Failed to resolve'),
  });

  const grantRewardMutation = useMutation({
    mutationFn: (data: any) => api.post('/api/admin/rewards/grant', data),
    onSuccess: () => { toast.success('Reward granted!'); queryClient.invalidateQueries({ queryKey: ['admin-users'] }); },
    onError: (err: any) => toast.error(err.response?.data?.detail || 'Failed to grant reward'),
  });

  // ── Derived data ──────────────────────────────────────────────────────
  const allUsers: any[]     = usersData?.users || [];
  const customers           = allUsers.filter((u: any) => u.role === 'customer');
  const providers           = allUsers.filter((u: any) => u.role === 'provider');
  const revenueChart: any[] = revenueData?.data || [];
  const topProviders: any[] = topProvidersData?.top_providers || [];
  const topCustomers: any[] = topCustomersData?.top_customers || [];
  const disputes: any[]     = disputesData?.disputes || [];
  const loginLogs: any[]    = loginData?.logs || [];
  const loginSummary        = loginData?.summary || {};
  const bookings: any[]     = bookingsData?.bookings || [];
  const transactions: any[] = txData?.transactions || [];
  const txSummary           = txData?.summary || {};

  const filteredCustomers = customers.filter((c: any) =>
    !searchQuery || c.full_name?.toLowerCase().includes(searchQuery.toLowerCase()) || c.email?.toLowerCase().includes(searchQuery.toLowerCase())
  );
  const filteredProviders = providers.filter((p: any) =>
    !searchQuery || p.full_name?.toLowerCase().includes(searchQuery.toLowerCase()) || p.email?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const tabs: { key: AdminTab; label: string; icon: any; color?: string }[] = [
    { key: 'overview',           label: 'Overview',          icon: BarChart3,     },
    { key: 'login-activity',     label: 'Login Activity',    icon: LogIn,         color: 'text-blue-500'   },
    { key: 'customers',          label: 'Customers',         icon: Users,         color: 'text-teal-500'   },
    { key: 'providers',          label: 'Providers',         icon: UserCheck,     color: 'text-green-500'  },
    { key: 'bookings',           label: 'All Bookings',      icon: Calendar,      color: 'text-purple-500' },
    { key: 'transactions',       label: 'Transactions',      icon: CreditCard,    color: 'text-orange-500' },
    { key: 'command',            label: 'Command',           icon: Activity,      },
    { key: 'providers-lifecycle',label: 'Lifecycle',         icon: UserPlus,      },
    { key: 'finance',            label: 'Finance',           icon: DollarSign,    },
    { key: 'trust',              label: 'Trust & Safety',    icon: Shield,        },
    { key: 'marketing',          label: 'Marketing',         icon: Megaphone,     },
    { key: 'analytics',          label: 'Analytics',         icon: TrendingUp,    },
    { key: 'emergency',          label: 'Emergency',         icon: AlertTriangle, },
    { key: 'community',          label: 'Community',         icon: Globe,         },
    { key: 'strategy',           label: 'Strategy',          icon: BookOpen,      },
    { key: 'tech',               label: 'Tech Ops',          icon: Settings,      },
  ];

  return (
    <DashboardLayout role="admin" title="Admin Dashboard">
      {selectedUserId && (
        <UserDetailModal userId={selectedUserId} onClose={() => setSelectedUserId(null)} />
      )}

      <div className="space-y-5">
        {/* Tab Navigation */}
        <div className="flex gap-1.5 bg-white rounded-2xl p-1.5 shadow-sm border border-gray-100 overflow-x-auto">
          {tabs.map(t => {
            const Icon = t.icon;
            return (
              <button key={t.key} onClick={() => { setActiveTab(t.key); setSearchQuery(''); }}
                className={`flex items-center gap-1.5 px-3.5 py-2 rounded-xl font-bold text-xs whitespace-nowrap transition-all duration-200 ${
                  activeTab === t.key ? 'bg-teal-600 text-white shadow-md' : 'text-gray-500 hover:text-gray-800 hover:bg-gray-50'
                }`}>
                <Icon size={13} />
                {t.label}
              </button>
            );
          })}
        </div>

        {/* ── OVERVIEW TAB ── */}
        {activeTab === 'overview' && (
          <div className="space-y-6">
            {/* Stats */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              <StatCard label="Total Users"      value={(dashData?.users?.total ?? 0).toLocaleString()} icon={Users}      color="text-blue-600"   bg="bg-blue-50"   sub={`${dashData?.users?.customers ?? 0} customers, ${dashData?.users?.providers ?? 0} providers`} onClick={() => setActiveTab('customers')} />
              <StatCard label="Platform Revenue" value={`₹${((dashData?.revenue?.total ?? 0) / 100000).toFixed(1)}L`}    icon={DollarSign} color="text-green-600"  bg="bg-green-50"  sub={`₹${((dashData?.revenue?.commission ?? 0) / 100000).toFixed(2)}L commission`}  onClick={() => setActiveTab('transactions')} />
              <StatCard label="Total Bookings"   value={(dashData?.bookings?.total ?? 0).toLocaleString()} icon={Calendar}   color="text-purple-600" bg="bg-purple-50" sub={`${dashData?.bookings?.today ?? 0} today · ${dashData?.bookings?.active ?? 0} active`} onClick={() => setActiveTab('bookings')} />
              <StatCard label="Login Sessions"   value={(loginSummary?.total_logins ?? 0).toLocaleString()} icon={LogIn}   color="text-teal-600"   bg="bg-teal-50"   sub={`${loginSummary?.failed_logins ?? 0} failed attempts`} onClick={() => setActiveTab('login-activity')} />
            </div>

            {/* Revenue Chart */}
            <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
              <div className="flex items-center justify-between mb-5">
                <div>
                  <h3 className="font-black text-gray-900 text-lg">Revenue & Bookings</h3>
                  <p className="text-sm text-gray-500">Platform performance over time — fetched live from DB</p>
                </div>
              </div>
              {revenueChart.length === 0 ? (
                <div className="h-60 flex items-center justify-center text-gray-400 font-medium">No revenue data yet</div>
              ) : (
                <ResponsiveContainer width="100%" height={240}>
                  <AreaChart data={revenueChart}>
                    <defs>
                      <linearGradient id="admRevGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%"  stopColor="#0D7A7F" stopOpacity={0.3} />
                        <stop offset="95%" stopColor="#0D7A7F" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#F0F4F8" />
                    <XAxis dataKey="date" tick={{ fontSize: 12, fontWeight: 700 }} />
                    <YAxis tick={{ fontSize: 12 }} tickFormatter={v => `₹${(v / 100000).toFixed(0)}L`} />
                    <Tooltip formatter={(v: any) => [`₹${(v / 100000).toFixed(2)}L`, 'Revenue']} />
                    <Area type="monotone" dataKey="revenue" stroke="#0D7A7F" strokeWidth={2.5} fill="url(#admRevGrad)" />
                  </AreaChart>
                </ResponsiveContainer>
              )}
            </div>

            {/* Top performers + role distribution */}
            <div className="grid lg:grid-cols-3 gap-6">
              <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
                <h3 className="font-black text-gray-900 text-lg mb-4 flex items-center gap-2"><Award size={20} className="text-yellow-500" /> Top Providers</h3>
                {topProviders.length === 0 ? (
                  <p className="text-gray-400 text-sm text-center py-6">No data yet</p>
                ) : (
                  <div className="space-y-3">
                    {topProviders.map((p: any, i: number) => (
                      <div key={p.id} onClick={() => setSelectedUserId(p.id)} className="flex items-center justify-between bg-gray-50 p-3 rounded-xl hover:bg-teal-50 transition-colors cursor-pointer">
                        <div className="flex items-center gap-3">
                          <span className="w-8 h-8 bg-teal-600 text-white rounded-full flex items-center justify-center font-black text-sm">{i + 1}</span>
                          <div>
                            <p className="font-bold text-gray-900 text-sm">{p.name}</p>
                            <p className="text-xs text-gray-500">{p.bookings} bookings</p>
                          </div>
                        </div>
                        <div className="text-right">
                          <p className="font-black text-green-600 text-sm">₹{(p.earnings).toLocaleString('en-IN')}</p>
                          <p className="text-xs text-yellow-600">{p.rating?.toFixed(1)} ★</p>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
                <h3 className="font-black text-gray-900 text-lg mb-4 flex items-center gap-2"><Users size={20} className="text-blue-500" /> Top Customers</h3>
                {topCustomers.length === 0 ? (
                  <p className="text-gray-400 text-sm text-center py-6">No data yet</p>
                ) : (
                  <div className="space-y-3">
                    {topCustomers.map((c: any, i: number) => (
                      <div key={c.id || c._id || i} onClick={() => setSelectedUserId(c.id || c._id)} className="flex items-center justify-between bg-gray-50 p-3 rounded-xl hover:bg-blue-50 transition-colors cursor-pointer">
                        <div className="flex items-center gap-3">
                          <span className="w-8 h-8 bg-blue-600 text-white rounded-full flex items-center justify-center font-black text-sm">{i + 1}</span>
                          <div>
                            <p className="font-bold text-gray-900 text-sm">{c.name || c.full_name}</p>
                            <p className="text-xs text-gray-500">{c.bookings || c.bookings_count || 0} bookings</p>
                          </div>
                        </div>
                        <div className="text-right">
                          <p className="font-black text-blue-600 text-sm">₹{(c.spent || 0).toLocaleString('en-IN')}</p>
                          <p className="text-xs text-gray-400">{c.credits || c.quickserve_credits || 0} credits</p>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
                <h3 className="font-black text-gray-900 text-lg mb-4 flex items-center gap-2"><LogIn size={20} className="text-indigo-500" /> Login Activity</h3>
                <div className="space-y-2 mb-4">
                  {[
                    { label: 'Customer Logins', val: loginSummary?.customer_logins ?? 0, color: 'text-teal-600', bg: 'bg-teal-50' },
                    { label: 'Provider Logins', val: loginSummary?.provider_logins ?? 0, color: 'text-blue-600', bg: 'bg-blue-50' },
                    { label: 'Admin Logins',    val: loginSummary?.admin_logins    ?? 0, color: 'text-purple-600', bg: 'bg-purple-50' },
                    { label: 'Failed Attempts', val: loginSummary?.failed_logins   ?? 0, color: 'text-red-600', bg: 'bg-red-50' },
                  ].map(s => (
                    <div key={s.label} className={`${s.bg} rounded-xl p-3 flex items-center justify-between`}>
                      <span className="text-xs font-bold text-gray-600">{s.label}</span>
                      <span className={`font-black ${s.color}`}>{s.val}</span>
                    </div>
                  ))}
                </div>
                <button onClick={() => setActiveTab('login-activity')} className="text-xs text-teal-600 font-bold hover:underline">View all →</button>
              </div>
            </div>

            {/* Open Disputes */}
            <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
              <h3 className="font-black text-gray-900 text-lg mb-4 flex items-center gap-2"><AlertTriangle size={20} className="text-red-500" /> Open Disputes</h3>
              {disputes.filter((d: any) => d.status !== 'resolved').length === 0 ? (
                <p className="text-gray-400 text-sm text-center py-6">No open disputes 🎉</p>
              ) : (
                disputes.filter((d: any) => d.status !== 'resolved').slice(0, 5).map((d: any) => (
                  <div key={d._id} className="bg-red-50 border border-red-200 rounded-xl p-4 mb-3">
                    <div className="flex items-start justify-between">
                      <div>
                        <p className="font-bold text-gray-900 text-sm">{d.title || 'Dispute'}</p>
                        <p className="text-xs text-gray-500 mt-0.5">{d.customer_name || 'Customer'} · {d.provider_name || 'Provider'} · ₹{(d.amount || 0).toLocaleString('en-IN')}</p>
                      </div>
                      <button onClick={() => resolveMutation.mutate({ id: d._id })}
                        className="bg-green-500 hover:bg-green-600 text-white px-3 py-1.5 rounded-lg font-bold text-xs transition-colors">
                        Resolve
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>

            {/* Grant Reward */}
            <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
              <h3 className="font-black text-gray-900 text-lg mb-5 flex items-center gap-2"><Gift size={20} className="text-yellow-500" /> Grant Reward</h3>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-black text-gray-400 uppercase tracking-widest mb-1.5">User Email</label>
                  <input value={rewardForm.email} onChange={e => setRewardForm({ ...rewardForm, email: e.target.value })} placeholder="user@example.com" className="w-full px-3 py-2.5 rounded-xl border-2 border-gray-100 focus:border-teal-400 text-sm font-medium focus:outline-none" />
                </div>
                <div>
                  <label className="block text-xs font-black text-gray-400 uppercase tracking-widest mb-1.5">Reason</label>
                  <input value={rewardForm.reason} onChange={e => setRewardForm({ ...rewardForm, reason: e.target.value })} placeholder="Reason…" className="w-full px-3 py-2.5 rounded-xl border-2 border-gray-100 focus:border-teal-400 text-sm font-medium focus:outline-none" />
                </div>
                <div>
                  <label className="block text-xs font-black text-gray-400 uppercase tracking-widest mb-1.5">Type</label>
                  <select value={rewardForm.type} onChange={e => setRewardForm({ ...rewardForm, type: e.target.value })} className="w-full px-3 py-2.5 rounded-xl border-2 border-gray-100 focus:border-teal-400 text-sm font-medium bg-white focus:outline-none">
                    <option value="credits">Credits</option>
                    <option value="points">Loyalty Points</option>
                    <option value="discount">Gift Badge</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-black text-gray-400 uppercase tracking-widest mb-1.5">Amount</label>
                  <input type="number" value={rewardForm.amount} onChange={e => setRewardForm({ ...rewardForm, amount: Number(e.target.value) })} className="w-full px-3 py-2.5 rounded-xl border-2 border-gray-100 focus:border-teal-400 text-sm font-medium focus:outline-none" />
                </div>
              </div>
              <button onClick={() => grantRewardMutation.mutate(rewardForm)} disabled={grantRewardMutation.isPending}
                className="mt-4 bg-teal-600 disabled:bg-gray-400 hover:bg-teal-700 text-white px-8 py-3 rounded-xl font-black transition-all hover:shadow-lg">
                {grantRewardMutation.isPending ? 'Processing…' : 'Grant Reward'}
              </button>
            </div>
          </div>
        )}

        {/* ── LOGIN ACTIVITY TAB ── */}
        {activeTab === 'login-activity' && (
          <div className="space-y-6">
            {/* Summary Cards */}
            <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
              {[
                { label: 'Total Logins',     val: loginSummary?.total_logins    ?? 0, color: 'text-teal-600',   bg: 'bg-teal-50'   },
                { label: 'Customer Logins',  val: loginSummary?.customer_logins ?? 0, color: 'text-blue-600',   bg: 'bg-blue-50'   },
                { label: 'Provider Logins',  val: loginSummary?.provider_logins ?? 0, color: 'text-green-600',  bg: 'bg-green-50'  },
                { label: 'Admin Logins',     val: loginSummary?.admin_logins    ?? 0, color: 'text-purple-600', bg: 'bg-purple-50' },
                { label: 'Failed Attempts',  val: loginSummary?.failed_logins   ?? 0, color: 'text-red-600',    bg: 'bg-red-50'    },
              ].map(s => (
                <div key={s.label} className={`${s.bg} rounded-2xl p-5`}>
                  <p className={`text-3xl font-black ${s.color}`}>{s.val}</p>
                  <p className="text-xs font-bold text-gray-500 mt-1">{s.label}</p>
                </div>
              ))}
            </div>

            {/* Filter + table */}
            <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
              <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between gap-4 flex-wrap">
                <h3 className="font-black text-gray-900 text-xl flex items-center gap-2"><LogIn size={18} /> Login Activity Log</h3>
                <div className="flex gap-2 flex-wrap">
                  {['all', 'customer', 'provider', 'admin', 'failed'].map(f => (
                    <button key={f} onClick={() => setLoginFilter(f)}
                      className={`px-4 py-2 rounded-xl font-bold text-xs transition-all ${loginFilter === f ? 'bg-teal-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}>
                      {f.charAt(0).toUpperCase() + f.slice(1)}
                    </button>
                  ))}
                  <button onClick={() => refetchLogin()} className="p-2 rounded-xl bg-gray-100 hover:bg-gray-200 transition-colors"><RefreshCw size={14} /></button>
                </div>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gray-50">
                    <tr>{['Name', 'Email', 'Role', 'Method', 'Status', 'Timestamp'].map(h => (
                      <th key={h} className="text-left py-3.5 px-5 font-black text-gray-400 text-xs uppercase tracking-wider">{h}</th>
                    ))}</tr>
                  </thead>
                  <tbody className="divide-y divide-gray-50">
                    {(loginFilter === 'failed'
                      ? loginLogs.filter((l: any) => l.status === 'failed')
                      : loginFilter !== 'all'
                        ? loginLogs.filter((l: any) => l.role === loginFilter)
                        : loginLogs
                    ).map((log: any, i: number) => (
                      <tr key={log._id || i} className="hover:bg-teal-50/30 transition-colors">
                        <td className="py-4 px-5 font-bold text-gray-900">{log.full_name || '—'}</td>
                        <td className="py-4 px-5 text-gray-500 text-sm">{log.email}</td>
                        <td className="py-4 px-5"><StatusBadge status={log.role || 'unknown'} /></td>
                        <td className="py-4 px-5 text-gray-600 text-sm font-medium capitalize">{log.method || 'email'}</td>
                        <td className="py-4 px-5">
                          <span className={`flex items-center gap-1 text-xs font-bold w-fit px-2.5 py-1 rounded-full ${log.status === 'success' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                            {log.status === 'success' ? <CheckCircle size={11} /> : <XCircle size={11} />}
                            {log.status}
                          </span>
                        </td>
                        <td className="py-4 px-5 text-gray-400 text-xs whitespace-nowrap">{log.timestamp_str || (log.timestamp ? new Date(log.timestamp).toLocaleString() : '—')}</td>
                      </tr>
                    ))}
                    {loginLogs.length === 0 && (
                      <tr><td colSpan={6} className="text-center py-16 text-gray-400 font-medium">No login records yet — login activity is recorded after first login</td></tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* ── CUSTOMERS TAB ── */}
        {activeTab === 'customers' && (
          <div className="space-y-5">
            <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
              <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between gap-4 flex-wrap">
                <h3 className="font-black text-gray-900 text-xl flex items-center gap-2"><Users size={18} /> Customer Management ({customers.length})</h3>
                <div className="relative">
                  <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                  <input type="text" placeholder="Search customers…" value={searchQuery}
                    onChange={e => setSearchQuery(e.target.value)}
                    className="pl-9 pr-4 py-2 text-sm border border-gray-200 rounded-xl focus:outline-none focus:border-teal-400 w-52" />
                </div>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gray-50">
                    <tr>{['Name', 'Email', 'Phone', 'City', 'Credits', 'Bookings', 'Joined', 'Actions'].map(h => (
                      <th key={h} className="text-left py-3.5 px-5 font-black text-gray-400 text-xs uppercase tracking-wider">{h}</th>
                    ))}</tr>
                  </thead>
                  <tbody className="divide-y divide-gray-50">
                    {filteredCustomers.length === 0
                      ? <tr><td colSpan={8} className="py-16 text-center text-gray-400 font-medium">No customers found</td></tr>
                      : filteredCustomers.map((c: any, i: number) => (
                        <tr key={c._id || i} className="hover:bg-teal-50/30 transition-colors">
                          <td className="py-4 px-5 font-bold text-gray-900">{c.full_name}</td>
                          <td className="py-4 px-5 text-gray-500 text-sm">{c.email}</td>
                          <td className="py-4 px-5 text-gray-500 text-sm">{c.phone || '—'}</td>
                          <td className="py-4 px-5 text-gray-500 text-sm">{c.city || '—'}</td>
                          <td className="py-4 px-5"><span className="bg-green-100 text-green-700 px-2.5 py-1 rounded-full text-xs font-bold">{c.quickserve_credits ?? 0} pts</span></td>
                          <td className="py-4 px-5 font-bold text-gray-700">{c.bookings_count ?? 0}</td>
                          <td className="py-4 px-5 text-xs text-gray-400">{c.created_at ? new Date(c.created_at).toLocaleDateString() : '—'}</td>
                          <td className="py-4 px-5">
                            <div className="flex gap-2">
                              <button onClick={() => setSelectedUserId(c._id)} className="bg-teal-600 hover:bg-teal-700 text-white px-3 py-1.5 rounded-lg font-bold text-xs transition-colors flex items-center gap-1"><Eye size={11} /> View</button>
                              <button onClick={() => grantRewardMutation.mutate({ email: c.email, amount: 250, type: 'credits', reason: 'Admin bonus' })} className="bg-blue-500 hover:bg-blue-600 text-white px-3 py-1.5 rounded-lg font-bold text-xs transition-colors">Reward</button>
                            </div>
                          </td>
                        </tr>
                      ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* ── PROVIDERS TAB ── */}
        {activeTab === 'providers' && (
          <div className="space-y-5">
            <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
              <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between gap-4 flex-wrap">
                <h3 className="font-black text-gray-900 text-xl flex items-center gap-2"><UserCheck size={18} /> Provider Management ({providers.length})</h3>
                <div className="relative">
                  <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                  <input type="text" placeholder="Search providers…" value={searchQuery}
                    onChange={e => setSearchQuery(e.target.value)}
                    className="pl-9 pr-4 py-2 text-sm border border-gray-200 rounded-xl focus:outline-none focus:border-teal-400 w-52" />
                </div>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gray-50">
                    <tr>{['Name', 'Email', 'Phone', 'Rating', 'Bookings', 'Specialization', 'Score', 'Status', 'Joined', 'Actions'].map(h => (
                      <th key={h} className="text-left py-3.5 px-5 font-black text-gray-400 text-xs uppercase tracking-wider">{h}</th>
                    ))}</tr>
                  </thead>
                  <tbody className="divide-y divide-gray-50">
                    {filteredProviders.length === 0
                      ? <tr><td colSpan={10} className="py-16 text-center text-gray-400 font-medium">No providers found</td></tr>
                      : filteredProviders.map((p: any, i: number) => (
                        <tr key={p._id || i} className="hover:bg-teal-50/30 transition-colors">
                          <td className="py-4 px-5 font-bold text-gray-900">{p.full_name}</td>
                          <td className="py-4 px-5 text-gray-500 text-sm">{p.email}</td>
                          <td className="py-4 px-5 text-gray-500 text-sm">{p.phone || '—'}</td>
                          <td className="py-4 px-5"><span className="text-yellow-600 font-black">{(p.rating ?? 0).toFixed(1)} ★</span></td>
                          <td className="py-4 px-5 font-bold text-gray-700">{p.bookings_count ?? 0}</td>
                          <td className="py-4 px-5 text-xs text-gray-500">{(p.specializations || p.service_categories || []).slice(0, 2).join(', ') || '—'}</td>
                          <td className="py-4 px-5"><span className="bg-indigo-100 text-indigo-700 px-2 py-0.5 rounded-full text-xs font-bold">{p.quickserve_score || p.aptitude_score || 0}</span></td>
                          <td className="py-4 px-5">
                            {p.verified_by_admin && !p.suspended ? (
                              <span className="bg-green-100 text-green-700 px-2.5 py-1 rounded-full text-xs font-bold flex items-center gap-1 w-fit"><CheckCircle size={11} /> Verified</span>
                            ) : p.suspended ? (
                              <span className="bg-red-100 text-red-700 px-2.5 py-1 rounded-full text-xs font-bold flex items-center gap-1 w-fit"><XCircle size={11} /> Suspended</span>
                            ) : (
                              <span className="bg-yellow-100 text-yellow-700 px-2.5 py-1 rounded-full text-xs font-bold">Pending</span>
                            )}
                          </td>
                          <td className="py-4 px-5 text-xs text-gray-400">{p.created_at ? new Date(p.created_at).toLocaleDateString() : '—'}</td>
                          <td className="py-4 px-5">
                            <div className="flex gap-1.5 flex-wrap">
                              <button onClick={() => setSelectedUserId(p._id)} className="bg-teal-600 hover:bg-teal-700 text-white px-2.5 py-1.5 rounded-lg font-bold text-xs transition-colors flex items-center gap-1"><Eye size={11} /> View</button>
                              {!p.verified_by_admin && !p.suspended && (
                                <button onClick={() => verifyMutation.mutate(p._id)} className="bg-green-500 hover:bg-green-600 text-white px-2.5 py-1.5 rounded-lg font-bold text-xs transition-colors">Verify</button>
                              )}
                              {!p.suspended && (
                                <button onClick={() => { const r = window.prompt('Suspension reason:'); if (r) suspendMutation.mutate({ id: p._id, reason: r }); }}
                                  className="bg-red-500 hover:bg-red-600 text-white px-2.5 py-1.5 rounded-lg font-bold text-xs transition-colors">Suspend</button>
                              )}
                            </div>
                          </td>
                        </tr>
                      ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* ── ALL BOOKINGS TAB ── */}
        {activeTab === 'bookings' && (
          <div className="space-y-5">
            <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
              <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between gap-4 flex-wrap">
                <h3 className="font-black text-gray-900 text-xl flex items-center gap-2"><Calendar size={18} /> All Bookings ({bookingsData?.total ?? 0})</h3>
                <div className="flex gap-2 flex-wrap">
                  {['all', 'pending', 'confirmed', 'in_progress', 'completed', 'cancelled'].map(f => (
                    <button key={f} onClick={() => setBookingFilter(f)}
                      className={`px-3 py-1.5 rounded-xl font-bold text-xs transition-all ${bookingFilter === f ? 'bg-teal-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}>
                      {f.replace('_', ' ')}
                    </button>
                  ))}
                </div>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gray-50">
                    <tr>{['Booking ID', 'Service', 'Customer', 'Provider', 'Amount', 'Payment', 'Status', 'Date', 'Action'].map(h => (
                      <th key={h} className="text-left py-3.5 px-5 font-black text-gray-400 text-xs uppercase tracking-wider">{h}</th>
                    ))}</tr>
                  </thead>
                  <tbody className="divide-y divide-gray-50">
                    {bookings.length === 0
                      ? <tr><td colSpan={9} className="py-16 text-center text-gray-400 font-medium">No bookings found</td></tr>
                      : bookings.map((b: any, i: number) => (
                        <tr key={b._id || i} className="hover:bg-teal-50/30 transition-colors">
                          <td className="py-4 px-5">
                            <span className="font-mono text-xs bg-gray-100 px-2 py-1 rounded-lg text-gray-600">#{b._id?.slice(-6)}</span>
                          </td>
                          <td className="py-4 px-5 font-bold text-gray-900 text-sm">{b.service_name || b.category || '—'}</td>
                          <td className="py-4 px-5">
                            <div>
                              <p className="font-bold text-gray-900 text-sm">{b.customer_name || '—'}</p>
                              <p className="text-xs text-gray-400">{b.customer_email}</p>
                              {b.customer_phone && <p className="text-xs text-gray-400">{b.customer_phone}</p>}
                            </div>
                          </td>
                          <td className="py-4 px-5">
                            <div>
                              <p className="font-bold text-gray-900 text-sm">{b.provider_name || '—'}</p>
                              <p className="text-xs text-gray-400">{b.provider_email}</p>
                              {b.provider_rating > 0 && <p className="text-xs text-yellow-600 font-bold">{b.provider_rating?.toFixed(1)} ★</p>}
                            </div>
                          </td>
                          <td className="py-4 px-5">
                            <p className="font-black text-gray-900">₹{(b.final_amount || b.amount || 0).toLocaleString('en-IN')}</p>
                            {b.provider_payout > 0 && <p className="text-xs text-green-600">Payout: ₹{b.provider_payout.toLocaleString('en-IN')}</p>}
                          </td>
                          <td className="py-4 px-5"><StatusBadge status={b.payment_status || 'unpaid'} /></td>
                          <td className="py-4 px-5"><StatusBadge status={b.status} /></td>
                          <td className="py-4 px-5 text-xs text-gray-400 whitespace-nowrap">{b.created_at ? new Date(b.created_at).toLocaleDateString() : '—'}</td>
                          <td className="py-4 px-5">
                            <div className="flex gap-1.5">
                              {b.customer_id && <button onClick={() => setSelectedUserId(b.user_id || b.customer_id)} className="text-xs bg-blue-50 text-blue-600 px-2 py-1 rounded-lg font-bold hover:bg-blue-100 transition-colors">Customer</button>}
                              {b.provider_id  && <button onClick={() => setSelectedUserId(b.provider_id)}  className="text-xs bg-teal-50 text-teal-600 px-2 py-1 rounded-lg font-bold hover:bg-teal-100 transition-colors">Provider</button>}
                            </div>
                          </td>
                        </tr>
                      ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* ── TRANSACTIONS TAB ── */}
        {activeTab === 'transactions' && (
          <div className="space-y-6">
            {/* Summary */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              {[
                { label: 'Total Incoming', val: `₹${(txSummary.total_incoming || 0).toLocaleString('en-IN')}`, icon: ArrowUpRight,   color: 'text-green-600',  bg: 'bg-green-50'  },
                { label: 'Total Outgoing', val: `₹${(txSummary.total_outgoing || 0).toLocaleString('en-IN')}`, icon: ArrowDownRight, color: 'text-red-600',    bg: 'bg-red-50'    },
                { label: 'Total Refunds',  val: `₹${(txSummary.total_refunds  || 0).toLocaleString('en-IN')}`, icon: RefreshCw,     color: 'text-orange-600', bg: 'bg-orange-50' },
                { label: 'Platform Net',   val: `₹${(txSummary.platform_net   || 0).toLocaleString('en-IN')}`, icon: Wallet,        color: 'text-teal-600',   bg: 'bg-teal-50'   },
              ].map(s => {
                const Icon = s.icon;
                return (
                  <div key={s.label} className={`${s.bg} rounded-2xl p-5 flex items-center gap-4`}>
                    <div className={`w-12 h-12 bg-white rounded-xl flex items-center justify-center shadow-sm`}><Icon size={22} className={s.color} /></div>
                    <div>
                      <p className={`text-2xl font-black ${s.color}`}>{s.val}</p>
                      <p className="text-xs font-bold text-gray-500 mt-0.5">{s.label}</p>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Filter + table */}
            <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
              <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between gap-4 flex-wrap">
                <h3 className="font-black text-gray-900 text-xl flex items-center gap-2"><CreditCard size={18} /> Transaction History ({txData?.total ?? 0})</h3>
                <div className="flex gap-2 flex-wrap">
                  {['all', 'payment', 'payout', 'refund'].map(f => (
                    <button key={f} onClick={() => setTxFilter(f)}
                      className={`px-4 py-2 rounded-xl font-bold text-xs transition-all ${txFilter === f ? 'bg-teal-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}>
                      {f.charAt(0).toUpperCase() + f.slice(1)}
                    </button>
                  ))}
                  <button onClick={() => refetchTx()} className="p-2 rounded-xl bg-gray-100 hover:bg-gray-200 transition-colors"><RefreshCw size={14} /></button>
                </div>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gray-50">
                    <tr>{['ID', 'Type', 'From / To', 'Amount', 'Method', 'Status', 'Description', 'Date'].map(h => (
                      <th key={h} className="text-left py-3.5 px-5 font-black text-gray-400 text-xs uppercase tracking-wider">{h}</th>
                    ))}</tr>
                  </thead>
                  <tbody className="divide-y divide-gray-50">
                    {transactions.length === 0
                      ? <tr><td colSpan={8} className="py-16 text-center text-gray-400 font-medium">No transactions found</td></tr>
                      : transactions.map((tx: any, i: number) => (
                        <tr key={tx.id || i} className="hover:bg-teal-50/30 transition-colors">
                          <td className="py-4 px-5"><span className="font-mono text-xs bg-gray-100 px-2 py-1 rounded-lg text-gray-600">#{tx.id?.slice(-6)}</span></td>
                          <td className="py-4 px-5">
                            <span className={`text-xs font-bold px-2.5 py-1 rounded-full ${
                              tx.type === 'payment' ? 'bg-blue-100 text-blue-700' :
                              tx.type === 'payout'  ? 'bg-green-100 text-green-700' :
                              'bg-orange-100 text-orange-700'
                            }`}>{tx.type}</span>
                          </td>
                          <td className="py-4 px-5">
                            <p className="font-bold text-gray-900 text-sm">{tx.customer_name || tx.provider_name || '—'}</p>
                            <p className="text-xs text-gray-400">{tx.customer_email || tx.provider_email || ''}</p>
                          </td>
                          <td className="py-4 px-5 font-black text-gray-900">₹{(tx.amount || 0).toLocaleString('en-IN')}</td>
                          <td className="py-4 px-5 text-gray-500 text-sm capitalize">{tx.method || '—'}</td>
                          <td className="py-4 px-5"><StatusBadge status={tx.status || 'pending'} /></td>
                          <td className="py-4 px-5 text-xs text-gray-500 max-w-xs truncate">{tx.description || '—'}</td>
                          <td className="py-4 px-5 text-xs text-gray-400 whitespace-nowrap">{tx.created_at ? new Date(tx.created_at).toLocaleDateString() : '—'}</td>
                        </tr>
                      ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* Section-level tabs delegated to sub-components */}
        {activeTab === 'command'            && <MarketplaceCommand />}
        {activeTab === 'providers-lifecycle'&& <ProviderLifecycle />}
        {activeTab === 'finance'            && <FinancialControls />}
        {activeTab === 'trust'              && <TrustSafety />}
        {activeTab === 'marketing'          && <MarketingGrowth />}
        {activeTab === 'analytics'          && <ProductAnalytics />}
        {activeTab === 'emergency'          && <EmergencyOperations />}
        {activeTab === 'community'          && <CommunityGovernance />}
        {activeTab === 'tech'               && <TechnicalOperations />}
        {activeTab === 'strategy'           && <StrategicPlanning />}
      </div>
    </DashboardLayout>
  );
};

export default AdminDashboardNew;
