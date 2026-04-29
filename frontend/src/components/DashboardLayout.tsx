import React, { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useTranslation } from 'react-i18next';
import {
  LayoutDashboard, Calendar, Search, MessageSquare,
  AlertTriangle, LogOut, DollarSign,
  Briefcase, Users, BarChart3, Shield, Bell, Menu, X, Sparkles, Globe
} from 'lucide-react';
import LanguageSwitcher from './LanguageSwitcher';

export type SidebarRole = 'customer' | 'provider' | 'admin';

interface NavItem {
  label: string;
  icon: React.ElementType;
  to: string;
  color?: string;
}

const getNavByRole = (t: (k: string) => string): Record<SidebarRole, NavItem[]> => ({
  customer: [
    { label: t('Overview'),     icon: LayoutDashboard, to: '/dashboard',          color: 'text-teal-300'   },
    { label: t('Bookings'),     icon: Calendar,        to: '/bookings',           color: 'text-blue-300'   },
    { label: t('Services'),     icon: Search,          to: '/services',           color: 'text-purple-300' },
    { label: t('Loyalty'),      icon: DollarSign,      to: '/loyalty',            color: 'text-yellow-300' },
    { label: t('Chat'),         icon: MessageSquare,   to: '/chat',               color: 'text-green-300'  },
    { label: t('Features Lab'), icon: Sparkles,        to: '/enhanced-features',  color: 'text-indigo-300' },
  ],
  provider: [
    { label: t('Overview'),     icon: LayoutDashboard, to: '/provider-dashboard', color: 'text-teal-300'   },
    { label: t('Bookings'),     icon: Briefcase,       to: '/bookings',           color: 'text-blue-300'   },
    { label: t('Earnings'),     icon: DollarSign,      to: '/provider-dashboard', color: 'text-green-300'  },
    { label: t('Chat'),         icon: MessageSquare,   to: '/chat',               color: 'text-pink-300'   },
    { label: t('Features Lab'), icon: Sparkles,        to: '/enhanced-features',  color: 'text-indigo-300' },
  ],
  admin: [
    { label: t('Overview'),   icon: LayoutDashboard, to: '/admin-dashboard',  color: 'text-teal-300'   },
    { label: t('Customers'),  icon: Users,           to: '/admin-dashboard',  color: 'text-blue-300'   },
    { label: t('Providers'),  icon: Shield,          to: '/admin-dashboard',  color: 'text-purple-300' },
    { label: t('Analytics'),  icon: BarChart3,       to: '/admin/analytics',  color: 'text-orange-300' },
    { label: t('Disputes'),   icon: AlertTriangle,   to: '/admin-dashboard',  color: 'text-red-300'    },
  ],
});

const getRoleMeta = (t: (k: string) => string): Record<SidebarRole, { label: string; gradient: string; glow: string; ambientA: string; ambientB: string; ambientC: string }> => ({
  customer: {
    label: t('Customer'),
    gradient: 'from-teal-900 via-[#0D2A30] to-[#0D1F2D]',
    glow: 'shadow-teal-900/50',
    ambientA: 'bg-teal-400/20',
    ambientB: 'bg-cyan-400/15',
    ambientC: 'bg-blue-400/10',
  },
  provider: {
    label: t('Provider'),
    gradient: 'from-[#0D1F2D] via-[#0D2233] to-[#132040]',
    glow: 'shadow-blue-900/50',
    ambientA: 'bg-blue-400/20',
    ambientB: 'bg-indigo-400/15',
    ambientC: 'bg-teal-400/10',
  },
  admin: {
    label: t('Admin'),
    gradient: 'from-[#1a0d2d] via-[#1a122d] to-[#0D1F2D]',
    glow: 'shadow-purple-900/50',
    ambientA: 'bg-purple-400/20',
    ambientB: 'bg-pink-400/15',
    ambientC: 'bg-indigo-400/10',
  },
});

interface DashboardLayoutProps {
  children: React.ReactNode;
  role: SidebarRole;
  title?: string;
  activeTab?: string;
  onTabChange?: (tab: string) => void;
}

const DashboardLayout: React.FC<DashboardLayoutProps> = ({ children, role, title }) => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const { t } = useTranslation();
  const [mobileOpen, setMobileOpen] = useState(false);

  const nav = getNavByRole(t)[role];
  const meta = getRoleMeta(t)[role];
  const displayName = user?.full_name || user?.name || 'User';
  const initials = displayName.split(' ').map((n: string) => n[0]).join('').toUpperCase().slice(0, 2);

  const handleLogout = () => { logout(); navigate('/'); };

  return (
    <div className="min-h-screen relative overflow-x-hidden" style={{ background: 'linear-gradient(145deg, #f0fafa 0%, #e8f5f5 40%, #f0f4ff 100%)' }}>

      {/* ── Ambient Blobs ───────────────────────────────────────────── */}
      <div className="fixed inset-0 pointer-events-none -z-10 overflow-hidden">
        <div className={`absolute -top-32 -right-32 w-[500px] h-[500px] ${meta.ambientA} rounded-full blur-3xl animate-blob`} />
        <div className={`absolute top-1/2 -left-32 w-96 h-96 ${meta.ambientB} rounded-full blur-3xl animate-blob animation-delay-2000`} />
        <div className={`absolute bottom-0 right-1/3 w-80 h-80 ${meta.ambientC} rounded-full blur-3xl animate-blob animation-delay-4000`} />
        {/* Subtle dot grid */}
        <div className="absolute inset-0 opacity-[0.03]"
          style={{ backgroundImage: 'radial-gradient(circle, #0D7A7F 1px, transparent 1px)', backgroundSize: '32px 32px' }}
        />
      </div>

      {/* ── Top Nav ─────────────────────────────────────────────────── */}
      <header className={`sticky top-0 z-50 bg-gradient-to-r ${meta.gradient} shadow-2xl ${meta.glow} backdrop-blur-xl`}>
        <div className="max-w-screen-2xl mx-auto px-4 sm:px-6">
          <div className="flex items-center justify-between h-16 gap-4">

            {/* Logo */}
            <Link to="/" className="flex items-center gap-2.5 group shrink-0">
              <img src="/logo.jpeg" alt="QuickServe" className="h-9 w-auto group-hover:scale-110 transition-transform duration-300" />
            </Link>

            {/* Right: Bell + User + Logout */}
            <div className="flex items-center gap-2 shrink-0">
              <Link to="/notifications" className="relative w-9 h-9 rounded-xl bg-white/10 hover:bg-white/20 flex items-center justify-center text-white/70 hover:text-white transition-all duration-200 hover:scale-110">
                <Bell size={17} />
                <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-red-500 rounded-full ring-2 ring-white/20 animate-pulse" />
              </Link>
              
              <LanguageSwitcher variant="dark" className="ml-1" />

              <div className="flex items-center gap-2.5 pl-2 border-l border-white/20">
                <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-teal-400 to-teal-600 flex items-center justify-center text-white font-black text-sm shadow-lg shadow-teal-500/30 ring-2 ring-white/20">
                  {initials}
                </div>
                <div className="hidden sm:block">
                  <p className="text-white font-bold text-sm leading-tight">{displayName.split(' ')[0]}</p>
                  <p className="text-white/50 text-xs font-medium">{meta.label}</p>
                </div>
              </div>

              <button
                onClick={handleLogout}
              className="hidden sm:flex items-center gap-1.5 px-3 py-2 rounded-xl text-red-400 hover:text-white hover:bg-red-500/20 border border-transparent hover:border-red-500/30 transition-all duration-200 font-bold text-sm ml-1"
              >
                <LogOut size={15} />
                <span>{t('Out')}</span>
              </button>

              {/* Mobile hamburger */}
              <button
                className="lg:hidden w-9 h-9 rounded-xl bg-white/10 hover:bg-white/20 flex items-center justify-center text-white transition-all"
                onClick={() => setMobileOpen(true)}
              >
                <Menu size={18} />
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* ── Mobile Drawer ───────────────────────────────────────────── */}
      {mobileOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={() => setMobileOpen(false)} />
          <div className={`absolute right-0 top-0 h-full w-72 bg-gradient-to-b ${meta.gradient} p-5 flex flex-col shadow-2xl`}>
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center gap-2.5">
                <img src="/logo.jpeg" alt="QuickServe" className="h-8 w-auto" />
              </div>
              <button onClick={() => setMobileOpen(false)} className="text-white/60 hover:text-white p-1 rounded-lg hover:bg-white/10 transition-all">
                <X size={20} />
              </button>
            </div>
            <div className="flex items-center gap-3 p-3 rounded-2xl bg-white/10 border border-white/15 mb-5">
              <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-teal-400 to-teal-600 flex items-center justify-center text-white font-black">
                {initials}
              </div>
              <div>
                <p className="text-white font-bold text-sm">{displayName}</p>
                <p className="text-white/50 text-xs">{meta.label}</p>
              </div>
            </div>
            <nav className="flex-1 space-y-1">
              {nav.map((item) => {
                const Icon = item.icon;
                const isActive = location.pathname === item.to;
                return (
                  <Link key={item.label} to={item.to} onClick={() => setMobileOpen(false)}
                    className={`flex items-center gap-3 px-4 py-3 rounded-xl font-bold text-sm transition-all ${
                      isActive ? 'bg-white/15 text-white border border-white/20' : 'text-white/50 hover:text-white hover:bg-white/10'
                    }`}
                  >
                    <Icon size={17} className={isActive ? 'text-teal-300' : item.color} />
                    {item.label}
                  </Link>
                );
              })}
            </nav>
            <button onClick={handleLogout}
              className="flex items-center gap-3 px-4 py-3 rounded-xl text-red-400 hover:bg-red-500/20 border border-transparent hover:border-red-500/30 font-bold text-sm transition-all mt-4"
            >
              <LogOut size={17} />
              {t('Logout')}
            </button>
          </div>
        </div>
      )}

      {/* ── Sub Navbar ──────────────────────────────────────────────── */}
      <div className="bg-white/80 backdrop-blur-md border-b border-gray-200 shadow-sm sticky top-16 z-40">
        <div className="max-w-screen-2xl mx-auto px-4 sm:px-6">
          <nav className="flex items-center gap-1 overflow-x-auto scrollbar-hidden py-2">
            {nav.map((item) => {
              const Icon = item.icon;
              const isActive = location.pathname === item.to;
              return (
                <Link
                  key={item.label}
                  to={item.to}
                  className={`flex items-center gap-1.5 px-4 py-2 rounded-xl font-bold text-sm whitespace-nowrap transition-all duration-200 shrink-0
                    ${ isActive
                      ? 'bg-teal-600 text-white shadow-md shadow-teal-200'
                      : 'text-gray-500 hover:text-gray-900 hover:bg-gray-100'
                    }`}
                >
                  <Icon size={15} className={isActive ? 'text-white' : item.color?.replace('300', '500') || 'text-gray-400'} />
                  {item.label}
                </Link>
              );
            })}
          </nav>
        </div>
      </div>

      {/* ── Main Content ────────────────────────────────────────────── */}
      <main className="max-w-screen-2xl mx-auto px-4 sm:px-6 py-8">
        {children}
      </main>
    </div>
  );
};

export default DashboardLayout;
