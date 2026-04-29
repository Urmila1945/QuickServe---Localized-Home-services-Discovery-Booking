import React, { useState, useRef, useEffect as useEffectAlias } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { MapPin, ArrowRight, Search, ChevronDown, Globe, User } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import LanguageSwitcher from '../components/LanguageSwitcher';
import { servicesAPI } from '../services/api';

const HomeEnhanced: React.FC = () => {
  const navigate = useNavigate();
  const { t, i18n } = useTranslation();
  const [hoveredCategory, setHoveredCategory] = useState<string | null>(null);
  const [showCategories, setShowCategories] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCity, setSelectedCity] = useState('');
  const [cities, setCities] = useState<string[]>([]);
  const [serviceCategories, setServiceCategories] = useState<{ value: string; label: string; icon: string }[]>([]);
  const [showServiceSuggestions, setShowServiceSuggestions] = useState(false);
  const searchInputRef = useRef<HTMLInputElement>(null);
  const suggestionsRef = useRef<HTMLDivElement>(null);

  // Fetch cities on mount
  React.useEffect(() => {
    servicesAPI.getCities()
      .then(data => {
        setCities(data.map((item: any) => item.city).filter(Boolean));
      })
      .catch(err => console.error('Failed to fetch cities:', err));

    servicesAPI.getCategories()
      .then((data: any) => {
        const cats = (data.categories || data || []).map((c: any) => ({
          value: c.value || c,
          label: c.label || (c.value || c).charAt(0).toUpperCase() + (c.value || c).slice(1),
          icon: c.icon || '🔧',
        }));
        setServiceCategories(cats);
      })
      .catch(() => {
        setServiceCategories([
          { value: 'electrician', label: 'Electrician', icon: '⚡' },
          { value: 'plumber',     label: 'Plumber',     icon: '🔧' },
          { value: 'cleaner',     label: 'Cleaning',    icon: '🧹' },
          { value: 'carpenter',   label: 'Carpenter',   icon: '🪚' },
          { value: 'painter',     label: 'Painter',     icon: '🎨' },
          { value: 'tutor',       label: 'Tutor',       icon: '📚' },
          { value: 'beautician',  label: 'Beautician',  icon: '💄' },
          { value: 'driver',      label: 'Driver',      icon: '🚗' },
        ]);
      });
  }, []);

  // Close suggestions when clicking outside
  useEffectAlias(() => {
    const handler = (e: MouseEvent) => {
      if (
        searchInputRef.current && !searchInputRef.current.contains(e.target as Node) &&
        suggestionsRef.current && !suggestionsRef.current.contains(e.target as Node)
      ) {
        setShowServiceSuggestions(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const handleSearchClick = () => {
    const params = new URLSearchParams();
    if (searchQuery) params.append('q', searchQuery);
    if (selectedCity) params.append('city', selectedCity);
    navigate(`/services?${params.toString()}`);
  };


  // Categories for the dropdown menu
  const categories = [
    { name: 'Plumbing', icon: '🔧' },
    { name: 'Electrical', icon: '⚡' },
    { name: 'Cleaning', icon: '🧹' },
    { name: 'Tutoring', icon: '📚' },
    { name: 'Repair', icon: '🔨' },
    { name: 'Beauty', icon: '💄' },
    { name: 'Fitness', icon: '💪' },
    { name: 'Delivery', icon: '📦' },
  ];

  // Categories with images for the display section
  const categoriesWithImages = [
    { 
      name: 'Plumbing', 
      icon: '🔧', 
      count: '2,500+ pros',
      color: 'from-blue-500 to-cyan-600',
      image: 'https://images.unsplash.com/photo-1581578731548-c64695cc6952?w=400&h=300&fit=crop'
    },
    { 
      name: 'Electrical', 
      icon: '⚡', 
      count: '1,800+ pros',
      color: 'from-yellow-500 to-orange-600',
      image: 'https://images.unsplash.com/photo-1621905251189-08b45d6a269e?w=400&h=300&fit=crop'
    },
    { 
      name: 'Cleaning', 
      icon: '🧹', 
      count: '3,200+ pros',
      color: 'from-green-500 to-emerald-600',
      image: 'https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=400&h=300&fit=crop'
    },
    { 
      name: 'Tutoring', 
      icon: '📚', 
      count: '2,100+ pros',
      color: 'from-purple-500 to-pink-600',
      image: 'https://images.unsplash.com/photo-1522202176988-66273c2fd55f?w=400&h=300&fit=crop'
    },
    { 
      name: 'Repair', 
      icon: '🔨', 
      count: '1,900+ pros',
      color: 'from-red-500 to-pink-600',
      image: 'https://images.unsplash.com/photo-1504148455328-c376907d081c?w=400&h=300&fit=crop'
    },
    { 
      name: 'Beauty', 
      icon: '💄', 
      count: '2,700+ pros',
      color: 'from-pink-500 to-rose-600',
      image: 'https://images.unsplash.com/photo-1560066984-138dadb4c035?w=400&h=300&fit=crop'
    },
    { 
      name: 'Fitness', 
      icon: '💪', 
      count: '1,500+ pros',
      color: 'from-orange-500 to-red-600',
      image: 'https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?w=400&h=300&fit=crop'
    },
    { 
      name: 'Delivery', 
      icon: '📦', 
      count: '2,300+ pros',
      color: 'from-indigo-500 to-purple-600',
      image: 'https://images.unsplash.com/photo-1566576912321-d58ddd7a6088?w=400&h=300&fit=crop'
    },
  ];

  const features = [
    {
      title: 'AI-Powered Matching',
      description: 'Smart algorithms find the perfect service provider for your needs in seconds',
      icon: '🤖',
      gradient: 'from-purple-500 to-pink-600',
      stats: '99% accuracy',
      link: '/ai-matching',
    },
    {
      title: 'Real-time Tracking',
      description: 'Track your service provider in real-time with live GPS updates and ETAs',
      icon: '📍',
      gradient: 'from-blue-500 to-cyan-600',
      stats: '< 30s updates',
      link: '/real-time-tracking',
    },
    {
      title: 'Instant Price Estimator',
      description: 'Know your service cost before booking with our AI surge pricing calculator',
      icon: '🧮',
      gradient: 'from-teal-500 to-emerald-600',
      stats: 'Real-time rates',
      link: '/price-estimator',
    },
    {
      title: 'Verified Providers',
      description: 'All providers are background-checked, verified, and community-rated',
      icon: '✅',
      gradient: 'from-orange-500 to-red-600',
      stats: '2.5M+ checks',
      link: '/verified-providers',
    },
  ];



  return (
    <div className="min-h-screen font-sans">
      {/* Horizontal Navbar */}
      <nav className="fixed top-0 left-0 right-0 z-50 bg-[#0D7A7F] shadow-lg">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            {/* Logo */}
            <Link to="/" className="flex items-center space-x-2">
              <img src="/logo.jpeg" alt="QuickServe" className="h-10 w-auto" />
            </Link>

            {/* Navigation Links */}
            <div className="hidden md:flex items-center space-x-8">
              <Link to="/services" className="text-white hover:text-[#D1EEEE] font-semibold transition-colors">
                {t('Find Services')}
              </Link>
              
              <div className="relative">
                <button
                  onClick={() => setShowCategories(!showCategories)}
                  className="flex items-center space-x-1 text-white hover:text-[#D1EEEE] font-semibold transition-colors"
                >
                  <span>{t('Categories')}</span>
                  <ChevronDown className="w-4 h-4" />
                </button>
                {showCategories && (
                  <div className="absolute top-full mt-2 bg-white rounded-lg shadow-xl py-2 w-48">
                    {categories.map((cat, idx) => (
                      <Link
                        key={idx}
                        to={`/services?category=${encodeURIComponent(cat.name.toLowerCase())}`}
                        className="block px-4 py-2 hover:bg-[#D1EEEE] text-gray-800 font-medium transition-colors"
                        onClick={() => setShowCategories(false)}
                      >
                        {cat.icon} {t(cat.name)}
                      </Link>
                    ))}
                  </div>
                )}
              </div>

              <Link to="/" className="text-white hover:text-[#D1EEEE] font-semibold transition-colors">
                {t('How It Works')}
              </Link>
              
              <Link to="/provider-onboarding" className="text-white hover:text-[#D1EEEE] font-semibold transition-colors">
                {t('Become a Provider')}
              </Link>
            </div>

            {/* Right Side: Language Selector & Profile */}
            <div className="flex items-center space-x-4">
              {/* Language Selector */}
              <LanguageSwitcher variant="dark" />

              {/* Profile Icon */}
              <Link
                to="/login"
                className="flex items-center justify-center w-10 h-10 bg-white hover:bg-[#D1EEEE] rounded-full transition-all shadow-md"
              >
                <User className="w-5 h-5 text-[#0D7A7F]" />
              </Link>
            </div>
          </div>
        </div>
      </nav>

      {/* Hero Section with Handshake Background */}
      <div className="relative h-screen flex flex-col items-center justify-center overflow-hidden pt-16">
        {/* Background Image */}
        <div 
          className="absolute inset-0 bg-cover bg-center z-0"
          style={{
            backgroundImage: 'url(https://images.unsplash.com/photo-1521791136064-7986c2920216?w=1920&h=1080&fit=crop)',
          }}
        >
          {/* Subtle overlay to make text pop */}
          <div className="absolute inset-0 bg-black/10"></div>
        </div>

        {/* Content Container */}
        <div className="relative z-10 w-full max-w-5xl px-4 flex flex-col items-center text-center">
          {/* Main Title Box */}
          <div className="bg-[#0D7A7F] text-white px-8 py-4 rounded-[30px] shadow-2xl mb-6 animate-fade-in">
            <h1 className="text-3xl md:text-5xl font-black tracking-tight">
              {t('Find & Book Local Services Instantly')}
            </h1>
          </div>

          {/* Subtitle Box */}
          <div className="bg-[#D1EEEE] text-[#0D3B3B] max-w-xl px-6 py-4 rounded-[18px] shadow-lg mb-10 animate-slide-up">
            <p className="text-base md:text-lg font-semibold">
              {t('Connect with verified professionals. Book instantly. Pay securely.')}
            </p>
          </div>

          {/* Search Bar Container */}
          <div className="w-full max-w-4xl bg-white rounded-full p-2 shadow-2xl flex flex-col md:flex-row items-center animate-slide-up delay-200">
            {/* Service Input with suggestions */}
            <div className="flex-[1.5] w-full flex items-center px-8 py-1 border-b md:border-b-0 md:border-r border-gray-100 relative">
              <Search className="w-5 h-5 text-[#0D7A7F] mr-3 shrink-0" />
              <input
                ref={searchInputRef}
                type="text"
                placeholder={t('What service do you need?')}
                value={searchQuery}
                onChange={(e) => { setSearchQuery(e.target.value); setShowServiceSuggestions(true); }}
                onFocus={() => setShowServiceSuggestions(true)}
                onKeyDown={(e) => e.key === 'Enter' && handleSearchClick()}
                className="w-full py-4 text-lg text-gray-800 placeholder-gray-400 bg-transparent focus:outline-none font-medium"
                autoComplete="off"
              />
              {/* Suggestions dropdown */}
              {showServiceSuggestions && (
                <div
                  ref={suggestionsRef}
                  className="absolute left-0 top-full mt-3 w-full bg-white rounded-2xl shadow-2xl border border-gray-100 z-50 overflow-hidden max-h-64 overflow-y-auto"
                  style={{ minWidth: '280px' }}
                >
                  {serviceCategories
                    .filter(c =>
                      !searchQuery.trim() ||
                      c.label.toLowerCase().includes(searchQuery.toLowerCase()) ||
                      c.value.toLowerCase().includes(searchQuery.toLowerCase())
                    )
                    .map((cat) => (
                      <button
                        key={cat.value}
                        className="w-full flex items-center gap-3 px-5 py-3 hover:bg-[#D1EEEE]/50 transition-colors text-left group"
                        onMouseDown={(e) => {
                          e.preventDefault();
                          setSearchQuery(cat.label);
                          setShowServiceSuggestions(false);
                        }}
                      >
                        <span className="text-xl w-8 text-center">{cat.icon}</span>
                        <span className="font-semibold text-gray-800 group-hover:text-[#0D7A7F] transition-colors">
                          {cat.label}
                        </span>
                      </button>
                    ))
                  }
                  {serviceCategories.filter(c =>
                    !searchQuery.trim() ||
                    c.label.toLowerCase().includes(searchQuery.toLowerCase()) ||
                    c.value.toLowerCase().includes(searchQuery.toLowerCase())
                  ).length === 0 && (
                    <p className="px-5 py-4 text-sm text-gray-400 text-center">{t('No matching services')}</p>
                  )}
                </div>
              )}
            </div>

            {/* City Dropdown */}
            <div className="flex-1 w-full flex items-center px-8 py-1">
              <MapPin className="w-5 h-5 text-[#0D7A7F] mr-3 shrink-0" />
              <div className="relative w-full">
                <select
                  value={selectedCity}
                  onChange={(e) => setSelectedCity(e.target.value)}
                  className="w-full py-4 text-lg text-gray-800 bg-transparent focus:outline-none appearance-none font-medium cursor-pointer"
                >
                  <option value="">{t('All Cities')}</option>
                  {cities.map((city, idx) => (
                    <option key={idx} value={city}>{city}</option>
                  ))}
                </select>
              </div>
            </div>

            <button
              onClick={handleSearchClick}
              className="w-full md:w-auto bg-[#0D7A7F] hover:bg-[#0D3B3B] text-white px-10 py-4 rounded-full text-xl font-bold transition-all duration-300 hover:scale-105 active:scale-95 shadow-lg md:ml-2"
            >
              {t('Search')}
            </button>
          </div>
        </div>
      </div>

      {/* Categories Section (Keeping existing but styled better) */}
      <div className="bg-white py-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-bold text-gray-900 mb-4">{t('Popular Services 🔥')}</h2>
            <p className="text-xl text-gray-600">{t('Browse thousands of verified professionals across categories')}</p>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
            {categoriesWithImages.map((category, index) => (
              <Link
                key={index}
                to={`/services?category=${encodeURIComponent(category.name.toLowerCase())}`}
                className="group relative overflow-hidden rounded-2xl shadow-lg hover:shadow-2xl transition-all duration-300 hover:scale-105"
                onMouseEnter={() => setHoveredCategory(category.name)}
                onMouseLeave={() => setHoveredCategory(null)}
              >
                {/* Image Background */}
                <div className="relative h-64">
                  <img
                    src={category.image}
                    alt={category.name}
                    className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-110"
                  />
                  
                  {/* Gradient Overlay */}
                  <div className={`absolute inset-0 bg-gradient-to-t ${category.color} opacity-70 group-hover:opacity-90 transition-opacity duration-300`}></div>
                  
                  {/* Content */}
                  <div className="absolute inset-0 flex flex-col items-center justify-center text-white p-6">
                    <div className={`text-5xl mb-3 transition-transform duration-300 ${
                      hoveredCategory === category.name ? 'scale-125' : 'scale-100'
                    }`}>
                      {category.icon}
                    </div>
                    <h3 className="text-2xl font-bold mb-2">{t(category.name)}</h3>
                    <p className="text-sm font-medium text-white/90">{category.count}</p>
                  </div>

                  {/* Hover Arrow */}
                  <div className={`absolute bottom-4 right-4 transition-all duration-300 ${
                    hoveredCategory === category.name ? 'opacity-100 translate-x-0' : 'opacity-0 translate-x-4'
                  }`}>
                    <ArrowRight className="w-6 h-6 text-white" />
                  </div>
                </div>
              </Link>
            ))}
          </div>
        </div>
      </div>

      {/* Features Section */}
      <div className="bg-gray-50 py-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-bold text-gray-900 mb-4">{t('Why Choose QuickServe? ✨')}</h2>
            <p className="text-xl text-gray-600">{t('Experience the future of home services')}</p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8">
            {features.map((feature, index) => (
              <Link
                key={index}
                to={feature.link}
                className="bg-white rounded-2xl shadow-xl p-8 hover:shadow-2xl transition-all duration-300 hover:scale-105 hover:-translate-y-2 block group"
              >
                <div className={`w-16 h-16 bg-gradient-to-br ${feature.gradient} rounded-2xl flex items-center justify-center mb-6 text-3xl shadow-lg`}>
                  {feature.icon}
                </div>
                <h3 className="text-xl font-bold text-gray-900 mb-3 group-hover:text-[#0D7A7F] transition-colors">{t(feature.title)}</h3>
                <p className="text-gray-600 mb-4">{t(feature.description)}</p>
                <div className={`inline-block px-4 py-2 bg-gradient-to-r ${feature.gradient} text-white rounded-full text-sm font-semibold`}>
                  {feature.stats}
                </div>
              </Link>
            ))}
          </div>
        </div>
      </div>

      {/* CTA Section */}
      <div className="bg-gradient-to-r from-primary-600 via-purple-600 to-pink-600 py-20">
        <div className="max-w-4xl mx-auto px-4 text-center">
          <h2 className="text-4xl md:text-5xl font-bold text-white mb-6">
            {t('Ready to Get Started? 🚀')}
          </h2>
          <p className="text-xl text-white/90 mb-10">
            {t('Join our growing community and 75K+ verified professionals')}
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link
              to="/register"
              className="inline-flex items-center justify-center gap-2 bg-white hover:bg-gray-100 text-primary-600 px-10 py-5 rounded-full font-bold text-lg transition-all duration-300 hover:scale-105 shadow-2xl"
            >
              {t('Find a Pro')}
              <ArrowRight className="w-5 h-5" />
            </Link>
            <Link
              to="/provider-onboarding"
              className="inline-flex items-center justify-center gap-2 bg-transparent hover:bg-white/10 text-white border-2 border-white px-10 py-5 rounded-full font-bold text-lg transition-all duration-300 hover:scale-105"
            >
              {t('Become a Provider')}
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
};

export default HomeEnhanced;
