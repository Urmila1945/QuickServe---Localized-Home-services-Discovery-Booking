import React, { useState, useRef, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Globe, ChevronDown } from 'lucide-react';

interface LanguageSwitcherProps {
  className?: string;
  variant?: 'light' | 'dark' | 'transparent';
}

const LanguageSwitcher: React.FC<LanguageSwitcherProps> = ({ className = '', variant = 'light' }) => {
  const { t, i18n } = useTranslation();
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const languages = [
    { code: 'en', label: 'English', short: 'EN' },
    { code: 'hi', label: 'हिंदी', short: 'हिं' },
    { code: 'mr', label: 'मराठी', short: 'मर' },
  ];

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const currentLang = languages.find(l => l.code === i18n.language) || languages[0];

  const variantStyles = {
    light: 'bg-white text-gray-800 border-gray-200 hover:bg-gray-50',
    dark: 'bg-[#0D3B3B] text-white hover:bg-[#0D3B3B]/80 border-transparent',
    transparent: 'bg-transparent text-white hover:bg-white/10 border-transparent',
  };

  return (
    <div className={`relative ${className}`} ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={`flex items-center gap-2 px-3 py-2 rounded-full font-semibold text-sm transition-all border ${variantStyles[variant]}`}
      >
        <Globe className="w-4 h-4" />
        <span>{currentLang.short}</span>
        <ChevronDown className={`w-3 h-3 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {isOpen && (
        <div className="absolute right-0 mt-2 w-32 bg-white rounded-xl shadow-xl py-2 z-[100] border border-gray-100 animate-fade-in">
          {languages.map((lang) => (
            <button
              key={lang.code}
              onClick={() => {
                i18n.changeLanguage(lang.code);
                setIsOpen(false);
              }}
              className={`w-full text-left px-4 py-2 text-sm font-bold transition-colors hover:bg-teal-50 hover:text-teal-700 ${
                i18n.language === lang.code ? 'text-teal-600 bg-teal-50/50' : 'text-gray-700'
              }`}
            >
              {lang.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
};

export default LanguageSwitcher;
