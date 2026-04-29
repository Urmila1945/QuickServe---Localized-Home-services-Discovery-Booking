import React, { useState, useEffect } from 'react';
import { Search, MapPin } from 'lucide-react';
import VoiceSearch from './VoiceSearch';
import LocationService, { LocationData } from '../../utils/locationService';

interface EnhancedSearchBarProps {
  onSearch: (query: string, location?: LocationData) => void;
  placeholder?: string;
  className?: string;
}

const EnhancedSearchBar: React.FC<EnhancedSearchBarProps> = ({
  onSearch,
  placeholder = "What service do you need?",
  className = ""
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [location, setLocation] = useState<LocationData | null>(null);
  const [isGettingLocation, setIsGettingLocation] = useState(false);
  const [locationError, setLocationError] = useState<string | null>(null);

  const locationService = LocationService.getInstance();

  useEffect(() => {
    // Try to get cached location on component mount
    const cachedLocation = locationService.getCachedLocation();
    if (cachedLocation) {
      setLocation(cachedLocation);
    }
  }, []);

  const handleSearch = () => {
    if (searchQuery.trim()) {
      onSearch(searchQuery.trim(), location || undefined);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSearch();
    }
  };

  const handleVoiceResult = (transcript: string) => {
    setSearchQuery(transcript);
    // Auto-search after voice input
    setTimeout(() => {
      onSearch(transcript, location || undefined);
    }, 500);
  };

  const getCurrentLocation = async () => {
    setIsGettingLocation(true);
    setLocationError(null);

    try {
      const currentLocation = await locationService.getCurrentLocation();
      setLocation(currentLocation);
    } catch (error: any) {
      setLocationError(error.message);
      console.error('Location error:', error);
    } finally {
      setIsGettingLocation(false);
    }
  };

  const processVoiceCommand = (transcript: string) => {
    const lowerTranscript = transcript.toLowerCase();
    
    // Extract service type from voice command
    const serviceKeywords = {
      'plumber': ['plumber', 'plumbing', 'pipe', 'leak', 'water'],
      'electrician': ['electrician', 'electrical', 'wiring', 'power', 'electricity'],
      'cleaner': ['cleaner', 'cleaning', 'clean', 'maid', 'housekeeping'],
      'tutor': ['tutor', 'teacher', 'teaching', 'education', 'study'],
      'repair': ['repair', 'fix', 'broken', 'maintenance'],
      'beauty': ['beauty', 'salon', 'hair', 'makeup', 'spa'],
      'fitness': ['fitness', 'gym', 'trainer', 'workout', 'exercise'],
      'delivery': ['delivery', 'courier', 'pickup', 'transport']
    };

    let detectedService = '';
    for (const [service, keywords] of Object.entries(serviceKeywords)) {
      if (keywords.some(keyword => lowerTranscript.includes(keyword))) {
        detectedService = service;
        break;
      }
    }

    // Check for location-based commands
    if (lowerTranscript.includes('near me') || lowerTranscript.includes('nearby')) {
      if (!location) {
        getCurrentLocation();
      }
    }

    return detectedService || transcript;
  };

  const handleEnhancedVoiceResult = (transcript: string) => {
    const processedQuery = processVoiceCommand(transcript);
    setSearchQuery(processedQuery);
    
    // Auto-search after processing voice command
    setTimeout(() => {
      onSearch(processedQuery, location || undefined);
    }, 500);
  };

  return (
    <div className={`relative ${className}`}>
      <div className="relative bg-white rounded-full shadow-2xl border border-gray-200">
        <input
          type="text"
          placeholder={placeholder}
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          onKeyPress={handleKeyPress}
          className="w-full px-6 py-4 text-gray-800 rounded-full text-lg focus:outline-none focus:ring-4 focus:ring-primary-300 pr-32"
        />
        
        <div className="absolute right-2 top-2 flex items-center space-x-2">
          <VoiceSearch 
            onVoiceResult={handleEnhancedVoiceResult}
            placeholder="Try: 'Find plumber near me'"
          />
          
          <button
            onClick={getCurrentLocation}
            disabled={isGettingLocation}
            className={`p-2 rounded-full transition-all duration-300 ${
              location
                ? 'bg-green-500 hover:bg-green-600 text-white'
                : isGettingLocation
                ? 'bg-yellow-500 text-white animate-spin'
                : 'bg-gray-200 hover:bg-gray-300 text-gray-600'
            }`}
            title={location ? `Location: ${location.address}` : 'Get current location'}
          >
            <MapPin className="h-5 w-5" />
          </button>
          
          <button
            onClick={handleSearch}
            className="bg-primary-500 hover:bg-primary-600 text-white p-2 rounded-full transition-all duration-300 hover:scale-105"
          >
            <Search className="h-5 w-5" />
          </button>
        </div>
      </div>

      {/* Location Display */}
      {location && (
        <div className="mt-2 flex items-center justify-center text-sm text-green-600">
          <MapPin className="h-4 w-4 mr-1" />
          <span>📍 {location.address || `${location.latitude}, ${location.longitude}`}</span>
        </div>
      )}

      {/* Location Error */}
      {locationError && (
        <div className="mt-2 flex items-center justify-center text-sm text-red-600">
          <span>⚠️ {locationError}</span>
        </div>
      )}

      {/* Voice Commands Help */}
      <div className="mt-4 text-center">
        <div className="text-xs text-gray-500">
          💡 Try voice commands: "Find plumber near me", "I need a cleaner", "Emergency electrician"
        </div>
      </div>
    </div>
  );
};

export default EnhancedSearchBar;