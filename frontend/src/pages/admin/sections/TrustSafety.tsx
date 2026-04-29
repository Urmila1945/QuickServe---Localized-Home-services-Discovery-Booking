import React, { useState, useEffect } from 'react';
import { Shield, Flag, Camera, FileText, AlertTriangle, CheckCircle, XCircle } from 'lucide-react';
import api from '../../../services/api';
import toast from 'react-hot-toast';

const TrustSafety: React.FC = () => {
  const [disputeList, setDisputeList] = useState<any[]>([]);
  const [reviews, setReviews] = useState<any[]>([]);
  const [activeSection, setActiveSection] = useState<'disputes'|'reviews'|'incidents'|'content'|'legal'>('disputes');

  useEffect(() => {
    const fetchTrust = async () => {
      try {
        const res = await api.get('/api/admin/trust-safety').then(r => r.data);
        setDisputeList(res.disputes || []);
        setReviews(res.review_queue || []);
      } catch (err) {
        console.error('Failed to load trust data', err);
      }
    };
    fetchTrust();
  }, []);

  const resolveDispute = (id: string, outcome: string) => {
    setDisputeList(prev => prev.map(d => d.id===id ? {...d, status:'resolved'} : d));
    toast.success(`Dispute ${id} resolved: ${outcome}`);
  };

  const moderateReview = (id: string, action: 'approve'|'remove') => {
    setReviews(prev => prev.filter(r => r.id !== id));
    toast.success(action==='approve' ? 'Review approved' : 'Review removed from platform');
  };

  const sections = [
    { key:'disputes',  label:'Disputes',  icon:'⚖️' },
    { key:'reviews',   label:'Reviews',   icon:'🔍' },
    { key:'incidents', label:'Incidents', icon:'🚑' },
    { key:'content',   label:'Content',   icon:'📸' },
    { key:'legal',     label:'Legal',     icon:'📜' },
  ] as const;

  const statusColor: Record<string, string> = {
    pending:      'bg-yellow-100 text-yellow-700',
    under_review: 'bg-blue-100 text-blue-700',
    escalated:    'bg-red-100 text-red-700',
    resolved:     'bg-green-100 text-green-700',
  };

  return (
    <div className="space-y-6">
      <div className="flex gap-2 bg-white rounded-2xl p-1.5 shadow-sm border border-gray-100 overflow-x-auto">
        {sections.map(s => (
          <button key={s.key} onClick={() => setActiveSection(s.key)}
            className={`flex items-center gap-1.5 px-4 py-2 rounded-xl font-bold text-sm whitespace-nowrap transition-all ${activeSection===s.key?'bg-teal-600 text-white shadow':'text-gray-500 hover:text-gray-800 hover:bg-gray-50'}`}>
            {s.icon} {s.label}
          </button>
        ))}
      </div>

      {activeSection === 'disputes' && (
        <div className="space-y-4">
          <div className="grid grid-cols-3 gap-4">
            {[
              { label:'Open',         value:disputeList.filter(d=>d.status==='pending').length,      color:'text-yellow-600', bg:'bg-yellow-50' },
              { label:'Under Review', value:disputeList.filter(d=>d.status==='under_review').length, color:'text-blue-600',   bg:'bg-blue-50'   },
              { label:'Escalated',    value:disputeList.filter(d=>d.status==='escalated').length,    color:'text-red-600',    bg:'bg-red-50'    },
            ].map(s => (
              <div key={s.label} className={`${s.bg} rounded-2xl p-4 text-center`}>
                <p className={`text-2xl font-black ${s.color}`}>{s.value}</p>
                <p className="text-xs font-bold text-gray-500 mt-0.5">{s.label}</p>
              </div>
            ))}
          </div>

          {disputeList.map(d => (
            <div key={d.id} className={`bg-white rounded-2xl p-5 shadow-sm border ${d.status==='escalated'?'border-red-300':d.status==='resolved'?'border-green-200':'border-gray-100'}`}>
              <div className="flex items-start justify-between flex-wrap gap-4">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-black text-gray-500 text-sm">#{d.id}</span>
                    <span className={`text-xs font-black px-2.5 py-1 rounded-full capitalize ${statusColor[d.status]}`}>{d.status.replace('_',' ')}</span>
                    <span className="text-xs font-black bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full">{d.category}</span>
                  </div>
                  <p className="font-bold text-gray-900">{d.title}</p>
                  <p className="text-xs text-gray-400 mt-1">Customer: <strong>{d.customer}</strong> · Provider: <strong>{d.provider}</strong> · ₹{d.amount.toLocaleString()} · {d.date}</p>
                </div>
                {d.status !== 'resolved' && (
                  <div className="flex flex-wrap gap-2 shrink-0">
                    <button onClick={() => resolveDispute(d.id, 'Customer favor')}
                      className="text-xs bg-green-600 hover:bg-green-700 text-white px-3 py-1.5 rounded-xl font-black transition-all active:scale-95">Customer Wins</button>
                    <button onClick={() => resolveDispute(d.id, 'Provider favor')}
                      className="text-xs bg-blue-600 hover:bg-blue-700 text-white px-3 py-1.5 rounded-xl font-black transition-all active:scale-95">Provider Wins</button>
                    <button onClick={() => resolveDispute(d.id, 'Split 50/50')}
                      className="text-xs bg-yellow-500 hover:bg-yellow-600 text-white px-3 py-1.5 rounded-xl font-black transition-all active:scale-95">Split</button>
                  </div>
                )}
                {d.status === 'resolved' && <CheckCircle size={24} className="text-green-500 shrink-0" />}
              </div>
            </div>
          ))}
        </div>
      )}

      {activeSection === 'reviews' && (
        <div className="space-y-4">
          {reviews.map(r => (
            <div key={r.id} className="bg-white rounded-2xl p-5 shadow-sm border border-red-100">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="font-bold text-gray-900 text-sm">{r.reviewer}</span>
                    <span className="text-yellow-600 font-black text-xs">{'★'.repeat(r.rating)}</span>
                    <span className="text-xs font-black text-red-600 bg-red-100 px-2 py-0.5 rounded-full">{r.flag}</span>
                  </div>
                  <p className="text-sm text-gray-700 italic mb-1">"{r.text}"</p>
                  <p className="text-xs text-gray-400">About: {r.subject}</p>
                  <div className="flex items-center gap-2 mt-2">
                    <span className="text-xs text-gray-500">AI Suspicion:</span>
                    <div className="w-24 h-2 bg-gray-100 rounded-full overflow-hidden">
                      <div className="h-full rounded-full bg-red-500" style={{ width:`${r.score}%` }} />
                    </div>
                    <span className="font-black text-red-600 text-xs">{r.score}%</span>
                  </div>
                </div>
                <div className="flex flex-col gap-2 shrink-0">
                  <button onClick={() => moderateReview(r.id,'approve')} className="bg-green-600 hover:bg-green-700 text-white px-3 py-1.5 rounded-xl font-black text-xs transition-all flex items-center gap-1"><CheckCircle size={11} /> Keep</button>
                  <button onClick={() => moderateReview(r.id,'remove')} className="bg-red-500 hover:bg-red-600 text-white px-3 py-1.5 rounded-xl font-black text-xs transition-all flex items-center gap-1"><XCircle size={11} /> Remove</button>
                </div>
              </div>
            </div>
          ))}
          {reviews.length === 0 && <div className="bg-green-50 rounded-2xl p-8 text-center font-black text-green-700">All reviews moderated! 🎉</div>}
        </div>
      )}
    </div>
  );
};

export default TrustSafety;
