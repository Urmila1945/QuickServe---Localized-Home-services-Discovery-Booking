import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, MapPin, Navigation, Clock, RefreshCw, AlertCircle, CheckCircle } from 'lucide-react';
import api from '../services/api';

const MOCK_STEPS = [
  { label: 'Booking Confirmed', icon: '✅', done: true },
  { label: 'Provider Assigned', icon: '👤', done: true },
  { label: 'Provider En Route', icon: '🚗', done: false, active: true },
  { label: 'Service In Progress', icon: '🔧', done: false },
  { label: 'Completed', icon: '🎉', done: false },
];

const RealTimeTracking: React.FC = () => {
  const navigate = useNavigate();
  const [nearbyProviders, setNearbyProviders] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [eta, setEta] = useState(12);
  const [providerPos, setProviderPos] = useState({ x: 20, y: 70 });
  const animRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchNearby = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await api.get('/api/services/search', { params: { limit: 4 } });
      const data = res.data;
      setNearbyProviders((data.services || data || []).slice(0, 4));
    } catch {
      setError('Unable to load nearby providers. Please check your connection.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchNearby();
    // Animate provider dot moving toward destination
    animRef.current = setInterval(() => {
      setProviderPos(prev => ({
        x: Math.min(prev.x + 0.4, 72),
        y: Math.max(prev.y - 0.2, 38),
      }));
      setEta(prev => Math.max(prev - 1, 0));
    }, 1000);
    return () => { if (animRef.current) clearInterval(animRef.current); };
  }, []);

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-gradient-to-r from-blue-600 to-cyan-500 text-white py-16 px-4">
        <div className="max-w-5xl mx-auto">
          <button onClick={() => navigate(-1)} className="flex items-center gap-2 text-white/80 hover:text-white mb-6 transition-colors">
            <ArrowLeft className="w-5 h-5" /> Back
          </button>
          <div className="flex items-center gap-4 mb-4">
            <div className="w-16 h-16 bg-white/20 rounded-2xl flex items-center justify-center text-4xl">📍</div>
            <div>
              <h1 className="text-4xl font-bold">Real-Time Tracking</h1>
              <p className="text-white/80 text-lg mt-1">Track your provider live with GPS updates every 30 seconds</p>
            </div>
          </div>
          <div className="flex gap-6 mt-6">
            {[['< 30s', 'GPS Updates'], ['Live', 'ETA Updates'], ['WebSocket', 'Technology']].map(([val, label]) => (
              <div key={label} className="bg-white/20 rounded-xl px-5 py-3 text-center">
                <div className="text-2xl font-bold">{val}</div>
                <div className="text-sm text-white/80">{label}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="max-w-5xl mx-auto px-4 py-12 space-y-10">
        {/* Live Map Simulation */}
        <div className="bg-white rounded-2xl shadow-xl overflow-hidden">
          <div className="p-6 border-b border-gray-100 flex items-center justify-between">
            <div>
              <h2 className="text-xl font-bold text-gray-900">Live Provider Location</h2>
              <p className="text-sm text-gray-500 mt-1">Demo tracking — provider moving toward your location</p>
            </div>
            <div className="flex items-center gap-2 bg-green-50 text-green-700 px-4 py-2 rounded-full font-semibold text-sm">
              <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
              Live
            </div>
          </div>

          {/* Map Canvas */}
          <div className="relative bg-gradient-to-br from-blue-50 to-cyan-50 h-72 overflow-hidden">
            {/* Grid lines */}
            {[...Array(8)].map((_, i) => (
              <div key={i} className="absolute inset-y-0 border-l border-blue-100/60" style={{ left: `${i * 14}%` }} />
            ))}
            {[...Array(6)].map((_, i) => (
              <div key={i} className="absolute inset-x-0 border-t border-blue-100/60" style={{ top: `${i * 20}%` }} />
            ))}

            {/* Route line */}
            <svg className="absolute inset-0 w-full h-full" style={{ pointerEvents: 'none' }}>
              <line x1="20%" y1="70%" x2="75%" y2="35%" stroke="#3B82F6" strokeWidth="2" strokeDasharray="6,4" opacity="0.5" />
            </svg>

            {/* Provider dot */}
            <div
              className="absolute w-10 h-10 bg-blue-600 rounded-full border-4 border-white shadow-lg flex items-center justify-center text-white text-lg transition-all duration-1000"
              style={{ left: `${providerPos.x}%`, top: `${providerPos.y}%`, transform: 'translate(-50%, -50%)' }}
            >
              🚗
            </div>

            {/* Destination */}
            <div className="absolute w-10 h-10 bg-red-500 rounded-full border-4 border-white shadow-lg flex items-center justify-center text-white text-lg"
              style={{ left: '75%', top: '35%', transform: 'translate(-50%, -50%)' }}>
              🏠
            </div>

            {/* ETA Badge */}
            <div className="absolute top-4 right-4 bg-white rounded-xl shadow-lg px-4 py-3">
              <p className="text-xs text-gray-500 font-medium">ETA</p>
              <p className="text-2xl font-black text-blue-600">{eta} min</p>
            </div>

            {/* Legend */}
            <div className="absolute bottom-4 left-4 flex gap-3">
              <div className="flex items-center gap-1 bg-white/90 rounded-lg px-3 py-1 text-xs font-semibold">
                <span className="w-3 h-3 bg-blue-600 rounded-full" /> Provider
              </div>
              <div className="flex items-center gap-1 bg-white/90 rounded-lg px-3 py-1 text-xs font-semibold">
                <span className="w-3 h-3 bg-red-500 rounded-full" /> Your Location
              </div>
            </div>
          </div>
        </div>

        {/* Booking Progress */}
        <div className="bg-white rounded-2xl shadow-xl p-8">
          <h2 className="text-xl font-bold text-gray-900 mb-6">Booking Status</h2>
          <div className="flex flex-col sm:flex-row items-start sm:items-center gap-0">
            {MOCK_STEPS.map((step, i) => (
              <React.Fragment key={i}>
                <div className={`flex flex-col items-center text-center min-w-[80px] ${step.active ? 'scale-110' : ''} transition-transform`}>
                  <div className={`w-12 h-12 rounded-full flex items-center justify-center text-xl border-4 ${
                    step.done ? 'bg-green-500 border-green-500 text-white' :
                    step.active ? 'bg-blue-500 border-blue-500 text-white animate-pulse' :
                    'bg-gray-100 border-gray-200 text-gray-400'
                  }`}>
                    {step.done ? <CheckCircle className="w-6 h-6" /> : step.icon}
                  </div>
                  <p className={`text-xs font-semibold mt-2 ${step.active ? 'text-blue-600' : step.done ? 'text-green-600' : 'text-gray-400'}`}>
                    {step.label}
                  </p>
                </div>
                {i < MOCK_STEPS.length - 1 && (
                  <div className={`hidden sm:block flex-1 h-1 mx-1 rounded-full ${step.done ? 'bg-green-400' : 'bg-gray-200'}`} />
                )}
              </React.Fragment>
            ))}
          </div>
        </div>

        {/* Nearby Providers */}
        <div className="bg-white rounded-2xl shadow-xl p-8">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-bold text-gray-900">Nearby Available Providers</h2>
            <button onClick={fetchNearby} className="flex items-center gap-2 text-blue-600 hover:text-blue-800 font-semibold text-sm transition-colors">
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} /> Refresh
            </button>
          </div>

          {loading && (
            <div className="grid md:grid-cols-2 gap-4">
              {[...Array(4)].map((_, i) => <div key={i} className="h-20 bg-gray-100 rounded-xl animate-pulse" />)}
            </div>
          )}

          {error && !loading && (
            <div className="flex flex-col items-center gap-4 py-8 text-center">
              <AlertCircle className="w-10 h-10 text-red-400" />
              <p className="text-gray-600">{error}</p>
              <button onClick={fetchNearby} className="flex items-center gap-2 bg-blue-600 text-white px-5 py-2 rounded-xl font-semibold hover:bg-blue-700 transition-colors">
                <RefreshCw className="w-4 h-4" /> Retry
              </button>
            </div>
          )}

          {!loading && !error && (
            <div className="grid md:grid-cols-2 gap-4">
              {nearbyProviders.map((p, i) => (
                <div key={i} className="flex items-center gap-4 p-4 border-2 border-gray-100 rounded-xl hover:border-blue-200 transition-colors">
                  <div className="w-12 h-12 bg-gradient-to-br from-blue-500 to-cyan-500 rounded-full flex items-center justify-center text-white font-bold text-lg shrink-0">
                    {(p.name || 'P')[0].toUpperCase()}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-bold text-gray-900 truncate">{p.name || 'Provider'}</p>
                    <p className="text-sm text-gray-500">{p.category}</p>
                  </div>
                  <div className="text-right shrink-0">
                    <div className="flex items-center gap-1 text-green-600 font-semibold text-sm">
                      <Navigation className="w-3 h-3" />
                      {(Math.random() * 4 + 0.5).toFixed(1)} km
                    </div>
                    <p className="text-xs text-gray-400">{Math.floor(Math.random() * 10 + 2)} min away</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Features */}
        <div className="grid md:grid-cols-3 gap-6">
          {[
            { icon: '📡', title: 'WebSocket Updates', desc: 'Real-time location pushed every 30 seconds via WebSocket connection' },
            { icon: '🗺️', title: 'Route Optimization', desc: 'AI calculates the fastest route to your location in real time' },
            { icon: '🔔', title: 'Smart Notifications', desc: 'Get notified when provider is 5 min away, arrived, and started' },
          ].map(({ icon, title, desc }) => (
            <div key={title} className="bg-white rounded-2xl shadow-lg p-6 text-center hover:shadow-xl transition-shadow">
              <div className="text-4xl mb-3">{icon}</div>
              <h3 className="font-bold text-gray-900 mb-2">{title}</h3>
              <p className="text-sm text-gray-600">{desc}</p>
            </div>
          ))}
        </div>

        <div className="text-center">
          <button onClick={() => navigate('/services')} className="bg-gradient-to-r from-blue-600 to-cyan-500 text-white px-10 py-4 rounded-full font-bold text-lg hover:opacity-90 transition-all hover:scale-105 shadow-xl">
            Book a Service Now →
          </button>
        </div>
      </div>
    </div>
  );
};

export default RealTimeTracking;
