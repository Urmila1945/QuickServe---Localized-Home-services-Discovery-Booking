import React, { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import { User } from '../types';
import { authAPI } from '../services/api';
import toast from 'react-hot-toast';

interface AuthContextType {
  user: User | null;
  login: (email: string, password: string) => Promise<void>;
  register: (userData: any) => Promise<void>;
  googleLogin: (credential: string) => Promise<void>;
  logout: () => void;
  loading: boolean;
  isAuthenticated: boolean;
}

// ── Safe default so useContext never returns undefined during HMR ──────────
const defaultContext: AuthContextType = {
  user: null,
  login: async () => {},
  register: async () => {},
  googleLogin: async () => {},
  logout: () => {},
  loading: true,
  isAuthenticated: false,
};

export const AuthContext = createContext<AuthContextType>(defaultContext);

export const useAuth = () => {
  // With the default value above, this can never be undefined — no throw needed
  return useContext(AuthContext);
};

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  // ── logout defined first so Session-Guard can reference it ─────────────
  const logout = useCallback(async () => {
    try { await authAPI.logout(); } catch (_) {}
    setUser(null);
    localStorage.removeItem('token');
    toast.success('Logged out successfully');
  }, []);

  const fetchUser = useCallback(async () => {
    const token = localStorage.getItem('token');
    if (!token) {
      setUser(null);
      setLoading(false);
      return;
    }
    try {
      const userData = await authAPI.getMe();
      setUser(userData);
    } catch (error: any) {
      if (error.response?.status !== 401) {
        console.error('Failed to fetch user:', error);
      }
      setUser(null);
      localStorage.removeItem('token');
    } finally {
      setLoading(false);
    }
  }, []);

  // Initial session restore
  useEffect(() => {
    fetchUser();
  }, [fetchUser]);

  // ── Session-Guard: proactive JWT expiry monitor ────────────────────────
  useEffect(() => {
    const checkToken = () => {
      const token = localStorage.getItem('token');
      if (!token) return;
      try {
        const payload = JSON.parse(atob(token.split('.')[1]));
        const now = Math.floor(Date.now() / 1000);
        // 10-minute buffer before expiry
        if (payload.exp && payload.exp < now + 600) {
          console.warn('Session-Guard: Token close to expiry. Logging out...');
          toast.error('Session expired. Please log in again.');
          logout();
        }
      } catch (_) {
        logout();
      }
    };

    checkToken();
    const interval = setInterval(checkToken, 300_000); // every 5 min
    return () => clearInterval(interval);
  }, [user, logout]);

  const login = async (email: string, password: string) => {
    try {
      await authAPI.login(email, password);
      await fetchUser();
      toast.success('Login successful!');
    } catch (error: any) {
      console.error('Login error:', error);
      const msg =
        error.code === 'ECONNABORTED'
          ? 'Connection timed out. Make sure the backend is running on port 8000.'
          : typeof error.response?.data?.detail === 'string'
          ? error.response.data.detail
          : 'Login failed. Please check your credentials.';
      toast.error(msg);
      throw error;
    }
  };

  const register = async (userData: any) => {
    try {
      await authAPI.register(userData);
      await fetchUser();
      toast.success('Registration successful!');
    } catch (error: any) {
      console.error('Registration error:', error);
      const detail = error.response?.data?.detail;
      const errorMessage =
        typeof detail === 'string'
          ? detail
          : Array.isArray(detail)
          ? detail.map((e: any) => e.msg).join(', ')
          : 'Registration failed. Please try again.';
      toast.error(errorMessage);
      throw error;
    }
  };

  const googleLogin = async (credential: string) => {
    try {
      await authAPI.googleLogin(credential);
      await fetchUser();
      toast.success('Google login successful!');
    } catch (error: any) {
      console.error('Google login error:', error);
      toast.error(error.response?.data?.detail || 'Google login failed. Please try again.');
      throw error;
    }
  };

  const value: AuthContextType = {
    user,
    login,
    register,
    googleLogin,
    logout,
    loading,
    isAuthenticated: !!user,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};
