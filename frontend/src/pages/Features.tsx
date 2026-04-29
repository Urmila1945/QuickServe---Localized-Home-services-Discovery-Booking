import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import VoiceHail from '../components/features/VoiceHail';
import NeighborhoodProof from '../components/features/NeighborhoodProof';
import SmartScheduler from '../components/features/SmartScheduler';
import { Mic, Users, Calendar, Sparkles } from 'lucide-react';

const Features: React.FC = () => {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<'voice' | 'neighborhood' | 'scheduler'>('voice');

  const tabs = [
    { id: 'voice' as const, name: 'Voice Hail', icon: Mic, color: 'from-red-500 to-orange-500' },
    { id: 'neighborhood' as const, name: 'Neighborhood Trust', icon: Users, color: 'from-green-500 to-emerald-600' },
    { id: 'scheduler' as const, name: 'Smart Scheduler', icon: Calendar, color: 'from-blue-500 to-purple-600' },
  ];

  return (
    <div className="min-h-screen bg-transparent py-8">
      {/* Hero Section */}
      <div className="bg-white/10 backdrop-blur-md border-b border-white/20 text-white py-16 mb-8">
        <div className="max-w-7xl mx-auto px-4 text-center">
          <div className="inline-flex items-center justify-center w-20 h-20 bg-white/20 backdrop-blur-md rounded-2xl mb-6 float-animation">
            <Sparkles className="w-10 h-10 text-white" />
          </div>
          <h1 className="text-5xl font-bold mb-4 drop-shadow-lg animate-fade-in">
            ✨ Unique Features
          </h1>
          <p className="text-xl opacity-90 drop-shadow-md animate-fade-in-up max-w-2xl mx-auto">
            Experience the future of home services with AI-powered matching, community trust, and intelligent scheduling
          </p>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4">
        {/* Tab Navigation */}
        <div className="flex flex-wrap justify-center gap-4 mb-12">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`relative px-8 py-4 rounded-2xl font-semibold text-lg transition-all duration-300 ${
                activeTab === tab.id
                  ? `bg-gradient-to-r ${tab.color} text-white shadow-2xl scale-105`
                  : 'bg-white text-gray-700 hover:shadow-lg hover:scale-105'
              }`}
            >
              <div className="flex items-center gap-3">
                <tab.icon className="w-6 h-6" />
                <span>{tab.name}</span>
              </div>
              {activeTab === tab.id && (
                <div className="absolute -bottom-2 left-1/2 transform -translate-x-1/2 w-12 h-1 bg-white rounded-full"></div>
              )}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="animate-fade-in">
          {activeTab === 'voice' && (
            <div>
              <VoiceHail onHailComplete={(service, urgency) => {
                navigate(`/services?q=${service}&emergency=${urgency === 'high'}`);
              }} />
            </div>
          )}

          {activeTab === 'neighborhood' && (
            <div>
              <NeighborhoodProof />
            </div>
          )}

          {activeTab === 'scheduler' && (
            <div>
              <SmartScheduler />
            </div>
          )}
        </div>

        {/* Additional Benefits */}
        <div className="mt-16 grid md:grid-cols-3 gap-8">
          <div className="bg-white rounded-2xl shadow-xl p-8 text-center hover:shadow-2xl transition-all duration-300 hover:scale-105">
            <div className="w-16 h-16 bg-gradient-to-br from-purple-500 to-pink-600 rounded-full flex items-center justify-center mx-auto mb-4">
              <span className="text-3xl">🎯</span>
            </div>
            <h3 className="text-xl font-bold text-gray-900 mb-2">99% Match Accuracy</h3>
            <p className="text-gray-600">Our AI finds the perfect provider for your specific needs</p>
          </div>

          <div className="bg-white rounded-2xl shadow-xl p-8 text-center hover:shadow-2xl transition-all duration-300 hover:scale-105">
            <div className="w-16 h-16 bg-gradient-to-br from-blue-500 to-cyan-600 rounded-full flex items-center justify-center mx-auto mb-4">
              <span className="text-3xl">⚡</span>
            </div>
            <h3 className="text-xl font-bold text-gray-900 mb-2">2-Minute Response</h3>
            <p className="text-gray-600">Get matched with available providers in under 2 minutes</p>
          </div>

          <div className="bg-white rounded-2xl shadow-xl p-8 text-center hover:shadow-2xl transition-all duration-300 hover:scale-105">
            <div className="w-16 h-16 bg-gradient-to-br from-green-500 to-emerald-600 rounded-full flex items-center justify-center mx-auto mb-4">
              <span className="text-3xl">💰</span>
            </div>
            <h3 className="text-xl font-bold text-gray-900 mb-2">Save Up to 25%</h3>
            <p className="text-gray-600">Smart scheduling helps you save on peak-hour premiums</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Features;
