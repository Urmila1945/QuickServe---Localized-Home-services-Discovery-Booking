import React, { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Menu, X, Globe, User } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import LanguageSwitcher from './LanguageSwitcher';

const Navbar: React.FC = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [showLang, setShowLang] = useState(false);
  const { t, i18n } = useTranslation();


  const isHome = location.pathname === '/';

  const handleLogout = () => {
    logout();
    navigate('/');
    setMobileMenuOpen(false);
  };


  return (
    <nav className={`${isHome ? 'bg-transparent' : 'bg-white/95 backdrop-blur-md shadow-sm border-b border-primary-light/30'} fixed top-0 left-0 right-0 z-50 transition-all duration-300`}>
      <div className="max-w-[1400px] mx-auto px-6">
        <div className="flex justify-between items-center h-20">
          {/* Logo */}
          <div className="flex items-center">
            <Link to="/" className="flex items-center space-x-1 group hover:opacity-80 transition-opacity">
              <img src="/logo.jpeg" alt="QuickServe" className="h-12 object-contain" />
            </Link>
          </div>

          {/* Desktop Navigation Links */}
          <div className="hidden lg:flex items-center space-x-8">
            <Link to="/services" className="text-base font-semibold text-primary-dark hover:text-primary transition-all relative group">
              {t('Find Services')}
              <span className="absolute -bottom-1 left-0 w-0 h-0.5 bg-primary transition-all group-hover:w-full"></span>
            </Link>
            <Link to="/services?view=categories" className="text-base font-semibold text-primary-dark hover:text-primary transition-all relative group">
              {t('Categories')}
              <span className="absolute -bottom-1 left-0 w-0 h-0.5 bg-primary transition-all group-hover:w-full"></span>
            </Link>
            <Link to="/features" className="text-base font-semibold text-primary-dark hover:text-primary transition-all relative group">
              {t('How It Works')}
              <span className="absolute -bottom-1 left-0 w-0 h-0.5 bg-primary transition-all group-hover:w-full"></span>
            </Link>

            <Link to="/subscriptions" className="text-base font-semibold text-primary-dark hover:text-primary transition-all relative group">
              👑 {t('Plans')}
              <span className="absolute -bottom-1 left-0 w-0 h-0.5 bg-primary transition-all group-hover:w-full"></span>
            </Link>
          </div>

          {/* Actions */}
          <div className="hidden lg:flex items-center space-x-6">
            <Link 
              to="/provider-onboarding" 
              className="bg-[#D1EEEE] hover:bg-[#B4E4E4] text-[#0D3B3B] px-6 py-2.5 rounded-lg font-bold text-[15px] transition-all duration-300 hover:shadow-md active:scale-95"
            >
              {t('Become a Provider')}
            </Link>
            
            <LanguageSwitcher variant="light" />
            
            <Link 
              to={user ? "/dashboard" : "/login"} 
              className="w-10 h-10 bg-gray-100 rounded-full flex items-center justify-center text-primary-dark hover:bg-primary-light transition-all border-2 border-transparent hover:border-primary shadow-sm overflow-hidden"
            >
              {user ? (
                <span className="font-bold uppercase text-sm">{(user.full_name || user.name)[0]}</span>
              ) : (
                <User className="w-5 h-5" />
              )}
            </Link>
          </div>

          {/* Mobile menu button */}
          <div className="lg:hidden flex items-center">
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="text-primary-dark hover:bg-primary-light p-2 rounded-lg transition-colors"
            >
              {mobileMenuOpen ? <X className="w-8 h-8" /> : <Menu className="w-8 h-8" />}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile Menu */}
      {mobileMenuOpen && (
        <div className="lg:hidden bg-white border-t border-gray-100 p-6 shadow-xl animate-fade-in">
          <div className="flex flex-col space-y-6">
            <Link
              to="/services"
              className="text-xl font-bold text-primary-dark"
              onClick={() => setMobileMenuOpen(false)}
            >
              {t('Find Services')}
            </Link>
            <Link
              to="/services?view=categories"
              className="text-xl font-bold text-primary-dark"
              onClick={() => setMobileMenuOpen(false)}
            >
              {t('Categories')}
            </Link>
            <Link
              to="/features"
              className="text-xl font-bold text-primary-dark"
              onClick={() => setMobileMenuOpen(false)}
            >
              {t('How It Works')}
            </Link>
            <Link
              to="/provider-onboarding"
              className="bg-primary-light text-primary-dark px-6 py-4 rounded-xl font-bold text-center shadow-sm"
              onClick={() => setMobileMenuOpen(false)}
            >
              {t('Become a Provider')}
            </Link>
            {user ? (
              <button
                onClick={handleLogout}
                className="text-xl font-bold text-red-500 text-left"
              >
                {t('Logout')}
              </button>
            ) : (
              <Link
                to="/login"
                className="text-xl font-bold text-primary-dark"
                onClick={() => setMobileMenuOpen(false)}
              >
                {t('Login')}
              </Link>
            )}
          </div>
        </div>
      )}
    </nav>
  );
};

export default Navbar;
