import React, { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { 
  queueAPI, surgeAPI, gamificationAPI, predictiveAPI, moodSyncAPI,
  communityAPI, bundlesAPI, eventsAPI, swapAPI, arPreviewAPI, rouletteAPI, aiConciergeAPI
} from '../services/api';
import DashboardLayout from '../components/DashboardLayout';
import { useAuth } from '../contexts/AuthContext';
import toast from 'react-hot-toast';
import { 
  Activity, TrendingUp, Award, Thermometer, Smile, Users, 
  Package, Calendar, Repeat, Eye, Bot, Loader2, Play,
  Cpu, Zap, Sparkles, MapPin, Clock, Camera, MessageSquare, Gift,
  ChevronRight, RefreshCw, Send, Settings, UserPlus, ShieldCheck
} from 'lucide-react';

const FeatureCard = ({ title, icon: Icon, color, children, onRun, isLoading }: any) => (
  <div className="bg-white/80 backdrop-blur-xl border border-gray-100 rounded-3xl p-6 shadow-xl hover:shadow-2xl transition-all duration-300 group">
    <div className="flex items-center justify-between mb-6">
      <div className={`p-4 rounded-2xl ${color} text-white shadow-lg group-hover:scale-110 transition-transform`}>
        <Icon size={24} />
      </div>
      <button 
        onClick={onRun}
        disabled={isLoading}
        className="p-2 hover:bg-gray-100 rounded-xl transition-colors disabled:opacity-50"
      >
        {isLoading ? <Loader2 className="animate-spin text-gray-400" /> : <RefreshCw className="text-gray-400 group-hover:rotate-180 transition-transform duration-500" size={20} />}
      </button>
    </div>
    <h3 className="text-xl font-bold text-gray-800 mb-2">{title}</h3>
    <div className="text-gray-600 text-sm mb-6 min-h-[50px]">
      {children}
    </div>
  </div>
);

const ResultPanel = ({ data, title }: any) => (
  <div className="col-span-full mt-8 bg-gray-900 text-green-400 p-6 rounded-3xl font-mono text-sm overflow-auto max-h-[400px] border-4 border-gray-800 shadow-2xl relative">
    <div className="flex items-center gap-2 mb-4 text-gray-400 border-b border-gray-700 pb-2">
      <Cpu size={14} />
      <span>System Logs: {title}</span>
    </div>
    <pre className="whitespace-pre-wrap">{JSON.stringify(data, null, 2)}</pre>
  </div>
);

const EnhancedFeatures = () => {
  const { user } = useAuth();
  const [activeResult, setActiveResult] = useState<{title: string, data: any} | null>(null);

  // --- Real-time Data Queries ---
  const { data: gameProfile } = useQuery({
    queryKey: ['gameProfile'],
    queryFn: gamificationAPI.getProfile
  });

  const { data: healthScore } = useQuery({
    queryKey: ['healthScore'],
    queryFn: predictiveAPI.getHealthScore
  });

  const { data: moodInsights } = useQuery({
    queryKey: ['moodInsights'],
    queryFn: moodSyncAPI.getInsights
  });

  const { data: communityRes } = useQuery({
    queryKey: ['communityChallenges'],
    queryFn: communityAPI.getActiveChallenges
  });

  const { data: bundlesRes } = useQuery({
    queryKey: ['bundles'],
    queryFn: bundlesAPI.getRecommendations
  });

  const { data: eventsRes } = useQuery({
    queryKey: ['events'],
    queryFn: eventsAPI.getUpcoming
  });

  // --- Feature Implementation Mutations ---
  const queueMutation = useMutation({
    mutationFn: (data: any = { service_type: 'plumbing', priority: 'premium' }) => queueAPI.join(data),
    onSuccess: (res) => {
        setActiveResult({ title: 'Smart Queue', data: res });
        toast.success("Successfully joined the queue!");
    }
  });

  const surgeMutation = useMutation({
    mutationFn: () => surgeAPI.calculate({ 
        service_type: 'cleaning', 
        location: { lat: 12.97, lng: 77.59 },
        urgency: 'high'
    }),
    onSuccess: (res) => setActiveResult({ title: 'Surge Pricing', data: res })
  });

  const moodMutation = useMutation({
    mutationFn: (mood: string = 'energetic') => moodSyncAPI.updateMood({ 
        mood, 
        energy_level: 9, 
        availability_hours: 8,
        notes: "Real-time sync from Features Lab" 
    }),
    onSuccess: (res) => setActiveResult({ title: 'Mood Sync Status', data: res })
  });

  const arMutation = useMutation({
    mutationFn: async () => {
        const fd = new FormData();
        const blob = new Blob([JSON.stringify({type: "living_room"})], { type: 'application/json' });
        fd.append('file', blob, 'room.jpg');
        return arPreviewAPI.uploadSpace(fd);
    },
    onSuccess: (res) => setActiveResult({ title: 'AR Spatial Analysis', data: res })
  });

  const aiChatMutation = useMutation({
    mutationFn: (msg: string = "Optimize my schedule for tomorrow.") => aiConciergeAPI.chat({ 
        message: msg,
        context: { user_location: "Mumbai", current_tasks: 3 }
    }),
    onSuccess: (res) => setActiveResult({ title: 'AI Recommendation Engine', data: res })
  });

  const gameMutation = useMutation({
    mutationFn: () => gamificationAPI.updateProgress({ challenge_id: 'streak_master', progress: Math.floor(Math.random() * 7) }),
    onSuccess: (res) => {
        setActiveResult({ title: 'XP Accumulation', data: res });
        // Trigger re-fetch of profile
    }
  });

  const bundleMutation = useMutation({
    mutationFn: () => bundlesAPI.optimize({ 
        services: ["cleaning", "plumbing"], 
        max_budget: 1200 
    }),
    onSuccess: (res) => setActiveResult({ title: 'Bundle Optimization', data: res })
  });

  const rouletteMutation = useMutation({
    mutationFn: () => rouletteAPI.spin({ category: 'cleaning', bet_amount: 50 }),
    onSuccess: (res) => setActiveResult({ title: 'Discovery Spin Result', data: res })
  });

  const predictMutation = useMutation({
    mutationFn: () => predictiveAPI.getCalendar(),
    onSuccess: (res) => setActiveResult({ title: 'Maintenance Forecast', data: res })
  });

  const communityMutation = useMutation({
    mutationFn: () => communityAPI.getNeighborhoodStats("400001"),
    onSuccess: (res) => setActiveResult({ title: 'Neighborhood Pulse', data: res })
  });

  const swapMutation = useMutation({
    mutationFn: () => swapAPI.browse(),
    onSuccess: (res) => setActiveResult({ title: 'Swap Marketplace', data: res })
  });

  const eventMutation = useMutation({
    mutationFn: () => eventsAPI.getUpcoming(),
    onSuccess: (res) => setActiveResult({ title: 'Live Events Feed', data: res })
  });

  return (
    <DashboardLayout role={(user?.role as any) || 'customer'}>
      <div className="min-h-screen bg-[#F8FAFC] pb-20">
        {/* Header Section */}
        <div className="bg-gradient-to-r from-blue-700 via-indigo-700 to-purple-800 text-white py-12 px-8 rounded-b-[4rem] shadow-2xl relative overflow-hidden mb-12">
          <div className="absolute top-0 right-0 w-96 h-96 bg-white/10 rounded-full blur-3xl -mr-48 -mt-48"></div>
          <div className="absolute bottom-0 left-0 w-64 h-64 bg-purple-500/20 rounded-full blur-2xl -ml-32 -mb-32"></div>
          
          <div className="relative z-10 max-w-7xl mx-auto">
            <div className="flex items-center gap-3 mb-4">
              <div className="px-3 py-1 bg-white/20 backdrop-blur-md rounded-full text-xs font-semibold tracking-wider uppercase">Beta Testing Environment</div>
              <Sparkles className="text-yellow-400" size={18} />
            </div>
            <h1 className="text-5xl font-extrabold mb-4 tracking-tight">Features Lab <span className="text-blue-300">v2.0</span></h1>
            <p className="text-blue-100 text-lg max-w-2xl">
              Execute and validate all 12 experimental API endpoints. This environment is designed for real-time testing of QuickServe's advanced service modules.
            </p>
          </div>
        </div>

        <div className="max-w-7xl mx-auto px-8">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            
            {/* 1. Smart Queue */}
            <FeatureCard 
              title="Smart Queue" icon={Activity} color="bg-blue-600"
              onRun={() => queueMutation.mutate({ service_type: 'plumbing', priority: 'premium' })} isLoading={queueMutation.isPending}
            >
              <div className="flex flex-col gap-2">
                <p>Real-time positioning and estimated wait times.</p>
                <div className="flex items-center gap-2 text-xs font-bold text-blue-600 bg-blue-50 px-2 py-1 rounded-lg w-fit">
                  <Clock size={12} />
                  <span>AVG WAIT: 15 MIN</span>
                </div>
              </div>
            </FeatureCard>

            {/* 2. Surge Pricing */}
            <FeatureCard 
              title="Surge Logic" icon={TrendingUp} color="bg-orange-600"
              onRun={() => surgeMutation.mutate()} isLoading={surgeMutation.isPending}
            >
              <div className="flex flex-col gap-2">
                <p>Dynamic multiplier calculation based on demand.</p>
                <div className="flex items-center gap-2 text-xs font-bold text-orange-600 bg-orange-50 px-2 py-1 rounded-lg w-fit">
                  <Zap size={12} />
                  <span>PEAK: 1.25x - 1.8x</span>
                </div>
              </div>
            </FeatureCard>

            {/* 3. Gamification */}
            <FeatureCard 
              title="Progression" icon={Award} color="bg-purple-600"
              onRun={() => gameMutation.mutate()} isLoading={gameMutation.isPending}
            >
              {gameProfile ? (
                <div className="flex flex-col gap-2">
                  <div className="flex items-center justify-between text-xs font-bold mb-1">
                    <span className="text-purple-700">LEVEL {gameProfile.level}</span>
                    <span className="text-purple-400">{gameProfile.xp} / {(gameProfile.level)*1000} XP</span>
                  </div>
                  <div className="w-full bg-purple-100 h-2 rounded-full overflow-hidden shadow-inner">
                    <div className="bg-gradient-to-r from-purple-500 to-indigo-600 h-full transition-all duration-1000" style={{ width: `${(gameProfile.xp % 1000) / 10}%` }}></div>
                  </div>
                </div>
              ) : "Tracking challenges and XP accumulation."}
            </FeatureCard>

            {/* 4. Predictive Maintenance */}
            <FeatureCard 
              title="Maintenance" icon={Thermometer} color="bg-cyan-600"
              onRun={() => predictMutation.mutate()} isLoading={predictMutation.isPending}
            >
              {healthScore ? (
                <div className="flex flex-col gap-2">
                  <div className="flex items-center gap-2">
                    <div className="text-2xl font-black text-cyan-700">{healthScore.overall_score}%</div>
                    <div className="text-xs bg-cyan-100 text-cyan-700 px-2 py-0.5 rounded-full font-bold">HEALTH SCORE</div>
                  </div>
                  <p className="text-[10px] uppercase tracking-tighter text-cyan-500 font-bold">{healthScore.grade} GRADE MAINTAINED</p>
                </div>
              ) : "AI-powered maintenance forecasting."}
            </FeatureCard>

            {/* 5. Mood Sync */}
            <FeatureCard 
              title="Mood Sync" icon={Smile} color="bg-pink-600"
              onRun={() => moodMutation.mutate('energetic')} isLoading={moodMutation.isPending}
            >
              {moodInsights ? (
                <div className="space-y-2">
                  <p className="text-xs">Active Providers: <span className="font-bold text-pink-600">{moodInsights.total_active_providers}</span></p>
                  <div className="flex gap-1 flex-wrap">
                    {Object.entries(moodInsights.mood_distribution || {}).slice(0, 3).map(([m, count]: any) => (
                      <span key={m} className="px-1.5 py-0.5 bg-pink-50 text-[10px] rounded border border-pink-100 font-medium capitalize">{m}</span>
                    ))}
                  </div>
                </div>
              ) : "Provider energy and mood alignment."}
            </FeatureCard>

            {/* 6. Neighborhood Community */}
            <FeatureCard 
              title="Community" icon={Users} color="bg-emerald-600"
              onRun={() => communityMutation.mutate()} isLoading={communityMutation.isPending}
            >
              {communityRes ? (
                <div className="space-y-2">
                  <p className="text-xs font-semibold text-emerald-700">{communityRes.challenges?.length || 0} Local Challenges Active</p>
                  <div className="flex -space-x-2">
                    {[1,2,3].map(i => (
                      <div key={i} className="h-6 w-6 rounded-full border-2 border-white bg-emerald-100 flex items-center justify-center text-[10px] font-bold text-emerald-600 shadow-sm">U{i}</div>
                    ))}
                  </div>
                </div>
              ) : "Localized neighborhood participation."}
            </FeatureCard>

            {/* 7. Smart Bundles */}
            <FeatureCard 
              title="Service Bundles" icon={Package} color="bg-yellow-600"
              onRun={() => bundleMutation.mutate()} isLoading={bundleMutation.isPending}
            >
              <div className="space-y-2">
                <p>Intelligent service groupings with optimized pricing.</p>
                {bundlesRes?.recommendations && (
                   <span className="text-[10px] bg-yellow-100 text-yellow-700 px-2 py-0.5 rounded-full font-bold">NEW PACKS FOUND</span>
                )}
              </div>
            </FeatureCard>

            {/* 8. Live Events */}
            <FeatureCard 
              title="Service Events" icon={Calendar} color="bg-red-600"
              onRun={() => eventMutation.mutate()} isLoading={eventMutation.isPending}
            >
              <div className="space-y-2">
                <p>Hyper-local service showcases and real-time event booking.</p>
                {eventsRes?.upcoming?.length > 0 && (
                  <div className="flex items-center gap-1 text-[10px] text-red-600 font-black animate-pulse">
                    <div className="h-1.5 w-1.5 rounded-full bg-red-600"></div>
                    LIVE EVENT IN YOUR AREA
                  </div>
                )}
              </div>
            </FeatureCard>

            {/* 9. Swap Marketplace */}
            <FeatureCard 
              title="Swap Trade" icon={Repeat} color="bg-indigo-600"
              onRun={() => swapMutation.mutate()} isLoading={swapMutation.isPending}
            >
              <div className="space-y-2">
                <p>Peer-to-peer service swapping with secure hours verification.</p>
                <div className="flex items-center gap-2 text-[10px] font-bold text-indigo-600">
                  <ShieldCheck size={12} />
                  TRUSTED SWAP NETWORK
                </div>
              </div>
            </FeatureCard>

            {/* 10. AR Space Preview */}
            <FeatureCard 
              title="AR Preview" icon={Eye} color="bg-rose-600"
              onRun={() => arMutation.mutate()} isLoading={arMutation.isPending}
            >
              <div className="space-y-2">
                <p>Visualizing services in your space using augmented reality.</p>
                <div className="flex items-center gap-1 text-[10px] font-bold text-rose-500">
                  <Camera size={12} />
                  SPATIAL SCAN READY
                </div>
              </div>
            </FeatureCard>

            {/* 11. Service Roulette */}
            <FeatureCard 
              title="Discovery" icon={Play} color="bg-amber-600"
              onRun={() => rouletteMutation.mutate()} isLoading={rouletteMutation.isPending}
            >
              <div className="space-y-2">
                <p>Surprise recommendations with mystery packages.</p>
                <div className="flex items-center gap-1 text-[10px] font-bold text-amber-600">
                  <Gift size={12} />
                  PRIZE POOL: 5000 XP
                </div>
              </div>
            </FeatureCard>

            {/* 12. AI Concierge */}
            <FeatureCard 
              title="AI Concierge" icon={Bot} color="bg-violet-600"
              onRun={() => aiChatMutation.mutate("Optimize my schedule for tomorrow.")} isLoading={aiChatMutation.isPending}
            >
              <div className="space-y-2">
                <p>Conversational service management and proactive automation.</p>
                <div className="flex items-center gap-1 text-[10px] font-bold text-violet-600">
                  <MessageSquare size={12} />
                  AI AGENT ONLINE
                </div>
              </div>
            </FeatureCard>

            {/* Results Display */}
            {activeResult && (
              <ResultPanel title={activeResult.title} data={activeResult.data} />
            )}
          </div>

          <div className="mt-20 border-t border-gray-200 pt-12 flex flex-col md:flex-row items-center justify-between gap-8 mb-20">
            <div className="flex items-center gap-6">
                <div className="group relative">
                    <div className="absolute -inset-1 bg-gradient-to-r from-blue-600 to-indigo-600 rounded-full blur opacity-25 group-hover:opacity-50 transition duration-1000 group-hover:duration-200"></div>
                    <div className="relative flex items-center gap-3 bg-white px-6 py-3 rounded-full border border-gray-100 leading-none">
                        <Activity className="text-blue-600" size={18} />
                        <span className="text-gray-700 font-medium">Gateway: Connected</span>
                    </div>
                </div>
                <div className="flex items-center gap-3 bg-white px-6 py-3 rounded-full border border-gray-100 shadow-sm leading-none">
                    <Settings className="text-gray-400" size={18} />
                    <span className="text-gray-700 font-medium">Auto-Validation: On</span>
                </div>
            </div>
            
            <div className="flex -space-x-4 overflow-hidden">
                {[1,2,3,4,5].map(i => (
                    <img key={i} className="inline-block h-10 w-10 rounded-full ring-4 ring-white" src={`https://api.dicebear.com/7.x/avataaars/svg?seed=${i}`} alt="" />
                ))}
                <div className="flex items-center justify-center h-10 w-10 rounded-full bg-gray-100 ring-4 ring-white text-xs font-bold text-gray-400">+12</div>
            </div>
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
};

export default EnhancedFeatures;
