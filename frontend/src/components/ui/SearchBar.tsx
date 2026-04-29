import React, { useState } from 'react';
import { MagnifyingGlassIcon, MapPinIcon } from '@heroicons/react/24/outline';

interface SearchBarProps {
  onSearch: (query: string, location?: { lat: number; lng: number }) => void;
  placeholder?: string;
  className?: string;
}

export default function SearchBar({ onSearch, placeholder = "Search services...", className = "" }: SearchBarProps) {
  const [query, setQuery] = useState('');
  const [location, setLocation] = useState<{ lat: number; lng: number } | null>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSearch(query, location || undefined);
  };

  const getCurrentLocation = () => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          setLocation({
            lat: position.coords.latitude,
            lng: position.coords.longitude
          });
        },
        (error) => {
          console.error('Error getting location:', error);
        }
      );
    }
  };

  return (
    <form onSubmit={handleSubmit} className={`relative ${className}`}>
      <div className="flex rounded-lg shadow-lg overflow-hidden">
        <div className="flex-1 relative">
          <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={placeholder}
            className="w-full pl-10 pr-4 py-3 border-0 focus:ring-2 focus:ring-primary-500 focus:outline-none"
          />
        </div>
        <button
          type="button"
          onClick={getCurrentLocation}
          className="px-4 py-3 bg-gray-100 hover:bg-gray-200 border-l border-gray-300 transition-colors"
          title="Use current location"
        >
          <MapPinIcon className="w-5 h-5 text-gray-600" />
        </button>
        <button
          type="submit"
          className="px-6 py-3 bg-primary-600 hover:bg-primary-700 text-white font-medium transition-colors"
        >
          Search
        </button>
      </div>
    </form>
  );
}