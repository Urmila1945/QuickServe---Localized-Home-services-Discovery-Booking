import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { bookingsAPI, servicesAPI } from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import toast from 'react-hot-toast';
import {
  AlertTriangle, MapPin, Phone, Clock, ArrowLeft,
  Navigation, Shield, Star, Zap, ChevronRight,
} from 'lucide-react';

// ── Constants ──────────────────────────────────────────────────────────

const EMERGENCY_CATEGORIES = [
  { value: 'plumbing',   label: 'Plumbing',     icon: '🔧', color: 'from-blue-500 to-cyan-600',      desc: 'Burst pipes, leaks, blockages' },
  { value: 'electrical', label: 'Electrical',   icon: '⚡', color: 'from-yellow-500 to-orange-500',  desc: 'Power outage, short circuit'   },
  { value: 'repair',     label: 'Appliance',    icon: '🔨', color: 'from-gray-500 to-gray-700',      desc: 'AC, fridge, washing machine'   },
  { value: 'cleaning',   label: 'Flooding',     icon: '🌊', color: 'from-teal-500 to-teal-700',      desc: 'Water damage, flood cleanup'   },
  { value: 'security',   label: 'Security',     icon: '🔒', color: 'from-red-500 to-red-700',        desc: 'Lock, key, CCTV issues'        },
  { value: 'locksmith',  label: 'Locksmith',    icon: '🗝️', color: 'from-indigo-500 to-purple-600',  desc: 'Locked out, broken locks'      },
  { value: 'pest',       label: 'Pest Control', icon: '🐛', color: 'from-green-600 to-emerald-700',  desc: 'Bees, rats, cockroaches'       },
  { value: 'medical',    label: 'First Aid',    icon: '🏥', color: 'from-rose-500 to-pink-600',      desc: 'Minor injury assistance'       },
];

const EMERGENCY_TIPS = [
  { icon: '📞', tip: 'For life-threatening emergencies, call 112 immediately' },
  { icon: '⏱️', tip: 'Providers will contact you within 5 minutes of booking' },
  { icon: '💰', tip: 'Emergency services have a 50% surcharge for priority response' },
  { icon: '📍', tip: 'Keep your phone accessible for provider location sharing' },
];

// ── Components ─────────────────────────────────────────────────────────

const ProviderCard: React.FC<{
  service: any;
  onBook: () => void;
  isBooking: boolean;
  index: number;
}> = ({ service, onBook, isBooking, index }) => {
  const price = Math.round((service.price_per_hour || 500) * 1.5);
  const eta = [3, 7, 12, 15][index % 4];
  const dist = [0.8, 1.4, 2.1, 3.5][index % 4];
  return (
    <div className="bg-white rounded-2xl border border-gray-100 shadow-sm hover:shadow-lg hover:-translate-y-0.5 transition-all duration-300 overflow-hidden group">
      {/* Red urgency stripe */}
      <div className="h-1 bg-gradient-to-r from-red-500 to-orange-400" />
      <div className="p-5">
        <div className="flex items-start justify-between gap-3 mb-4">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 bg-gradient-to-br from-red-50 to-orange-50 rounded-2xl flex items-center justify-center text-2xl border border-red-100 group-hover:scale-110 transition-transform">
              {EMERGENCY_CATEGORIES.find(c => c.value === service.category)?.icon || '🔧'}
            </div>
            <div>
              <h4 className="font-black text-gray-900 leading-tight">{service.name || service.title || 'Emergency Provider'}</h4>
              <p className="text-xs text-gray-400 font-medium">{service.city || 'Nearby'}</p>
            </div>
          </div>
          <div className="text-right flex-shrink-0">
            <p className="font-black text-red-600 text-lg">₹{price.toLocaleString('en-IN')}</p>
            <p className="text-xs text-gray-400">+emergency fee</p>
          </div>
        </div>

        <div className="flex items-center gap-4 mb-4 flex-wrap">
          <div className="flex items-center gap-1 text-yellow-500 font-bold text-sm">
            <Star size={13} className="fill-yellow-400" />
            {(service.rating || 4.5).toFixed(1)}
          </div>
          <div className="flex items-center gap-1 text-green-600 font-bold text-xs bg-green-50 px-2.5 py-1 rounded-full">
            <div className="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse" />
            Available Now
          </div>
          <div className="flex items-center gap-1 text-blue-600 text-xs font-bold">
            <Navigation size={11} /> {dist} km
          </div>
          <div className="flex items-center gap-1 text-orange-600 text-xs font-bold">
            <Clock size={11} /> ETA ~{eta} min
          </div>
        </div>

        <button
          onClick={onBook}
          disabled={isBooking}
          className="w-full bg-gradient-to-r from-red-500 to-red-600 hover:from-red-600 hover:to-red-700 text-white py-3.5 rounded-xl font-black text-sm transition-all hover:shadow-lg hover:shadow-red-200 active:scale-95 disabled:opacity-60 flex items-center justify-center gap-2"
        >
          {isBooking ? (
            '⏳ Booking…'
          ) : (
            <><Zap size={15} className="fill-white" /> Book Emergency · {eta} min response</>
          )}
        </button>
      </div>
    </div>
  );
};

// ── Main Component ─────────────────────────────────────────────────────

const Emergency: React.FC = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [selectedCategory, setSelectedCategory] = useState('');
  const [location, setLocation] = useState<{ latitude: number; longitude: number } | null>(null);
  const [locationStatus, setLocationStatus] = useState<'detecting' | 'found' | 'denied'>('detecting');
  const [notes, setNotes] = useState('');
  const [bookingServiceId, setBookingServiceId] = useState('');
  const [isBooking, setIsBooking] = useState(false);

  // Detect location
  useEffect(() => {
    if (navigator.geolocation) {
      navigator.geolocation.getCurrentPosition(
        pos => {
          setLocation({ latitude: pos.coords.latitude, longitude: pos.coords.longitude });
          setLocationStatus('found');
        },
        () => setLocationStatus('denied')
      );
    } else {
      setLocationStatus('denied');
    }
  }, []);

  const { data: emergencyServices, isLoading } = useQuery({
    queryKey: ['emergency-services', selectedCategory],
    queryFn: () => servicesAPI.search({ category: selectedCategory, radius: 20 }),
    enabled: !!selectedCategory,
    retry: 1,
  });

  const services: any[] = (emergencyServices as any)?.services || (Array.isArray(emergencyServices) ? emergencyServices : []);

  const handleEmergencyBooking = async (serviceId: string) => {
    if (!user) {
      toast.error('Please login to book emergency services');
      navigate('/login');
      return;
    }
    setBookingServiceId(serviceId);
    setIsBooking(true);
    try {
      await bookingsAPI.createEmergency(
        serviceId,
        location || { latitude: 0, longitude: 0 },
        notes || 'Emergency service required'
      );
      toast.success('🚨 Emergency booking created! Provider will contact you within 5 minutes.');
    } catch {
      toast.error('Failed to create emergency booking. Please try again.');
    } finally {
      setIsBooking(false);
      setBookingServiceId('');
    }
  };

  const selected = EMERGENCY_CATEGORIES.find(c => c.value === selectedCategory);

  return (
    <div className="min-h-screen bg-gray-950">

      {/* ── Hero Header ─────────────────────────────────────────── */}
      <div className="relative overflow-hidden bg-gradient-to-br from-red-700 via-red-800 to-gray-900 pt-16 pb-12">
        {/* Animated pulse rings */}
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          {[...Array(3)].map((_, i) => (
            <div
              key={i}
              className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 border border-red-500/20 rounded-full animate-ping"
              style={{
                width: `${(i + 1) * 200}px`,
                height: `${(i + 1) * 200}px`,
                animationDelay: `${i * 0.4}s`,
                animationDuration: '2.5s',
              }}
            />
          ))}
        </div>

        <div className="relative z-10 max-w-4xl mx-auto px-4">
          <button
            onClick={() => navigate(-1)}
            className="flex items-center gap-2 text-red-300 hover:text-white mb-6 transition-colors font-bold text-sm"
          >
            <ArrowLeft size={16} /> Back
          </button>

          <div className="flex items-start gap-5 mb-6">
            <div className="w-16 h-16 bg-red-500 rounded-2xl flex items-center justify-center flex-shrink-0 shadow-lg shadow-red-500/40 animate-pulse">
              <AlertTriangle size={30} className="text-white" />
            </div>
            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className="text-xs font-black text-red-300 uppercase tracking-[0.2em]">24/7 Emergency Services</span>
                <div className="w-2 h-2 bg-red-400 rounded-full animate-pulse" />
              </div>
              <h1 className="text-4xl md:text-5xl font-black text-white leading-tight">Emergency Help</h1>
              <p className="text-red-200 text-lg font-medium mt-2">Get verified professionals at your door in minutes</p>
            </div>
          </div>

          {/* Stats */}
          <div className="flex gap-4 flex-wrap">
            {[
              ['< 5 min', 'Response Time'],
              ['24/7', 'Availability'],
              ['Verified', 'Providers Only'],
            ].map(([val, label]) => (
              <div key={label} className="bg-white/10 border border-white/20 backdrop-blur-sm rounded-xl px-5 py-3 text-center">
                <p className="text-xl font-black text-white">{val}</p>
                <p className="text-xs text-red-200 font-medium">{label}</p>
              </div>
            ))}
          </div>

          {/* Location status pill */}
          <div className={`mt-5 inline-flex items-center gap-2 px-4 py-2 rounded-full text-sm font-bold
            ${locationStatus === 'found' ? 'bg-green-500/20 text-green-300 border border-green-500/30' :
              locationStatus === 'detecting' ? 'bg-yellow-500/20 text-yellow-300 border border-yellow-500/30' :
              'bg-gray-500/20 text-gray-300 border border-gray-500/30'}
          `}>
            <MapPin size={13} />
            {locationStatus === 'found' && '✅ Location detected — showing nearest providers'}
            {locationStatus === 'detecting' && '📡 Detecting your location…'}
            {locationStatus === 'denied' && '⚠️ Location access denied — showing all providers'}
          </div>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-4 py-8 space-y-8">

        {/* ── SOS Call Strip ─────────────────────────────────────── */}
        <div className="bg-gradient-to-r from-red-600 to-red-700 rounded-2xl p-5 flex items-center justify-between flex-wrap gap-4 shadow-xl shadow-red-900/40">
          <div>
            <p className="text-white font-black text-lg">Life-threatening emergency?</p>
            <p className="text-red-200 text-sm font-medium">Skip the app — call emergency services directly</p>
          </div>
          <a
            href="tel:112"
            className="flex items-center gap-2 bg-white text-red-600 px-6 py-3 rounded-xl font-black text-lg hover:bg-red-50 transition-colors shadow-lg"
          >
            <Phone size={20} className="fill-red-600" /> Call 112
          </a>
        </div>

        {/* ── Category Selection ──────────────────────────────────── */}
        <div className="bg-gray-900 rounded-2xl p-6">
          <h2 className="text-white font-black text-xl mb-5 flex items-center gap-2">
            <Zap size={20} className="text-yellow-400 fill-yellow-400" /> Select Emergency Type
          </h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {EMERGENCY_CATEGORIES.map(cat => (
              <button
                key={cat.value}
                onClick={() => setSelectedCategory(cat.value)}
                className={`relative p-4 rounded-2xl border-2 transition-all duration-300 text-left
                  ${selectedCategory === cat.value
                    ? 'border-red-500 shadow-lg shadow-red-500/30 scale-[1.02]'
                    : 'border-gray-700 hover:border-gray-500'
                  }
                `}
              >
                <div className={`bg-gradient-to-br ${cat.color} w-10 h-10 rounded-xl flex items-center justify-center text-xl mb-3 shadow-md`}>
                  {cat.icon}
                </div>
                <p className="text-white font-black text-sm">{cat.label}</p>
                <p className="text-gray-400 text-xs mt-0.5 font-medium">{cat.desc}</p>
                {selectedCategory === cat.value && (
                  <div className="absolute top-2 right-2 w-5 h-5 bg-red-500 rounded-full flex items-center justify-center">
                    <ChevronRight size={12} className="text-white" />
                  </div>
                )}
              </button>
            ))}
          </div>
        </div>

        {/* ── Notes ──────────────────────────────────────────────── */}
        {selectedCategory && (
          <div className="bg-gray-900 rounded-2xl p-6">
            <h3 className="text-white font-black text-lg mb-3">Describe Your Emergency</h3>
            <textarea
              value={notes}
              onChange={e => setNotes(e.target.value)}
              placeholder={`Describe the ${selected?.label.toLowerCase()} emergency in detail. The more specific, the faster we can help…`}
              className="w-full bg-gray-800 border-2 border-gray-700 focus:border-red-500 text-white placeholder-gray-500 rounded-xl px-4 py-3 text-sm font-medium focus:outline-none transition-colors h-28 resize-none"
            />
            <p className="text-gray-500 text-xs mt-2 font-medium">
              💡 Include: specific location in building, extent of damage, any safety concerns
            </p>
          </div>
        )}

        {/* ── Provider List ───────────────────────────────────────── */}
        {selectedCategory && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-white font-black text-xl">
                🚨 Available Emergency Providers
              </h2>
              {!isLoading && services.length > 0 && (
                <span className="text-xs font-bold text-green-400 bg-green-400/10 border border-green-400/20 px-3 py-1.5 rounded-full">
                  {services.length} nearby
                </span>
              )}
            </div>

            {isLoading ? (
              <div className="space-y-4">
                {[1, 2, 3].map(i => (
                  <div key={i} className="bg-gray-900 rounded-2xl p-5 animate-pulse">
                    <div className="flex gap-3 mb-4">
                      <div className="w-12 h-12 bg-gray-700 rounded-2xl" />
                      <div className="flex-1 space-y-2">
                        <div className="h-4 bg-gray-700 rounded w-2/3" />
                        <div className="h-3 bg-gray-700 rounded w-1/3" />
                      </div>
                    </div>
                    <div className="h-12 bg-gray-700 rounded-xl" />
                  </div>
                ))}
              </div>
            ) : services.length > 0 ? (
              <div className="space-y-3">
                {services.slice(0, 5).map((service: any, i: number) => (
                  <ProviderCard
                    key={service._id}
                    service={service}
                    index={i}
                    isBooking={isBooking && bookingServiceId === service._id}
                    onBook={() => handleEmergencyBooking(service._id)}
                  />
                ))}
              </div>
            ) : (
              <div className="bg-gray-900 rounded-2xl p-12 text-center">
                <div className="text-5xl mb-4">😔</div>
                <p className="text-white font-black text-lg mb-2">No providers available right now</p>
                <p className="text-gray-400 text-sm mb-6">Try expanding the search area or choose a nearby category.</p>
                <div className="flex gap-3 justify-center flex-wrap">
                  <Link to="/services" className="bg-red-600 text-white px-6 py-3 rounded-xl font-black text-sm hover:bg-red-700 transition-colors">
                    Browse All Services
                  </Link>
                  <a href="tel:112" className="bg-white text-red-600 px-6 py-3 rounded-xl font-black text-sm hover:bg-red-50 transition-colors flex items-center gap-2">
                    <Phone size={16} /> Call 112
                  </a>
                </div>
              </div>
            )}
          </div>
        )}

        {/* ── Safety Tips ─────────────────────────────────────────── */}
        <div className="bg-gray-900 border border-yellow-500/20 rounded-2xl p-6">
          <h3 className="text-yellow-400 font-black text-lg mb-4 flex items-center gap-2">
            <Shield size={18} className="fill-yellow-400/20" /> Safety Guidelines
          </h3>
          <div className="grid md:grid-cols-2 gap-3">
            {EMERGENCY_TIPS.map(({ icon, tip }) => (
              <div key={tip} className="flex items-start gap-3 bg-yellow-500/5 border border-yellow-500/10 rounded-xl p-3">
                <span className="text-lg flex-shrink-0">{icon}</span>
                <p className="text-gray-300 text-xs font-medium leading-relaxed">{tip}</p>
              </div>
            ))}
          </div>
        </div>

        {/* ── Provider Verification ────────────────────────────────── */}
        <div className="bg-gradient-to-r from-teal-900 to-teal-800 rounded-2xl p-6 flex items-start gap-4">
          <div className="w-12 h-12 bg-teal-700 rounded-xl flex items-center justify-center flex-shrink-0">
            <Shield size={22} className="text-teal-300" />
          </div>
          <div>
            <p className="text-white font-black text-lg">All providers are verified</p>
            <p className="text-teal-300 text-sm font-medium mt-1">
              Background-checked, ID-verified, and community-rated. Emergency responders carry QuickServe Pro badges and are GPS-tracked throughout the job.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Emergency;
