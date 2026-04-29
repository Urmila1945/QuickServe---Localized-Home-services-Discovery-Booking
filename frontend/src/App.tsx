import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from 'react-hot-toast';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import Navbar from './components/Navbar';

// Public pages
import HomeEnhanced from './pages/HomeEnhanced';
import Login from './pages/Login';
import Register from './pages/Register';
import Services from './pages/Services';
import Features from './pages/Features';
import ProviderOnboarding from './pages/ProviderOnboarding';
import AIMatching from './pages/AIMatching';
import RealTimeTracking from './pages/RealTimeTracking';
import SecurePayments from './pages/SecurePayments';
import VerifiedProviders from './pages/VerifiedProviders';
import Emergency from './pages/Emergency';
import Subscriptions from './pages/Subscriptions';
import PriceEstimator from './pages/PriceEstimator';

// Dashboard pages (have own sidebar layout)
import CustomerDashboard from './pages/CustomerDashboard';
import ProviderDashboardNew from './pages/ProviderDashboardNew';
import AdminDashboardNew from './pages/AdminDashboardNew';
import Bookings from './pages/Bookings';
import Loyalty from './pages/Loyalty';
import Chat from './pages/Chat';
import Analytics from './pages/admin/Analytics';
import EnhancedFeatures from './pages/EnhancedFeatures';
import Notifications from './pages/Notifications';
import Profile from './pages/Profile';

// Legacy dashboards (kept for backward compat)
import ReceiptVerify from './pages/ReceiptVerify';
import ChatbotWidget from './components/ChatbotWidget';

import './index.css';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 5 * 60 * 1000,
    },
  },
});

/** Pages that render their own full-screen layout (no Navbar) */
const SIDEBAR_PATHS = [
  '/dashboard', '/bookings', '/loyalty', '/chat',
  '/provider-dashboard', '/admin-dashboard', '/admin/analytics',
  '/enhanced-features', '/emergency', '/notifications', '/profile'
];

const FEATURE_PATHS = [
  '/ai-matching', '/real-time-tracking', '/secure-payments',
  '/verified-providers', '/verify/receipt', '/price-estimator'
];

// ── Error boundary ─────────────────────────────────────────────────────────
class AppErrorBoundary extends React.Component<
  { children: React.ReactNode },
  { hasError: boolean; error: Error | null }
> {
  constructor(props: any) {
    super(props);
    this.state = { hasError: false, error: null };
  }
  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }
  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error('[AppErrorBoundary]', error, info);
  }
  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen flex flex-col items-center justify-center bg-gray-50 p-8">
          <div className="bg-white rounded-2xl shadow-xl p-10 max-w-md text-center">
            <div className="text-6xl mb-4">⚠️</div>
            <h1 className="text-2xl font-black text-gray-800 mb-3">Something went wrong</h1>
            <p className="text-gray-500 mb-6 text-sm font-mono break-all">
              {this.state.error?.message}
            </p>
            <button
              onClick={() => {
                this.setState({ hasError: false, error: null });
                window.location.href = '/';
              }}
              className="bg-teal-600 hover:bg-teal-700 text-white px-8 py-3 rounded-xl font-bold transition-all"
            >
              Back to Home
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

// ── Protected route ────────────────────────────────────────────────────────
const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user, loading } = useAuth();
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="w-10 h-10 border-4 border-teal-600/30 border-t-teal-600 rounded-full animate-spin" />
      </div>
    );
  }
  return user ? <>{children}</> : <Navigate to="/login" replace />;
};

/** Smart dashboard: routes to the right dashboard based on the user's role */
const SmartDashboard: React.FC = () => {
  const { user } = useAuth();
  if (user?.role === 'admin')    return <AdminDashboardNew />;
  if (user?.role === 'provider') return <ProviderDashboardNew />;
  return <CustomerDashboard />;
};

// ── Main app content (must be inside AuthProvider + Router) ────────────────
const AppContent: React.FC = () => {
  const { user } = useAuth();
  const location = useLocation();
  const showNavbar =
    !SIDEBAR_PATHS.some((p) => location.pathname.startsWith(p)) &&
    !FEATURE_PATHS.some((p) => location.pathname.startsWith(p));

  return (
    <div className="min-h-screen bg-transparent">
      {showNavbar && <Navbar />}
      <main className={showNavbar ? 'pt-0' : ''}>
        <Routes>
          {/* ── Public routes ── */}
          <Route path="/"                    element={<HomeEnhanced />} />
          <Route path="/login"               element={user ? <Navigate to="/dashboard" replace /> : <Login />} />
          <Route path="/register"            element={user ? <Navigate to="/dashboard" replace /> : <Register />} />
          <Route path="/services"            element={<Services />} />
          <Route path="/features"            element={<Features />} />
          <Route path="/provider-onboarding" element={<ProviderOnboarding />} />
          
          <Route path="/verify/receipt/:hash" element={<ReceiptVerify />} />
          <Route path="/subscriptions"        element={<Subscriptions />} />

          {/* ── Protected / sidebar routes ── */}
          <Route path="/dashboard" element={
            <ProtectedRoute><SmartDashboard /></ProtectedRoute>
          } />
          
          {/* Protected Feature Pages */}
          <Route path="/ai-matching" element={
            <ProtectedRoute><AIMatching /></ProtectedRoute>
          } />
          <Route path="/real-time-tracking" element={
            <ProtectedRoute><RealTimeTracking /></ProtectedRoute>
          } />
          <Route path="/secure-payments" element={
            <ProtectedRoute><SecurePayments /></ProtectedRoute>
          } />
          <Route path="/verified-providers" element={
            <ProtectedRoute><VerifiedProviders /></ProtectedRoute>
          } />
          <Route path="/price-estimator" element={
            <ProtectedRoute><PriceEstimator /></ProtectedRoute>
          } />

          <Route path="/emergency" element={
            <ProtectedRoute><Emergency /></ProtectedRoute>
          } />
          <Route path="/enhanced-features" element={
            <ProtectedRoute><EnhancedFeatures /></ProtectedRoute>
          } />
          <Route path="/bookings" element={
            <ProtectedRoute><Bookings /></ProtectedRoute>
          } />
          <Route path="/loyalty" element={
            <ProtectedRoute><Loyalty /></ProtectedRoute>
          } />
          <Route path="/chat" element={
            <ProtectedRoute><Chat /></ProtectedRoute>
          } />
          <Route path="/provider-dashboard" element={
            <ProtectedRoute><ProviderDashboardNew /></ProtectedRoute>
          } />
          <Route path="/admin-dashboard" element={
            <ProtectedRoute><AdminDashboardNew /></ProtectedRoute>
          } />
          <Route path="/admin/analytics" element={
            <ProtectedRoute><Analytics /></ProtectedRoute>
          } />
          <Route path="/notifications" element={
            <ProtectedRoute><Notifications /></ProtectedRoute>
          } />
          <Route path="/profile" element={
            <ProtectedRoute><Profile /></ProtectedRoute>
          } />

          {/* Catch-all */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>

      <Toaster
        position="top-right"
        toastOptions={{
          duration: 3000,
          style: {
            background: '#fff',
            color: '#363636',
            padding: '16px',
            borderRadius: '12px',
            boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
          },
          success: { iconTheme: { primary: '#0D7A7F', secondary: '#fff' } },
          error:   { iconTheme: { primary: '#f56565', secondary: '#fff' } },
        }}
      />
      <ChatbotWidget />
    </div>
  );
};

// ── Root: Provider order matters   QueryClient > Router > AuthProvider > AppContent
const App: React.FC = () => (
  <AppErrorBoundary>
    <QueryClientProvider client={queryClient}>
      <Router>
        <AuthProvider>
          <AppContent />
        </AuthProvider>
      </Router>
    </QueryClientProvider>
  </AppErrorBoundary>
);

export default App;
