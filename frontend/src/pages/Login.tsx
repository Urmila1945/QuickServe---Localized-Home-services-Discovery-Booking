import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useTranslation } from 'react-i18next';
import toast from 'react-hot-toast';

declare global {
  interface Window {
    google: any;
  }
}

const Login: React.FC = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const { login, googleLogin } = useAuth();
  const navigate = useNavigate();
  const { t } = useTranslation();

  useEffect(() => {
    // Only init Google Sign-In once and only if client ID is properly configured
    const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID?.trim();
    if (!window.google || !clientId || clientId.includes('your_google')) return;
    // Prevent double-init in React StrictMode
    if ((window as any).__googleInitDone) return;
    (window as any).__googleInitDone = true;
    try {
      window.google.accounts.id.initialize({
        client_id: clientId,
        callback: handleGoogleResponse,
      });
      const googleButton = document.getElementById('googleSignInButton');
      if (googleButton) {
        window.google.accounts.id.renderButton(googleButton, {
          theme: 'outline',
          size: 'large',
          width: '400',
          text: 'signin_with',
        });
      }
    } catch (e) {
      console.warn('Google Sign-In init failed:', e);
    }
  }, []);

  const handleGoogleResponse = async (response: any) => {
    try {
      setLoading(true);
      await googleLogin(response.credential);
      navigate('/dashboard');
    } catch (error) {
      console.error('Google login failed:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      await login(email, password);
      navigate('/dashboard');
    } catch (error: any) {
      console.error('Login failed:', error);
      toast.error(error.response?.data?.detail || 'Login failed. Please check your credentials.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#F8FAFA] pt-28 pb-16 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-10 animate-fade-in-up">
        <div className="text-center">
          <Link to="/" className="inline-flex flex-col items-center group">
            <div className="h-20 w-20 bg-primary-dark rounded-[24px] flex items-center justify-center shadow-2xl group-hover:rotate-6 transition-transform">
              <span className="text-white font-black text-4xl">N</span>
            </div>
            <h1 className="mt-6 text-4xl font-black text-primary-dark tracking-tight">QuickServe</h1>
          </Link>
          <h2 className="mt-8 text-3xl font-black text-gray-900 tracking-tight">
            {t('Welcome Back')}
          </h2>
          <p className="mt-3 text-lg text-gray-500 font-medium">
            {t('New here?')}{' '}
            <Link
              to="/register"
              className="font-black text-primary hover:text-primary-dark underline decoration-2 underline-offset-4"
            >
              {t('Create an account')}
            </Link>
          </p>
        </div>

        <form className="mt-10 space-y-8 bg-white rounded-[40px] p-10 shadow-2xl border border-gray-100/50" onSubmit={handleSubmit}>
          <div className="space-y-6">
            <div className="space-y-2">
              <label htmlFor="email" className="text-xs font-black text-gray-400 uppercase tracking-widest ml-1">
                {t('Email Address')}
              </label>
              <input
                id="email"
                name="email"
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="block w-full px-6 py-5 bg-gray-50 border-2 border-transparent focus:border-primary-light focus:bg-white text-gray-900 rounded-2xl focus:outline-none transition-all font-bold text-lg"
                placeholder="name@company.com"
              />
            </div>
            <div className="space-y-2">
              <div className="flex justify-between items-center ml-1">
                <label htmlFor="password" className="text-xs font-black text-gray-400 uppercase tracking-widest">
                  {t('Password')}
                </label>
                <button type="button" className="text-xs font-black text-primary hover:text-primary-dark uppercase tracking-widest">
                  {t('Forgot?')}
                </button>
              </div>
              <input
                id="password"
                name="password"
                type="password"
                autoComplete="current-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="block w-full px-6 py-5 bg-gray-50 border-2 border-transparent focus:border-primary-light focus:bg-white text-gray-900 rounded-2xl focus:outline-none transition-all font-bold text-lg"
                placeholder="••••••••"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full flex justify-center py-5 px-6 border border-transparent text-xl font-black rounded-2xl text-white bg-primary hover:bg-primary-dark focus:outline-none focus:ring-4 focus:ring-primary/20 transition-all duration-300 hover:scale-[1.02] active:scale-95 shadow-xl shadow-primary/20 disabled:opacity-50 disabled:hover:scale-100"
          >
            {loading ? (
              <div className="flex items-center gap-3">
                <div className="w-5 h-5 border-4 border-white/30 border-t-white rounded-full animate-spin"></div>
                {t('Signing in...')}
              </div>
            ) : t('Sign in to Dashboard')}
          </button>

          <div className="relative py-4">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t-2 border-gray-100"></div>
            </div>
            <div className="relative flex justify-center">
              <span className="px-4 bg-white text-xs font-black text-gray-400 uppercase tracking-[0.2em]">{t('Secure Login')}</span>
            </div>
          </div>

          <div id="googleSignInButton" className="flex justify-center rounded-2xl overflow-hidden shadow-md hover:shadow-lg transition-shadow"></div>

          {/* Demo Credentials Panel */}
          <div className="bg-gradient-to-br from-[#0D1F2D] to-[#0D3B3B] rounded-2xl p-6 border border-teal-800/40">
            <div className="flex items-center justify-between mb-4">
              <p className="text-xs font-black text-teal-300 uppercase tracking-[0.2em]">
                🔑 {t('Demo Login Credentials')}
              </p>
              <span className="text-[10px] font-bold text-teal-500 bg-teal-900/40 px-2 py-0.5 rounded-full">Password: password123</span>
            </div>
            <div className="grid grid-cols-1 gap-3">
              {[
                { role: 'Customer',  email: 'customer@demo.com', icon: '👤', color: 'hover:bg-blue-900/40',   badge: 'bg-blue-900/40 text-blue-300' },
                { role: 'Provider',  email: 'provider@demo.com', icon: '🔧', color: 'hover:bg-green-900/40',  badge: 'bg-green-900/40 text-green-300' },
                { role: 'Admin',     email: 'admin@demo.com',    icon: '🛡️', color: 'hover:bg-purple-900/40', badge: 'bg-purple-900/40 text-purple-300' },
              ].map(cred => (
                <button
                  key={cred.role}
                  type="button"
                  onClick={() => { setEmail(cred.email); setPassword('password123'); }}
                  className={`flex items-center justify-between px-4 py-3 bg-white/5 ${cred.color} rounded-xl border border-white/10 transition-all duration-200 hover:border-white/20 group`}
                >
                  <div className="flex items-center gap-3">
                    <span className="text-lg">{cred.icon}</span>
                    <div className="text-left">
                      <p className="text-white font-black text-sm">{cred.role}</p>
                      <p className="text-white/50 text-xs font-mono">{cred.email}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={`text-[10px] font-black px-2 py-0.5 rounded-full ${cred.badge}`}>{cred.role}</span>
                    <span className="text-white/30 group-hover:text-white/60 text-xs font-mono">→</span>
                  </div>
                </button>
              ))}
            </div>
            <div className="mt-4 pt-4 border-t border-white/10">
              <p className="text-center text-white/30 text-[11px] font-bold">
                {t('Click any row to auto-fill credentials, then press Sign In')}
              </p>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
};

export default Login;