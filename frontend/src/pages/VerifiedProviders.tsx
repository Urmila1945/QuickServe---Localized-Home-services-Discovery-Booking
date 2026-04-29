import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Star, CheckCircle, RefreshCw, AlertCircle, Shield, Award } from 'lucide-react';
import ProviderBadge from '../components/verification/ProviderBadge';
import ProviderProfileModal from '../components/verification/ProviderProfileModal';
import api from '../services/api';

const VerifiedProviders: React.FC = () => {
  const navigate = useNavigate();
  const [providers, setProviders] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [stats, setStats] = useState({ total: 0, verified: 0, avgRating: 0 });
  const [viewingProviderId, setViewingProviderId] = useState<string | null>(null);

  const fetchProviders = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await api.get('/api/services/search', { params: { limit: 8, sort: 'rating' } });
      const data = res.data;
      const list = (data.services || data || []).slice(0, 8);
      setProviders(list);
      const avg = list.reduce((s: number, p: any) => s + (p.rating || 4.5), 0) / (list.length || 1);
      setStats({ total: data.total || 305764, verified: Math.floor((data.total || 305764) * 0.87), avgRating: parseFloat(avg.toFixed(1)) });
    } catch {
      setError('Unable to load providers. Please check your connection.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchProviders(); }, []);

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-gradient-to-r from-orange-500 to-red-500 text-white py-16 px-4">
        <div className="max-w-5xl mx-auto">
          <button onClick={() => navigate(-1)} className="flex items-center gap-2 text-white/80 hover:text-white mb-6 transition-colors">
            <ArrowLeft className="w-5 h-5" /> Back
          </button>
          <div className="flex items-center gap-4 mb-4">
            <div className="w-16 h-16 bg-white/20 rounded-2xl flex items-center justify-center text-4xl">✅</div>
            <div>
              <h1 className="text-4xl font-bold">Verified Providers</h1>
              <p className="text-white/80 text-lg mt-1">Background-checked, verified, and community-rated professionals</p>
            </div>
          </div>
          <div className="flex gap-6 mt-6">
            {[
              [stats.total > 0 ? `${(stats.total / 1000).toFixed(0)}K+` : '305K+', 'Total Providers'],
              [stats.verified > 0 ? `${(stats.verified / 1000).toFixed(0)}K+` : '265K+', 'Verified'],
              [stats.avgRating > 0 ? `${stats.avgRating}★` : '4.7★', 'Avg Rating'],
            ].map(([val, label]) => (
              <div key={label} className="bg-white/20 rounded-xl px-5 py-3 text-center">
                <div className="text-2xl font-bold">{val}</div>
                <div className="text-sm text-white/80">{label}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="max-w-5xl mx-auto px-4 py-12 space-y-10">

        {/* Verification Process */}
        <div className="bg-white rounded-2xl shadow-xl p-8">
          <h2 className="text-xl font-bold text-gray-900 mb-6">Our 5-Step Verification Process</h2>
          <div className="grid md:grid-cols-5 gap-4">
            {[
              { icon: '📋', step: '1', title: 'Application', desc: 'Provider submits ID, skills & experience' },
              { icon: '🔍', step: '2', title: 'Background Check', desc: 'Criminal record & identity verification' },
              { icon: '🎓', step: '3', title: 'Skill Test', desc: 'Practical assessment by our experts' },
              { icon: '📞', step: '4', title: 'Reference Check', desc: 'Past employer & client references' },
              { icon: '✅', step: '5', title: 'Approved', desc: 'Badge awarded, listed on platform' },
            ].map(({ icon, step, title, desc }) => (
              <div key={step} className="text-center">
                <div className="w-12 h-12 bg-gradient-to-br from-orange-500 to-red-500 rounded-2xl flex items-center justify-center text-xl mx-auto mb-3 shadow-md">
                  {icon}
                </div>
                <div className="text-xs font-bold text-orange-500 mb-1">STEP {step}</div>
                <h3 className="font-bold text-gray-900 text-sm mb-1">{title}</h3>
                <p className="text-xs text-gray-500">{desc}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Provider Grid */}
        <div className="bg-white rounded-2xl shadow-xl p-8">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-bold text-gray-900">Top Verified Providers</h2>
            <button onClick={fetchProviders} className="flex items-center gap-2 text-orange-600 hover:text-orange-800 font-semibold text-sm transition-colors">
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} /> Refresh
            </button>
          </div>

          {loading && (
            <div className="grid md:grid-cols-2 gap-4">
              {[...Array(8)].map((_, i) => <div key={i} className="h-24 bg-gray-100 rounded-xl animate-pulse" />)}
            </div>
          )}

          {error && !loading && (
            <div className="flex flex-col items-center gap-4 py-10 text-center">
              <AlertCircle className="w-12 h-12 text-red-400" />
              <div>
                <p className="font-semibold text-gray-700">Connection Error</p>
                <p className="text-sm text-gray-500 mt-1">{error}</p>
              </div>
              <button
                onClick={fetchProviders}
                className="flex items-center gap-2 bg-orange-500 text-white px-6 py-2 rounded-xl font-semibold hover:bg-orange-600 transition-colors"
              >
                <RefreshCw className="w-4 h-4" /> Retry
              </button>
            </div>
          )}

          {!loading && !error && providers.length > 0 && (
            <div className="grid md:grid-cols-2 gap-4">
              {providers.map((p, i) => (
                <div
                  key={i}
                  onClick={() => setViewingProviderId(p.provider_id || p._id)}
                  className="flex items-center gap-4 p-4 border-2 border-gray-100 rounded-xl hover:border-orange-200 hover:shadow-md transition-all cursor-pointer group"
                >
                  <div className="w-12 h-12 bg-gradient-to-br from-orange-400 to-red-500 rounded-full flex items-center justify-center text-white font-bold text-lg shrink-0">
                    {(p.name || 'P')[0].toUpperCase()}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <p className="font-bold text-gray-900 truncate group-hover:text-orange-600 transition-colors">
                        {p.name || p.provider_name || 'Provider'}
                      </p>
                      <CheckCircle className="w-4 h-4 text-green-500 shrink-0" />
                    </div>
                    <p className="text-sm text-gray-500">{p.category} · {p.city || p.location || 'India'}</p>
                    {(p.provider_id || p._id) && (
                      <ProviderBadge providerId={p.provider_id || p._id} variant="compact" />
                    )}
                  </div>
                  <div className="text-right shrink-0">
                    <div className="flex items-center gap-1 text-yellow-500 justify-end">
                      <Star className="w-4 h-4 fill-current" />
                      <span className="font-bold text-gray-800">{(p.rating || 4.5).toFixed(1)}</span>
                    </div>
                    <p className="text-sm font-bold text-orange-600 mt-1">₹{p.price_per_hour || 500}/hr</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Trust Badges */}
        <div className="grid md:grid-cols-3 gap-6">
          {[
            { icon: <Shield className="w-8 h-8 text-orange-500" />, title: 'Background Verified', desc: 'Every provider passes a thorough criminal background check before joining' },
            { icon: <Award className="w-8 h-8 text-yellow-500" />, title: 'Skill Certified', desc: 'Practical skill assessments ensure only qualified professionals are listed' },
            { icon: <CheckCircle className="w-8 h-8 text-green-500" />, title: 'Community Rated', desc: 'Real reviews from real customers keep quality standards high' },
          ].map(({ icon, title, desc }) => (
            <div key={title} className="bg-white rounded-2xl shadow-lg p-6 flex gap-4 items-start hover:shadow-xl transition-shadow">
              <div className="shrink-0 mt-1">{icon}</div>
              <div>
                <h3 className="font-bold text-gray-900 mb-1">{title}</h3>
                <p className="text-sm text-gray-600">{desc}</p>
              </div>
            </div>
          ))}
        </div>

        <div className="text-center">
          <button
            onClick={() => navigate('/services')}
            className="bg-gradient-to-r from-orange-500 to-red-500 text-white px-10 py-4 rounded-full font-bold text-lg hover:opacity-90 transition-all hover:scale-105 shadow-xl"
          >
            Browse Verified Providers →
          </button>
        </div>
      </div>
      {viewingProviderId && (
        <ProviderProfileModal
          providerId={viewingProviderId}
          onClose={() => setViewingProviderId(null)}
        />
      )}
    </div>
  );
};

export default VerifiedProviders;
