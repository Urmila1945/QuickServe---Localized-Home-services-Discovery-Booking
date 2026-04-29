import React, { useState } from 'react';
import { Camera, Globe, MessageSquare } from 'lucide-react';
import toast from 'react-hot-toast';

const portfolioJobs = [
  { id:'pj1', title:'Panel Upgrade — Anjali Home',  date:'Dec 10', category:'Wiring', rating:5,   before:'🔌', after:'⚡', caption:'Complete 240V panel upgrade with safety breakers' },
  { id:'pj2', title:'AC Circuit Install — Whitefield',date:'Dec 5',category:'AC',     rating:4.8, before:'🏚️', after:'🏠', caption:'Dedicated AC circuit with automatic cutoff'        },
  { id:'pj3', title:'Smart Switches — Koramangala', date:'Nov 28', category:'Smart',  rating:5,   before:'💡', after:'🏙️', caption:'Full smart home switch integration (Alexa ready)' },
];

const seoKeywords = [
  { keyword:'Electrician Koramangala',  rank:4,  volume:'2.4k/mo', opportunity:'high'   },
  { keyword:'Emergency Electrician Bangalore', rank:8, volume:'1.8k/mo', opportunity:'high' },
  { keyword:'Home Wiring Bangalore',    rank:12, volume:'3.2k/mo', opportunity:'medium' },
  { keyword:'AC Wiring Installation',   rank:6,  volume:'980/mo',  opportunity:'medium' },
  { keyword:'Smart Switch Install',     rank:2,  volume:'560/mo',  opportunity:'low'    },
];

const reviewTemplates = [
  { scenario:'5-star review', template:"Thank you so much {{name}}! It was a pleasure working on your {{service}}. I'm glad everything is working perfectly. Please don't hesitate to call for any future needs! 🙏" },
  { scenario:'4-star review', template:"Thank you {{name}} for the kind feedback on the {{service}} job. I appreciate your notes and will work to improve. Looking forward to serving you again!" },
  { scenario:'Complaint review', template:"Hi {{name}}, I sincerely apologize for your experience. Please contact me directly at [phone] so I can make this right immediately. Customer satisfaction is my top priority." },
];

const PortfolioMarketing: React.FC = () => {
  const [activeTemplate, setActiveTemplate] = useState<string|null>(null);
  const [ambassadorProgress] = useState({ completed:68, required:100, badge:'Local Hero', perks:['Featured listing','+12% visibility','Priority matching'] });

  return (
    <div className="space-y-6">
      {/* Neighborhood Ambassador */}
      <div className="bg-gradient-to-r from-purple-600 to-indigo-700 rounded-2xl p-6 text-white shadow-lg">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 bg-white/15 rounded-2xl flex items-center justify-center backdrop-blur-sm border border-white/20 text-3xl">🏆</div>
            <div>
              <p className="text-purple-200 text-xs font-bold uppercase tracking-widest mb-1">Neighborhood Ambassador</p>
              <p className="font-black text-xl">"{ambassadorProgress.badge}" Progress</p>
              <p className="text-purple-200 text-sm mt-1">{ambassadorProgress.completed}/{ambassadorProgress.required} points to unlock</p>
            </div>
          </div>
          <div className="text-right">
            <div className="w-20 h-20 relative">
              <svg viewBox="0 0 36 36" className="w-full h-full -rotate-90">
                <circle cx="18" cy="18" r="15.9" fill="none" stroke="rgba(255,255,255,0.2)" strokeWidth="2.5" />
                <circle cx="18" cy="18" r="15.9" fill="none" stroke="white" strokeWidth="2.5"
                  strokeDasharray={`${ambassadorProgress.completed} ${ambassadorProgress.required}`} strokeLinecap="round" />
              </svg>
              <div className="absolute inset-0 flex items-center justify-center">
                <span className="font-black text-sm">{ambassadorProgress.completed}%</span>
              </div>
            </div>
          </div>
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          {ambassadorProgress.perks.map(p => (
            <span key={p} className="bg-white/15 backdrop-blur-sm border border-white/20 text-white text-xs font-bold px-3 py-1.5 rounded-full">{p}</span>
          ))}
        </div>
      </div>

      {/* Auto Portfolio */}
      <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-black text-gray-900 text-lg flex items-center gap-2"><Camera size={18} className="text-teal-600" /> Auto-Generated Portfolio</h3>
          <button onClick={() => toast.success('New portfolio item created with AI captions!')} className="text-xs bg-teal-600 hover:bg-teal-700 text-white px-4 py-2 rounded-xl font-black transition-all">+ Add Job Photos</button>
        </div>
        <div className="grid sm:grid-cols-3 gap-4">
          {portfolioJobs.map(job => (
            <div key={job.id} className="border border-gray-100 rounded-xl overflow-hidden hover:shadow-md hover:-translate-y-0.5 transition-all group">
              <div className="bg-gradient-to-br from-gray-100 to-gray-200 h-28 flex items-center justify-between px-6 text-4xl">
                <span>{job.before}</span>
                <span className="text-lg text-gray-400">→</span>
                <span>{job.after}</span>
              </div>
              <div className="p-3">
                <p className="font-black text-gray-900 text-sm">{job.title}</p>
                <p className="text-xs text-gray-400 mt-0.5">{job.caption}</p>
                <div className="flex items-center justify-between mt-2">
                  <span className="text-xs text-yellow-600 font-black">{job.rating} ★</span>
                  <div className="flex gap-1.5">
                    <button onClick={() => toast.success('Shared to Instagram!')} className="text-[10px] bg-pink-100 text-pink-700 font-black px-2 py-1 rounded-lg hover:bg-pink-200 transition-colors">📸 Share</button>
                    <button onClick={() => toast.success('Shared to Facebook!')} className="text-[10px] bg-blue-100 text-blue-700 font-black px-2 py-1 rounded-lg hover:bg-blue-200 transition-colors">👍 FB</button>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        {/* SEO Insights */}
        <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
          <h3 className="font-black text-gray-900 text-lg flex items-center gap-2 mb-4">
            <Globe size={18} className="text-blue-600" /> Local SEO Insights
          </h3>
          <div className="space-y-3">
            {seoKeywords.map(k => (
              <div key={k.keyword} className="flex items-center gap-3">
                <div className={`w-8 h-8 rounded-xl flex items-center justify-center font-black text-xs shrink-0 ${k.rank<=4?'bg-green-100 text-green-700':k.rank<=8?'bg-yellow-100 text-yellow-700':'bg-orange-100 text-orange-700'}`}>
                  #{k.rank}
                </div>
                <div className="flex-1">
                  <p className="text-sm font-bold text-gray-800">{k.keyword}</p>
                  <p className="text-xs text-gray-400">{k.volume} monthly searches</p>
                </div>
                <span className={`text-[10px] font-black px-2 py-1 rounded-full ${k.opportunity==='high'?'bg-green-100 text-green-700':k.opportunity==='medium'?'bg-yellow-100 text-yellow-700':'bg-gray-100 text-gray-500'}`}>
                  {k.opportunity}
                </span>
              </div>
            ))}
          </div>
          <div className="mt-4 p-3 bg-blue-50 rounded-xl border border-blue-100">
            <p className="text-xs font-bold text-blue-700">💡 Add "smart home" to your profile bio to rank for 2 new keywords</p>
          </div>
        </div>

        {/* Review Response Templates */}
        <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
          <h3 className="font-black text-gray-900 text-lg flex items-center gap-2 mb-4">
            <MessageSquare size={18} className="text-purple-600" /> Review Response Templates
          </h3>
          <div className="space-y-3">
            {reviewTemplates.map(t => (
              <div key={t.scenario} className="border border-gray-100 rounded-xl overflow-hidden">
                <button onClick={() => setActiveTemplate(activeTemplate===t.scenario?null:t.scenario)}
                  className="w-full flex items-center justify-between px-4 py-3 bg-gray-50 hover:bg-gray-100 transition-colors text-left">
                  <span className="font-bold text-gray-800 text-sm">{t.scenario}</span>
                  <span className="text-gray-400 text-xs">{activeTemplate===t.scenario?'▲':'▼'}</span>
                </button>
                {activeTemplate===t.scenario && (
                  <div className="p-4">
                    <p className="text-xs text-gray-600 italic leading-relaxed">{t.template}</p>
                    <div className="flex gap-2 mt-3">
                      <button onClick={() => { navigator.clipboard.writeText(t.template); toast.success('Copied!'); }}
                        className="text-xs bg-purple-100 text-purple-700 font-black px-3 py-1.5 rounded-xl hover:bg-purple-200 transition-colors">
                        📋 Copy
                      </button>
                      <button onClick={() => toast.success('Template customized with AI!')}
                        className="text-xs bg-teal-100 text-teal-700 font-black px-3 py-1.5 rounded-xl hover:bg-teal-200 transition-colors">
                        🤖 AI Personalize
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default PortfolioMarketing;
