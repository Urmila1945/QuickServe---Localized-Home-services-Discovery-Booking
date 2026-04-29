import React, { useState, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { surgeAPI, servicesAPI } from '../services/api';
import toast from 'react-hot-toast';
import {
  Calculator, Zap, MapPin, Clock, TrendingUp, TrendingDown, AlertTriangle,
  ArrowRight, RefreshCw, Loader2, CheckCircle, ChevronDown, Info, Star,
  Shield, Wrench, Droplets, Wind, BookOpen, Package, Sparkles, Heart, Car,
} from 'lucide-react';

// ── Types ──────────────────────────────────────────────────────────────
interface PriceResult {
  service_type: string;
  base_price: number;
  surge_multiplier: number;
  final_price: number;
  factors: { factor: string; multiplier: number }[];
  savings_tip: string | null;
}

// ── Constants ──────────────────────────────────────────────────────────
const SERVICE_OPTIONS = [
  { value: 'plumbing',    label: 'Plumbing',      icon: Droplets,  baseRange: '₹400–₹800'  },
  { value: 'electrical',  label: 'Electrical',    icon: Zap,       baseRange: '₹500–₹900'  },
  { value: 'cleaning',    label: 'Cleaning',      icon: Sparkles,  baseRange: '₹250–₹500'  },
  { value: 'repair',      label: 'Appliance Repair', icon: Wrench, baseRange: '₹350–₹700' },
  { value: 'beauty',      label: 'Beauty & Salon',icon: Heart,     baseRange: '₹300–₹600'  },
  { value: 'fitness',     label: 'Fitness',       icon: Star,      baseRange: '₹600–₹1200' },
  { value: 'delivery',    label: 'Delivery',      icon: Package,   baseRange: '₹80–₹200'   },
  { value: 'carpentry',   label: 'Carpentry',     icon: Wrench,    baseRange: '₹400–₹800'  },
];

const URGENCY_OPTIONS = [
  { value: 'normal',    label: 'Normal',    desc: 'Schedule for later',       icon: '📅', color: 'from-green-500 to-emerald-600',  badge: 'bg-green-100 text-green-700'  },
  { value: 'urgent',    label: 'Urgent',    desc: 'Within 2–4 hours',         icon: '⚡', color: 'from-orange-500 to-amber-600',   badge: 'bg-orange-100 text-orange-700' },
  { value: 'emergency', label: 'Emergency', desc: 'Within 30–60 minutes',     icon: '🚨', color: 'from-red-500 to-rose-600',       badge: 'bg-red-100 text-red-700'       },
];

const HOUSE_SIZES = [
  { value: 0.8, label: '1 BHK / Small',    sqft: '< 600 sqft',  icon: '🏠' },
  { value: 1.0, label: '2 BHK / Medium',   sqft: '600–1200 sqft', icon: '🏡' },
  { value: 1.3, label: '3 BHK / Large',    sqft: '1200–1800 sqft', icon: '🏘️' },
  { value: 1.6, label: 'Villa / XL',       sqft: '> 1800 sqft',   icon: '🏰' },
];

const CITIES = ['Mumbai', 'Delhi', 'Bangalore', 'Hyderabad', 'Chennai', 'Kolkata', 'Pune', 'Ahmedabad'];

// ── Helpers ────────────────────────────────────────────────────────────
const formatINR = (amount: number) =>
  new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(amount);

// ── Sub-components ─────────────────────────────────────────────────────
const SelectCard: React.FC<{
  selected: boolean;
  onClick: () => void;
  icon: React.ElementType;
  label: string;
  sub?: string;
  badge?: string;
  badgeColor?: string;
}> = ({ selected, onClick, icon: Icon, label, sub, badge, badgeColor = 'bg-teal-100 text-teal-700' }) => (
  <button
    onClick={onClick}
    className={`flex items-center gap-3 p-4 rounded-2xl border-2 transition-all duration-200 text-left w-full
      ${selected
        ? 'border-teal-500 bg-teal-50 shadow-lg shadow-teal-100'
        : 'border-gray-100 bg-white hover:border-teal-200 hover:shadow-md'}`}
  >
    <div className={`w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 ${selected ? 'bg-teal-600 text-white' : 'bg-gray-100 text-gray-500'}`}>
      <Icon size={18} />
    </div>
    <div className="flex-1 min-w-0">
      <p className={`font-bold text-sm ${selected ? 'text-teal-800' : 'text-gray-800'}`}>{label}</p>
      {sub && <p className="text-xs text-gray-400 mt-0.5">{sub}</p>}
    </div>
    {badge && (
      <span className={`text-[10px] font-black px-2 py-1 rounded-full ${badgeColor}`}>{badge}</span>
    )}
    {selected && <CheckCircle size={16} className="text-teal-600 flex-shrink-0" />}
  </button>
);

// ── Main Component ─────────────────────────────────────────────────────
const PriceEstimator: React.FC = () => {
  const [service, setService]     = useState('cleaning');
  const [urgency, setUrgency]     = useState('normal');
  const [houseSize, setHouseSize] = useState(1.0);
  const [city, setCity]           = useState('Mumbai');
  const [result, setResult]       = useState<PriceResult | null>(null);
  const [loading, setLoading]     = useState(false);
  const [showPredictions, setShowPredictions] = useState(false);

  // 24-hour predictions
  const { data: predictions, isFetching: predictionsLoading } = useQuery({
    queryKey: ['surge-predictions', service],
    queryFn: () => surgeAPI.getPredictions(),
    enabled: showPredictions,
    staleTime: 5 * 60 * 1000,
  });

  const estimate = useCallback(async () => {
    setLoading(true);
    try {
      const res = await surgeAPI.calculate({
        service_type: service,
        location: { lat: 12.97, lng: 77.59 },
        urgency,
      });
      // Apply house size multiplier client-side
      const adjusted: PriceResult = {
        ...res,
        final_price: Math.round(res.final_price * houseSize),
        base_price: Math.round(res.base_price * houseSize),
      };
      setResult(adjusted);
      toast.success('Price estimate ready!');
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || 'Could not calculate price. Please try again.');
    } finally {
      setLoading(false);
    }
  }, [service, urgency, houseSize]);

  const selectedService = SERVICE_OPTIONS.find(s => s.value === service);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-teal-50 to-blue-50">
      {/* Header */}
      <div className="bg-gradient-to-r from-teal-700 via-teal-600 to-emerald-600 text-white py-16 px-6 relative overflow-hidden">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,rgba(255,255,255,0.1),transparent_60%)]" />
        <div className="max-w-4xl mx-auto relative z-10 text-center">
          <div className="flex items-center justify-center gap-3 mb-4">
            <div className="w-14 h-14 bg-white/20 rounded-2xl flex items-center justify-center backdrop-blur-sm">
              <Calculator size={28} className="text-white" />
            </div>
          </div>
          <h1 className="text-4xl md:text-5xl font-black mb-4 tracking-tight">
            AI Price Estimator
          </h1>
          <p className="text-teal-100 text-lg max-w-xl mx-auto">
            Get instant, real-time price estimates powered by dynamic surge pricing — before you book.
          </p>
          <div className="flex items-center justify-center gap-6 mt-6 flex-wrap">
            {[
              { icon: Shield,     label: 'Transparent Pricing' },
              { icon: Zap,        label: 'Real-time Rates'    },
              { icon: TrendingUp, label: 'Dynamic AI Model'   },
            ].map(({ icon: Icon, label }) => (
              <div key={label} className="flex items-center gap-2 text-sm text-teal-200 font-medium">
                <Icon size={16} className="text-teal-300" />
                {label}
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="max-w-5xl mx-auto px-4 py-10 -mt-6">
        <div className="grid lg:grid-cols-3 gap-6">

          {/* ── LEFT: Configurator ─────────────────────────────────── */}
          <div className="lg:col-span-2 space-y-6">

            {/* Step 1: Service */}
            <div className="bg-white rounded-3xl shadow-sm border border-gray-100 p-6">
              <h2 className="font-black text-gray-900 text-lg mb-1 flex items-center gap-2">
                <span className="w-7 h-7 bg-teal-600 text-white rounded-full text-xs font-black flex items-center justify-center">1</span>
                Select Service
              </h2>
              <p className="text-sm text-gray-400 mb-4 ml-9">What service do you need?</p>
              <div className="grid grid-cols-2 gap-2">
                {SERVICE_OPTIONS.map(opt => (
                  <SelectCard
                    key={opt.value}
                    selected={service === opt.value}
                    onClick={() => setService(opt.value)}
                    icon={opt.icon}
                    label={opt.label}
                    sub={opt.baseRange}
                  />
                ))}
              </div>
            </div>

            {/* Step 2: Urgency */}
            <div className="bg-white rounded-3xl shadow-sm border border-gray-100 p-6">
              <h2 className="font-black text-gray-900 text-lg mb-1 flex items-center gap-2">
                <span className="w-7 h-7 bg-teal-600 text-white rounded-full text-xs font-black flex items-center justify-center">2</span>
                Urgency Level
              </h2>
              <p className="text-sm text-gray-400 mb-4 ml-9">Higher urgency = faster arrival + higher cost</p>
              <div className="grid grid-cols-3 gap-3">
                {URGENCY_OPTIONS.map(opt => (
                  <button
                    key={opt.value}
                    onClick={() => setUrgency(opt.value)}
                    className={`p-4 rounded-2xl border-2 text-center transition-all duration-200
                      ${urgency === opt.value
                        ? 'border-teal-500 bg-teal-50 shadow-lg shadow-teal-100'
                        : 'border-gray-100 bg-white hover:border-teal-200'}`}
                  >
                    <div className="text-3xl mb-2">{opt.icon}</div>
                    <p className={`font-black text-sm ${urgency === opt.value ? 'text-teal-800' : 'text-gray-800'}`}>{opt.label}</p>
                    <p className="text-[11px] text-gray-400 mt-0.5">{opt.desc}</p>
                    {urgency === opt.value && (
                      <span className={`inline-block text-[10px] font-black px-2 py-0.5 rounded-full mt-2 ${opt.badge}`}>Selected</span>
                    )}
                  </button>
                ))}
              </div>
            </div>

            {/* Step 3: House Size + City */}
            <div className="bg-white rounded-3xl shadow-sm border border-gray-100 p-6">
              <h2 className="font-black text-gray-900 text-lg mb-1 flex items-center gap-2">
                <span className="w-7 h-7 bg-teal-600 text-white rounded-full text-xs font-black flex items-center justify-center">3</span>
                Property Size & Location
              </h2>
              <p className="text-sm text-gray-400 mb-4 ml-9">Affects scope and travel time</p>

              <div className="grid grid-cols-2 gap-3 mb-4">
                {HOUSE_SIZES.map(opt => (
                  <button
                    key={opt.value}
                    onClick={() => setHouseSize(opt.value)}
                    className={`flex items-center gap-3 p-4 rounded-2xl border-2 transition-all duration-200 text-left
                      ${houseSize === opt.value
                        ? 'border-teal-500 bg-teal-50'
                        : 'border-gray-100 bg-white hover:border-teal-200'}`}
                  >
                    <span className="text-2xl">{opt.icon}</span>
                    <div>
                      <p className={`font-bold text-sm ${houseSize === opt.value ? 'text-teal-800' : 'text-gray-800'}`}>{opt.label}</p>
                      <p className="text-xs text-gray-400">{opt.sqft}</p>
                    </div>
                  </button>
                ))}
              </div>

              <div className="flex items-center gap-3 bg-gray-50 rounded-2xl px-4 py-3">
                <MapPin size={18} className="text-teal-600 flex-shrink-0" />
                <select
                  value={city}
                  onChange={e => setCity(e.target.value)}
                  className="flex-1 bg-transparent text-sm font-medium text-gray-800 focus:outline-none"
                >
                  {CITIES.map(c => <option key={c} value={c}>{c}</option>)}
                </select>
              </div>
            </div>

            {/* Estimate Button */}
            <button
              onClick={estimate}
              disabled={loading}
              className="w-full bg-gradient-to-r from-teal-600 to-emerald-600 hover:from-teal-700 hover:to-emerald-700 text-white py-5 rounded-2xl font-black text-lg transition-all duration-200 hover:shadow-lg hover:shadow-teal-200 disabled:opacity-60 disabled:cursor-not-allowed flex items-center justify-center gap-3"
            >
              {loading ? (
                <><Loader2 size={22} className="animate-spin" /> Calculating…</>
              ) : (
                <><Calculator size={22} /> Calculate My Price Estimate</>
              )}
            </button>
          </div>

          {/* ── RIGHT: Result Panel ────────────────────────────────── */}
          <div className="space-y-4">

            {/* Result Card */}
            {result ? (
              <div className="bg-white rounded-3xl shadow-lg border border-gray-100 overflow-hidden sticky top-6">
                <div className="bg-gradient-to-br from-teal-600 to-emerald-700 p-6 text-white">
                  <p className="text-teal-200 text-xs font-black uppercase tracking-widest mb-1">Estimated Cost</p>
                  <p className="text-5xl font-black">{formatINR(result.final_price)}</p>
                  <p className="text-teal-200 text-sm mt-1">
                    Base: {formatINR(result.base_price)} · Surge: {result.surge_multiplier}×
                  </p>
                </div>

                <div className="p-5 space-y-3">
                  {/* Factors */}
                  {result.factors.length > 0 && (
                    <div>
                      <p className="text-xs font-black text-gray-400 uppercase tracking-widest mb-2">Pricing Factors</p>
                      <div className="space-y-2">
                        {result.factors.map((f, i) => (
                          <div key={i} className="flex items-center justify-between bg-orange-50 rounded-xl px-3 py-2">
                            <span className="text-xs font-bold text-orange-700">{f.factor}</span>
                            <span className="text-xs font-black text-orange-600">+{Math.round((f.multiplier - 1) * 100)}%</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Savings tip */}
                  {result.savings_tip && (
                    <div className="flex items-start gap-2 bg-blue-50 rounded-xl p-3">
                      <Info size={14} className="text-blue-500 flex-shrink-0 mt-0.5" />
                      <p className="text-xs font-medium text-blue-700">{result.savings_tip}</p>
                    </div>
                  )}

                  {/* Low surge badge */}
                  {result.surge_multiplier <= 1.0 && (
                    <div className="flex items-center gap-2 bg-green-50 rounded-xl p-3">
                      <TrendingDown size={14} className="text-green-600" />
                      <p className="text-xs font-bold text-green-700">Great time to book — no surge pricing!</p>
                    </div>
                  )}

                  <Link
                    to={`/services?q=${selectedService?.label}`}
                    className="flex items-center justify-center gap-2 w-full bg-teal-600 hover:bg-teal-700 text-white py-3 rounded-xl font-black text-sm transition-all mt-2"
                  >
                    Book Now <ArrowRight size={16} />
                  </Link>

                  <button
                    onClick={estimate}
                    className="flex items-center justify-center gap-2 w-full bg-gray-50 hover:bg-gray-100 text-gray-600 py-3 rounded-xl font-bold text-sm transition-all border border-gray-100"
                  >
                    <RefreshCw size={14} /> Recalculate
                  </button>
                </div>
              </div>
            ) : (
              <div className="bg-white rounded-3xl shadow-sm border border-gray-100 p-8 text-center sticky top-6">
                <div className="w-20 h-20 bg-teal-50 rounded-3xl flex items-center justify-center mx-auto mb-4">
                  <Calculator size={36} className="text-teal-400" />
                </div>
                <p className="font-black text-gray-700 mb-2">Ready to Estimate</p>
                <p className="text-sm text-gray-400">Configure your service requirements on the left and click Calculate.</p>
              </div>
            )}

            {/* 24-hr Price Prediction */}
            <div className="bg-white rounded-3xl shadow-sm border border-gray-100 p-5">
              <button
                onClick={() => setShowPredictions(p => !p)}
                className="w-full flex items-center justify-between font-black text-gray-900"
              >
                <span className="flex items-center gap-2">
                  <TrendingUp size={16} className="text-purple-500" />
                  24-Hour Price Forecast
                </span>
                <ChevronDown size={16} className={`text-gray-400 transition-transform ${showPredictions ? 'rotate-180' : ''}`} />
              </button>

              {showPredictions && (
                <div className="mt-4">
                  {predictionsLoading ? (
                    <div className="flex justify-center py-4"><Loader2 size={20} className="animate-spin text-teal-500" /></div>
                  ) : predictions?.predictions ? (
                    <div className="space-y-1.5 max-h-60 overflow-y-auto pr-1">
                      {predictions.predictions.slice(0, 12).map((p: any, i: number) => {
                        const pct = Math.round((p.multiplier - 1) * 100);
                        const barColor = p.demand_level === 'high' ? 'bg-red-400' : p.demand_level === 'medium' ? 'bg-orange-400' : 'bg-green-400';
                        return (
                          <div key={i} className="flex items-center gap-2 text-xs">
                            <span className="w-12 font-mono text-gray-500 flex-shrink-0">
                              {String(p.hour).padStart(2, '0')}:00
                            </span>
                            <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
                              <div className={`h-full ${barColor} rounded-full`} style={{ width: `${Math.min(p.multiplier * 50, 100)}%` }} />
                            </div>
                            <span className={`w-10 font-black text-right ${pct > 0 ? 'text-red-500' : 'text-green-600'}`}>
                              {pct > 0 ? `+${pct}%` : `${pct}%`}
                            </span>
                          </div>
                        );
                      })}
                    </div>
                  ) : (
                    <p className="text-sm text-gray-400 text-center py-3">No predictions available.</p>
                  )}
                </div>
              )}
            </div>

            {/* How it works */}
            <div className="bg-gradient-to-br from-teal-50 to-blue-50 rounded-3xl p-5 border border-teal-100">
              <p className="font-black text-gray-900 mb-3 text-sm flex items-center gap-2">
                <Info size={14} className="text-teal-500" /> How We Calculate
              </p>
              <ul className="space-y-2 text-xs text-gray-600">
                {['Base price by service category', 'Real-time demand from active bookings', 'Time-of-day and weekend factors', 'Provider availability ratio', 'Your urgency level preference'].map(item => (
                  <li key={item} className="flex items-center gap-2">
                    <CheckCircle size={11} className="text-teal-500 flex-shrink-0" />
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default PriceEstimator;
