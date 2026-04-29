import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import toast from 'react-hot-toast';
import { useTranslation } from 'react-i18next';

const Register: React.FC = () => {
  const { t } = useTranslation();
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    full_name: '',
    phone: '',
    role: 'customer',
  });
  const [loading, setLoading] = useState(false);
  const { register } = useAuth();
  const navigate = useNavigate();

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      await register(formData);
      toast.success('Registration successful!');
      navigate('/dashboard');
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Registration failed');
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
            {t('Create Your Account')}
          </h2>
          <p className="mt-3 text-lg text-gray-500 font-medium">
            {t('Already have an account?')}{' '}
            <Link
              to="/login"
              className="font-black text-primary hover:text-primary-dark underline decoration-2 underline-offset-4"
            >
              {t('Sign in')}
            </Link>
          </p>
        </div>

        <form className="mt-10 space-y-8 bg-white rounded-[40px] p-10 shadow-2xl border border-gray-100/50" onSubmit={handleSubmit}>
          <div className="space-y-6">
            <div className="space-y-2">
              <label htmlFor="full_name" className="text-xs font-black text-gray-400 uppercase tracking-widest ml-1">
                {t('Full Name')}
              </label>
              <input
                id="full_name"
                name="full_name"
                type="text"
                required
                value={formData.full_name}
                onChange={handleChange}
                className="block w-full px-6 py-4 bg-gray-50 border-2 border-transparent focus:border-primary-light focus:bg-white text-gray-900 rounded-2xl focus:outline-none transition-all font-bold text-lg"
                placeholder="John Doe"
              />
            </div>
            
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
                value={formData.email}
                onChange={handleChange}
                className="block w-full px-6 py-4 bg-gray-50 border-2 border-transparent focus:border-primary-light focus:bg-white text-gray-900 rounded-2xl focus:outline-none transition-all font-bold text-lg"
                placeholder="john@example.com"
              />
            </div>

            <div className="space-y-2">
              <label htmlFor="phone" className="text-xs font-black text-gray-400 uppercase tracking-widest ml-1">
                {t('Phone Number')}
              </label>
              <input
                id="phone"
                name="phone"
                type="tel"
                required
                value={formData.phone}
                onChange={handleChange}
                className="block w-full px-6 py-4 bg-gray-50 border-2 border-transparent focus:border-primary-light focus:bg-white text-gray-900 rounded-2xl focus:outline-none transition-all font-bold text-lg"
                placeholder="+1 (555) 000-0000"
              />
            </div>

            <div className="space-y-2">
              <label htmlFor="role" className="text-xs font-black text-gray-400 uppercase tracking-widest ml-1">
                {t('I want to')}
              </label>
              <select
                id="role"
                name="role"
                value={formData.role}
                onChange={handleChange}
                className="block w-full px-6 py-4 bg-gray-50 border-2 border-transparent focus:border-primary-light focus:bg-white text-gray-900 rounded-2xl focus:outline-none transition-all font-bold text-lg appearance-none cursor-pointer"
              >
                <option value="customer">{t('Book Services (Customer)')}</option>
                <option value="provider">{t('Offer Services (Provider)')}</option>
              </select>
            </div>

            <div className="space-y-2">
              <label htmlFor="password" className="text-xs font-black text-gray-400 uppercase tracking-widest ml-1">
                {t('Password')}
              </label>
              <input
                id="password"
                name="password"
                type="password"
                autoComplete="new-password"
                required
                value={formData.password}
                onChange={handleChange}
                className="block w-full px-6 py-4 bg-gray-50 border-2 border-transparent focus:border-primary-light focus:bg-white text-gray-900 rounded-2xl focus:outline-none transition-all font-bold text-lg"
                placeholder="••••••••"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full flex justify-center py-5 px-6 border border-transparent text-xl font-black rounded-2xl text-white bg-primary hover:bg-primary-dark focus:outline-none focus:ring-4 focus:ring-primary/20 transition-all duration-300 hover:scale-[1.02] active:scale-95 shadow-xl shadow-primary/20 disabled:opacity-50"
          >
            {loading ? (
              <div className="flex items-center gap-3">
                <div className="w-5 h-5 border-4 border-white/30 border-t-white rounded-full animate-spin"></div>
                {t('Creating Account...')}
              </div>
            ) : t('Create My Account')}
          </button>

          <p className="text-center text-xs text-gray-400 font-bold leading-relaxed px-4">
            {t('By joining, you agree to our')} <span className="text-primary-dark underline cursor-pointer">{t('Terms of Service')}</span> {t('and')} <span className="text-primary-dark underline cursor-pointer">{t('Privacy Policy')}</span>.
          </p>
        </form>
      </div>
    </div>
  );
};

export default Register;