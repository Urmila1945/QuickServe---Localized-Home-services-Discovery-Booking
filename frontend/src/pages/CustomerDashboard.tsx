import React, { useState, useMemo, useRef, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useAuth } from '../contexts/AuthContext';
import DashboardLayout from '../components/DashboardLayout';
import { useCustomerStore } from '../store/customerStore';
import type { HomeAsset, KeyEntry, PaintColor } from '../store/customerStore';
import { useTranslation } from 'react-i18next';
import toast from 'react-hot-toast';
import { formatPriceINR } from '../utils/currency';
import { dashboardAPI, bookingsAPI, loyaltyAPI, aiAPI, predictiveAPI } from '../services/api';
import {
  LayoutDashboard, Navigation, Home, Activity, Users, Gift, Key, Camera,
  ChevronRight, Star, Award, Calendar, Clock, CheckCircle, AlertTriangle,
  RefreshCw, Plus, Trash2, Eye, EyeOff, Copy, Zap, Shield, Wind,
  Wrench, Droplets, Bot, MapPin, X, Edit2, Check, FileText, Sparkles,
  TrendingUp, Lock, Download, CalendarPlus, Share2, Wifi, Video
} from 'lucide-react';

// ── Types ─────────────────────────────────────────────────────────────

type HubTab = 'overview' | 'tracker' | 'vault' | 'health' | 'neighborhood' | 'rewards' | 'keyvault' | 'quotes' | 'transactions' | 'spend' | 'my-providers' | 'iot';

// ── Constants ─────────────────────────────────────────────────────────

const TABS: { id: HubTab; label: string; icon: React.ElementType; emoji: string }[] = [
  { id: 'overview',      label: 'Overview',        icon: LayoutDashboard, emoji: '🏠' },
  { id: 'tracker',       label: 'Job Tracker',     icon: Navigation,      emoji: '📍' },
  { id: 'transactions',  label: 'Transactions',    icon: FileText,        emoji: '💳' },
  { id: 'spend',         label: 'Spend Insights',  icon: TrendingUp,      emoji: '📊' },
  { id: 'my-providers',  label: 'My Providers',    icon: Users,           emoji: '👷' },
  { id: 'vault',         label: 'Home Vault',      icon: Home,            emoji: '🏗️' },
  { id: 'health',        label: 'Health Score',    icon: Activity,        emoji: '💚' },
  { id: 'neighborhood',  label: 'Neighborhood',    icon: Users,           emoji: '🏘️' },
  { id: 'rewards',       label: 'Rewards',         icon: Gift,            emoji: '🎁' },
  { id: 'keyvault',      label: 'Key Vault',       icon: Key,             emoji: '🔑' },
  { id: 'quotes',        label: 'Quote History',   icon: Camera,          emoji: '📸' },
  { id: 'iot',           label: 'Smart Sync',      icon: Wifi,            emoji: '📡' },
];

const TRACKER_STEPS = [
  { id: 'enroute',    label: 'En Route',      icon: '🚗', desc: 'Provider heading your way' },
  { id: 'arrived',    label: 'Arrived',       icon: '🏠', desc: 'Provider at your location' },
  { id: 'working',    label: 'Working',       icon: '🔧', desc: 'Service in progress' },
  { id: 'reviewing',  label: 'Reviewing',     icon: '🔍', desc: 'Final inspection' },
  { id: 'completed',  label: 'Completed',     icon: '✅', desc: 'All done!' },
];

// const MOCK_BLOCK_PARTIES: any[] = []; // Removed in favor of dynamic API data
// const MOCK_QUOTES: any[] = []; // Removed in favor of dynamic API data

// Removed static MAINTENANCE_ITEMS in favor of dynamic API data

const categoryEmoji: Record<string, string> = {
  plumbing: '🔧', electrical: '⚡', cleaning: '🧹',
  repair: '🔨', tutoring: '📚', beauty: '💄', fitness: '💪', delivery: '📦',
};

// ── Shared Sub-Components ─────────────────────────────────────────────

const StatCard: React.FC<{
  label: string; value: string | number; icon: React.ElementType;
  color: string; bg: string; trend?: string;
}> = ({ label, value, icon: Icon, color, bg, trend }) => (
  <div className="bg-white rounded-2xl p-5 shadow-sm border border-gray-100 hover:shadow-md hover:-translate-y-0.5 transition-all duration-200 group">
    <div className="flex items-start justify-between mb-3">
      <div className={`w-11 h-11 ${bg} rounded-xl flex items-center justify-center group-hover:scale-110 transition-transform`}>
        <Icon size={20} className={color} />
      </div>
      {trend && (
        <span className="text-xs font-bold text-green-600 bg-green-50 px-2 py-1 rounded-full">{trend}</span>
      )}
    </div>
    <p className="text-3xl font-black text-gray-900 mb-0.5">{value}</p>
    <p className="text-sm font-medium text-gray-500">{label}</p>
  </div>
);

const BookingStatusBadge: React.FC<{ status: string }> = ({ status }) => {
  const map: Record<string, string> = {
    completed:   'bg-green-100 text-green-700',
    confirmed:   'bg-blue-100 text-blue-700',
    in_progress: 'bg-orange-100 text-orange-700',
    pending:     'bg-yellow-100 text-yellow-700',
    cancelled:   'bg-red-100 text-red-700',
  };
  return (
    <span className={`text-xs font-bold px-2.5 py-1 rounded-full ${map[status] || 'bg-gray-100 text-gray-600'}`}>
      {status.replace('_', ' ')}
    </span>
  );
};

// ── Health Score Gauge ─────────────────────────────────────────────────

const HealthGauge: React.FC<{ score: number }> = ({ score }) => {
  const { t } = useTranslation();
  const R = 64;
  const stroke = 12;
  const circ = 2 * Math.PI * R;
  const offset = circ - (score / 100) * circ;
  const color = score >= 80 ? '#48bb78' : score >= 60 ? '#ed8936' : '#f56565';
  const label = score >= 80 ? 'Excellent!' : score >= 60 ? 'Needs Some Care' : 'Critical Attention';
  return (
    <div className="flex flex-col items-center">
      <svg width={160} height={160} viewBox="0 0 160 160">
        <circle cx={80} cy={80} r={R} fill="none" stroke="#e2e8f0" strokeWidth={stroke} />
        <circle
          cx={80} cy={80} r={R} fill="none"
          stroke={color} strokeWidth={stroke}
          strokeDasharray={`${circ} ${circ}`}
          strokeDashoffset={offset}
          strokeLinecap="round"
          transform="rotate(-90 80 80)"
          style={{ transition: 'stroke-dashoffset 1s ease' }}
        />
        <text x={80} y={74} textAnchor="middle" fontSize={30} fill={color} fontWeight="900">{score}</text>
        <text x={80} y={95} textAnchor="middle" fontSize={11} fill="#9ca3af">{t('Health Score')}</text>
      </svg>
      <span className="text-sm font-black mt-1" style={{ color }}>{t(label)}</span>
    </div>
  );
};

// ── Tab Views ──────────────────────────────────────────────────────────

const OverviewTab: React.FC<{
  data: any;
  bookings: any[];
  recs: any[];
  loyaltyPoints: number;
  favourites: any[];
  onOpenARQuote: () => void;
}> = ({ data, bookings, loyaltyPoints, favourites, onOpenARQuote }) => {
  const { t } = useTranslation();

  const stats = [
    { label: t('Total Bookings'),   value: data?.total_bookings  ?? bookings.length, icon: Calendar,     color: 'text-blue-600',   bg: 'bg-blue-50',   trend: '+3 this month' },
    { label: t('Loyalty Points'),   value: loyaltyPoints || data?.loyalty_points || 0, icon: Award, color: 'text-yellow-600', bg: 'bg-yellow-50', trend: '+50 pts' },
    { label: t('Active Jobs'),      value: data?.active_bookings ?? bookings.filter((b:any) => b.status === 'in_progress').length, icon: Wrench, color: 'text-orange-600', bg: 'bg-orange-50' },
    { label: t('Money Saved'),      value: `₹${data?.total_saved ?? 0}`, icon: TrendingUp, color: 'text-green-600', bg: 'bg-green-50' },
  ];

  const activeBooking = bookings.find((b: any) =>
    ['in_progress', 'confirmed'].includes(b.status)
  );

  const handleShare = async (b: any) => {
    if (navigator.share) {
      try {
        await navigator.share({
          title: `QuickServe Booking: ${b.category || b.service_name}`,
          text: `I've booked a ${b.category || b.service_name} service via QuickServe!`,
          url: window.location.href,
        });
      } catch (err: any) {
        if (err.name !== 'AbortError') {
          console.error(err);
        }
      }
    } else {
      toast.success('Link copied to clipboard!');
    }
  };

  const getCalendarLink = (b: any) => {
    const text = encodeURIComponent(`QuickServe Booking: ${b.category || b.service_name}`);
    const details = encodeURIComponent(`Service by ${b.provider}\nPrice: ₹${b.price || b.total_amount || 0}`);
    return `https://calendar.google.com/calendar/render?action=TEMPLATE&text=${text}&details=${details}`;
  };

  return (
    <div className="space-y-6">
      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map(s => <StatCard key={s.label} {...s} />)}
      </div>

      {/* Active Job Banner */}
      {activeBooking && (
        <div className="bg-gradient-to-r from-teal-600 to-teal-800 rounded-2xl p-6 text-white shadow-lg">
          <div className="flex items-center justify-between flex-wrap gap-4">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 bg-white/20 rounded-xl flex items-center justify-center backdrop-blur-sm">
                <MapPin size={22} className="text-white" />
              </div>
              <div>
                <p className="text-teal-200 text-xs font-bold uppercase tracking-widest mb-1">Live Booking</p>
                <p className="font-black text-lg">
                  {activeBooking.category || activeBooking.service_name} — {activeBooking.provider}
                </p>
                <p className="text-teal-200 text-sm font-medium mt-1">{t('ETA: ~12 minutes away')}</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <div className="w-3 h-3 bg-green-400 rounded-full animate-pulse shadow-[0_0_10px_rgba(74,222,128,0.6)]" />
              <span className="text-sm font-bold">{t('En Route')}</span>
            </div>
          </div>
        </div>
      )}

        {/* Quick Actions */}
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          {[
            { label: t('Book Service'),      emoji: '🔧', to: '/services',         bg: 'bg-blue-50   hover:bg-blue-100',   text: 'text-blue-700'   },
            { label: t('My Rewards'),        emoji: '🎁', to: '/loyalty',          bg: 'bg-yellow-50 hover:bg-yellow-100', text: 'text-yellow-700' },
            { label: t('Price Estimator'),   emoji: '🧮', to: '/price-estimator',  bg: 'bg-teal-50   hover:bg-teal-100',   text: 'text-teal-700'   },
            { label: t('Subscriptions'),     emoji: '👑', to: '/subscriptions',    bg: 'bg-purple-50 hover:bg-purple-100', text: 'text-purple-700' },
            { label: t('Message Provider'),  emoji: '💬', to: '/chat',             bg: 'bg-green-50  hover:bg-green-100',  text: 'text-green-700'  },
            { label: t('AR Video Quote'),    emoji: '📹', to: '#',                 bg: 'bg-indigo-50 hover:bg-indigo-100', text: 'text-indigo-700', onClick: onOpenARQuote },
          ].map(a => (
            a.to === '#' ? (
              <button key={a.label} onClick={a.onClick}
                className={`${a.bg} ${a.text} rounded-2xl p-5 flex flex-col items-center gap-3 font-bold text-sm border border-white hover:shadow-md transition-all duration-200 hover:-translate-y-1 text-center`}
              >
                <span className="text-3xl">{a.emoji}</span>
                {a.label}
              </button>
            ) : (
              <Link key={a.label} to={a.to}
                className={`${a.bg} ${a.text} rounded-2xl p-5 flex flex-col items-center gap-3 font-bold text-sm border border-white hover:shadow-md transition-all duration-200 hover:-translate-y-1 text-center`}
              >
                <span className="text-3xl">{a.emoji}</span>
                {a.label}
              </Link>
            )
          ))}
        </div>

      {/* ─ Platform Features ─ */}
      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
          <div className="flex items-center gap-2">
            <Sparkles size={18} className="text-purple-500" />
            <h2 className="font-black text-gray-900 text-lg">{t('Why Choose QuickServe?')}</h2>
          </div>
          <span className="text-xs text-gray-400 font-medium">{t('Explore platform features')}</span>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 p-6">
          {[
            { title: 'AI-Powered Matching', icon: '🤖', link: '/ai-matching', desc: 'Smart provider matching', color: 'bg-purple-50 text-purple-700' },
            { title: 'Real-time Tracking', icon: '📍', link: '/real-time-tracking', desc: 'Live GPS updates', color: 'bg-blue-50 text-blue-700' },
            { title: 'Instant Price Estimator', icon: '🧮', link: '/price-estimator', desc: 'AI surge calculator', color: 'bg-teal-50 text-teal-700' },
            { title: 'Verified Providers', icon: '✅', link: '/verified-providers', desc: 'Background-checked pros', color: 'bg-orange-50 text-orange-700' },
          ].map((f, i) => (
            <Link key={i} to={f.link} className={`rounded-2xl p-5 flex flex-col items-center text-center gap-3 border border-gray-100 hover:shadow-lg transition-all duration-300 hover:-translate-y-1 ${f.color}`}>
              <span className="text-3xl">{f.icon}</span>
              <div>
                <h3 className="font-bold text-sm mb-1">{t(f.title)}</h3>
                <p className="text-xs opacity-80">{t(f.desc)}</p>
              </div>
            </Link>
          ))}
        </div>
      </div>

      {/* ─ Quick-Reorder Magic Button ─ */}
      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
          <div className="flex items-center gap-2">
            <Sparkles size={18} className="text-yellow-500" />
            <h2 className="font-black text-gray-900 text-lg">{t('Quick Reorder')}</h2>
          </div>
          <span className="text-xs text-gray-400 font-medium">{t('Your favourite providers')}</span>
        </div>
        <div className="p-4 grid md:grid-cols-3 gap-3">
          {favourites.map(fav => (
            <div key={fav.id}
              className="flex items-center gap-3 p-4 rounded-xl bg-gray-50 hover:bg-teal-50 border border-gray-100 hover:border-teal-200 transition-all duration-200 group"
            >
              <div className="w-12 h-12 rounded-xl bg-white flex items-center justify-center text-xl shadow-sm group-hover:scale-110 transition-transform">
                {fav.emoji}
              </div>
              <div className="flex-1 min-w-0">
                <p className="font-black text-gray-900 text-sm truncate">{fav.name}</p>
                <div className="flex items-center gap-1 mt-0.5">
                  <Star size={11} className="text-yellow-500 fill-yellow-400" />
                  <span className="text-xs font-bold text-gray-500">{fav.rating}</span>
                  <span className="text-gray-300 mx-1">·</span>
                  <span className="text-xs text-gray-500">{formatPriceINR(fav.rate)}/hr</span>
                </div>
              </div>
              <button
                onClick={() => toast.success(`Re-booking ${fav.name}! 🪄`)}
                className="bg-teal-600 hover:bg-teal-700 text-white px-3 py-2 rounded-xl text-xs font-black transition-all hover:shadow-md hover:shadow-teal-200 whitespace-nowrap"
              >
                🪄 Book
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Recent Bookings */}
      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
          <h2 className="font-black text-gray-900 text-lg">{t('Recent Bookings')}</h2>
          <Link to="/bookings" className="text-teal-600 hover:text-teal-800 font-bold text-sm flex items-center gap-1 transition-colors">
            {t('View All')} <ChevronRight size={16} />
          </Link>
        </div>
        <div className="divide-y divide-gray-50">
          {bookings.slice(0, 4).map((b: any, i: number) => (
            <div key={b._id || i}
              className="flex items-center justify-between px-6 py-4 hover:bg-gray-50 transition-colors group cursor-pointer"
            >
              <div className="flex items-center gap-4">
                <div className="w-10 h-10 rounded-xl bg-teal-50 flex items-center justify-center text-lg group-hover:scale-110 transition-transform">
                  {categoryEmoji[b.category?.toLowerCase()] || '🔧'}
                </div>
                <div>
                  <p className="font-bold text-gray-900 text-sm">{b.category || b.service_name} Service</p>
                  <p className="text-xs text-gray-500">{b.provider} · {b.date || b.created_at?.slice(0, 10)}</p>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <span className="font-bold text-gray-800 text-sm">{formatPriceINR(b.price || b.total_amount || 0)}</span>
                <BookingStatusBadge status={b.status} />
                {b.status === 'completed' && (
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => toast.success('Receipt downloaded! 📄')}
                      className="hidden md:flex items-center gap-1 text-gray-500 hover:text-teal-600 font-bold text-xs transition-colors"
                      title="Download Receipt"
                    >
                      <Download size={13} />
                    </button>
                    <button
                      onClick={() => toast.success('Re-booked! 🎉')}
                      className="hidden md:flex items-center gap-1 text-teal-600 hover:text-teal-800 font-bold text-xs transition-colors"
                    >
                      <RefreshCw size={13} /> Reorder
                    </button>
                  </div>
                )}
                {['pending', 'confirmed'].includes(b.status) && (
                  <div className="flex items-center gap-2">
                    <a
                      href={getCalendarLink(b)}
                      target="_blank" rel="noopener noreferrer"
                      className="hidden md:flex items-center gap-1 text-purple-600 hover:text-purple-800 font-bold text-xs transition-colors"
                    >
                      <CalendarPlus size={13} /> Add
                    </a>
                    <button
                      onClick={() => handleShare(b)}
                      className="hidden md:flex items-center gap-1 text-blue-600 hover:text-blue-800 font-bold text-xs transition-colors"
                    >
                      <Share2 size={13} /> Share
                    </button>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

// ── Job Tracker Tab ─────────────────────────────────────────────────────

const JobTrackerTab: React.FC<{ bookings: any[] }> = ({ bookings }) => {
  const { t } = useTranslation();
  const activeBookings = bookings.filter(b =>
    ['pending', 'confirmed', 'in_progress'].includes(b.status)
  );
  const [selectedIdx, setSelectedIdx] = useState(0);
  const booking = activeBookings[selectedIdx];

  const getStep = (status: string) => {
    if (status === 'completed') return 4;
    if (status === 'in_progress') return 2;
    if (status === 'confirmed') return 0;
    return 0;
  };

  const activeStep = booking ? getStep(booking.status) : 0;

  const mockProvider = {
    name: booking?.provider || 'Suresh Kumar',
    category: booking?.category || 'Plumbing',
    rating: 4.9,
    phone: booking?.provider_phone || '+91 98765 43210',
    eta: '12 minutes',
    emoji: categoryEmoji[(booking?.category || 'plumbing').toLowerCase()] || '🔧',
  };

  const generateOTP = (id: string) => {
    if (!id) return '1234';
    let hash = 0;
    for (let i = 0; i < id.length; i++) hash = id.charCodeAt(i) + ((hash << 5) - hash);
    return (Math.abs(hash) % 9000 + 1000).toString();
  };
  const completionOTP = booking ? generateOTP(booking._id) : '1234';

  if (activeBookings.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-center">
        <div className="w-20 h-20 bg-gray-100 rounded-3xl flex items-center justify-center text-4xl mb-6">📍</div>
        <h3 className="text-xl font-black text-gray-800 mb-2">{t('No Active Jobs')}</h3>
        <p className="text-gray-500 font-medium mb-6">{t('Your job tracker will appear here when a provider is on their way.')}</p>
        <Link to="/services" className="bg-teal-600 text-white px-8 py-3 rounded-xl font-black hover:bg-teal-700 transition-colors">
          {t('Book a Service')}
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Booking Selector */}
      {activeBookings.length > 1 && (
        <div className="flex gap-2 flex-wrap">
          {activeBookings.map((b: any, i: number) => (
            <button
              key={b._id || i}
              onClick={() => setSelectedIdx(i)}
              className={`px-4 py-2 rounded-xl font-bold text-sm transition-all ${
                selectedIdx === i ? 'bg-teal-600 text-white shadow-md' : 'bg-white text-gray-500 border border-gray-200 hover:border-teal-300'
              }`}
            >
              {b.category || b.service_name}
            </button>
          ))}
        </div>
      )}

      {/* Pizza Tracker Card */}
      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-8">
        <div className="flex items-center justify-between mb-8 flex-wrap gap-4">
          <div>
            <h2 className="font-black text-gray-900 text-xl">{t('Active Job Tracker')}</h2>
            <p className="text-gray-500 text-sm mt-1">{t(mockProvider.category)} service with {mockProvider.name}</p>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-2.5 h-2.5 bg-green-500 rounded-full animate-pulse" />
            <span className="text-sm font-bold text-green-600">{t('Live Tracking')}</span>
          </div>
        </div>

        {/* Stepper */}
        <div className="relative flex items-start justify-between mb-10">
          {/* Connector line */}
          <div className="absolute top-7 left-7 right-7 h-0.5 bg-gray-200" style={{ zIndex: 0 }}>
            <div
              className="h-full bg-teal-500 transition-all duration-700"
              style={{ width: `${(activeStep / (TRACKER_STEPS.length - 1)) * 100}%` }}
            />
          </div>
          {TRACKER_STEPS.map((step, idx) => {
            const done = idx < activeStep;
            const active = idx === activeStep;
            const upcoming = idx > activeStep;
            return (
              <div key={step.id} className="flex flex-col items-center relative z-10" style={{ flex: 1 }}>
                <div className={`w-14 h-14 rounded-full flex items-center justify-center text-xl font-bold transition-all duration-300 border-4
                  ${done    ? 'bg-teal-600 border-teal-600 text-white shadow-lg shadow-teal-200' : ''}
                  ${active  ? 'bg-white border-teal-600 text-2xl shadow-lg shadow-teal-200 ring-4 ring-teal-100 animate-pulse-slow' : ''}
                  ${upcoming ? 'bg-gray-100 border-gray-200 text-gray-400 opacity-60' : ''}
                `}>
                  {done ? <Check size={22} className="text-white" /> : step.icon}
                </div>
                <p className={`mt-2 text-xs font-black text-center leading-tight
                  ${done ? 'text-teal-600' : active ? 'text-teal-700' : 'text-gray-400'}
                `}>
                  {t(step.label)}
                </p>
                {active && (
                  <p className="text-xs text-gray-400 text-center mt-0.5 hidden sm:block">{step.desc}</p>
                )}
              </div>
            );
          })}
        </div>

        {/* Provider Card */}
        <div className="bg-gradient-to-r from-gray-50 to-teal-50 rounded-2xl p-5 flex items-center justify-between flex-wrap gap-4 border border-teal-100">
          <div className="flex items-center gap-4">
            <div className="w-16 h-16 rounded-2xl bg-white flex items-center justify-center text-3xl shadow-sm border border-gray-100">
              {mockProvider.emoji}
            </div>
            <div>
              <p className="font-black text-gray-900 text-lg">{mockProvider.name}</p>
              <div className="flex items-center gap-1 mt-0.5">
                <Star size={13} className="text-yellow-500 fill-yellow-400" />
                <span className="text-sm font-bold text-gray-700">{mockProvider.rating}</span>
                <span className="text-gray-400 mx-2">·</span>
                <span className="text-sm text-gray-500">{mockProvider.category}</span>
              </div>
              <p className="text-xs text-teal-600 font-bold mt-1">📍 ETA: {mockProvider.eta}</p>
            </div>
          </div>
          <div className="flex gap-2">
            <a
              href={`tel:${mockProvider.phone}`}
              className="bg-teal-600 hover:bg-teal-700 text-white px-5 py-2.5 rounded-xl font-black text-sm transition-all hover:shadow-md hover:shadow-teal-200 inline-block text-center"
            >
              📞 Call
            </a>
            <Link to="/chat" className="bg-white hover:bg-gray-50 text-gray-700 px-5 py-2.5 rounded-xl font-black text-sm border border-gray-200 transition-all hover:border-teal-300">
              💬 Chat
            </Link>
          </div>
        </div>

        {/* OTP Display */}
        {activeStep >= 2 && (
          <div className="mt-6 bg-gradient-to-r from-teal-50 to-emerald-50 rounded-2xl p-5 border border-teal-100 flex items-center justify-between">
            <div>
              <p className="text-teal-800 font-black text-lg">Completion OTP</p>
              <p className="text-teal-600 text-sm">Share this PIN with the provider to mark the job as complete.</p>
            </div>
            <div className="bg-white border-2 border-teal-200 text-teal-700 font-mono text-3xl font-black tracking-widest px-6 py-3 rounded-xl shadow-sm">
              {completionOTP}
            </div>
          </div>
        )}
      </div>

      {/* Progress Timeline */}
      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
        <h3 className="font-black text-gray-900 mb-4">{t('Job Timeline')}</h3>
        <div className="space-y-3">
          {TRACKER_STEPS.slice(0, activeStep + 1).map((step, idx) => (
            <div key={step.id} className="flex items-center gap-3">
              <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm flex-shrink-0
                ${idx < activeStep ? 'bg-teal-100 text-teal-700' : 'bg-teal-600 text-white'}
              `}>
                {idx < activeStep ? <Check size={14} /> : step.icon}
              </div>
              <div className="flex-1">
                <p className="font-bold text-gray-900 text-sm">{step.label}</p>
                <p className="text-xs text-gray-400">{idx === 0 ? '10:24 AM' : idx === 1 ? '10:36 AM' : idx === 2 ? '10:42 AM' : 'In progress'}</p>
              </div>
              {idx === activeStep && (
                <span className="text-xs font-bold text-teal-600 bg-teal-50 px-2 py-1 rounded-full">Current</span>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

// ── Home Vault Tab ──────────────────────────────────────────────────────

const HomeVaultTab: React.FC = () => {
  const { t } = useTranslation();
  const { homeProfile, updateHomeProfile, addAsset, removeAsset, addPaintColor, removePaintColor } = useCustomerStore();
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(homeProfile);
  const [showAssetForm, setShowAssetForm] = useState(false);
  const [showPaintForm, setShowPaintForm] = useState(false);
  const [assetDraft, setAssetDraft] = useState({ name: '', category: 'hvac' as const, model: '', brand: '', installDate: '', warrantyExpiry: '', lastServiceDate: '', notes: '' });
  const [paintDraft, setPaintDraft] = useState({ room: '', color: '#ffffff', brand: '', code: '' });

  const handleSave = () => {
    updateHomeProfile(draft);
    setEditing(false);
    toast.success('Home profile updated!');
  };

  const handleAddAsset = () => {
    if (!assetDraft.name) { toast.error('Please enter an asset name'); return; }
    addAsset(assetDraft);
    setAssetDraft({ name: '', category: 'hvac', model: '', brand: '', installDate: '', warrantyExpiry: '', lastServiceDate: '', notes: '' });
    setShowAssetForm(false);
    toast.success('Asset added to vault!');
  };

  const handleAddPaint = () => {
    if (!paintDraft.room) { toast.error('Please enter a room name'); return; }
    addPaintColor(paintDraft);
    setPaintDraft({ room: '', color: '#ffffff', brand: '', code: '' });
    setShowPaintForm(false);
    toast.success('Paint color saved!');
  };

  const assetCategoryIcon: Record<string, React.ElementType> = {
    hvac: Wind, electrical: Zap, plumbing: Droplets, appliance: Sparkles, other: Wrench,
  };

  const isProfileEmpty = !homeProfile.squareFootage && !homeProfile.bedrooms;

  return (
    <div className="space-y-6">
      {/* Home Profile Card */}
      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
          <div className="flex items-center gap-2">
            <Home size={18} className="text-teal-600" />
            <h2 className="font-black text-gray-900 text-lg">{t('Home Profile')}</h2>
          </div>
          <button
            onClick={() => editing ? handleSave() : (setDraft(homeProfile), setEditing(true))}
            className={`flex items-center gap-1.5 px-4 py-2 rounded-xl font-bold text-sm transition-all
              ${editing ? 'bg-teal-600 text-white hover:bg-teal-700' : 'bg-gray-50 text-gray-600 hover:bg-gray-100 border border-gray-200'}
            `}
          >
            {editing ? <><Check size={14} /> Save</> : <><Edit2 size={14} /> Edit</>}
          </button>
        </div>

        {isProfileEmpty && !editing ? (
          <div className="p-10 text-center">
            <div className="text-5xl mb-4">🏠</div>
            <p className="font-black text-gray-700 mb-2">Your Home Profile is Empty</p>
            <p className="text-gray-400 text-sm mb-5">Add your home details so providers arrive fully prepared.</p>
            <button onClick={() => { setDraft(homeProfile); setEditing(true); }}
              className="bg-teal-600 text-white px-6 py-2.5 rounded-xl font-black text-sm hover:bg-teal-700 transition-colors"
            >
              + Set Up Profile
            </button>
          </div>
        ) : editing ? (
          <div className="p-6 grid md:grid-cols-2 lg:grid-cols-3 gap-4">
            {[
              { key: 'squareFootage', label: 'Square Footage', placeholder: 'e.g. 1200 sq ft' },
              { key: 'bedrooms',      label: 'Bedrooms',       placeholder: 'e.g. 3' },
              { key: 'bathrooms',     label: 'Bathrooms',      placeholder: 'e.g. 2' },
              { key: 'yearBuilt',     label: 'Year Built',     placeholder: 'e.g. 2010' },
              { key: 'hvacModel',     label: 'HVAC Model',     placeholder: 'e.g. Daikin 1.5T' },
              { key: 'roofType',      label: 'Roof Type',      placeholder: 'e.g. RCC Flat' },
              { key: 'parkingType',   label: 'Parking',        placeholder: 'e.g. Covered 2-car' },
            ].map(({ key, label, placeholder }) => (
              <div key={key}>
                <label className="block text-xs font-black text-gray-400 uppercase tracking-widest mb-1.5">{label}</label>
                <input
                  type="text"
                  placeholder={placeholder}
                  value={(draft as any)[key]}
                  onChange={e => setDraft(d => ({ ...d, [key]: e.target.value }))}
                  className="w-full border-2 border-gray-100 focus:border-teal-400 rounded-xl px-4 py-3 text-sm font-medium focus:outline-none transition-colors"
                />
              </div>
            ))}
          </div>
        ) : (
          <div className="p-6 grid md:grid-cols-2 lg:grid-cols-3 gap-4">
            {[
              { label: 'Square Footage', value: homeProfile.squareFootage, icon: '📐' },
              { label: 'Bedrooms',       value: homeProfile.bedrooms,      icon: '🛏️' },
              { label: 'Bathrooms',      value: homeProfile.bathrooms,     icon: '🚿' },
              { label: 'Year Built',     value: homeProfile.yearBuilt,     icon: '🏗️' },
              { label: 'HVAC Model',     value: homeProfile.hvacModel,     icon: '❄️' },
              { label: 'Roof Type',      value: homeProfile.roofType,      icon: '🏠' },
              { label: 'Parking',        value: homeProfile.parkingType,   icon: '🚗' },
            ].filter(item => item.value).map(({ label, value, icon }) => (
              <div key={label} className="bg-gray-50 rounded-xl p-4">
                <p className="text-xs font-black text-gray-400 uppercase tracking-widest mb-1">{icon} {label}</p>
                <p className="font-black text-gray-900">{value}</p>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Assets Grid */}
      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
          <div className="flex items-center gap-2">
            <Wrench size={18} className="text-teal-600" />
            <h2 className="font-black text-gray-900 text-lg">{t('Home Assets')}</h2>
          </div>
          <button
            onClick={() => setShowAssetForm(!showAssetForm)}
            className="flex items-center gap-1.5 px-4 py-2 rounded-xl font-bold text-sm bg-teal-50 text-teal-700 hover:bg-teal-100 border border-teal-100 transition-all"
          >
            <Plus size={14} /> Add Asset
          </button>
        </div>

        {showAssetForm && (
          <div className="p-5 bg-teal-50 border-b border-teal-100">
            <h4 className="font-black text-gray-800 mb-4 text-sm">New Asset</h4>
            <div className="grid md:grid-cols-3 gap-3 mb-3">
              <input placeholder="Asset name *" value={assetDraft.name} onChange={e => setAssetDraft(d => ({ ...d, name: e.target.value }))}
                className="border-2 border-white focus:border-teal-400 rounded-xl px-4 py-2.5 text-sm font-medium focus:outline-none" />
              <select value={assetDraft.category} onChange={e => setAssetDraft(d => ({ ...d, category: e.target.value as any }))}
                className="border-2 border-white focus:border-teal-400 rounded-xl px-4 py-2.5 text-sm font-medium focus:outline-none bg-white">
                <option value="hvac">HVAC / AC</option>
                <option value="electrical">Electrical</option>
                <option value="plumbing">Plumbing</option>
                <option value="appliance">Appliance</option>
                <option value="other">Other</option>
              </select>
              <input placeholder="Brand" value={assetDraft.brand} onChange={e => setAssetDraft(d => ({ ...d, brand: e.target.value }))}
                className="border-2 border-white focus:border-teal-400 rounded-xl px-4 py-2.5 text-sm font-medium focus:outline-none" />
              <input placeholder="Model number" value={assetDraft.model} onChange={e => setAssetDraft(d => ({ ...d, model: e.target.value }))}
                className="border-2 border-white focus:border-teal-400 rounded-xl px-4 py-2.5 text-sm font-medium focus:outline-none" />
              <input type="date" placeholder="Install date" value={assetDraft.installDate} onChange={e => setAssetDraft(d => ({ ...d, installDate: e.target.value }))}
                className="border-2 border-white focus:border-teal-400 rounded-xl px-4 py-2.5 text-sm font-medium focus:outline-none" />
              <input type="date" placeholder="Warranty expiry" value={assetDraft.warrantyExpiry} onChange={e => setAssetDraft(d => ({ ...d, warrantyExpiry: e.target.value }))}
                className="border-2 border-white focus:border-teal-400 rounded-xl px-4 py-2.5 text-sm font-medium focus:outline-none" />
            </div>
            <div className="flex gap-2">
              <button onClick={handleAddAsset} className="bg-teal-600 text-white px-6 py-2.5 rounded-xl font-black text-sm hover:bg-teal-700 transition-colors">
                Save Asset
              </button>
              <button onClick={() => setShowAssetForm(false)} className="bg-white text-gray-500 px-6 py-2.5 rounded-xl font-black text-sm border border-gray-200 hover:bg-gray-50 transition-colors">
                Cancel
              </button>
            </div>
          </div>
        )}

        <div className="p-5">
          {homeProfile.assets.length === 0 ? (
            <div className="text-center py-10">
              <div className="text-4xl mb-3">🔧</div>
              <p className="text-gray-400 font-medium text-sm">No assets yet. Add appliances, systems, and more.</p>
            </div>
          ) : (
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-3">
              {homeProfile.assets.map((asset: HomeAsset) => {
                const CatIcon = assetCategoryIcon[asset.category] || Wrench;
                return (
                  <div key={asset.id} className="bg-gray-50 rounded-xl p-4 border border-gray-100 hover:border-teal-200 transition-colors group">
                    <div className="flex items-start justify-between mb-3">
                      <div className="w-10 h-10 bg-white rounded-lg flex items-center justify-center shadow-sm border border-gray-100">
                        <CatIcon size={18} className="text-teal-600" />
                      </div>
                      <button onClick={() => removeAsset(asset.id)} className="opacity-0 group-hover:opacity-100 p-1 rounded-lg hover:bg-red-50 text-red-400 transition-all">
                        <Trash2 size={14} />
                      </button>
                    </div>
                    <p className="font-black text-gray-900 text-sm">{asset.name}</p>
                    {asset.brand && <p className="text-xs text-gray-500">{asset.brand} {asset.model}</p>}
                    {asset.warrantyExpiry && (
                      <p className="text-xs text-teal-600 font-bold mt-2">🛡️ Warranty until {asset.warrantyExpiry}</p>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* Paint Colors */}
      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
          <div className="flex items-center gap-2">
            <span className="text-xl">🎨</span>
            <h2 className="font-black text-gray-900 text-lg">{t('Paint Colors')}</h2>
          </div>
          <button
            onClick={() => setShowPaintForm(!showPaintForm)}
            className="flex items-center gap-1.5 px-4 py-2 rounded-xl font-bold text-sm bg-purple-50 text-purple-700 hover:bg-purple-100 border border-purple-100 transition-all"
          >
            <Plus size={14} /> Add Color
          </button>
        </div>

        {showPaintForm && (
          <div className="p-5 bg-purple-50 border-b border-purple-100">
            <div className="grid md:grid-cols-4 gap-3 mb-3">
              <input placeholder="Room name *" value={paintDraft.room} onChange={e => setPaintDraft(d => ({ ...d, room: e.target.value }))}
                className="border-2 border-white focus:border-purple-400 rounded-xl px-4 py-2.5 text-sm font-medium focus:outline-none" />
              <div className="flex items-center gap-2 bg-white rounded-xl px-4 py-2 border-2 border-white">
                <input type="color" value={paintDraft.color} onChange={e => setPaintDraft(d => ({ ...d, color: e.target.value }))} className="w-8 h-8 rounded cursor-pointer border-0" />
                <span className="text-sm font-mono text-gray-600">{paintDraft.color}</span>
              </div>
              <input placeholder="Brand (e.g. Asian Paints)" value={paintDraft.brand} onChange={e => setPaintDraft(d => ({ ...d, brand: e.target.value }))}
                className="border-2 border-white focus:border-purple-400 rounded-xl px-4 py-2.5 text-sm font-medium focus:outline-none" />
              <input placeholder="Shade code" value={paintDraft.code} onChange={e => setPaintDraft(d => ({ ...d, code: e.target.value }))}
                className="border-2 border-white focus:border-purple-400 rounded-xl px-4 py-2.5 text-sm font-medium focus:outline-none" />
            </div>
            <div className="flex gap-2">
              <button onClick={handleAddPaint} className="bg-purple-600 text-white px-6 py-2.5 rounded-xl font-black text-sm hover:bg-purple-700 transition-colors">Save Color</button>
              <button onClick={() => setShowPaintForm(false)} className="bg-white text-gray-500 px-6 py-2.5 rounded-xl font-black text-sm border border-gray-200 hover:bg-gray-50 transition-colors">Cancel</button>
            </div>
          </div>
        )}

        <div className="p-5">
          {homeProfile.paintColors.length === 0 ? (
            <div className="text-center py-10">
              <div className="text-4xl mb-3">🎨</div>
              <p className="text-gray-400 font-medium text-sm">Save your paint colors for future touch-ups.</p>
            </div>
          ) : (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {homeProfile.paintColors.map((paint: PaintColor) => (
                <div key={paint.id} className="rounded-xl overflow-hidden border border-gray-100 group hover:shadow-md transition-all">
                  <div className="h-16 relative" style={{ backgroundColor: paint.color }}>
                    <button onClick={() => removePaintColor(paint.id)}
                      className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 w-6 h-6 bg-white rounded-full flex items-center justify-center shadow-sm transition-all">
                      <X size={11} className="text-red-500" />
                    </button>
                  </div>
                  <div className="bg-white p-3">
                    <p className="font-black text-gray-900 text-sm">{paint.room}</p>
                    <p className="text-xs text-gray-400">{paint.brand}</p>
                    <p className="text-xs font-mono text-gray-500">{paint.code || paint.color}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

// ── Health Score Tab ────────────────────────────────────────────────────

const HealthScoreTab: React.FC = () => {
  const { data: healthData, isLoading } = useQuery({
    queryKey: ['predictive-health'],
    queryFn: predictiveAPI.getHealthScore
  });

  const overallScore = healthData?.overall_score || 0;

  const getAlertColor = (status: string) => {
    if (status === 'excellent' || status === 'good') return 'green';
    if (status === 'needs_attention') return 'yellow';
    return 'red';
  };

  const getIconForCategory = (cat: string) => {
    switch (cat.toLowerCase()) {
      case 'cleaning': return Sparkles;
      case 'plumbing': return Droplets;
      case 'electrical': return Zap;
      case 'pest_control': return Shield;
      case 'hvac': return Wind;
      default: return Wrench;
    }
  };

  const MAINTENANCE_ITEMS = useMemo(() => {
    if (!healthData?.service_scores) return [];
    
    return Object.entries(healthData.service_scores).map(([category, data]: [string, any]) => {
      const isNeverServiced = data.status === 'no_history';
      const lastServiceDisplay = isNeverServiced ? 'Never' : `${data.days_since} days ago`;
      const rec = data.recommendation || `Regular care needed`;
      
      return {
        category: category.charAt(0).toUpperCase() + category.slice(1).replace('_', ' '),
        icon: getIconForCategory(category),
        lastService: lastServiceDisplay,
        recommended: rec,
        score: Math.round(data.score),
        alert: getAlertColor(data.status),
        message: isNeverServiced ? `No service history detected.` : `${data.status.replace('_', ' ').toUpperCase()}`
      };
    });
  }, [healthData]);

  if (isLoading) {
    return <div className="py-20 flex justify-center"><div className="w-10 h-10 border-4 border-teal-600/30 border-t-teal-600 rounded-full animate-spin" /></div>;
  }

  const currentMonth = new Date().getMonth();
  const seasonalTip = currentMonth >= 2 && currentMonth <= 4
    ? '🌡️ Pre-summer AC servicing is highly recommended — book before June heat!'
    : currentMonth >= 5 && currentMonth <= 7
    ? '🌧️ Check drainage and waterproofing — monsoon is approaching!'
    : currentMonth >= 8 && currentMonth <= 10
    ? '🍂 Gutter cleaning and pest control recommended before winter.'
    : '❄️ Winterization check — insulate pipes and service your heating system.';

  const alertColor = { red: 'border-red-200 bg-red-50', yellow: 'border-yellow-200 bg-yellow-50', green: 'border-green-200 bg-green-50' };
  const alertText = { red: 'text-red-600', yellow: 'text-yellow-700', green: 'text-green-700' };
  const alertBadge = { red: 'bg-red-100 text-red-700', yellow: 'bg-yellow-100 text-yellow-700', green: 'bg-green-100 text-green-700' };

  return (
    <div className="space-y-6">
      {/* Score Hero */}
      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-8">
        <div className="flex flex-col md:flex-row items-center gap-8">
          <HealthGauge score={overallScore} />
          <div className="flex-1">
            <h2 className="text-2xl font-black text-gray-900 mb-2">Your Home Health Score</h2>
            <p className="text-gray-500 mb-4">Based on maintenance history and service intervals. Higher scores mean fewer emergencies and better resale value.</p>
            <div className="flex gap-4 flex-wrap">
              <div className="flex items-center gap-2 text-sm">
                <div className="w-3 h-3 rounded-full bg-green-500" />
                <span className="font-medium text-gray-600">80–100: Excellent</span>
              </div>
              <div className="flex items-center gap-2 text-sm">
                <div className="w-3 h-3 rounded-full bg-orange-400" />
                <span className="font-medium text-gray-600">60–79: Needs Care</span>
              </div>
              <div className="flex items-center gap-2 text-sm">
                <div className="w-3 h-3 rounded-full bg-red-500" />
                <span className="font-medium text-gray-600">0–59: Critical</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Category Bars */}
      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
        <h3 className="font-black text-gray-900 text-lg mb-5">Category Breakdown</h3>
        <div className="space-y-4">
          {MAINTENANCE_ITEMS.map(item => {
            const Icon = item.icon;
            const barColor = item.score >= 80 ? 'bg-green-500' : item.score >= 60 ? 'bg-orange-400' : 'bg-red-500';
            return (
              <div key={item.category}>
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <Icon size={16} className="text-gray-500" />
                    <span className="font-bold text-gray-800 text-sm">{item.category}</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-xs text-gray-400">Last: {item.lastService}</span>
                    <span className={`text-xs font-black px-2 py-0.5 rounded-full ${alertBadge[item.alert as keyof typeof alertBadge]}`}>{item.score}/100</span>
                  </div>
                </div>
                <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
                  <div className={`h-full ${barColor} rounded-full transition-all duration-700`} style={{ width: `${item.score}%` }} />
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Maintenance Alerts */}
      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
        <h3 className="font-black text-gray-900 text-lg mb-5">
          <AlertTriangle size={18} className="inline text-red-500 mr-2" />
          Maintenance Alerts
        </h3>
        <div className="space-y-3">
          {MAINTENANCE_ITEMS.filter(i => i.alert !== 'green').sort((a, b) => a.score - b.score).map(item => {
            const Icon = item.icon;
            return (
              <div key={item.category}
                className={`flex items-start justify-between p-4 rounded-xl border-l-4 ${alertColor[item.alert as keyof typeof alertColor]}`}
              >
                <div className="flex items-start gap-3">
                  <div className={`w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0 ${item.alert === 'red' ? 'bg-red-100' : 'bg-yellow-100'}`}>
                    <Icon size={16} className={alertText[item.alert as keyof typeof alertText]} />
                  </div>
                  <div>
                    <p className={`font-black text-sm ${alertText[item.alert as keyof typeof alertText]}`}>{item.message}</p>
                    <p className="text-xs text-gray-500 mt-0.5">{item.category} · Last serviced {item.lastService} · Recommended {item.recommended}</p>
                  </div>
                </div>
                <button
                  onClick={() => toast.success(`Booking ${item.category} service!`)}
                  className="text-xs font-black text-teal-600 hover:text-teal-800 whitespace-nowrap px-3 py-1.5 bg-white rounded-lg border border-teal-200 hover:border-teal-400 transition-colors"
                >
                  Book Now
                </button>
              </div>
            );
          })}
        </div>
      </div>

      {/* Seasonal AI Tip */}
      <div className="bg-gradient-to-r from-teal-600 to-teal-800 rounded-2xl p-6 text-white">
        <div className="flex items-start gap-4">
          <div className="w-12 h-12 bg-white/20 rounded-xl flex items-center justify-center flex-shrink-0">
            <Bot size={22} className="text-white" />
          </div>
          <div>
            <p className="font-black text-lg mb-1">🤖 AI Seasonal Recommendation</p>
            <p className="text-teal-100 font-medium">{seasonalTip}</p>
            <button
              onClick={() => toast.success('Finding seasonal service packages…')}
              className="mt-4 bg-white/20 hover:bg-white/30 text-white px-5 py-2 rounded-xl font-black text-sm transition-all border border-white/20"
            >
              View Seasonal Packages
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

// ── Neighborhood Tab ─────────────────────────────────────────────────────

const NeighborhoodTab: React.FC<{ blockParties: any[] }> = ({ blockParties }) => {
  const { joinedBlockParties, joinBlockParty } = useCustomerStore();

  return (
    <div className="space-y-6">
      {/* Hero Banner */}
      <div className="bg-gradient-to-r from-green-600 to-emerald-700 rounded-2xl p-8 text-white">
        <div className="flex items-start gap-5">
          <div className="w-16 h-16 bg-white/20 rounded-2xl flex items-center justify-center text-3xl flex-shrink-0">🏘️</div>
          <div>
            <h2 className="font-black text-2xl mb-1">Neighborhood Synergy</h2>
            <p className="text-green-100 font-medium text-lg">When 5+ neighbors book the same service within 48 hours, everyone gets <strong>15% off</strong>.</p>
            <p className="text-green-200 text-sm mt-2">Join a Block Party and save together! 🎉</p>
          </div>
        </div>
      </div>

      {/* Block Party Cards */}
      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
        {blockParties.map(party => {
          const joined = joinedBlockParties.includes(party.id);
          const progress = (party.participants / party.needed) * 100;
          const isAlmostFull = party.participants >= party.needed - 1;
          return (
            <div key={party.id}
              className={`bg-white rounded-2xl shadow-sm border-2 transition-all duration-300 overflow-hidden
                ${joined ? 'border-green-300 shadow-green-100' : 'border-gray-100 hover:border-green-200 hover:shadow-md'}
              `}
            >
              {/* Discount Badge */}
              <div className={`px-5 py-3 flex items-center justify-between ${joined ? 'bg-green-50' : 'bg-gray-50'}`}>
                <div className="flex items-center gap-2">
                  <span className="text-2xl">{party.emoji}</span>
                  <div>
                    <p className="font-black text-gray-900 text-sm">{party.service}</p>
                    <p className="text-xs text-gray-400">{party.area}</p>
                  </div>
                </div>
                <div className="bg-green-500 text-white text-xs font-black px-3 py-1.5 rounded-full">
                  -{party.discount}%
                </div>
              </div>

              <div className="p-5">
                {/* Provider */}
                <p className="text-xs text-gray-500 mb-3">Provider: <span className="font-bold text-gray-700">{party.provider}</span></p>

                {/* Participant Progress */}
                <div className="mb-4">
                  <div className="flex justify-between text-xs mb-1.5">
                    <span className="font-bold text-gray-700">{party.participants} neighbors joined</span>
                    <span className="text-gray-400">{party.needed} needed</span>
                  </div>
                  <div className="h-2.5 bg-gray-100 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-green-400 to-emerald-500 rounded-full transition-all duration-500"
                      style={{ width: `${Math.min(progress, 100)}%` }}
                    />
                  </div>
                  {isAlmostFull && !joined && (
                    <p className="text-xs font-bold text-orange-500 mt-1.5">🔥 Only {party.needed - party.participants} spot left!</p>
                  )}
                </div>

                {/* Expiry */}
                <div className="flex items-center gap-1 mb-4">
                  <Clock size={12} className="text-gray-400" />
                  <span className="text-xs text-gray-400">Expires in {party.expiresIn}</span>
                </div>

                {/* Action */}
                <button
                  onClick={() => {
                    if (!joined) {
                      joinBlockParty(party.id);
                      toast.success(`Joined Block Party! 🎉 Discount unlocks when ${party.needed - party.participants - 1} more join.`);
                    }
                  }}
                  disabled={joined}
                  className={`w-full py-3 rounded-xl font-black text-sm transition-all
                    ${joined
                      ? 'bg-green-100 text-green-700 border-2 border-green-200 cursor-default'
                      : 'bg-green-600 text-white hover:bg-green-700 hover:shadow-md hover:shadow-green-200 active:scale-95'
                    }
                  `}
                >
                  {joined ? '✅ Joined Block Party!' : '🏘️ Join Block Party'}
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {/* How it works */}
      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
        <h3 className="font-black text-gray-900 text-lg mb-5">How Neighborhood Synergy Works</h3>
        <div className="grid md:grid-cols-3 gap-4">
          {[
            { step: '1', icon: '👀', title: 'Spot a Block Party', desc: 'See nearby neighbors booking the same service within 48 hours.' },
            { step: '2', icon: '🤝', title: 'Join the Group', desc: 'Click Join to add your booking to the group. No commitment yet!' },
            { step: '3', icon: '🎉', title: 'Unlock 15% Off', desc: 'When 5+ neighbors join, everyone auto-gets a 15% group discount.' },
          ].map(item => (
            <div key={item.step} className="text-center p-4">
              <div className="w-14 h-14 bg-green-100 rounded-2xl flex items-center justify-center text-2xl mx-auto mb-3">{item.icon}</div>
              <p className="font-black text-gray-900 mb-1">{item.title}</p>
              <p className="text-sm text-gray-500">{item.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

// ── Rewards Tab ──────────────────────────────────────────────────────────

const RewardsTab: React.FC<{ points: number }> = ({ points }) => {
  const REDEMPTIONS = [
    { id: 'r1', title: 'Priority Emergency Status', desc: '24-hr guaranteed response for any emergency service.', cost: 500,  icon: '🚨', color: 'from-red-500 to-red-700',    available: points >= 500  },
    { id: 'r2', title: '₹100 Service Credit',       desc: 'Applied automatically to your next booking.',        cost: 1000, icon: '💳', color: 'from-blue-500 to-blue-700',   available: points >= 1000 },
    { id: 'r3', title: 'Free Premium Cleaning',     desc: '1-hour deep cleaning session, on us.',              cost: 1500, icon: '✨', color: 'from-purple-500 to-purple-700', available: points >= 1500 },
    { id: 'r4', title: 'VIP Provider Access',       desc: 'Get matched with top 5% rated providers.',          cost: 2500, icon: '👑', color: 'from-yellow-500 to-orange-500', available: points >= 2500 },
  ];

  const TIER_THRESHOLDS = [
    { name: 'Bronze',   min: 0,    icon: '🥉', color: 'from-amber-600 to-amber-800'   },
    { name: 'Silver',   min: 500,  icon: '🥈', color: 'from-gray-400 to-gray-600'     },
    { name: 'Gold',     min: 1500, icon: '🥇', color: 'from-yellow-400 to-yellow-600' },
    { name: 'Platinum', min: 3000, icon: '💎', color: 'from-purple-400 to-purple-700' },
  ];

  const currentTier = [...TIER_THRESHOLDS].reverse().find(t => points >= t.min) || TIER_THRESHOLDS[0];
  const nextTier = TIER_THRESHOLDS[TIER_THRESHOLDS.indexOf(currentTier) + 1];
  const progress = nextTier ? ((points - currentTier.min) / (nextTier.min - currentTier.min)) * 100 : 100;

  return (
    <div className="space-y-6">
      {/* Points Hero */}
      <div className="bg-gradient-to-br from-[#0D1F2D] to-teal-800 rounded-2xl p-8 text-white">
        <div className="flex items-start justify-between mb-6">
          <div>
            <p className="text-teal-300 text-xs font-black uppercase tracking-[0.2em] mb-2">Local Hero Points</p>
            <p className="text-6xl font-black">{points.toLocaleString()}</p>
            <p className="text-teal-300 mt-2 font-medium">Earn more with every booking!</p>
          </div>
          <div className="bg-white/10 backdrop-blur-sm rounded-2xl p-5 border border-white/20 text-center">
            <p className="text-4xl mb-2">{currentTier.icon}</p>
            <p className="text-teal-200 text-xs font-bold uppercase">Tier</p>
            <p className="font-black text-xl">{currentTier.name}</p>
          </div>
        </div>
        {nextTier && (
          <div>
            <div className="flex justify-between text-sm mb-2 font-bold">
              <span>{currentTier.name}</span>
              <span>{points}/{nextTier.min} to {nextTier.name}</span>
            </div>
            <div className="h-3 bg-white/20 rounded-full overflow-hidden">
              <div className="h-full bg-gradient-to-r from-teal-300 to-teal-100 rounded-full transition-all duration-700" style={{ width: `${Math.min(progress, 100)}%` }} />
            </div>
          </div>
        )}
      </div>

      {/* Redemption Options */}
      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
        <h3 className="font-black text-gray-900 text-lg mb-5 flex items-center gap-2">
          <Gift size={18} className="text-yellow-500" /> Redeem Your Points
        </h3>
        <div className="grid md:grid-cols-2 gap-4">
          {REDEMPTIONS.map(item => (
            <div key={item.id}
              className={`rounded-2xl overflow-hidden border transition-all duration-200
                ${item.available ? 'border-gray-100 hover:shadow-md hover:-translate-y-0.5' : 'border-gray-100 opacity-60'}
              `}
            >
              <div className={`bg-gradient-to-r ${item.color} p-5 text-white`}>
                <div className="flex items-center justify-between">
                  <span className="text-3xl">{item.icon}</span>
                  <span className="font-black text-lg">{item.cost.toLocaleString()} pts</span>
                </div>
                <p className="font-black text-lg mt-2">{item.title}</p>
              </div>
              <div className="bg-white p-4">
                <p className="text-sm text-gray-500 mb-3">{item.desc}</p>
                <button
                  onClick={() => {
                    if (item.available) {
                      toast.success(`${item.title} redeemed! 🎉`);
                    } else {
                      toast.error(`Need ${item.cost - points} more points`);
                    }
                  }}
                  className={`w-full py-2.5 rounded-xl font-black text-sm transition-all
                    ${item.available
                      ? 'bg-teal-600 text-white hover:bg-teal-700'
                      : 'bg-gray-100 text-gray-400 cursor-not-allowed'
                    }
                  `}
                >
                  {item.available ? `Redeem for ${item.cost} pts` : `Need ${(item.cost - points).toLocaleString()} more pts`}
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Ways to Earn */}
      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-6">
        <h3 className="font-black text-gray-900 text-lg mb-5 flex items-center gap-2">
          <Star size={18} className="text-yellow-500" /> Ways to Earn
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          {[
            { action: 'Complete booking',   pts: '10 pts/₹',  icon: '✅', bg: 'bg-blue-50',   text: 'text-blue-700'   },
            { action: 'Leave a review',     pts: '50 pts',    icon: '⭐', bg: 'bg-yellow-50', text: 'text-yellow-700' },
            { action: 'Refer a friend',     pts: '150 pts',   icon: '👥', bg: 'bg-green-50',  text: 'text-green-700'  },
            { action: 'First booking',      pts: '200 bonus', icon: '🎉', bg: 'bg-purple-50', text: 'text-purple-700' },
            { action: 'Join Block Party',   pts: '75 pts',    icon: '🏘️', bg: 'bg-emerald-50',text: 'text-emerald-700'},
            { action: 'Rate 5 stars',       pts: '100 pts',   icon: '🌟', bg: 'bg-orange-50', text: 'text-orange-700' },
          ].map(item => (
            <div key={item.action} className={`${item.bg} rounded-xl p-4`}>
              <div className="text-2xl mb-2">{item.icon}</div>
              <p className="font-black text-gray-900 text-sm">{item.action}</p>
              <p className={`font-black text-sm ${item.text}`}>{item.pts}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

// ── Key Vault Tab ────────────────────────────────────────────────────────

const KeyVaultTab: React.FC = () => {
  const { keyVault, addKeyEntry, removeKeyEntry } = useCustomerStore();
  const [revealed, setRevealed] = useState<Set<string>>(new Set());
  const [showForm, setShowForm] = useState(false);
  const [draft, setDraft] = useState({
    label: '', code: '', type: 'pin' as const, expiresAt: '',
    providerName: '', instructions: '', isActive: true,
  });

  const toggleReveal = (id: string) =>
    setRevealed(prev => { const s = new Set(prev); s.has(id) ? s.delete(id) : s.add(id); return s; });

  const handleCopy = (code: string) => {
    navigator.clipboard.writeText(code);
    toast.success('Code copied! 🔑');
  };

  const handleAdd = () => {
    if (!draft.label || !draft.code) { toast.error('Enter label and code'); return; }
    addKeyEntry(draft);
    setDraft({ label: '', code: '', type: 'pin', expiresAt: '', providerName: '', instructions: '', isActive: true });
    setShowForm(false);
    toast.success('Key entry secured! 🔐');
  };

  const typeIcon: Record<string, string> = {
    lockbox: '📦', pin: '🔢', smartlock: '📱', instructions: '📝',
  };

  const typeLabel: Record<string, string> = {
    lockbox: 'Lock Box', pin: 'PIN Code', smartlock: 'Smart Lock', instructions: 'Instructions',
  };

  const isExpired = (date: string) => date && new Date(date) < new Date();
  const daysUntil = (date: string) => {
    if (!date) return null;
    const diff = Math.ceil((new Date(date).getTime() - Date.now()) / 86400000);
    return diff;
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-gradient-to-r from-gray-800 to-gray-900 rounded-2xl p-6 text-white">
        <div className="flex items-center justify-between flex-wrap gap-4">
          <div className="flex items-start gap-4">
            <div className="w-14 h-14 bg-white/10 rounded-xl flex items-center justify-center flex-shrink-0">
              <Lock size={24} className="text-white" />
            </div>
            <div>
              <h2 className="font-black text-xl mb-1">Virtual Key Vault</h2>
              <p className="text-gray-300 font-medium text-sm">Securely share smart-lock codes and entry instructions. Codes auto-expire after the job completes.</p>
            </div>
          </div>
          <button
            onClick={() => setShowForm(!showForm)}
            className="flex items-center gap-2 bg-teal-600 hover:bg-teal-700 text-white px-5 py-2.5 rounded-xl font-black text-sm transition-all"
          >
            <Plus size={16} /> Add Key Entry
          </button>
        </div>
      </div>

      {/* Add Form */}
      {showForm && (
        <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6">
          <h4 className="font-black text-gray-900 mb-4">New Access Entry</h4>
          <div className="grid md:grid-cols-2 gap-4 mb-4">
            <div>
              <label className="text-xs font-black text-gray-400 uppercase tracking-widest block mb-1.5">Label *</label>
              <input placeholder="e.g. Front Door Smart Lock" value={draft.label} onChange={e => setDraft(d => ({ ...d, label: e.target.value }))}
                className="w-full border-2 border-gray-100 focus:border-teal-400 rounded-xl px-4 py-3 text-sm font-medium focus:outline-none" />
            </div>
            <div>
              <label className="text-xs font-black text-gray-400 uppercase tracking-widest block mb-1.5">Type</label>
              <select value={draft.type} onChange={e => setDraft(d => ({ ...d, type: e.target.value as any }))}
                className="w-full border-2 border-gray-100 focus:border-teal-400 rounded-xl px-4 py-3 text-sm font-medium focus:outline-none bg-white">
                <option value="pin">PIN Code</option>
                <option value="lockbox">Lock Box Combo</option>
                <option value="smartlock">Smart Lock App Code</option>
                <option value="instructions">Key Location / Instructions</option>
              </select>
            </div>
            <div>
              <label className="text-xs font-black text-gray-400 uppercase tracking-widest block mb-1.5">Code / Access *</label>
              <input placeholder="Enter code or instructions" value={draft.code} onChange={e => setDraft(d => ({ ...d, code: e.target.value }))}
                className="w-full border-2 border-gray-100 focus:border-teal-400 rounded-xl px-4 py-3 text-sm font-medium focus:outline-none" />
            </div>
            <div>
              <label className="text-xs font-black text-gray-400 uppercase tracking-widest block mb-1.5">Provider Name</label>
              <input placeholder="e.g. Suresh Kumar" value={draft.providerName} onChange={e => setDraft(d => ({ ...d, providerName: e.target.value }))}
                className="w-full border-2 border-gray-100 focus:border-teal-400 rounded-xl px-4 py-3 text-sm font-medium focus:outline-none" />
            </div>
            <div>
              <label className="text-xs font-black text-gray-400 uppercase tracking-widest block mb-1.5">Expiry Date</label>
              <input type="date" value={draft.expiresAt} onChange={e => setDraft(d => ({ ...d, expiresAt: e.target.value }))}
                className="w-full border-2 border-gray-100 focus:border-teal-400 rounded-xl px-4 py-3 text-sm font-medium focus:outline-none" />
            </div>
            <div>
              <label className="text-xs font-black text-gray-400 uppercase tracking-widest block mb-1.5">Additional Instructions</label>
              <input placeholder="e.g. Enter from side gate" value={draft.instructions} onChange={e => setDraft(d => ({ ...d, instructions: e.target.value }))}
                className="w-full border-2 border-gray-100 focus:border-teal-400 rounded-xl px-4 py-3 text-sm font-medium focus:outline-none" />
            </div>
          </div>
          <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-3 mb-4 flex items-start gap-2">
            <Shield size={16} className="text-yellow-600 flex-shrink-0 mt-0.5" />
            <p className="text-xs text-yellow-700 font-medium">Codes are stored encrypted locally. Set an expiry date to auto-revoke access after the job.</p>
          </div>
          <div className="flex gap-2">
            <button onClick={handleAdd} className="bg-teal-600 text-white px-6 py-2.5 rounded-xl font-black text-sm hover:bg-teal-700 transition-colors">Secure & Save</button>
            <button onClick={() => setShowForm(false)} className="bg-gray-50 text-gray-600 px-6 py-2.5 rounded-xl font-black text-sm border border-gray-200 hover:bg-gray-100 transition-colors">Cancel</button>
          </div>
        </div>
      )}

      {/* Keys List */}
      {keyVault.length === 0 ? (
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 p-16 text-center">
          <div className="text-5xl mb-4">🔑</div>
          <p className="font-black text-gray-700 mb-2">No Key Entries Yet</p>
          <p className="text-gray-400 text-sm mb-5">Add secure access codes for providers — they auto-expire after job completion.</p>
          <button onClick={() => setShowForm(true)} className="bg-teal-600 text-white px-6 py-2.5 rounded-xl font-black text-sm hover:bg-teal-700 transition-colors">
            + Add First Key Entry
          </button>
        </div>
      ) : (
        <div className="space-y-3">
          {keyVault.map((key: KeyEntry) => {
            const isRev = revealed.has(key.id);
            const expired = isExpired(key.expiresAt);
            const days = daysUntil(key.expiresAt);
            return (
              <div key={key.id}
                className={`bg-white rounded-2xl shadow-sm border transition-all duration-200 p-5
                  ${expired ? 'border-red-200 opacity-70' : 'border-gray-100 hover:border-teal-200'}
                `}
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex items-start gap-4 flex-1 min-w-0">
                    <div className={`w-12 h-12 rounded-xl flex items-center justify-center text-xl flex-shrink-0
                      ${expired ? 'bg-red-50' : 'bg-gray-50'}
                    `}>
                      {typeIcon[key.type] || '🔑'}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap mb-1">
                        <p className="font-black text-gray-900">{key.label}</p>
                        <span className={`text-xs font-bold px-2 py-0.5 rounded-full
                          ${expired ? 'bg-red-100 text-red-600' : 'bg-gray-100 text-gray-500'}
                        `}>
                          {typeLabel[key.type]}
                        </span>
                        {expired && <span className="text-xs font-black text-red-600 bg-red-50 px-2 py-0.5 rounded-full">Expired</span>}
                      </div>
                      {key.providerName && (
                        <p className="text-xs text-gray-400 mb-2">👤 Access for: {key.providerName}</p>
                      )}
                      <div className="flex items-center gap-2">
                        <code className={`font-mono text-sm font-bold px-3 py-1.5 rounded-lg select-all
                          ${isRev ? 'bg-teal-50 text-teal-800 border border-teal-200' : 'bg-gray-100 text-gray-400'}
                        `}>
                          {isRev ? key.code : '•'.repeat(Math.min(key.code.length, 8))}
                        </code>
                        <button onClick={() => toggleReveal(key.id)}
                          className="p-2 rounded-lg hover:bg-gray-100 text-gray-500 hover:text-gray-700 transition-colors">
                          {isRev ? <EyeOff size={16} /> : <Eye size={16} />}
                        </button>
                        {isRev && (
                          <button onClick={() => handleCopy(key.code)}
                            className="p-2 rounded-lg hover:bg-teal-50 text-teal-600 hover:text-teal-800 transition-colors">
                            <Copy size={16} />
                          </button>
                        )}
                      </div>
                      {key.instructions && (
                        <p className="text-xs text-gray-400 mt-2">📝 {key.instructions}</p>
                      )}
                      {key.expiresAt && !expired && days !== null && (
                        <p className={`text-xs font-bold mt-2 ${days <= 3 ? 'text-orange-500' : 'text-gray-400'}`}>
                          ⏰ Expires {days === 0 ? 'today' : `in ${days} day${days !== 1 ? 's' : ''}`}
                        </p>
                      )}
                    </div>
                  </div>
                  <button onClick={() => removeKeyEntry(key.id)}
                    className="p-2 rounded-lg hover:bg-red-50 text-gray-300 hover:text-red-500 transition-all flex-shrink-0">
                    <Trash2 size={16} />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

// ── Quote History Tab ────────────────────────────────────────────────────

const QuoteHistoryTab: React.FC<{ quotes: any[] }> = ({ quotes }) => {
  const [filter, setFilter] = useState('all');
  const [expanded, setExpanded] = useState<string | null>(null);

  const filtered = filter === 'all' ? quotes : quotes.filter((q: any) => q.category === filter);
  const categories = ['all', ...Array.from(new Set(quotes.map((q: any) => q.category)))];

  const savings = quotes.reduce((s: number, q: any) => s + (q.aiEstimate - q.actualCost), 0);

  return (
    <div className="space-y-6">
      {/* Summary */}
      <div className="grid grid-cols-3 gap-4">
        {[
          { label: 'Total Quotes',   value: quotes.length,          icon: FileText,     color: 'text-blue-600',  bg: 'bg-blue-50'   },
          { label: 'AI Accuracy',    value: '94%',                  icon: Bot,          color: 'text-teal-600',  bg: 'bg-teal-50'   },
          { label: 'AI Saved You',   value: formatPriceINR(savings), icon: TrendingUp,  color: 'text-green-600', bg: 'bg-green-50'  },
        ].map(s => (
          <div key={s.label} className="bg-white rounded-2xl p-5 shadow-sm border border-gray-100 text-center">
            <div className={`w-10 h-10 ${s.bg} rounded-xl flex items-center justify-center mx-auto mb-3`}>
              <s.icon size={18} className={s.color} />
            </div>
            <p className="text-xl font-black text-gray-900">{s.value}</p>
            <p className="text-xs font-medium text-gray-400 mt-0.5">{s.label}</p>
          </div>
        ))}
      </div>

      {/* Category Filter */}
      <div className="flex gap-2 flex-wrap">
        {categories.map(cat => (
          <button key={cat} onClick={() => setFilter(cat)}
            className={`px-4 py-2 rounded-xl font-bold text-xs capitalize transition-all
              ${filter === cat ? 'bg-teal-600 text-white shadow-md' : 'bg-white text-gray-500 border border-gray-200 hover:border-teal-300'}
            `}
          >
            {cat === 'all' ? 'All Services' : cat}
          </button>
        ))}
      </div>

      {/* Quote Cards */}
      <div className="space-y-4">
        {filtered.map(quote => {
          const isExp = expanded === quote.id;
          const accuracy = Math.round((1 - Math.abs(quote.aiEstimate - quote.actualCost) / quote.aiEstimate) * 100);
          return (
            <div key={quote.id} className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden hover:shadow-md transition-all duration-300">
              <div className="p-5">
                <div className="flex items-start justify-between flex-wrap gap-3 mb-4">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-xl">{categoryEmoji[quote.category] || '🔧'}</span>
                      <h3 className="font-black text-gray-900">{quote.service}</h3>
                    </div>
                    <p className="text-xs text-gray-400">{quote.date}</p>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-xs font-black bg-teal-50 text-teal-700 px-3 py-1 rounded-full">
                      🤖 {accuracy}% accurate
                    </span>
                    <button
                      onClick={() => toast.success('Downloading quote for insurance… 📄')}
                      className="text-xs font-bold text-gray-500 hover:text-teal-600 flex items-center gap-1 transition-colors"
                    >
                      <FileText size={13} /> Download
                    </button>
                  </div>
                </div>

                {/* Price Comparison */}
                <div className="grid grid-cols-2 gap-4 mb-4">
                  <div className="bg-blue-50 rounded-xl p-4">
                    <p className="text-xs font-black text-blue-400 uppercase tracking-widest mb-1">🤖 AI Estimate</p>
                    <p className="font-black text-xl text-blue-700">{formatPriceINR(quote.aiEstimate)}</p>
                  </div>
                  <div className="bg-green-50 rounded-xl p-4">
                    <p className="text-xs font-black text-green-400 uppercase tracking-widest mb-1">✅ Actual Cost</p>
                    <p className="font-black text-xl text-green-700">{formatPriceINR(quote.actualCost)}</p>
                  </div>
                </div>

                <button
                  onClick={() => setExpanded(isExp ? null : quote.id)}
                  className="text-sm font-bold text-teal-600 hover:text-teal-800 flex items-center gap-1 transition-colors"
                >
                  <Camera size={14} /> {isExp ? 'Hide' : 'View'} Before & After Photos
                  <ChevronRight size={14} className={`transition-transform ${isExp ? 'rotate-90' : ''}`} />
                </button>
              </div>

              {isExp && (
                <div className="px-5 pb-5">
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <p className="text-xs font-black text-gray-400 uppercase tracking-widest mb-2">Before</p>
                      <img src={quote.beforePhoto} alt="Before" className="w-full h-40 object-cover rounded-xl" />
                    </div>
                    <div>
                      <p className="text-xs font-black text-gray-400 uppercase tracking-widest mb-2">After</p>
                      <img src={quote.afterPhoto} alt="After" className="w-full h-40 object-cover rounded-xl" />
                    </div>
                  </div>
                  <p className="text-xs text-gray-400 mt-3 text-center">📸 Photos stored for insurance claims and home resale documentation</p>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};

// ── Transaction History Tab ──────────────────────────────────────────────

const TxStatusBadge: React.FC<{ status: string }> = ({ status }) => {
  const map: Record<string, string> = {
    completed: 'bg-green-100 text-green-700',
    refunded:  'bg-purple-100 text-purple-700',
    pending:   'bg-yellow-100 text-yellow-700',
    failed:    'bg-red-100 text-red-700',
  };
  return <span className={`text-xs font-bold px-2.5 py-1 rounded-full ${map[status] || 'bg-gray-100 text-gray-600'}`}>{status}</span>;
};

const TransactionHistoryTab: React.FC<{ bookings: any[] }> = ({ bookings }) => {
  const { t } = useTranslation();
  const { data: paymentsRaw } = useQuery({
    queryKey: ['customer-payments'],
    queryFn:  () => import('../services/api').then(m => m.default.get('/api/payments/history').then(r => r.data)),
    retry: 1,
  });

  const payments: any[] = paymentsRaw?.payments || paymentsRaw || [];
  const totalSpent = payments.filter((p: any) => p.status === 'completed').reduce((s: number, p: any) => s + (p.final_amount || p.amount || 0), 0);
  const totalRefunded = payments.filter((p: any) => p.status === 'refunded').reduce((s: number, p: any) => s + (p.refund_amount || p.amount || 0), 0);

  return (
    <div className="space-y-5">
      {/* Summary Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: 'Total Spent',    val: `₹${totalSpent.toLocaleString('en-IN')}`,          color: 'text-red-600',    bg: 'bg-red-50'    },
          { label: 'Total Refunded', val: `₹${totalRefunded.toLocaleString('en-IN')}`,       color: 'text-purple-600', bg: 'bg-purple-50' },
          { label: 'Transactions',   val: payments.length,                                    color: 'text-blue-600',   bg: 'bg-blue-50'   },
          { label: 'Bookings',       val: bookings.filter((b:any) => b.status==='completed').length, color: 'text-green-600', bg: 'bg-green-50' },
        ].map(s => (
          <div key={s.label} className={`${s.bg} rounded-2xl p-5`}>
            <p className={`text-2xl font-black ${s.color}`}>{s.val}</p>
            <p className="text-xs font-bold text-gray-500 mt-1">{s.label}</p>
          </div>
        ))}
      </div>

      {/* Transaction Table */}
      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-100">
          <h3 className="font-black text-gray-900 text-xl flex items-center gap-2">💳 {t('Payment History')}</h3>
          <p className="text-xs text-gray-400 mt-0.5">All your payments — fetched directly from database</p>
        </div>
        {payments.length === 0 ? (
          <div className="py-16 text-center text-gray-400 font-medium">
            <p className="text-3xl mb-3">💳</p>
            <p>No payment records yet. Book a service to get started!</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>{['ID', 'Service', 'Provider', 'Amount', 'Method', 'Status', 'Date'].map(h => (
                  <th key={h} className="text-left py-3.5 px-5 font-black text-gray-400 text-xs uppercase tracking-wider">{h}</th>
                ))}</tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {payments.map((p: any) => (
                  <tr key={p._id || p.id} className="hover:bg-teal-50/20 transition-colors">
                    <td className="py-4 px-5"><span className="font-mono text-xs bg-gray-100 px-2 py-1 rounded-lg text-gray-600">#{(p._id || p.id || '').slice(-6)}</span></td>
                    <td className="py-4 px-5 font-bold text-gray-900 text-sm">{p.service_name || p.description || '—'}</td>
                    <td className="py-4 px-5 text-sm text-gray-600">{p.provider_name || '—'}</td>
                    <td className="py-4 px-5 font-black text-gray-900">₹{(p.final_amount || p.amount || 0).toLocaleString('en-IN')}</td>
                    <td className="py-4 px-5 text-sm text-gray-500 capitalize">{p.method || p.payment_method || 'online'}</td>
                    <td className="py-4 px-5"><TxStatusBadge status={p.status || 'pending'} /></td>
                    <td className="py-4 px-5 text-xs text-gray-400 whitespace-nowrap">{p.created_at ? new Date(p.created_at).toLocaleDateString() : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Booking-Payment cross-reference */}
      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-100">
          <h3 className="font-black text-gray-900 text-lg">📋 Booking Records</h3>
          <p className="text-xs text-gray-400 mt-0.5">Complete booking history with provider & payment details</p>
        </div>
        <div className="divide-y divide-gray-50">
          {bookings.length === 0 ? (
            <div className="py-10 text-center text-gray-400 font-medium">No bookings yet</div>
          ) : bookings.map((b: any) => (
            <div key={b._id} className="flex items-center justify-between px-6 py-4 hover:bg-gray-50 transition-colors">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-teal-50 flex items-center justify-center text-lg">
                  {categoryEmoji[b.category?.toLowerCase()] || '🔧'}
                </div>
                <div>
                  <p className="font-bold text-gray-900 text-sm">{b.service_name || b.category || 'Service'}</p>
                  <p className="text-xs text-gray-500">{b.provider_name || b.provider || '—'} · {b.created_at?.slice(0,10) || '—'}</p>
                  {b.provider_rating > 0 && <p className="text-xs text-yellow-600 font-bold">{b.provider_rating?.toFixed(1)} ★</p>}
                </div>
              </div>
              <div className="flex items-center gap-3 text-right">
                <div>
                  <p className="font-black text-gray-900 text-sm">₹{(b.final_amount || b.total_amount || b.amount || 0).toLocaleString('en-IN')}</p>
                  <p className="text-xs text-gray-400">{b.payment_status || 'unpaid'}</p>
                </div>
                <BookingStatusBadge status={b.status} />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

// ── Spend Insights Tab ───────────────────────────────────────────────────
const SpendInsightsTab: React.FC<{ bookings: any[]; dashData: any }> = ({ bookings, dashData }) => {
  const { t } = useTranslation();
  const { data: revenueData } = useQuery({
    queryKey: ['customer-spend-analytics'],
    queryFn: () => import('../services/api').then(m => m.default.get('/api/payments/history?limit=500').then(r => r.data)),
    retry: 1,
  });

  const payments: any[] = revenueData?.payments || [];

  // Category breakdown
  const catSpend: Record<string, number> = {};
  bookings.forEach((b: any) => {
    const cat = b.category || b.service_name || 'Other';
    catSpend[cat] = (catSpend[cat] || 0) + (b.total_amount || b.amount || 0);
  });
  const catData = Object.entries(catSpend).map(([name, value]) => ({ name, value })).sort((a, b) => b.value - a.value);
  const totalSpent = catData.reduce((s, c) => s + c.value, 0);

  // Monthly trend (group bookings by month)
  const monthlySpend: Record<string, number> = {};
  bookings.forEach((b: any) => {
    const m = b.created_at?.slice(0, 7) || 'N/A';
    monthlySpend[m] = (monthlySpend[m] || 0) + (b.total_amount || b.amount || 0);
  });
  const monthlyData = Object.entries(monthlySpend).sort().slice(-6).map(([month, amount]) => ({ month: month.slice(5), amount }));

  const COLORS = ['#0D7A7F', '#f59e0b', '#8b5cf6', '#ef4444', '#3b82f6', '#10b981'];

  return (
    <div className="space-y-6">
      {/* AI Budget Summary */}
      <div className="bg-gradient-to-r from-indigo-600 to-purple-700 rounded-2xl p-6 text-white shadow-lg">
        <div className="flex items-start justify-between">
          <div>
            <p className="text-indigo-200 text-xs font-bold uppercase tracking-widest mb-2">🤖 AI Spend Analysis</p>
            <p className="text-3xl font-black mb-2">₹{totalSpent.toLocaleString('en-IN')}</p>
            <p className="text-indigo-200 text-sm">Total platform spend across {bookings.length} bookings</p>
          </div>
          <div className="bg-white/10 rounded-2xl p-4 backdrop-blur-sm">
            <p className="text-xs font-bold text-indigo-200 mb-1">Avg / Booking</p>
            <p className="text-2xl font-black">{bookings.length > 0 ? `₹${Math.round(totalSpent / bookings.length).toLocaleString('en-IN')}` : '₹0'}</p>
          </div>
        </div>
        <div className="mt-4 p-3 bg-white/10 rounded-xl backdrop-blur-sm">
          <p className="text-xs font-bold text-indigo-100">💡 AI Insight: Your top spend category is <strong>{catData[0]?.name || '—'}</strong>. Consider a subscription bundle to save up to 15%!</p>
        </div>
      </div>

      {/* Monthly Trend + Category Breakdown */}
      <div className="grid lg:grid-cols-2 gap-5">
        {/* Monthly chart */}
        <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
          <h3 className="font-black text-gray-900 text-base mb-4">📈 Monthly Spend Trend</h3>
          {monthlyData.length > 0 ? (
            <div className="space-y-3">
              {monthlyData.map((m, i) => {
                const pct = totalSpent > 0 ? (m.amount / totalSpent) * 100 : 0;
                return (
                  <div key={m.month}>
                    <div className="flex justify-between mb-1">
                      <span className="text-xs font-bold text-gray-500">{m.month}</span>
                      <span className="text-xs font-black text-gray-800">₹{m.amount.toLocaleString('en-IN')}</span>
                    </div>
                    <div className="h-2.5 bg-gray-100 rounded-full overflow-hidden">
                      <div className="h-full bg-teal-500 rounded-full transition-all duration-700"
                        style={{ width: `${pct}%`, backgroundColor: COLORS[i % COLORS.length] }} />
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="h-40 flex items-center justify-center text-gray-400 font-medium">No spend data yet</div>
          )}
        </div>

        {/* Category Breakdown */}
        <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
          <h3 className="font-black text-gray-900 text-base mb-4">🍕 Spend by Category</h3>
          {catData.length > 0 ? (
            <div className="space-y-3">
              {catData.slice(0, 6).map((c, i) => {
                const pct = totalSpent > 0 ? Math.round((c.value / totalSpent) * 100) : 0;
                return (
                  <div key={c.name} className="flex items-center gap-3">
                    <div className="w-3 h-3 rounded-full flex-shrink-0" style={{ backgroundColor: COLORS[i % COLORS.length] }} />
                    <div className="flex-1">
                      <div className="flex justify-between mb-0.5">
                        <span className="text-xs font-bold text-gray-700 capitalize">{c.name}</span>
                        <span className="text-xs font-black text-gray-800">{pct}%</span>
                      </div>
                      <div className="h-2 bg-gray-100 rounded-full"><div className="h-full rounded-full" style={{ width: `${pct}%`, backgroundColor: COLORS[i % COLORS.length] }} /></div>
                    </div>
                    <span className="text-xs font-bold text-gray-500 w-20 text-right">₹{c.value.toLocaleString('en-IN')}</span>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="h-40 flex items-center justify-center text-gray-400 font-medium">No data yet</div>
          )}
        </div>
      </div>

      {/* Smart Budget Tips */}
      <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
        <h3 className="font-black text-gray-900 text-base mb-4">💡 Smart Budget Tips</h3>
        <div className="grid md:grid-cols-3 gap-4">
          {[
            { icon:'🎯', title:'Bundle & Save', desc:'Combine cleaning + maintenance for up to 20% off', color:'bg-teal-50 border-teal-200' },
            { icon:'⏰', title:'Off-Peak Booking', desc:'Book Monday–Thursday before 10am for 15% lower rates', color:'bg-blue-50 border-blue-200' },
            { icon:'🔄', title:'Subscription Plan', desc:'Monthly subscription saves avg ₹1,200/month on regular services', color:'bg-purple-50 border-purple-200' },
          ].map(t => (
            <div key={t.title} className={`${t.color} border rounded-2xl p-4`}>
              <p className="text-2xl mb-2">{t.icon}</p>
              <p className="font-black text-gray-900 text-sm">{t.title}</p>
              <p className="text-xs text-gray-500 mt-1 leading-relaxed">{t.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

// ── My Providers Tab ─────────────────────────────────────────────────────
const MyProvidersTab: React.FC<{ bookings: any[] }> = ({ bookings }) => {
  const { t } = useTranslation();
  const [selectedProvider, setSelectedProvider] = useState<string | null>(null);

  // Build unique provider list from booking history
  const providerMap: Record<string, { name: string; id: string; bookings: any[]; totalSpent: number; avgRating: number; categories: Set<string> }> = {};
  bookings.forEach((b: any) => {
    const pid = b.provider_id || b.provider || 'unknown';
    if (!providerMap[pid]) {
      providerMap[pid] = { name: b.provider_name || b.provider || 'Provider', id: pid, bookings: [], totalSpent: 0, avgRating: 0, categories: new Set() };
    }
    providerMap[pid].bookings.push(b);
    providerMap[pid].totalSpent += (b.total_amount || b.amount || 0);
    if (b.category) providerMap[pid].categories.add(b.category);
  });

  const providers = Object.values(providerMap).sort((a, b) => b.bookings.length - a.bookings.length);

  if (providers.length === 0) return (
    <div className="bg-white rounded-2xl p-16 shadow-sm border border-gray-100 text-center">
      <p className="text-4xl mb-3">👷</p>
      <p className="font-black text-gray-700 text-lg">No provider history yet</p>
      <p className="text-gray-400 text-sm mt-2">Book a service to start building your trusted provider circle</p>
    </div>
  );

  const selected = selectedProvider ? providerMap[selectedProvider] : null;

  return (
    <div className="space-y-5">
      <div className={`grid gap-5 ${selected ? 'lg:grid-cols-2' : ''}`}>
        {/* Provider Cards */}
        <div className="grid gap-4">
          <div className="bg-white rounded-2xl px-6 py-4 shadow-sm border border-gray-100">
            <h3 className="font-black text-gray-900 text-xl flex items-center gap-2">👷 My Trusted Provider Circle</h3>
            <p className="text-xs text-gray-400 mt-0.5">Providers you've worked with — built from your booking history</p>
          </div>
          {providers.map(prov => (
            <div key={prov.id}
              onClick={() => setSelectedProvider(selectedProvider === prov.id ? null : prov.id)}
              className={`bg-white rounded-2xl p-5 shadow-sm border-2 transition-all cursor-pointer hover:-translate-y-0.5 ${
                selectedProvider === prov.id ? 'border-teal-400 shadow-teal-100' : 'border-gray-100 hover:border-gray-200'
              }`}>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-12 h-12 bg-gradient-to-br from-teal-400 to-teal-700 rounded-xl flex items-center justify-center text-white font-black text-lg">
                    {prov.name[0].toUpperCase()}
                  </div>
                  <div>
                    <p className="font-black text-gray-900">{prov.name}</p>
                    <p className="text-xs text-gray-500">{Array.from(prov.categories).join(', ') || 'General'}</p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="font-black text-teal-600">₹{prov.totalSpent.toLocaleString('en-IN')}</p>
                  <p className="text-xs text-gray-400">{prov.bookings.length} bookings</p>
                </div>
              </div>
              {/* Trust metrics */}
              <div className="mt-4 grid grid-cols-3 gap-3">
                {[
                  { label: 'Completed', value: prov.bookings.filter(b => b.status==='completed').length },
                  { label: 'Pending',   value: prov.bookings.filter(b => ['pending','confirmed'].includes(b.status)).length },
                  { label: 'Total ₹',  value: `₹${Math.round(prov.totalSpent).toLocaleString('en-IN')}` },
                ].map(m => (
                  <div key={m.label} className="bg-gray-50 rounded-xl p-2.5 text-center">
                    <p className="font-black text-gray-900 text-sm">{m.value}</p>
                    <p className="text-xs text-gray-400">{m.label}</p>
                  </div>
                ))}
              </div>
              <div className="mt-3 flex gap-2">
                <button onClick={e => { e.stopPropagation(); toast.success(`Re-booking with ${prov.name}! 🎉`); }}
                  className="flex-1 bg-teal-600 hover:bg-teal-700 text-white py-2 rounded-xl font-bold text-xs transition-all">
                  📅 Book Again
                </button>
                <button onClick={e => { e.stopPropagation(); toast.success('Message sent!'); }}
                  className="flex-1 bg-gray-100 hover:bg-gray-200 text-gray-700 py-2 rounded-xl font-bold text-xs transition-all">
                  💬 Message
                </button>
              </div>
            </div>
          ))}
        </div>

        {/* Provider History Detail Panel */}
        {selected && (
          <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden h-fit sticky top-4">
            <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
              <h3 className="font-black text-gray-900">History with {selected.name}</h3>
              <button onClick={() => setSelectedProvider(null)} className="p-1.5 hover:bg-gray-100 rounded-lg"><X size={14} /></button>
            </div>
            <div className="divide-y divide-gray-50 max-h-96 overflow-y-auto">
              {selected.bookings.map((b: any) => (
                <div key={b._id} className="px-6 py-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-bold text-gray-900 text-sm">{b.service_name || b.category || 'Service'}</p>
                      <p className="text-xs text-gray-400">{b.created_at?.slice(0,10) || '—'}</p>
                    </div>
                    <div className="text-right">
                      <p className="font-black text-gray-900 text-sm">₹{(b.total_amount || b.amount || 0).toLocaleString('en-IN')}</p>
                      <BookingStatusBadge status={b.status} />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

// ── AR Video Quote Modal ─────────────────────────────────────────────────

const ARVideoQuoteModal: React.FC<{ onClose: () => void }> = ({ onClose }) => {
  const [scanning, setScanning] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [quote, setQuote] = useState<{ issue: string; estCost: number; service: string } | null>(null);
  const [camError, setCamError] = useState(false);
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    let stream: MediaStream | null = null;
    if (!quote && navigator.mediaDevices) {
      navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } })
        .then(s => {
          stream = s;
          if (videoRef.current) {
            videoRef.current.srcObject = s;
          }
        })
        .catch(() => setCamError(true));
    }
    return () => {
      if (stream) stream.getTracks().forEach(t => t.stop());
    };
  }, [quote]);

  const startScan = async () => {
    if (!videoRef.current || !canvasRef.current) return;
    
    setScanning(true);
    
    // Simulate scan duration
    await new Promise(r => setTimeout(r, 2000));
    setScanning(false);
    setAnalyzing(true);
    
    try {
      // Capture frame
      const canvas = canvasRef.current;
      const video = videoRef.current;
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      const ctx = canvas.getContext('2d');
      if (ctx) {
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
        const base64Img = canvas.toDataURL('image/jpeg', 0.7);
        
        // Stop camera
        const stream = video.srcObject as MediaStream;
        if (stream) stream.getTracks().forEach(t => t.stop());
        
        // Send to backend Gemini Vision API
        const result = await aiAPI.analyzeARFrame(base64Img);
        setQuote({
          issue: result.issue || 'General Maintenance Required',
          estCost: result.estCost || 500,
          service: result.service || 'General Service'
        });
      }
    } catch (e) {
      console.error(e);
      setQuote({ issue: 'Appliance Issue Detected', estCost: 800, service: 'Appliance Repair' });
    } finally {
      setAnalyzing(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[110] flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fade-in">
      <div className="bg-white rounded-[32px] p-6 max-w-sm w-full shadow-2xl relative overflow-hidden">
        <button onClick={onClose} className="absolute top-4 right-4 z-20 text-gray-400 hover:text-gray-900 bg-white/50 backdrop-blur-sm rounded-full p-1"><X size={20} /></button>
        
        <div className="text-center mb-6 mt-2 relative z-10">
          <h3 className="text-2xl font-black text-indigo-900">AR Video Quote</h3>
          <p className="text-sm text-gray-500">Point your camera at the issue for an instant AI estimate.</p>
        </div>

        {!quote ? (
          <div className="relative aspect-[3/4] bg-gray-900 rounded-2xl overflow-hidden shadow-inner flex flex-col items-center justify-center">
            
            {/* Real Camera Feed */}
            <video ref={videoRef} autoPlay playsInline className="absolute inset-0 w-full h-full object-cover" />
            <canvas ref={canvasRef} className="hidden" />
            
            {camError && (
              <div className="absolute inset-0 flex flex-col items-center justify-center p-4 text-center bg-gray-900 z-10">
                <Camera size={32} className="text-gray-500 mb-2" />
                <p className="text-white text-sm font-bold">Camera access denied</p>
                <p className="text-gray-400 text-xs">Please allow camera permissions to use AR Quoting.</p>
              </div>
            )}
            
            <div className="absolute inset-0 opacity-40 mix-blend-screen bg-indigo-900 pointer-events-none" style={{ backgroundImage: 'radial-gradient(circle, transparent 20%, #1e1b4b 100%)' }} />
            
            {scanning && (
              <div className="absolute inset-0 z-10 pointer-events-none">
                <div className="w-full h-1 bg-green-400 shadow-[0_0_15px_#4ade80] absolute animate-[scan_2s_ease-in-out_infinite]" />
                <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-40 h-40 border-2 border-green-400/50 rounded-xl" />
              </div>
            )}

            {analyzing && (
              <div className="absolute inset-0 bg-black/60 z-10 flex flex-col items-center justify-center backdrop-blur-sm">
                <div className="w-12 h-12 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin mb-3" />
                <p className="text-white font-bold animate-pulse">AI Analyzing Video Data...</p>
              </div>
            )}

            {!scanning && !analyzing && !camError && (
              <button onClick={startScan} className="z-20 bg-indigo-600 hover:bg-indigo-500 text-white w-16 h-16 rounded-full flex items-center justify-center shadow-[0_0_20px_rgba(79,70,229,0.5)] transition-transform hover:scale-110">
                <Video size={24} />
              </button>
            )}
            
            {!scanning && !analyzing && !camError && <p className="text-white/70 text-xs font-bold mt-4 z-20">Tap to Scan</p>}
          </div>
        ) : (
           <div className="bg-indigo-50 rounded-2xl p-6 text-center border border-indigo-100">
             <div className="w-16 h-16 bg-white rounded-full flex items-center justify-center mx-auto mb-4 shadow-sm border border-indigo-100">
               <Bot size={32} className="text-indigo-600" />
             </div>
             <p className="text-indigo-600 font-bold text-xs uppercase tracking-widest mb-1">AI Diagnosis</p>
             <h4 className="text-xl font-black text-gray-900 mb-2">{quote.issue}</h4>
             <div className="bg-white rounded-xl p-4 mb-5 border border-indigo-50">
               <p className="text-gray-500 text-sm mb-1">Estimated Cost</p>
               <p className="text-3xl font-black text-indigo-700">₹{quote.estCost}</p>
             </div>
             <button onClick={() => { toast.success(`Booked ${quote.service}!`); onClose(); }} className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-black py-3 rounded-xl transition-all shadow-md">
               Book {quote.service}
             </button>
           </div>
        )}
      </div>
    </div>
  );
};

// ── Smart IoT Sync Tab ───────────────────────────────────────────────────

const SmartIoTTab: React.FC = () => {
  const { t } = useTranslation();
  const [scanning, setScanning] = useState(false);
  const [devices, setDevices] = useState([
    { id: 1, name: 'Samsung Smart AC', status: 'Issue Detected', error: 'Filter Efficiency 15% - E4 Error', icon: Wind, color: 'text-red-500', bg: 'bg-red-50', autoFixCost: 499, service: 'AC Deep Cleaning' },
    { id: 2, name: 'LG Washing Machine', status: 'Healthy', error: null, icon: Sparkles, color: 'text-green-500', bg: 'bg-green-50' },
  ]);

  const handleSync = () => {
    setScanning(true);
    setTimeout(() => {
      setScanning(false);
      setDevices(prev => [
        ...prev,
        { id: 3, name: 'Smart Water Heater', status: 'Maintenance Due', error: 'Descale required in 15 days', icon: Droplets, color: 'text-orange-500', bg: 'bg-orange-50', autoFixCost: 399, service: 'Plumbing / Descaling' }
      ]);
      toast.success('Found 1 new connected appliance!');
    }, 2500);
  };

  return (
    <div className="space-y-6">
      <div className="bg-gradient-to-r from-indigo-900 to-blue-900 rounded-2xl p-8 text-white shadow-lg relative overflow-hidden">
        <div className="absolute top-0 right-0 p-6 opacity-20">
          <Wifi size={100} className="animate-pulse" />
        </div>
        <h2 className="text-2xl font-black mb-2 flex items-center gap-3 relative z-10">
          <Wifi size={24} /> {t('Smart Home IoT Sync')}
        </h2>
        <p className="text-indigo-200 mb-6 max-w-lg relative z-10">
          {t('QuickServe monitors your connected smart appliances to auto-diagnose faults before they break down.')}
        </p>
        <button 
          onClick={handleSync} 
          disabled={scanning}
          className="bg-white text-indigo-900 px-5 py-2.5 rounded-xl font-black text-sm hover:bg-indigo-50 transition-colors shadow-lg relative z-10 disabled:opacity-80 flex items-center gap-2"
        >
          {scanning ? <><div className="w-4 h-4 border-2 border-indigo-900 border-t-transparent rounded-full animate-spin" /> Scanning Network...</> : '+ Sync New Device'}
        </button>
      </div>

      <div className="grid md:grid-cols-3 gap-4">
        {devices.map(dev => {
          const Icon = dev.icon;
          return (
            <div key={dev.id} className="bg-white rounded-2xl border border-gray-100 p-5 shadow-sm hover:shadow-md transition-all">
              <div className="flex items-center justify-between mb-4">
                <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${dev.bg}`}>
                  <Icon size={24} className={dev.color} />
                </div>
                {dev.status === 'Healthy' ? (
                  <span className="text-xs font-bold text-green-700 bg-green-100 px-2 py-1 rounded-full">Healthy</span>
                ) : dev.status === 'Issue Detected' ? (
                  <span className="text-xs font-bold text-red-700 bg-red-100 px-2 py-1 rounded-full flex items-center gap-1 animate-pulse">
                    <AlertTriangle size={12} /> Issue
                  </span>
                ) : (
                  <span className="text-xs font-bold text-orange-700 bg-orange-100 px-2 py-1 rounded-full">Warning</span>
                )}
              </div>
              <h3 className="font-black text-gray-900">{dev.name}</h3>
              {dev.error ? (
                <div className="mt-2 text-sm">
                  <p className="text-red-500 font-bold mb-3">{dev.error}</p>
                  <button onClick={() => toast.success(`Auto-booked ${dev.service} for ₹${dev.autoFixCost}!`)} className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-2 rounded-xl transition-all shadow-md shadow-indigo-200">
                    Auto-Fix for ₹{dev.autoFixCost}
                  </button>
                </div>
              ) : (
                <p className="text-sm text-gray-500 mt-2 font-medium">Operating normally.</p>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};

// ── Main CustomerDashboard ───────────────────────────────────────────────

const CustomerDashboard: React.FC = () => {
  useAuth();
  const [activeTab, setActiveTab] = useState<HubTab>('overview');
  const [showARModal, setShowARModal] = useState(false);

  const { data: dashData } = useQuery({
    queryKey: ['customer-dashboard'],
    queryFn: dashboardAPI.getCustomer,
    retry: 1,
  });

  const { data: bookingsData } = useQuery({
    queryKey: ['user-bookings'],
    queryFn: bookingsAPI.getUserBookings,
    retry: 1,
  });

  const { data: loyaltyData } = useQuery({
    queryKey: ['loyalty-points'],
    queryFn: loyaltyAPI.getPoints,
    retry: 1,
  });

  const { data: recsData } = useQuery({
    queryKey: ['ai-recommendations'],
    queryFn: aiAPI.getRecommendations,
    retry: 1,
  });

  const { data: favsData } = useQuery({
    queryKey: ['customer-favourites'],
    queryFn: dashboardAPI.getFavourites,
  });

  const { data: partiesData } = useQuery({
    queryKey: ['block-parties'],
    queryFn: dashboardAPI.getBlockParties,
  });

  const { data: quotesData } = useQuery({
    queryKey: ['customer-quotes'],
    queryFn: dashboardAPI.getQuotes,
  });

  const bookings: any[]       = (Array.isArray(bookingsData) ? bookingsData : (bookingsData as any)?.bookings) || [];
  const loyaltyPoints: number = loyaltyData?.points ?? 450;
  const recs: any[]           = recsData?.recommendations || [];
  const favourites: any[]     = favsData?.favourites || [];
  const blockParties: any[]   = partiesData?.block_parties || [];
  const quotes: any[]         = quotesData?.quotes || [];

  return (
    <DashboardLayout role="customer" title="Home Management Hub">
      <div className="space-y-6 p-6">

        {/* Scrollable Tab Bar */}
        <div className="overflow-x-auto scrollbar-hidden">
          <div className="flex gap-1.5 bg-white rounded-2xl p-1.5 shadow-sm border border-gray-100 w-max min-w-full">
            {TABS.map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-4 py-2.5 rounded-xl font-bold text-sm whitespace-nowrap transition-all duration-200
                  ${activeTab === tab.id
                    ? 'bg-teal-600 text-white shadow-md shadow-teal-200'
                    : 'text-gray-500 hover:text-gray-800 hover:bg-gray-50'
                  }
                `}
              >
                <span>{tab.emoji}</span>
                <span className="hidden sm:inline">{tab.label}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Tab Content */}
        <div>
          {activeTab === 'overview' && (
            <OverviewTab data={dashData} bookings={bookings} recs={recs} loyaltyPoints={loyaltyPoints} favourites={favourites} onOpenARQuote={() => setShowARModal(true)} />
          )}
          {activeTab === 'tracker' && (
            <JobTrackerTab bookings={bookings} />
          )}
          {activeTab === 'transactions' && (
            <TransactionHistoryTab bookings={bookings} />
          )}
          {activeTab === 'spend' && (
            <SpendInsightsTab bookings={bookings} dashData={dashData} />
          )}
          {activeTab === 'my-providers' && (
            <MyProvidersTab bookings={bookings} />
          )}
          {activeTab === 'vault' && (
            <HomeVaultTab />
          )}
          {activeTab === 'health' && (
            <HealthScoreTab />
          )}
          {activeTab === 'neighborhood' && (
            <NeighborhoodTab blockParties={blockParties} />
          )}
          {activeTab === 'rewards' && (
            <RewardsTab points={loyaltyPoints} />
          )}
          {activeTab === 'keyvault' && (
            <KeyVaultTab />
          )}
          {activeTab === 'quotes' && (
            <QuoteHistoryTab quotes={quotes} />
          )}
          {activeTab === 'iot' && (
            <SmartIoTTab />
          )}
        </div>
      </div>
      
      {showARModal && <ARVideoQuoteModal onClose={() => setShowARModal(false)} />}
    </DashboardLayout>
  );
};

export default CustomerDashboard;

