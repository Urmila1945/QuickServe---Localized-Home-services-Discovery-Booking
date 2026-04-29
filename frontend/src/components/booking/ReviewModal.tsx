import React, { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { X, Star, Loader, Check, AlertTriangle, ShieldCheck } from 'lucide-react';
import toast from 'react-hot-toast';
import { reviewsAPI, aiAPI } from '../../services/api';

// ── Types ──────────────────────────────────────────────────────────────

interface ReviewModalProps {
  bookingId: string;
  providerId: string;
  serviceTitle: string;
  onClose: () => void;
  onSuccess?: () => void;
}

type AuthenticityResult = {
  authenticity_score: number;
  is_suspicious: boolean;
  verdict: string;
  reasons: string[];
};

// ── Star Rating Component ─────────────────────────────────────────────

const StarRating: React.FC<{
  value: number;
  onChange: (v: number) => void;
}> = ({ value, onChange }) => {
  const [hovered, setHovered] = useState(0);
  const labels = ['', 'Poor', 'Fair', 'Good', 'Very Good', 'Excellent!'];
  return (
    <div className="text-center">
      <div className="flex justify-center gap-2 mb-2">
        {[1, 2, 3, 4, 5].map(n => (
          <button
            key={n}
            onMouseEnter={() => setHovered(n)}
            onMouseLeave={() => setHovered(0)}
            onClick={() => onChange(n)}
            className="transition-transform hover:scale-125 active:scale-95"
            aria-label={`Rate ${n} stars`}
          >
            <Star
              size={36}
              className={`transition-colors ${n <= (hovered || value) ? 'text-yellow-400 fill-yellow-400' : 'text-gray-200'}`}
            />
          </button>
        ))}
      </div>
      {(hovered || value) > 0 && (
        <p className="text-sm font-black text-yellow-600">{labels[hovered || value]}</p>
      )}
    </div>
  );
};

// ── Authenticity Badge ────────────────────────────────────────────────

const AuthenticityBadge: React.FC<{ result: AuthenticityResult }> = ({ result }) => {
  const score = Math.round(result.authenticity_score * 100);
  const color = result.is_suspicious
    ? 'border-red-200 bg-red-50'
    : score >= 80
    ? 'border-green-200 bg-green-50'
    : 'border-yellow-200 bg-yellow-50';
  const icon = result.is_suspicious
    ? <AlertTriangle size={16} className="text-red-500" />
    : <ShieldCheck size={16} className="text-green-600" />;
  const label = result.is_suspicious ? 'Suspicious review detected' : 'Review looks authentic';
  const textColor = result.is_suspicious ? 'text-red-700' : 'text-green-700';

  return (
    <div className={`flex items-start gap-3 p-3 rounded-xl border ${color}`}>
      <div className="flex-shrink-0 mt-0.5">{icon}</div>
      <div className="flex-1">
        <p className={`text-xs font-black ${textColor}`}>
          🤖 AI Review Check: {label}
        </p>
        <div className="flex items-center gap-2 mt-1">
          <div className="flex-1 h-1.5 bg-white rounded-full overflow-hidden">
            <div
              className={`h-full rounded-full transition-all ${result.is_suspicious ? 'bg-red-400' : 'bg-green-500'}`}
              style={{ width: `${score}%` }}
            />
          </div>
          <span className={`text-xs font-black ${textColor}`}>{score}%</span>
        </div>
        {result.reasons.length > 0 && (
          <ul className="mt-1.5 space-y-0.5">
            {result.reasons.slice(0, 2).map((r, i) => (
              <li key={i} className={`text-xs ${textColor} opacity-80`}>• {r}</li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
};

// ── Main Component ─────────────────────────────────────────────────────

const ReviewModal: React.FC<ReviewModalProps> = ({
  bookingId, providerId, serviceTitle, onClose, onSuccess,
}) => {
  const [rating, setRating] = useState(0);
  const [comment, setComment] = useState('');
  const [authenticity, setAuthenticity] = useState<AuthenticityResult | null>(null);
  const [checking, setChecking] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const submitMutation = useMutation({
    mutationFn: () => reviewsAPI.create({
      booking_id: bookingId,
      provider_id: providerId,
      rating,
      comment,
    }),
    onSuccess: () => {
      setSubmitted(true);
      toast.success('Review submitted! Thank you 🙏');
      onSuccess?.();
    },
    onError: () => toast.error('Failed to submit review. Please try again.'),
  });

  const handleCheckAuthenticity = async () => {
    if (!comment.trim() || !rating) {
      toast.error('Enter a rating and comment first');
      return;
    }
    setChecking(true);
    try {
      const result = await aiAPI.detectFakeReview(comment, rating);
      setAuthenticity(result);
    } catch {
      toast.error('AI check unavailable — you can still submit your review.');
    } finally {
      setChecking(false);
    }
  };

  const handleSubmit = async () => {
    if (!rating) { toast.error('Please select a star rating'); return; }
    if (!comment.trim()) { toast.error('Please write a comment'); return; }
    submitMutation.mutate();
  };

  const QUICK_REVIEWS = [
    'Great work, very professional!',
    'On time and efficient',
    'Excellent quality service',
    'Would highly recommend',
    'Good job, neat and clean',
  ];

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ background: 'rgba(0,0,0,0.65)', backdropFilter: 'blur(6px)' }}
      onClick={e => e.target === e.currentTarget && onClose()}
    >
      <div className="bg-white rounded-3xl shadow-2xl w-full max-w-md max-h-[90vh] overflow-y-auto">

        {/* Header */}
        <div className="bg-gradient-to-r from-yellow-400 to-orange-400 rounded-t-3xl p-6 text-white relative">
          <button
            onClick={onClose}
            className="absolute top-4 right-4 w-8 h-8 bg-white/20 hover:bg-white/30 rounded-full flex items-center justify-center transition-all"
          >
            <X size={15} />
          </button>
          <p className="text-yellow-100 text-xs font-black uppercase tracking-widest mb-1">Leave a Review</p>
          <h2 className="font-black text-xl leading-tight pr-10">{serviceTitle}</h2>
          <p className="text-yellow-100 text-sm mt-1 font-medium">Your honest feedback helps everyone</p>
        </div>

        <div className="p-6 space-y-6">
          {submitted ? (
            /* ── Success ── */
            <div className="text-center py-8 space-y-4">
              <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mx-auto">
                <Check size={36} className="text-green-600" />
              </div>
              <h3 className="font-black text-xl text-gray-900">Review Submitted!</h3>
              <p className="text-gray-500 text-sm">Thank you for your feedback. It helps other customers make informed decisions.</p>
              <button onClick={onClose} className="bg-teal-600 text-white px-8 py-3 rounded-xl font-black hover:bg-teal-700 transition-colors">
                Done
              </button>
            </div>
          ) : (
            <>
              {/* Star Rating */}
              <div>
                <label className="text-xs font-black text-gray-400 uppercase tracking-widest block mb-4">Your Rating</label>
                <StarRating value={rating} onChange={setRating} />
              </div>

              {/* Quick Review Chips */}
              <div>
                <label className="text-xs font-black text-gray-400 uppercase tracking-widest block mb-2">Quick Reviews</label>
                <div className="flex flex-wrap gap-2">
                  {QUICK_REVIEWS.map(qr => (
                    <button
                      key={qr}
                      onClick={() => setComment(prev => prev ? `${prev} ${qr}` : qr)}
                      className="text-xs font-bold px-3 py-1.5 rounded-full border border-gray-200 text-gray-600 hover:border-teal-400 hover:bg-teal-50 hover:text-teal-700 transition-all"
                    >
                      + {qr}
                    </button>
                  ))}
                </div>
              </div>

              {/* Comment */}
              <div>
                <label className="text-xs font-black text-gray-400 uppercase tracking-widest block mb-2">
                  Your Review <span className="text-red-400">*</span>
                </label>
                <textarea
                  value={comment}
                  onChange={e => setComment(e.target.value)}
                  placeholder="Describe your experience in detail — quality of work, punctuality, professionalism..."
                  className="w-full border-2 border-gray-100 focus:border-yellow-400 rounded-xl px-4 py-3 text-sm font-medium focus:outline-none transition-colors h-28 resize-none"
                />
                <p className="text-xs text-gray-400 mt-1 text-right">{comment.length} characters</p>
              </div>

              {/* AI Authenticity Check */}
              <div>
                <button
                  onClick={handleCheckAuthenticity}
                  disabled={checking || !comment.trim() || !rating}
                  className="flex items-center gap-2 text-sm font-bold text-teal-600 hover:text-teal-800 disabled:text-gray-300 transition-colors"
                >
                  {checking ? <Loader size={14} className="animate-spin" /> : <ShieldCheck size={14} />}
                  {checking ? 'Checking review authenticity…' : '🤖 Check with AI (optional)'}
                </button>
                {authenticity && <div className="mt-3"><AuthenticityBadge result={authenticity} /></div>}
              </div>

              {/* Disclaimer */}
              <div className="bg-gray-50 rounded-xl p-3 text-xs text-gray-400 font-medium">
                ℹ️ Reviews are verified using AI authenticity detection to maintain trust and quality on the platform.
              </div>

              {/* Submit */}
              <button
                onClick={handleSubmit}
                disabled={submitMutation.isPending || !rating || !comment.trim()}
                className="w-full bg-gradient-to-r from-yellow-400 to-orange-400 hover:from-yellow-500 hover:to-orange-500 text-white py-4 rounded-xl font-black text-sm transition-all hover:shadow-lg hover:shadow-yellow-200 active:scale-95 disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {submitMutation.isPending
                  ? <><Loader size={16} className="animate-spin" /> Submitting…</>
                  : <><Star size={16} className="fill-white" /> Submit Review</>
                }
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default ReviewModal;
