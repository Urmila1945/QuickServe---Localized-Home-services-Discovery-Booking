import React, { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { servicesAPI } from '../services/api';
import { Service, SearchFilters } from '../types';
import { formatPriceINR } from '../utils/currency';
import toast from 'react-hot-toast';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../contexts/AuthContext';
import BookingModal from '../components/booking/BookingModal';
import ProviderProfileModal from '../components/verification/ProviderProfileModal';
import { CheckCircle } from 'lucide-react';

const Services: React.FC = () => {
  const { t } = useTranslation();
  const { user } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
const [filters, setFilters] = useState<SearchFilters>({
    radius: 10,
    min_rating: 0,
  });
  const [location, setLocation] = useState<{ latitude: number; longitude: number } | null>(null);
  const [showRecommendations, setShowRecommendations] = useState(false);
  const [bookingService, setBookingService] = useState<Service | null>(null);
  const [viewingProviderId, setViewingProviderId] = useState<string | null>(null);

  // Initialize from URL params
  useEffect(() => {
    const q = searchParams.get('q') || '';
    const categoryParam = searchParams.get('category') || '';
    const cityParam = searchParams.get('city') || '';
    const lat = searchParams.get('latitude');
    const lng = searchParams.get('longitude');
    
    setFilters(prev => {
      const newFilters: SearchFilters = { 
        ...prev, 
        q, 
        category: categoryParam, 
        city: cityParam 
      };
      
      if (lat && lng) {
        const latitude = parseFloat(lat);
        const longitude = parseFloat(lng);
        newFilters.latitude = latitude;
        newFilters.longitude = longitude;
        setLocation({ latitude, longitude });
      } else {
        // If no location in URL, don't force previous location into filters if we want fresh search
        // but often we want to keep the geolocation if available.
      }
      return newFilters;
    });
  }, [searchParams]);

  // Sample service images for demonstration
  const serviceImages = {
    plumbing: 'https://images.unsplash.com/photo-1581578731548-c64695cc6952?w=400&h=250&fit=crop',
    electrical: 'https://images.unsplash.com/photo-1621905251189-08b45d6a269e?w=400&h=250&fit=crop',
    cleaning: 'https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=400&h=250&fit=crop',
    tutoring: 'https://images.unsplash.com/photo-1522202176988-66273c2fd55f?w=400&h=250&fit=crop',
    repair: 'https://images.unsplash.com/photo-1504148455328-c376907d081c?w=400&h=250&fit=crop',
    beauty: 'https://images.unsplash.com/photo-1560066984-138dadb4c035?w=400&h=250&fit=crop',
    fitness: 'https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?w=400&h=250&fit=crop',
    delivery: 'https://images.unsplash.com/photo-1566576912321-d58ddd7a6088?w=400&h=250&fit=crop'
  };

  // Get user location
  useEffect(() => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          setLocation({
            latitude: position.coords.latitude,
            longitude: position.coords.longitude,
          });
          setFilters(prev => ({
            ...prev,
            latitude: position.coords.latitude,
            longitude: position.coords.longitude,
          }));
        },
        (error) => {
          // Silent fallback for location
          console.warn('Geolocation failed, using default (Bangalore):', error);
          const defaultLocation = { latitude: 12.9716, longitude: 77.5946 };
          setLocation(defaultLocation);
          setFilters(prev => ({
            ...prev,
            latitude: defaultLocation.latitude,
            longitude: defaultLocation.longitude,
          }));
        }
      );
    }
  }, []);

  const { data: servicesData, isLoading: servicesLoading, isError: servicesError } = useQuery({
    queryKey: ['services', filters],
    queryFn: () => servicesAPI.search(filters) as Promise<any>,
    retry: 1,
    staleTime: 30000
  });

  const { data: recommendationsRaw, isLoading: recommendationsLoading, error: recommendationsError } = useQuery({
    queryKey: ['recommendations', location],
    queryFn: () => servicesAPI.getRecommendations(location!.latitude, location!.longitude) as Promise<any>,
    enabled: !!location && showRecommendations,
    retry: 1,
    staleTime: 30000
  });
  // Backend returns plain array for recommendations
  const recommendationsData = Array.isArray(recommendationsRaw)
    ? { recommendations: recommendationsRaw }
    : recommendationsRaw;

  const { data: categoriesData, isError: categoriesError } = useQuery({
    queryKey: ['categories'],
    queryFn: servicesAPI.getCategories as () => Promise<any>,
    retry: 1
  });

  const { data: citiesData, isError: citiesError } = useQuery({
    queryKey: ['cities'],
    queryFn: servicesAPI.getCities,
    retry: 1
  });

  const handleFilterChange = (key: keyof SearchFilters, value: any) => {
    setFilters(prev => ({ ...prev, [key]: value }));
  };

  const handleBookNow = (service: Service) => {
    if (!user) {
      toast.error('Please login to book a service');
      navigate('/login');
      return;
    }
    setBookingService(service);
  };

  const ServiceCard: React.FC<{ service: Service }> = ({ service }) => {
    const price = service.price_per_hour || service.price || 0;
    const serviceName = service.name || service.title || 'Service';
    const serviceRating = service.rating || 0;
    const serviceReviews = service.reviews_count || 0;
    
    return (
    <div className="bg-white rounded-2xl shadow-md overflow-hidden hover:shadow-2xl transition-all duration-300 hover:scale-[1.03] group border border-gray-100 flex flex-col">
      <div className="relative h-56 overflow-hidden">
        <img 
          src={serviceImages[service.category as keyof typeof serviceImages] || serviceImages.repair}
          alt={serviceName}
          className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-700"
        />
        <div className="absolute top-4 right-4 z-10">
        </div>
        <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/20 to-transparent p-6 flex flex-col justify-end">
          <div className="flex items-center text-white">
            <div className="flex items-center bg-white/20 backdrop-blur-md px-3 py-1 rounded-full">
              <span className="text-yellow-400 mr-1 text-lg">★</span>
              <span className="font-bold text-lg">{serviceRating.toFixed(1)}</span>
              <span className="text-sm ml-1 opacity-80">({serviceReviews})</span>
            </div>
          </div>
        </div>
      </div>
      
      <div className="p-6 flex-1 flex flex-col">
        <div className="flex justify-between items-start mb-4">
          <div className="flex-1">
            <h3 className="text-xl font-black text-primary-dark group-hover:text-primary transition-colors leading-tight mb-2">
              {serviceName}
            </h3>
            
            {/* Provider Verification Info */}
            <div 
              className="flex items-center gap-2 cursor-pointer hover:translate-x-1 transition-all group/prov" 
              onClick={(e) => {
                e.stopPropagation();
                if (service.provider_id) setViewingProviderId(service.provider_id);
              }}
            >
              <div className="w-8 h-8 rounded-lg bg-teal-50 border border-teal-100 flex items-center justify-center text-teal-600 font-bold text-xs">
                {service.provider_name?.[0] || 'P'}
              </div>
              <div className="flex flex-col">
                <span className="text-xs font-black text-gray-900 group-hover/prov:text-teal-600 transition-colors uppercase tracking-tighter">
                  {service.provider_name}
                </span>
                <span className="text-[10px] font-bold text-teal-600 uppercase flex items-center gap-1">
                  <CheckCircle size={10} className="fill-teal-50" /> Verified
                </span>
              </div>
            </div>
          </div>
          <div className="text-right flex flex-col items-end">
            <span className="text-2xl font-black text-primary">{formatPriceINR(price)}</span>
            <div className="text-[10px] font-bold text-gray-400 uppercase tracking-widest">{t('Per Hour')}</div>
          </div>
        </div>
        
        <p className="text-gray-500 text-sm mb-6 line-clamp-2 font-medium leading-relaxed">{service.description}</p>
        
        <div className="mt-auto">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center space-x-3 bg-gray-50 px-4 py-2 rounded-xl border border-gray-100">
              <span className="text-2xl">
                {(categoriesData?.categories || categoriesData || []).find((c: any) => c.value === service.category)?.icon || '🔧'}
              </span>
              <span className="text-xs font-black text-gray-500 uppercase tracking-widest">
                {service.category}
              </span>
            </div>
            {service.distance && (
              <div className="flex items-center text-xs font-bold text-gray-400">
                <span className="mr-1.5">📍</span>
                <span>{service.distance.toFixed(1)} km</span>
              </div>
            )}
          </div>
          
          <div className="flex items-center gap-3">
            <button
              onClick={() => handleBookNow(service)}
              className="flex-1 bg-primary hover:bg-primary-dark text-white px-6 py-4 rounded-xl text-sm font-black transition-all duration-300 hover:scale-[1.02] shadow-lg shadow-primary/20"
            >
              {t('Book Now')}
            </button>
            <button className="w-12 h-12 flex items-center justify-center rounded-xl border-2 border-primary-light text-primary hover:bg-primary-light transition-colors">
              <span className="text-xl">💬</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
  };

  const LoadingCard = () => (
    <div className="bg-white rounded-2xl shadow-md overflow-hidden animate-pulse border border-gray-100">
      <div className="h-56 bg-gray-200"></div>
      <div className="p-6 space-y-4">
        <div className="flex justify-between">
          <div className="h-6 bg-gray-200 rounded w-2/3"></div>
          <div className="h-6 bg-gray-200 rounded w-16"></div>
        </div>
        <div className="h-4 bg-gray-200 rounded"></div>
        <div className="h-4 bg-gray-200 rounded w-2/3"></div>
        <div className="pt-4 flex gap-3">
          <div className="h-12 bg-gray-200 rounded-xl flex-1"></div>
          <div className="h-12 bg-gray-200 rounded-xl w-12"></div>
        </div>
      </div>
    </div>
  );

  return (
    <>
    {bookingService && (
      <BookingModal
        service={bookingService}
        onClose={() => setBookingService(null)}
      />
    )}
    {viewingProviderId && (
      <ProviderProfileModal
        providerId={viewingProviderId}
        onClose={() => setViewingProviderId(null)}
      />
    )}
    <div className="min-h-screen bg-[#F8FAFA] pt-28 pb-16">
      {/* Hero Section */}
      <div className="bg-primary-dark text-white py-16 mb-12 relative overflow-hidden">
        <div className="absolute inset-0 bg-pattern-dots opacity-10"></div>
        <div className="max-w-7xl mx-auto px-4 text-center relative z-10">
          <h1 className="text-5xl md:text-6xl font-black mb-6 animate-fade-in tracking-tight text-transparent bg-clip-text bg-gradient-to-r from-teal-200 via-white to-teal-400 drop-shadow-[0_2px_2px_rgba(0,0,0,0.8)] pb-2">
            {t('Find Trusted Local Services')}
          </h1>
          <p className="text-xl md:text-2xl opacity-90 animate-fade-in-up font-bold text-teal-50 max-w-2xl mx-auto leading-relaxed drop-shadow-md">
            {t('Discover and book top-rated professionals for all your home service needs.')}
          </p>
        </div>
      </div>

      <div className="max-w-[1400px] mx-auto px-6">
        {/* Toggle between Search and Recommendations */}
        <div className="flex justify-center mb-12">
          <div className="bg-white/50 backdrop-blur-sm rounded-[24px] p-2 shadow-xl border border-white inline-flex">
            <button
              onClick={() => setShowRecommendations(false)}
              className={`px-10 py-4 rounded-[20px] font-black text-lg transition-all duration-300 ${
                !showRecommendations
                  ? 'bg-primary text-white shadow-xl scale-105'
                  : 'text-gray-500 hover:text-primary'
              }`}
            >
              {t('Search Services')}
            </button>
            <button
              onClick={() => setShowRecommendations(true)}
              className={`px-10 py-4 rounded-[20px] font-black text-lg transition-all duration-300 ${
                showRecommendations
                  ? 'bg-primary text-white shadow-xl scale-105'
                  : 'text-gray-500 hover:text-primary'
              }`}
            >
              {t('AI Smart Match')}
            </button>
          </div>
        </div>

        <div className="grid lg:grid-cols-4 gap-10">
          {/* Filters Sidebar */}
          {!showRecommendations && (
            <div className="lg:col-span-1">
              <div className="bg-white rounded-[32px] shadow-xl p-8 sticky top-28 border border-gray-50">
                <div className="flex items-center justify-between mb-8">
                  <h2 className="text-2xl font-black text-primary-dark">{t('Filters')}</h2>
                  <button 
                    onClick={() => setFilters({ radius: 10, min_rating: 0 })}
                    className="text-primary font-bold text-sm hover:underline"
                  >
                    {t('Reset')}
                  </button>
                </div>
                
                {/* Search Term */}
                <div className="mb-8">
                  <label className="block text-xs font-black text-gray-400 uppercase tracking-widest mb-4">
                    {t('Search')}
                  </label>
                  <div className="relative">
                    <span className="absolute left-5 top-1/2 -translate-y-1/2 text-primary font-bold">🔍</span>
                    <input
                      type="text"
                      placeholder={t('Search services…')}
                      value={filters.q || ''}
                      onChange={(e) => handleFilterChange('q', e.target.value || undefined)}
                      className="w-full bg-gray-50 border-2 border-transparent focus:border-primary-light rounded-2xl pl-12 pr-5 py-4 focus:outline-none focus:bg-white transition-all text-gray-800 font-bold"
                    />
                  </div>
                </div>

                {/* Category Filter */}
                <div className="mb-8">
                  <label className="block text-xs font-black text-gray-400 uppercase tracking-widest mb-4">
                    {t('Category')}
                  </label>
                  <select
                    value={filters.category || ''}
                    onChange={(e) => handleFilterChange('category', e.target.value || undefined)}
                    className="w-full bg-gray-50 border-2 border-transparent focus:border-primary-light rounded-2xl px-5 py-4 focus:outline-none focus:bg-white transition-all text-gray-800 font-bold appearance-none cursor-pointer"
                  >
                    <option value="">{t('All Services')}</option>
                    {(categoriesData?.categories || categoriesData || []).map((category: any, idx: number) => (
                      <option key={category.value || idx} value={category.value}>
                        {category.label}
                      </option>
                    ))}
                  </select>
                </div>

                {/* City Filter */}
                <div className="mb-8">
                  <label className="block text-xs font-black text-gray-400 uppercase tracking-widest mb-4">
                    {t('City')}
                  </label>
                  <select
                    value={filters.city || ''}
                    onChange={(e) => handleFilterChange('city', e.target.value || undefined)}
                    className="w-full bg-gray-50 border-2 border-transparent focus:border-primary-light rounded-2xl px-5 py-4 focus:outline-none focus:bg-white transition-all text-gray-800 font-bold appearance-none cursor-pointer"
                  >
                    <option value="">{t('All Cities')}</option>
                    {citiesData?.slice(0, 100).map((cityData: any) => (
                      <option key={cityData.city} value={cityData.city}>
                        {cityData.city} ({cityData.service_count})
                      </option>
                    ))}
                  </select>
                </div>

                {/* Radius Filter */}
                <div className="mb-8">
                  <div className="flex justify-between items-center mb-4">
                    <label className="text-xs font-black text-gray-400 uppercase tracking-widest">
                      {t('Distance')}
                    </label>
                    <span className="text-primary font-black">{filters.radius} km</span>
                  </div>
                  <input
                    type="range"
                    min="1"
                    max="50"
                    value={filters.radius}
                    onChange={(e) => handleFilterChange('radius', parseInt(e.target.value))}
                    className="w-full h-2 bg-gray-100 rounded-lg appearance-none cursor-pointer accent-primary"
                  />
                </div>

                {/* Rating Filter */}
                <div className="mb-8">
                  <label className="block text-xs font-black text-gray-400 uppercase tracking-widest mb-4">
                    {t('Min. Rating')}
                  </label>
                  <div className="grid grid-cols-2 gap-3">
                    {[0, 3, 4, 4.5].map((val) => (
                      <button
                        key={val}
                        onClick={() => handleFilterChange('min_rating', val)}
                        className={`py-3 rounded-xl font-bold transition-all ${
                          filters.min_rating === val
                            ? 'bg-primary text-white shadow-md shadow-primary/20'
                            : 'bg-gray-50 text-gray-500 hover:bg-primary-light/30'
                        }`}
                      >
                        {val === 0 ? t('Any') : `${val}+ ★`}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Price Filter */}
                <div className="mb-8">
                  <label className="block text-xs font-black text-gray-400 uppercase tracking-widest mb-4">
                    {t('Max Price')}
                  </label>
                  <div className="relative">
                    <span className="absolute left-5 top-1/2 -translate-y-1/2 text-gray-400 font-bold">₹</span>
                    <input
                      type="number"
                      placeholder={t('Unlimited')}
                      value={filters.max_price || ''}
                      onChange={(e) => handleFilterChange('max_price', e.target.value ? parseFloat(e.target.value) : undefined)}
                      className="w-full bg-gray-50 border-2 border-transparent focus:border-primary-light rounded-2xl pl-10 pr-5 py-4 focus:outline-none focus:bg-white transition-all text-gray-800 font-bold"
                    />
                  </div>
                </div>

              </div>
            </div>
          )}

          {/* Services Grid */}
          <div className={showRecommendations ? 'lg:col-span-4' : 'lg:col-span-3'}>
            {showRecommendations ? (
              <div>
            <div className="flex flex-col items-center text-center mb-12">
                  <div className="w-20 h-20 bg-primary-light rounded-3xl flex items-center justify-center text-4xl mb-6 shadow-inner">🤖</div>
                  <h2 className="text-4xl font-black text-primary-dark mb-4 tracking-tight">{t('AI-Smart Match')}</h2>
                  <p className="text-xl text-gray-500 font-medium max-w-xl">{t('Our algorithms analyzed your history and preferences to find these perfect matches.')}</p>
                </div>
                {recommendationsLoading ? (
                  <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
                    {[...Array(6)].map((_, i) => (
                      <LoadingCard key={i} />
                    ))}
                  </div>
                ) : recommendationsError ? (
                  <div className="text-center py-24 bg-white rounded-[40px] shadow-xl border border-gray-50">
                    <div className="text-8xl mb-8 opacity-20">⚠️</div>
                    <h3 className="text-3xl font-black text-red-600 mb-4">{t('Connection Error')}</h3>
                    <p className="text-xl text-gray-400 font-medium mb-10">{t('Unable to load recommendations. Please check your connection.')}</p>
                    <button 
                      onClick={() => window.location.reload()}
                      className="bg-primary hover:bg-primary-dark text-white px-10 py-4 rounded-2xl font-black text-lg transition-all shadow-xl shadow-primary/20"
                    >
                      {t('Retry')}
                    </button>
                  </div>
                ) : !recommendationsData?.recommendations || (recommendationsData.recommendations as any[]).length === 0 ? (
                  <div className="text-center py-24 bg-white rounded-[40px] shadow-xl border border-gray-50">
                    <div className="text-8xl mb-8 opacity-20">🤖</div>
                    <h3 className="text-3xl font-black text-primary-dark mb-4">{t('No Recommendations Yet')}</h3>
                    <p className="text-xl text-gray-400 font-medium mb-10">{t('Book a few services to get personalized AI recommendations!')}</p>
                  </div>
                ) : (
                  <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
                    {recommendationsData?.recommendations?.map((service: Service) => (
                      <ServiceCard key={service._id} service={service} />
                    ))}
                  </div>
                )}
              </div>
            ) : (
              <div>
                <div className="flex flex-col md:flex-row justify-between items-end mb-10 gap-6">
                  <div>
                    <h2 className="text-4xl font-black text-primary-dark tracking-tight mb-2">
                      {servicesData?.total || 0} {t('Professionals')}
                    </h2>
                    <p className="text-lg text-gray-400 font-bold uppercase tracking-widest">{t('Available in your area')}</p>
                  </div>
                  <div className="flex items-center gap-4 bg-white px-6 py-3 rounded-2xl shadow-sm border border-gray-100">
                    <span className="text-xs font-black text-gray-400 uppercase">{t('Sort by:')}</span>
                    <select className="bg-transparent font-black text-primary outline-none cursor-pointer">
                      <option value="recommended">{t('Recommended')}</option>
                      <option value="distance">{t('Distance')}</option>
                      <option value="price-low">{t('Price: Low to High')}</option>
                      <option value="highest-rated">{t('Highest Rated')}</option>
                    </select>
                  </div>
                </div>
                
                {servicesLoading ? (
                  <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
                    {[...Array(6)].map((_, i) => (
                      <LoadingCard key={i} />
                    ))}
                  </div>
                ) : !servicesData?.services || servicesData.services.length === 0 ? (
                  <div className="text-center py-24 bg-white rounded-[40px] shadow-xl border border-gray-100">
                    <div className="text-8xl mb-8 opacity-20">🔎</div>
                    <h3 className="text-3xl font-black text-primary-dark mb-4">{t('No Professionals Found')}</h3>
                    <p className="text-xl text-gray-400 font-medium mb-10">{t("We couldn't find any services matching your current filters.")}</p>
                    <button 
                      onClick={() => setFilters({ radius: 50, min_rating: 0 })}
                      className="bg-primary hover:bg-primary-dark text-white px-10 py-4 rounded-2xl font-black text-lg transition-all shadow-xl shadow-primary/20"
                    >
                      {t('Broaden Search Area')}
                    </button>
                  </div>
                ) : (
                  <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
                    {servicesData?.services?.map((service: Service) => (
                      <ServiceCard key={service._id} service={service} />
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
    </>
  );
};

export default Services;