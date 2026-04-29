import React, { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { loyaltyAPI, gamificationAPI } from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import DashboardLayout from '../components/DashboardLayout';
import { Trophy, Gift, Users, Star, ChevronRight, Copy, Check, Play, Target } from 'lucide-react';
import toast from 'react-hot-toast';

const tiers = [
  { name: 'Bronze',   minPoints: 0,    discount: 5,  color: 'from-amber-600 to-amber-800',    icon: '🥉', benefits: ['5% discount', 'Basic support', 'Email notifications'] },
  { name: 'Silver',   minPoints: 500,  discount: 10, color: 'from-gray-400 to-gray-600',       icon: '🥈', benefits: ['10% discount', 'Priority support', 'SMS notifications', 'Early access'] },
  { name: 'Gold',     minPoints: 1500, discount: 15, color: 'from-yellow-400 to-yellow-600',   icon: '🥇', benefits: ['15% discount', 'VIP support', 'Free cancellation', 'Exclusive offers'] },
  { name: 'Platinum', minPoints: 3000, discount: 20, color: 'from-purple-400 to-purple-700',   icon: '💎', benefits: ['20% discount', 'Concierge service', 'Premium providers', 'Personal assistant'] },
];

const Loyalty: React.FC = () => {
  const { user } = useAuth();
  const [referralCode, setReferralCode] = useState('');
  const [copied, setCopied] = useState(false);

  const { data: loyaltyData, refetch } = useQuery({
    queryKey: ['loyalty-points'],
    queryFn: loyaltyAPI.getPoints,
    retry: 1,
  });

  const points = loyaltyData?.points || 620;
  const currentTier = tiers.find(
    t => points >= t.minPoints &&
    (tiers.indexOf(t) === tiers.length - 1 || points < tiers[tiers.indexOf(t) + 1].minPoints)
  ) || tiers[0];
  const nextTier = tiers[tiers.indexOf(currentTier) + 1];
  const progress = nextTier
    ? ((points - currentTier.minPoints) / (nextTier.minPoints - currentTier.minPoints)) * 100
    : 100;

  const { data: challengeData } = useQuery({
    queryKey: ['gamification-challenges'],
    queryFn: gamificationAPI.getChallenges
  });

  const spinMutation = useMutation({
    mutationFn: gamificationAPI.dailySpin,
    onSuccess: (res) => {
      toast.success(`🎉 You won ${res.reward.points} points! ${res.reward.name}`);
      refetch();
    },
    onError: (err: any) => {
      toast.error(err.response?.data?.detail || 'Daily spin already used');
    }
  });

  const handleGenerateReferral = async () => {
    try {
      const data = await loyaltyAPI.generateReferral();
      const code = data.referral_code;
      setCopied(true);
      navigator.clipboard.writeText(code);
      toast.success(`Code: ${code} — copied!`);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      toast.error('Failed to generate code');
    }
  };

  const handleApplyReferral = async () => {
    if (!referralCode.trim()) { toast.error('Enter a referral code'); return; }
    try {
      await loyaltyAPI.applyReferral(referralCode);
      toast.success('Code applied! Bonus points added 🎉');
      setReferralCode('');
      refetch();
    } catch {
      toast.error('Invalid referral code');
    }
  };

  const role = (user?.role as 'customer' | 'provider' | 'admin') || 'customer';

  return (
    <DashboardLayout role={role} title="Loyalty & Rewards">
      <div className="p-6 space-y-6">

        {/* Points Hero Card */}
        <div className="bg-gradient-to-br from-[#0D1F2D] to-teal-800 rounded-2xl p-8 text-white shadow-lg">
          <div className="flex items-start justify-between mb-6">
            <div>
              <p className="text-teal-300 text-xs font-black uppercase tracking-[0.2em] mb-2">Your Loyalty Points</p>
              <p className="text-6xl font-black">{points.toLocaleString()}</p>
              <p className="text-teal-300 mt-2 font-medium">Keep earning to unlock better rewards!</p>
            </div>
            <div className="bg-white/10 backdrop-blur-sm rounded-2xl p-5 border border-white/20 text-center">
              <p className="text-4xl mb-2">{currentTier.icon}</p>
              <p className="text-teal-200 text-xs font-bold uppercase">Current Tier</p>
              <p className="font-black text-xl">{currentTier.name}</p>
            </div>
          </div>

          {/* Progress bar */}
          {nextTier && (
            <div>
              <div className="flex justify-between text-sm mb-2 font-bold">
                <span>{currentTier.name}</span>
                <span>{points}/{nextTier.minPoints} pts to {nextTier.name}</span>
              </div>
              <div className="h-3 bg-white/20 rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-teal-300 to-teal-100 rounded-full transition-all duration-700"
                  style={{ width: `${Math.min(progress, 100)}%` }}
                />
              </div>
              <p className="text-teal-300 text-xs mt-2 font-medium">
                {nextTier.minPoints - points} more points to unlock {nextTier.name} tier
              </p>
            </div>
          )}
        </div>

        {/* Daily Spin & Challenges */}
        <div className="grid lg:grid-cols-3 gap-6">
          <div className="bg-gradient-to-br from-purple-500 to-indigo-600 rounded-2xl p-6 text-white shadow-md flex flex-col justify-center items-center text-center">
            <Trophy size={48} className="text-yellow-300 mb-4" />
            <h3 className="font-black text-2xl mb-2">Daily Spin</h3>
            <p className="text-purple-100 text-sm mb-6">Test your luck daily to win bonus points and exclusive rewards!</p>
            <button
              onClick={() => spinMutation.mutate()}
              disabled={spinMutation.isPending}
              className="bg-white text-indigo-600 px-8 py-3 rounded-xl font-black shadow-lg hover:scale-105 active:scale-95 transition-all flex items-center gap-2"
            >
              <Play size={18} />
              {spinMutation.isPending ? 'Spinning...' : 'Spin the Wheel'}
            </button>
          </div>

          <div className="lg:col-span-2 bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
            <h3 className="font-black text-gray-900 text-lg mb-4 flex items-center gap-2">
              <Target size={20} className="text-red-500" /> Active Challenges
            </h3>
            <div className="space-y-4">
              {challengeData?.challenges?.map((c: any, i: number) => (
                <div key={i} className="flex items-center gap-4 bg-gray-50 p-4 rounded-xl border border-gray-100">
                  <div className="w-12 h-12 bg-white rounded-xl shadow-sm flex items-center justify-center text-2xl flex-shrink-0">
                    {c.badge_image || '🎖️'}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-black text-gray-900 mb-0.5">{c.name}</p>
                    <p className="text-xs text-gray-500 truncate">{c.description}</p>
                    <div className="w-full h-1.5 bg-gray-200 rounded-full mt-2">
                      <div className="h-full bg-red-500 rounded-full" style={{ width: `${(c.progress / c.requirement) * 100}%` }} />
                    </div>
                  </div>
                  <div className="text-right flex-shrink-0">
                    <p className="font-black text-indigo-600">{c.points_reward} pts</p>
                    <p className="text-[10px] font-bold text-gray-400 mt-1 uppercase">{c.progress}/{c.requirement}</p>
                  </div>
                </div>
              ))}
              {!challengeData?.challenges?.length && (
                <div className="text-center text-gray-500 text-sm p-4">No active challenges available.</div>
              )}
            </div>
          </div>
        </div>

        {/* Tier Cards */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {tiers.map(tier => {
            const isCurrent = currentTier.name === tier.name;
            return (
              <div
                key={tier.name}
                className={`rounded-2xl overflow-hidden shadow-sm transition-all duration-300 hover:shadow-lg hover:-translate-y-1 ${
                  isCurrent ? 'ring-2 ring-teal-500 ring-offset-2' : ''
                }`}
              >
                <div className={`bg-gradient-to-br ${tier.color} p-5 text-white relative`}>
                  {isCurrent && (
                    <span className="absolute top-3 right-3 bg-white text-teal-700 text-[10px] font-black px-2 py-0.5 rounded-full">YOU</span>
                  )}
                  <div className="text-3xl mb-2">{tier.icon}</div>
                  <h3 className="font-black text-lg">{tier.name}</h3>
                  <p className="text-4xl font-black">{tier.discount}%</p>
                  <p className="text-white/80 text-xs">discount</p>
                </div>
                <div className="bg-white p-4">
                  <p className="text-xs font-bold text-gray-400 mb-2">{tier.minPoints === 0 ? 'Starting tier' : `${tier.minPoints}+ points`}</p>
                  <ul className="space-y-1.5">
                    {tier.benefits.map((b, i) => (
                      <li key={i} className="text-xs text-gray-600 flex items-start gap-1.5">
                        <Check size={11} className="text-green-500 mt-0.5 flex-shrink-0" />
                        {b}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            );
          })}
        </div>

        {/* Referral Section */}
        <div className="grid md:grid-cols-2 gap-6">
          <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
            <div className="flex items-center gap-3 mb-5">
              <div className="w-11 h-11 bg-blue-100 rounded-xl flex items-center justify-center">
                <Users size={20} className="text-blue-600" />
              </div>
              <div>
                <h3 className="font-black text-gray-900">Refer Friends</h3>
                <p className="text-gray-500 text-sm">Earn 150 points per referral</p>
              </div>
            </div>
            <button
              onClick={handleGenerateReferral}
              className="w-full bg-gradient-to-r from-blue-500 to-purple-600 text-white py-3.5 rounded-xl font-black transition-all hover:shadow-lg hover:shadow-blue-200 hover:scale-[1.02] active:scale-95 flex items-center justify-center gap-2"
            >
              {copied ? <Check size={18} /> : <Copy size={18} />}
              {copied ? 'Copied!' : 'Generate & Copy Code'}
            </button>
            <div className="mt-4 bg-blue-50 rounded-xl p-4">
              <p className="text-xs font-black text-blue-700 mb-2">How it works</p>
              <ul className="space-y-1 text-xs text-blue-600">
                <li>• Generate your unique referral code</li>
                <li>• Share with friends & family</li>
                <li>• They get <strong>100 bonus points</strong> on signup</li>
                <li>• You earn <strong>150 points</strong> per referral!</li>
              </ul>
            </div>
          </div>

          <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
            <div className="flex items-center gap-3 mb-5">
              <div className="w-11 h-11 bg-green-100 rounded-xl flex items-center justify-center">
                <Gift size={20} className="text-green-600" />
              </div>
              <div>
                <h3 className="font-black text-gray-900">Redeem a Code</h3>
                <p className="text-gray-500 text-sm">Get 100 bonus points</p>
              </div>
            </div>
            <div className="space-y-3">
              <input
                type="text"
                value={referralCode}
                onChange={e => setReferralCode(e.target.value.toUpperCase())}
                placeholder="Enter referral code…"
                className="w-full border-2 border-gray-100 focus:border-teal-400 rounded-xl px-4 py-3 font-mono text-sm focus:outline-none transition-colors"
              />
              <button
                onClick={handleApplyReferral}
                className="w-full bg-gradient-to-r from-green-500 to-emerald-600 text-white py-3.5 rounded-xl font-black transition-all hover:shadow-lg hover:shadow-green-200 hover:scale-[1.02] active:scale-95"
              >
                ✨ Apply Code
              </button>
            </div>
          </div>
        </div>

        {/* Ways to Earn */}
        <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
          <h3 className="font-black text-gray-900 text-lg mb-5 flex items-center gap-2">
            <Star size={20} className="text-yellow-500" /> Ways to Earn Points
          </h3>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            {[
              { action: 'Complete a booking',      points: '10 pts per ₹', icon: '✅', bg: 'bg-blue-50',   text: 'text-blue-600'   },
              { action: 'Leave a review',          points: '50 points',    icon: '⭐', bg: 'bg-yellow-50', text: 'text-yellow-600' },
              { action: 'Refer a friend',          points: '150 points',   icon: '👥', bg: 'bg-green-50',  text: 'text-green-600'  },
              { action: 'First booking ever',      points: '200 bonus',    icon: '🎉', bg: 'bg-purple-50', text: 'text-purple-600' },
              { action: 'Monthly subscription',    points: '500 points',   icon: '💳', bg: 'bg-indigo-50', text: 'text-indigo-600' },
              { action: 'Rate provider 5★',        points: '100 points',   icon: '🌟', bg: 'bg-orange-50', text: 'text-orange-600' },
            ].map(item => (
              <div key={item.action} className={`${item.bg} rounded-xl p-5 hover:shadow-sm transition-all duration-200 hover:-translate-y-0.5`}>
                <div className="text-3xl mb-3">{item.icon}</div>
                <p className="font-black text-gray-900 text-sm mb-1">{item.action}</p>
                <p className={`font-black text-sm ${item.text}`}>{item.points}</p>
              </div>
            ))}
          </div>
        </div>

      </div>
    </DashboardLayout>
  );
};

export default Loyalty;
