import React, { useEffect, useState } from 'react';
import { ShieldCheck, ShieldAlert } from 'lucide-react';
import api from '../../services/api';

interface BadgeData {
  badge_earned: boolean;
  verified_jobs: number;
  jobs_needed: number;
  trust_score: number;
}

interface ProviderBadgeProps {
  providerId: string;
  /** compact: just the icon; full: icon + label + trust score */
  variant?: 'compact' | 'full';
}

const ProviderBadge: React.FC<ProviderBadgeProps> = ({ providerId, variant = 'compact' }) => {
  const [data, setData] = useState<BadgeData | null>(null);

  useEffect(() => {
    if (!providerId) return;
    api.get(`/api/work-verification/badge/${providerId}`)
      .then(r => setData(r.data))
      .catch(() => {/* silent */});
  }, [providerId]);

  if (!data) return null;

  if (variant === 'compact') {
    return data.badge_earned ? (
      <span title="Verified Provider – 3+ jobs with photo evidence" className="inline-flex items-center gap-1 text-xs font-bold text-teal-700 bg-teal-50 border border-teal-200 px-2 py-0.5 rounded-full">
        <ShieldCheck size={12} className="text-teal-600" /> Verified
      </span>
    ) : null;
  }

  return (
    <div className={`flex items-center gap-3 rounded-2xl p-4 border ${data.badge_earned ? 'bg-teal-50 border-teal-200' : 'bg-gray-50 border-gray-200'}`}>
      {data.badge_earned ? (
        <ShieldCheck size={28} className="text-teal-600 shrink-0" />
      ) : (
        <ShieldAlert size={28} className="text-gray-400 shrink-0" />
      )}
      <div className="flex-1">
        <p className={`font-black text-sm ${data.badge_earned ? 'text-teal-700' : 'text-gray-600'}`}>
          {data.badge_earned ? 'Verified Provider' : 'Verification Pending'}
        </p>
        <p className="text-xs text-gray-500">
          {data.badge_earned
            ? `${data.verified_jobs} verified jobs · Trust score ${data.trust_score}/100`
            : `${data.jobs_needed} more verified job${data.jobs_needed !== 1 ? 's' : ''} needed`}
        </p>
      </div>
      {data.badge_earned && (
        <div className="text-right">
          <p className="text-xl font-black text-teal-600">{data.trust_score}</p>
          <p className="text-xs text-gray-400">/ 100</p>
        </div>
      )}
    </div>
  );
};

export default ProviderBadge;
