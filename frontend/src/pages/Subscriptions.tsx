import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import toast from 'react-hot-toast';
import {
  CheckCircle, XCircle, Zap, Crown, Shield, Star, ArrowRight, Gift,
  Sparkles, Clock, Users, RefreshCw, Lock, HeartHandshake, TrendingDown,
  BadgeCheck, Calendar, Bot, Award,
} from 'lucide-react';

// ── Types ──────────────────────────────────────────────────────────────
interface Plan {
  id: string;
  name: string;
  emoji: string;
  tagline: string;
  price: number;
  annualPrice: number;
  color: string;
  bgGrad: string;
  icon: React.ElementType;
  badge?: string;
  features: { label: string; included: boolean; highlight?: boolean }[];
  serviceCredits: number;
  priority: string;
  ai: string;
}

// ── Plan Data ─────────────────────────────────────────────────────────
const PLANS: Plan[] = [
  {
    id: 'basic',
    name: 'Basic',
    emoji: '🏠',
    tagline: 'For occasional home care needs',
    price: 299,
    annualPrice: 2499,
    color: 'from-blue-500 to-cyan-600',
    bgGrad: 'from-blue-50 to-cyan-50',
    icon: Shield,
    serviceCredits: 1,
    priority: 'Standard queue',
    ai: 'Basic chatbot',
    features: [
      { label: '1 free service/month (up to ₹500)', included: true, highlight: true },
      { label: '5% discount on all bookings',         included: true  },
      { label: 'Standard queue priority',              included: true  },
      { label: 'Basic AI chatbot support',             included: true  },
      { label: 'Email support',                        included: true  },
      { label: 'Surge price protection',               included: false },
      { label: 'Priority matching',                    included: false },
      { label: 'VIP provider access',                  included: false },
      { label: 'Monthly home health report',           included: false },
    ],
  },
  {
    id: 'pro',
    name: 'Pro',
    emoji: '⚡',
    tagline: 'For busy homeowners who need more',
    price: 699,
    annualPrice: 5999,
    color: 'from-teal-500 to-emerald-600',
    bgGrad: 'from-teal-50 to-emerald-50',
    icon: Zap,
    badge: 'Most Popular',
    serviceCredits: 3,
    priority: 'Priority queue',
    ai: 'Advanced AI concierge',
    features: [
      { label: '3 free services/month (up to ₹800 each)', included: true, highlight: true },
      { label: '15% discount on all bookings',              included: true, highlight: true },
      { label: 'Priority queue — skip the wait',            included: true  },
      { label: 'Advanced AI concierge',                     included: true  },
      { label: '24/7 phone + chat support',                 included: true  },
      { label: 'Surge price capped at 1.2×',               included: true, highlight: true },
      { label: 'Priority provider matching',                included: true  },
      { label: 'VIP provider access',                       included: false },
      { label: 'Monthly home health report',                included: true  },
    ],
  },
  {
    id: 'elite',
    name: 'Elite',
    emoji: '👑',
    tagline: 'The complete white-glove experience',
    price: 1499,
    annualPrice: 12999,
    color: 'from-purple-600 to-pink-600',
    bgGrad: 'from-purple-50 to-pink-50',
    icon: Crown,
    badge: 'Best Value',
    serviceCredits: 8,
    priority: 'Emergency priority',
    ai: 'Personal AI concierge',
    features: [
      { label: '8 free services/month (up to ₹1500 each)', included: true, highlight: true },
      { label: '25% discount on all bookings',              included: true, highlight: true },
      { label: 'Emergency priority — 30-min response',      included: true, highlight: true },
      { label: 'Personal AI concierge + scheduling',        included: true  },
      { label: 'Dedicated account manager',                 included: true  },
      { label: 'Surge pricing completely eliminated',        included: true, highlight: true },
      { label: 'VIP-only premium providers',                included: true  },
      { label: 'Weekly home health report',                  included: true  },
      { label: 'Free annual home inspection',               included: true, highlight: true },
    ],
  },
];

const PERKS = [
  { icon: TrendingDown, title: 'Surge Shield',        desc: 'Never pay peak prices during bad weather or high demand periods.',      color: 'text-blue-600',   bg: 'bg-blue-50'   },
  { icon: Calendar,     title: 'Auto-Schedule',        desc: 'AI automatically books recurring services (cleaning, pest control…).',  color: 'text-teal-600',   bg: 'bg-teal-50'   },
  { icon: Bot,          title: 'AI Concierge',         desc: 'Your personal assistant remembers preferences and handles rebooks.',     color: 'text-purple-600', bg: 'bg-purple-50' },
  { icon: BadgeCheck,   title: 'Verified VIPs',        desc: 'Access top-rated providers with exclusive availability windows.',        color: 'text-orange-600', bg: 'bg-orange-50' },
  { icon: HeartHandshake,title:'Satisfaction Guarantee',desc: 'Not happy? We rebook at no cost. Every time. No questions asked.',     color: 'text-pink-600',   bg: 'bg-pink-50'   },
  { icon: Award,        title: '2× Loyalty Points',    desc: 'Subscribers earn double Local Hero Points on every booking.',           color: 'text-yellow-600', bg: 'bg-yellow-50' },
];

// ── Main Component ─────────────────────────────────────────────────────
const Subscriptions: React.FC = () => {
  const { user } = useAuth();
  const [annual, setAnnual]         = useState(false);
  const [activePlan, setActivePlan] = useState<string | null>(null);
  const [loading, setLoading]       = useState<string | null>(null);
  const [showPayment, setShowPayment] = useState<Plan | null>(null);

  const handleSubscribeClick = (plan: Plan) => {
    if (!user) {
      toast.error('Please log in to subscribe');
      return;
    }
    setShowPayment(plan);
  };

  const handleProcessPayment = async () => {
    if (!showPayment) return;
    setLoading(showPayment.id);
    await new Promise(r => setTimeout(r, 1500)); // simulate payment gateway
    setActivePlan(showPayment.id);
    setLoading(null);
    toast.success(`🎉 Payment Successful! Welcome to QuickServe ${showPayment.name}.`);
    setShowPayment(null);
  };

  return (
    <div className="min-h-screen bg-white">
      {showPayment && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
          <div className="bg-white rounded-3xl shadow-2xl w-full max-w-md overflow-hidden relative">
            <button 
              onClick={() => setShowPayment(null)}
              className="absolute top-4 right-4 p-2 text-gray-400 hover:text-gray-600 bg-gray-100 hover:bg-gray-200 rounded-full transition-colors z-20"
            >
              <XCircle size={20} />
            </button>
            <div className="p-8">
              <div className="text-center mb-6">
                <div className={`w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-4 bg-gradient-to-br ${showPayment.color}`}>
                   <showPayment.icon size={28} className="text-white" />
                </div>
                <h3 className="text-2xl font-black text-gray-900">Complete Payment</h3>
                <p className="text-gray-500 text-sm mt-1">Subscribe to {showPayment.name} Plan</p>
              </div>
              
              <div className="bg-gray-50 rounded-2xl p-4 mb-6 border border-gray-100 flex justify-between items-center">
                <span className="font-bold text-gray-700">Total to pay:</span>
                <span className="text-xl font-black text-primary-dark">
                  ₹{annual ? showPayment.annualPrice.toLocaleString() : showPayment.price.toLocaleString()}
                </span>
              </div>
              
              <div className="space-y-4 mb-8">
                <div>
                  <label className="block text-xs font-bold text-gray-500 uppercase tracking-wide mb-1">Card Number</label>
                  <input type="text" placeholder="XXXX XXXX XXXX XXXX" className="w-full bg-white border border-gray-200 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary font-mono" defaultValue="4242 4242 4242 4242" />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-bold text-gray-500 uppercase tracking-wide mb-1">Expiry</label>
                    <input type="text" placeholder="MM/YY" className="w-full bg-white border border-gray-200 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary font-mono" defaultValue="12/25" />
                  </div>
                  <div>
                    <label className="block text-xs font-bold text-gray-500 uppercase tracking-wide mb-1">CVV</label>
                    <input type="text" placeholder="XXX" className="w-full bg-white border border-gray-200 rounded-xl px-4 py-3 text-sm focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary font-mono" defaultValue="123" />
                  </div>
                </div>
              </div>
              
              <button
                onClick={handleProcessPayment}
                disabled={loading === showPayment.id}
                className="w-full bg-primary hover:bg-primary-dark text-white py-4 rounded-xl font-black text-lg transition-all shadow-lg active:scale-95 flex justify-center items-center gap-2 disabled:opacity-70"
              >
                {loading === showPayment.id ? <><RefreshCw className="animate-spin" size={20} /> Processing...</> : <><Lock size={18} /> Pay Securely</>}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Hero */}
      <div className="bg-gradient-to-br from-gray-900 via-teal-900 to-gray-900 text-white pt-24 pb-20 px-6 relative overflow-hidden">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,rgba(13,122,127,0.25),transparent_70%)]" />
        <div className="absolute top-20 left-10 w-72 h-72 bg-teal-500/10 rounded-full blur-3xl" />
        <div className="absolute bottom-0 right-10 w-80 h-80 bg-purple-500/10 rounded-full blur-3xl" />
        <div className="max-w-4xl mx-auto text-center relative z-10">
          <div className="inline-flex items-center gap-2 bg-white/10 backdrop-blur-sm border border-white/20 rounded-full px-4 py-2 text-sm font-bold mb-6">
            <Sparkles size={14} className="text-yellow-400" /> Introducing QuickServe Plans
          </div>
          <h1 className="text-5xl md:text-6xl font-black mb-6 leading-tight">
            Your Home, <br />
            <span className="bg-gradient-to-r from-teal-400 to-emerald-400 bg-clip-text text-transparent">Always Taken Care Of</span>
          </h1>
          <p className="text-gray-300 text-xl max-w-2xl mx-auto mb-10">
            Predictable monthly pricing, guaranteed availability, and AI-powered scheduling — everything your home needs, on autopilot.
          </p>

          {/* Billing Toggle */}
          <div className="inline-flex items-center gap-4 bg-white/10 backdrop-blur-sm border border-white/20 rounded-2xl p-2">
            <button
              onClick={() => setAnnual(false)}
              className={`px-6 py-2.5 rounded-xl font-bold text-sm transition-all ${!annual ? 'bg-white text-gray-900 shadow-md' : 'text-gray-300 hover:text-white'}`}
            >
              Monthly
            </button>
            <button
              onClick={() => setAnnual(true)}
              className={`px-6 py-2.5 rounded-xl font-bold text-sm transition-all ${annual ? 'bg-white text-gray-900 shadow-md' : 'text-gray-300 hover:text-white'}`}
            >
              Annual
              <span className="ml-2 bg-green-500 text-white text-[10px] font-black px-2 py-0.5 rounded-full">Save 30%</span>
            </button>
          </div>
        </div>
      </div>

      {/* Plans */}
      <div className="max-w-6xl mx-auto px-4 -mt-8 pb-20">
        <div className="grid md:grid-cols-3 gap-6">
          {PLANS.map(plan => {
            const Icon = plan.icon;
            const price = annual ? Math.round(plan.annualPrice / 12) : plan.price;
            const isActive = activePlan === plan.id;
            const isLoading = loading === plan.id;
            const isPopular = plan.id === 'pro';

            return (
              <div
                key={plan.id}
                className={`relative bg-white rounded-3xl border-2 transition-all duration-300 overflow-hidden
                  ${isPopular ? 'border-teal-500 shadow-2xl shadow-teal-100 scale-105 z-10' : 'border-gray-100 shadow-lg hover:shadow-xl hover:-translate-y-1'}
                  ${isActive ? 'ring-4 ring-teal-300' : ''}
                `}
              >
                {plan.badge && (
                  <div className={`absolute top-0 left-0 right-0 bg-gradient-to-r ${plan.color} text-white text-center text-xs font-black py-2 tracking-wider uppercase`}>
                    ⭐ {plan.badge}
                  </div>
                )}

                <div className={`bg-gradient-to-br ${plan.bgGrad} p-7 ${plan.badge ? 'pt-12' : 'pt-7'}`}>
                  <div className={`w-14 h-14 bg-gradient-to-br ${plan.color} rounded-2xl flex items-center justify-center shadow-lg mb-4`}>
                    <Icon size={24} className="text-white" />
                  </div>
                  <div className="flex items-end gap-2 mb-1">
                    <span className="text-4xl font-black text-gray-900">₹{price.toLocaleString()}</span>
                    <span className="text-gray-400 font-medium mb-1">/mo</span>
                  </div>
                  {annual && (
                    <p className="text-xs text-green-600 font-bold mb-1">
                      Billed ₹{plan.annualPrice.toLocaleString()}/year · Save ₹{(plan.price * 12 - plan.annualPrice).toLocaleString()}
                    </p>
                  )}
                  <h3 className="text-2xl font-black text-gray-900 mt-2">{plan.emoji} {plan.name}</h3>
                  <p className="text-gray-500 text-sm mt-1">{plan.tagline}</p>

                  <div className="flex gap-2 mt-4 flex-wrap">
                    <span className="text-xs font-bold bg-white/80 text-gray-700 px-3 py-1 rounded-full border border-white shadow-sm">
                      {plan.serviceCredits} services/mo
                    </span>
                    <span className="text-xs font-bold bg-white/80 text-gray-700 px-3 py-1 rounded-full border border-white shadow-sm">
                      {plan.priority}
                    </span>
                  </div>
                </div>

                <div className="p-6">
                  <ul className="space-y-3 mb-6">
                    {plan.features.map((feat, i) => (
                      <li key={i} className={`flex items-start gap-3 text-sm ${feat.included ? (feat.highlight ? 'text-gray-900 font-bold' : 'text-gray-700') : 'text-gray-300 line-through'}`}>
                        {feat.included
                          ? <CheckCircle size={16} className={`flex-shrink-0 mt-0.5 ${feat.highlight ? 'text-teal-600' : 'text-green-500'}`} />
                          : <XCircle size={16} className="flex-shrink-0 mt-0.5 text-gray-200" />
                        }
                        {feat.label}
                      </li>
                    ))}
                  </ul>

                  <button
                    onClick={() => isActive ? toast('Already subscribed! 🎉') : handleSubscribeClick(plan)}
                    disabled={isLoading}
                    className={`w-full py-4 rounded-2xl font-black text-base transition-all flex items-center justify-center gap-2
                      ${isActive
                        ? 'bg-green-100 text-green-700 border-2 border-green-200'
                        : isPopular
                          ? `bg-gradient-to-r ${plan.color} text-white shadow-lg hover:shadow-xl hover:scale-[1.02] active:scale-95`
                          : 'bg-gray-900 text-white hover:bg-gray-800 active:scale-95'
                      } disabled:opacity-60`}
                  >
                    {isLoading ? (
                      <><RefreshCw size={18} className="animate-spin" /> Processing…</>
                    ) : isActive ? (
                      <><CheckCircle size={18} /> Active Plan</>
                    ) : (
                      <>Get {plan.name} <ArrowRight size={18} /></>
                    )}
                  </button>

                  {!user && (
                    <p className="text-center text-xs text-gray-400 mt-3 flex items-center justify-center gap-1">
                      <Lock size={11} />
                      <Link to="/register" className="text-teal-600 font-bold hover:underline">Create account</Link> to subscribe
                    </p>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {/* Annual Savings Banner */}
        {!annual && (
          <div
            className="mt-8 bg-gradient-to-r from-green-600 to-emerald-600 rounded-2xl p-5 text-white flex items-center justify-between flex-wrap gap-4 cursor-pointer hover:from-green-700 hover:to-emerald-700 transition-all"
            onClick={() => setAnnual(true)}
          >
            <div className="flex items-center gap-3">
              <Gift size={22} className="text-green-200" />
              <div>
                <p className="font-black">Switch to Annual & Save up to ₹5,988/year</p>
                <p className="text-green-200 text-sm">That's like getting 2 months completely free!</p>
              </div>
            </div>
            <button className="bg-white text-green-700 px-5 py-2.5 rounded-xl font-black text-sm hover:bg-green-50 transition-colors">
              Switch to Annual
            </button>
          </div>
        )}

        {/* Perks Grid */}
        <div className="mt-20">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-black text-gray-900 mb-3">Every Plan Includes</h2>
            <p className="text-gray-500 text-lg">Exclusive subscriber-only benefits that set QuickServe apart</p>
          </div>
          <div className="grid md:grid-cols-3 gap-5">
            {PERKS.map(perk => {
              const Icon = perk.icon;
              return (
                <div key={perk.title} className="bg-white rounded-2xl border border-gray-100 p-6 shadow-sm hover:shadow-md transition-all hover:-translate-y-0.5">
                  <div className={`w-12 h-12 ${perk.bg} rounded-xl flex items-center justify-center mb-4`}>
                    <Icon size={22} className={perk.color} />
                  </div>
                  <h3 className="font-black text-gray-900 mb-2">{perk.title}</h3>
                  <p className="text-sm text-gray-500">{perk.desc}</p>
                </div>
              );
            })}
          </div>
        </div>

        {/* FAQ */}
        <div className="mt-20 max-w-3xl mx-auto">
          <h2 className="text-3xl font-black text-gray-900 text-center mb-10">Common Questions</h2>
          <div className="space-y-4">
            {[
              {
                q: 'Can I cancel anytime?',
                a: 'Yes! You can cancel your subscription at any time from your dashboard. Monthly plans cancel immediately; annual plans refund the unused portion.',
              },
              {
                q: 'Do unused service credits roll over?',
                a: 'Basic plan credits expire monthly. Pro and Elite plans allow up to 2 credits to roll over each month — use them how you like.',
              },
              {
                q: 'Which services qualify for free monthly credits?',
                a: 'All standard services — cleaning, plumbing, electrical, repair, beauty, and more. Emergency dispatch and specialist services may have an additional surcharge.',
              },
              {
                q: 'What is Surge Shield?',
                a: 'Pro subscribers have surge pricing capped at 1.2×. Elite subscribers never pay surge pricing — no matter the demand or weather conditions.',
              },
            ].map(({ q, a }) => (
              <details key={q} className="group bg-white border border-gray-100 rounded-2xl p-5 shadow-sm hover:border-teal-200 transition-all cursor-pointer">
                <summary className="font-black text-gray-900 flex items-center justify-between gap-3 list-none">
                  {q}
                  <span className="text-teal-600 text-xl group-open:rotate-45 transition-transform inline-block">+</span>
                </summary>
                <p className="text-gray-500 text-sm mt-3 leading-relaxed">{a}</p>
              </details>
            ))}
          </div>
        </div>

        {/* Bottom CTA */}
        <div className="mt-20 bg-gradient-to-br from-gray-900 to-teal-900 rounded-3xl p-10 text-white text-center relative overflow-hidden">
          <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,rgba(13,122,127,0.3),transparent_70%)]" />
          <div className="relative z-10">
            <div className="flex justify-center mb-6">
              <div className="flex -space-x-3">
                {[1,2,3,4,5].map(i => (
                  <img key={i} src={`https://i.pravatar.cc/40?u=sub${i}`} alt="" className="w-10 h-10 rounded-full ring-4 ring-gray-900" />
                ))}
              </div>
              <div className="ml-3 text-left">
                <div className="flex">
                  {[1,2,3,4,5].map(i => <Star key={i} size={14} className="text-yellow-400 fill-yellow-400" />)}
                </div>
                <p className="text-gray-300 text-xs">10,000+ happy subscribers</p>
              </div>
            </div>
            <h2 className="text-3xl font-black mb-4">Start Your Home Care Journey</h2>
            <p className="text-gray-300 mb-8 max-w-md mx-auto">Join thousands of homeowners who never worry about finding a good service provider again.</p>
            <div className="flex gap-3 justify-center flex-wrap">
              <button
                onClick={() => handleSubscribeClick(PLANS[1])}
                className="bg-teal-500 hover:bg-teal-400 text-white px-8 py-4 rounded-2xl font-black flex items-center gap-2 transition-all"
              >
                <Zap size={18} /> Start Pro — ₹699/mo
              </button>
              <Link to="/services" className="bg-white/10 hover:bg-white/20 text-white border border-white/20 px-8 py-4 rounded-2xl font-black transition-all">
                Browse Services First
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Subscriptions;
