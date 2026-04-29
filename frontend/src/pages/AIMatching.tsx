import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Brain, Zap, Star, CheckCircle, RefreshCw, AlertCircle } from 'lucide-react';
import { servicesAPI } from '../services/api';

const CATEGORIES = ['plumber', 'electrician', 'house cleaning', 'ac technician', 'carpenter', 'painter', 'pest control expert', 'fitness', 'tutoring', 'appliance repair', 'bathroom cleaning', 'mobile repair technician'];

const AIMatching: React.FC = () => {
  const navigate = useNavigate();
  const [selectedService, setSelectedService] = useState('');
  const [matches, setMatches] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [recommendations, setRecommendations] = useState<any[]>([]);
  const [recLoading, setRecLoading] = useState(true);
  const [recError, setRecError] = useState('');

  const fetchRecommendations = async () => {
    setRecLoading(true);
    setRecError('');
    try {
      const data = await servicesAPI.getRecommendations();
      setRecommendations(data.slice(0, 6));
    } catch {
      setRecError('Unable to load recommendations. Please check your connection.');
    } finally {
      setRecLoading(false);
    }
  };

  useEffect(() => { fetchRecommendations(); }, []);

  const handleSmartMatch = async () => {
    if (!selectedService) return;
    setLoading(true);
    setError('');
    setMatches([]);
    try {
      const data = await servicesAPI.search({
        category: selectedService,
        limit: 5
      });
      const results = data.services || [];
      if (results.length === 0) throw new Error('No providers found');
      setMatches(results);
    } catch {
      setError('Could not find matches. Try a different service or check your connection.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-gradient-to-r from-purple-600 to-pink-600 text-white py-16 px-4">
        <div className="max-w-5xl mx-auto">
          <button onClick={() => navigate(-1)} className="flex items-center gap-2 text-white/80 hover:text-white mb-6 transition-colors">
            <ArrowLeft className="w-5 h-5" /> Back
          </button>
          <div className="flex items-center gap-4 mb-4">
            <div className="w-16 h-16 bg-white/20 rounded-2xl flex items-center justify-center text-4xl">🤖</div>
            <div>
              <h1 className="text-4xl font-bold">AI-Powered Matching</h1>
              <p className="text-white/80 text-lg mt-1">Smart algorithms find your perfect provider in seconds</p>
            </div>
          </div>
          <div className="flex gap-6 mt-6">
            {[['99%', 'Match Accuracy'], ['< 2min', 'Response Time'], ['305K+', 'Providers']].map(([val, label]) => (
              <div key={label} className="bg-white/20 rounded-xl px-5 py-3 text-center">
                <div className="text-2xl font-bold">{val}</div>
                <div className="text-sm text-white/80">{label}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="max-w-5xl mx-auto px-4 py-12 space-y-12">
        {/* Smart Match Tool */}
        <div className="bg-white rounded-2xl shadow-xl p-8">
          <div className="flex items-center gap-3 mb-6">
            <Brain className="w-7 h-7 text-purple-600" />
            <h2 className="text-2xl font-bold text-gray-900">Find Your Perfect Match</h2>
          </div>
          <div className="flex flex-col sm:flex-row gap-4">
            <select
              value={selectedService}
              onChange={e => setSelectedService(e.target.value)}
              className="flex-1 border-2 border-gray-200 rounded-xl px-4 py-3 text-gray-800 focus:outline-none focus:border-purple-500 font-medium"
            >
              <option value="">Select a service category...</option>
              {CATEGORIES.map(c => (
                <option key={c} value={c}>{c.charAt(0).toUpperCase() + c.slice(1)}</option>
              ))}
            </select>
            <button
              onClick={handleSmartMatch}
              disabled={!selectedService || loading}
              className="bg-gradient-to-r from-purple-600 to-pink-600 text-white px-8 py-3 rounded-xl font-bold hover:opacity-90 disabled:opacity-50 transition-all flex items-center gap-2"
            >
              {loading ? <RefreshCw className="w-5 h-5 animate-spin" /> : <Zap className="w-5 h-5" />}
              {loading ? 'Matching...' : 'Smart Match'}
            </button>
          </div>

          {error && (
            <div className="mt-4 flex items-center gap-3 bg-red-50 border border-red-200 rounded-xl p-4 text-red-700">
              <AlertCircle className="w-5 h-5 shrink-0" />
              <span>{error}</span>
              <button onClick={handleSmartMatch} className="ml-auto text-sm font-semibold underline">Retry</button>
            </div>
          )}

          {matches.length > 0 && (
            <div className="mt-6 space-y-3">
              <p className="text-sm font-semibold text-gray-500 uppercase tracking-wide">Top Matches</p>
              {matches.map((m, i) => (
                <div key={i} className="flex items-center gap-4 p-4 border-2 border-purple-100 rounded-xl hover:border-purple-300 transition-colors">
                  <div className="w-10 h-10 bg-gradient-to-br from-purple-500 to-pink-500 rounded-full flex items-center justify-center text-white font-bold shrink-0">
                    #{i + 1}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-bold text-gray-900 truncate">{m.name || m.provider_name || 'Provider'}</p>
                    <p className="text-sm text-gray-500">{m.category} · {m.city || m.location}</p>
                  </div>
                  <div className="flex items-center gap-1 text-yellow-500 shrink-0">
                    <Star className="w-4 h-4 fill-current" />
                    <span className="font-bold text-gray-800">{(m.rating || 4.5).toFixed(1)}</span>
                  </div>
                  <div className="text-right shrink-0">
                    <p className="font-bold text-purple-600">₹{m.price_per_hour || m.hourly_rate || 500}/hr</p>
                  </div>
                  <button
                    onClick={() => navigate(`/services?q=${m.category}&city=${m.city || ''}`)}
                    className="bg-purple-600 text-white px-4 py-2 rounded-lg text-sm font-semibold hover:bg-purple-700 transition-colors shrink-0"
                  >
                    Book
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* AI Recommendations */}
        <div className="bg-white rounded-2xl shadow-xl p-8">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="text-2xl font-bold text-gray-900">AI-Smart Match</h2>
              <p className="text-gray-500 mt-1">Our algorithms analyzed your history and preferences to find these perfect matches.</p>
            </div>
            <button onClick={fetchRecommendations} className="flex items-center gap-2 text-purple-600 hover:text-purple-800 font-semibold transition-colors">
              <RefreshCw className={`w-4 h-4 ${recLoading ? 'animate-spin' : ''}`} /> Refresh
            </button>
          </div>

          {recLoading && (
            <div className="grid md:grid-cols-3 gap-4">
              {[...Array(6)].map((_, i) => (
                <div key={i} className="h-32 bg-gray-100 rounded-xl animate-pulse" />
              ))}
            </div>
          )}

          {recError && !recLoading && (
            <div className="flex flex-col items-center gap-4 py-10 text-center">
              <AlertCircle className="w-12 h-12 text-red-400" />
              <div>
                <p className="font-semibold text-gray-700">Connection Error</p>
                <p className="text-sm text-gray-500 mt-1">{recError}</p>
              </div>
              <button
                onClick={fetchRecommendations}
                className="flex items-center gap-2 bg-purple-600 text-white px-6 py-2 rounded-xl font-semibold hover:bg-purple-700 transition-colors"
              >
                <RefreshCw className="w-4 h-4" /> Retry
              </button>
            </div>
          )}

          {!recLoading && !recError && recommendations.length > 0 && (
            <div className="grid md:grid-cols-3 gap-4">
              {recommendations.map((rec, i) => (
                <div
                  key={i}
                  onClick={() => navigate(`/services?q=${rec.category}`)}
                  className="border-2 border-gray-100 rounded-xl p-5 hover:border-purple-300 hover:shadow-md transition-all cursor-pointer group"
                >
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-xs font-bold uppercase tracking-wide text-purple-600 bg-purple-50 px-2 py-1 rounded-full">
                      {rec.category}
                    </span>
                    <div className="flex items-center gap-1 text-yellow-500">
                      <Star className="w-3 h-3 fill-current" />
                      <span className="text-xs font-bold text-gray-700">{(rec.rating || 4.5).toFixed(1)}</span>
                    </div>
                  </div>
                  <p className="font-bold text-gray-900 truncate group-hover:text-purple-700 transition-colors">
                    {rec.name || rec.provider_name || 'Provider'}
                  </p>
                  <p className="text-sm text-gray-500 mt-1">{rec.city || rec.location || 'India'}</p>
                  <p className="text-purple-600 font-bold mt-2">₹{rec.price_per_hour || 500}/hr</p>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* How It Works */}
        <div className="bg-gradient-to-br from-purple-50 to-pink-50 rounded-2xl p-8">
          <h2 className="text-2xl font-bold text-gray-900 mb-6">How AI Matching Works</h2>
          <div className="grid md:grid-cols-3 gap-6">
            {[
              { step: '01', title: 'Analyze Your Needs', desc: 'AI reads your service request, location, budget, and past preferences', icon: '🧠' },
              { step: '02', title: 'Score 305K+ Providers', desc: 'Each provider is scored on rating, proximity, availability, and specialization', icon: '⚡' },
              { step: '03', title: 'Deliver Top Matches', desc: 'You get the top 5 best-fit providers ranked by our match score', icon: '🎯' },
            ].map(({ step, title, desc, icon }) => (
              <div key={step} className="bg-white rounded-xl p-6 shadow-sm">
                <div className="flex items-center gap-3 mb-3">
                  <span className="text-3xl">{icon}</span>
                  <span className="text-sm font-bold text-purple-400">STEP {step}</span>
                </div>
                <h3 className="font-bold text-gray-900 mb-2">{title}</h3>
                <p className="text-sm text-gray-600">{desc}</p>
              </div>
            ))}
          </div>
        </div>

        {/* CTA */}
        <div className="text-center">
          <button
            onClick={() => navigate('/services')}
            className="bg-gradient-to-r from-purple-600 to-pink-600 text-white px-10 py-4 rounded-full font-bold text-lg hover:opacity-90 transition-all hover:scale-105 shadow-xl"
          >
            Browse All Services →
          </button>
        </div>
      </div>
    </div>
  );
};

export default AIMatching;
