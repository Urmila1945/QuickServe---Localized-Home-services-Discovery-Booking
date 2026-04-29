import React from 'react';
import { X, CheckCircle, Star, Award, Shield, Briefcase, Camera, MapPin, Calculator, Clock, Zap, Info } from 'lucide-react';
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import api from '../../services/api';

interface ProviderProfileModalProps {
  providerId: string;
  onClose: () => void;
}

const ProviderProfileModal: React.FC<ProviderProfileModalProps> = ({ providerId, onClose }) => {
  const [activeTab, setActiveTab] = useState<'verification' | 'estimate'>('verification');
  const [estimateHours, setEstimateHours] = useState(2);
  const [urgencyMultiplier, setUrgencyMultiplier] = useState(1);
  const { data: trustData, isLoading: trustLoading } = useQuery({
    queryKey: ['provider-trust', providerId],
    queryFn: () => api.get(`/api/work-verification/trust-score/${providerId}`).then(r => r.data),
    enabled: !!providerId,
  });

  const { data: providerInfo, isLoading: infoLoading } = useQuery({
    queryKey: ['provider-info', providerId],
    queryFn: () => api.get(`/api/providers/${providerId}`).then(r => r.data).catch(() => ({})),
    enabled: !!providerId,
  });

  if (trustLoading || infoLoading) {
    return (
      <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/50">
        <div className="bg-white rounded-3xl p-8 flex flex-col items-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
          <p className="mt-4 text-gray-500">Loading profile...</p>
        </div>
      </div>
    );
  }

  const rating = trustData?.breakdown?.raw_rating || providerInfo?.rating || 0;
  const experience = providerInfo?.experience_years || providerInfo?.experience || 0;
  const aptitude = providerInfo?.aptitude_score || providerInfo?.quickserve_score || 0;
  const galleryCount = trustData?.breakdown?.evidence_count || 0;

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm" onClick={onClose}>
      <div className="bg-white rounded-[32px] shadow-2xl w-full max-w-xl relative flex flex-col max-h-[90vh]" onClick={e => e.stopPropagation()}>
        
        <button 
          onClick={onClose} 
          className="absolute top-6 right-6 p-2 hover:bg-gray-100 rounded-full text-gray-400 transition-colors z-20"
        >
          <X size={24} />
        </button>

        <div className="p-8 overflow-y-auto custom-scrollbar">
          {/* Header */}
          <div className="flex items-center gap-6 mb-8">
            <div className="w-24 h-24 rounded-2xl bg-gray-100 overflow-hidden flex items-center justify-center text-primary font-black text-3xl">
              {providerInfo?.full_name?.[0] || 'P'}
            </div>
            <div>
              <div className="flex items-center gap-2 mb-1">
                <h2 className="text-2xl font-black text-gray-900">{providerInfo?.full_name || 'Verified Provider'}</h2>
                <CheckCircle className="text-primary" size={20} />
              </div>
              <p className="text-gray-500 font-bold uppercase text-xs tracking-widest flex items-center gap-2">
                {providerInfo?.category || 'Professional Service'}
                <span className="opacity-30">|</span>
                <span className="flex items-center gap-1"><MapPin size={12} /> {providerInfo?.city || 'India'}</span>
              </p>
            </div>
          </div>

          {/* Tabs */}
          <div className="flex gap-4 border-b border-gray-100 mb-6">
            <button 
              onClick={() => setActiveTab('verification')}
              className={`pb-3 font-bold text-sm transition-colors border-b-2 ${activeTab === 'verification' ? 'border-primary text-primary-dark' : 'border-transparent text-gray-400 hover:text-gray-600'}`}
            >
              Verification & Trust
            </button>
            <button 
              onClick={() => setActiveTab('estimate')}
              className={`pb-3 font-bold text-sm transition-colors border-b-2 flex items-center gap-1.5 ${activeTab === 'estimate' ? 'border-primary text-primary-dark' : 'border-transparent text-gray-400 hover:text-gray-600'}`}
            >
              <Calculator size={16} /> Quick Estimate
            </button>
          </div>

          {/* Tab Content */}
          <div className="min-h-[300px]">
            {activeTab === 'verification' ? (
              <div className="animate-fade-in">
                <div className="bg-gray-50 rounded-2xl p-6 mb-8 border border-gray-100">
                  <h3 className="text-sm font-black text-gray-400 uppercase tracking-widest mb-4">Official Verification</h3>
                  <div className="grid grid-cols-2 gap-6">
                    <div>
                      <p className="text-xs font-bold text-gray-500 mb-1">Assessment Score</p>
                      <p className="text-xl font-black text-gray-900">{aptitude}%</p>
                      <p className="text-[10px] text-green-600 font-bold mt-1">✓ Passed quickServe Exam</p>
                    </div>
                    <div>
                      <p className="text-xs font-bold text-gray-500 mb-1">Experience</p>
                      <p className="text-xl font-black text-gray-900">{experience} Yrs</p>
                      <p className="text-[10px] text-green-600 font-bold mt-1">✓ Verified Tenure</p>
                    </div>
                    <div>
                      <p className="text-xs font-bold text-gray-500 mb-1">Work Gallery</p>
                      <p className="text-xl font-black text-gray-900">{galleryCount} Items</p>
                      <p className="text-[10px] text-green-600 font-bold mt-1">✓ Photo-Verified</p>
                    </div>
                    <div>
                      <p className="text-xs font-bold text-gray-500 mb-1">Review Rating</p>
                      <p className="text-xl font-black text-gray-900">{rating.toFixed(1)} / 5.0</p>
                      <p className="text-[10px] text-green-600 font-bold mt-1">✓ Customer Satisfaction</p>
                    </div>
                  </div>
                </div>

                <div className="space-y-4 mb-8">
                  <h4 className="text-xs font-black text-gray-400 uppercase tracking-widest">Verification Criteria</h4>
                  {[
                    { label: 'Aptitude Assessment', desc: 'Practical test of trade knowledge and safety.' },
                    { label: 'ID & Background Check', desc: 'Government ID verification & criminal record scan.' },
                    { label: 'On-site GPS Verification', desc: 'Every job location is verified via provider check-in.' },
                    { label: 'Customer Quality Review', desc: 'Continuous monitoring of rating and feedback.' }
                  ].map((item, i) => (
                    <div key={i} className="flex gap-3">
                      <CheckCircle className="text-primary shrink-0" size={16} />
                      <div>
                        <p className="text-sm font-bold text-gray-900 leading-none mb-1">{item.label}</p>
                        <p className="text-xs text-gray-500">{item.desc}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="animate-fade-in bg-white rounded-2xl border border-gray-100 shadow-sm p-6 mb-8">
                <div className="flex items-center justify-between mb-6">
                  <h3 className="font-black text-lg text-gray-900">Get a Price Estimate</h3>
                  <div className="bg-teal-50 px-3 py-1.5 rounded-lg text-teal-700 font-bold text-sm">
                    ₹{providerInfo?.price_per_hour || providerInfo?.price || 500} / hr
                  </div>
                </div>

                <div className="space-y-6">
                  <div>
                    <label className="flex items-center gap-2 text-sm font-bold text-gray-700 mb-3">
                      <Clock size={16} className="text-gray-400" />
                      Estimated Duration (Hours)
                    </label>
                    <div className="flex items-center gap-4">
                      <input 
                        type="range" min="1" max="10" step="0.5"
                        value={estimateHours} 
                        onChange={(e) => setEstimateHours(parseFloat(e.target.value))}
                        className="flex-1 h-2 bg-gray-100 rounded-lg appearance-none cursor-pointer accent-primary"
                      />
                      <span className="font-black text-xl w-12 text-right">{estimateHours}h</span>
                    </div>
                  </div>

                  <div>
                    <label className="flex items-center gap-2 text-sm font-bold text-gray-700 mb-3">
                      <Zap size={16} className="text-gray-400" />
                      Urgency
                    </label>
                    <div className="grid grid-cols-3 gap-2">
                      {[
                        { label: 'Flexible', mult: 1, color: 'bg-green-50 text-green-700 border-green-200' },
                        { label: 'Today', mult: 1.2, color: 'bg-orange-50 text-orange-700 border-orange-200' },
                        { label: 'Emergency', mult: 1.5, color: 'bg-red-50 text-red-700 border-red-200' }
                      ].map((urgency) => (
                        <button
                          key={urgency.label}
                          onClick={() => setUrgencyMultiplier(urgency.mult)}
                          className={`py-2 px-1 rounded-xl text-xs font-bold border-2 transition-all ${
                            urgencyMultiplier === urgency.mult 
                              ? urgency.color 
                              : 'bg-white border-gray-100 text-gray-500 hover:border-gray-300'
                          }`}
                        >
                          {urgency.label}
                        </button>
                      ))}
                    </div>
                  </div>

                  <div className="bg-gradient-to-br from-gray-900 to-primary-dark rounded-2xl p-5 text-white flex justify-between items-center shadow-lg mt-6">
                    <div>
                      <p className="text-xs text-gray-400 font-bold uppercase tracking-widest mb-1 flex items-center gap-1"><Info size={12}/> Estimated Total</p>
                      <p className="text-3xl font-black">
                        ₹{Math.round((providerInfo?.price_per_hour || providerInfo?.price || 500) * estimateHours * urgencyMultiplier)}
                      </p>
                    </div>
                    <div className="text-right text-xs text-gray-300">
                      <p>{estimateHours} hrs × ₹{providerInfo?.price_per_hour || providerInfo?.price || 500}</p>
                      {urgencyMultiplier > 1 && <p>+ {Math.round((urgencyMultiplier - 1)*100)}% urgency fee</p>}
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>

          <button 
            className="w-full bg-primary hover:bg-primary-dark text-white py-4 rounded-xl font-black text-lg transition-all shadow-lg active:scale-95 flex items-center justify-center gap-2"
            onClick={onClose}
          >
            {activeTab === 'estimate' ? 'Book at Estimated Price' : 'Book This Provider'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default ProviderProfileModal;
