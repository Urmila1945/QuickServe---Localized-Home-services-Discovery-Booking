import React, { useState, useEffect } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { 
  Calendar, DollarSign, TrendingUp, Map as MapIcon, MapPin,
  MessageSquare, Image as ImageIcon, Bot, ChevronRight,
  Clock, Star, Users, ArrowUpRight, Route
} from 'lucide-react';
import { dashboardAPI, aiAPI } from '../../services/api';
import toast from 'react-hot-toast';

const ProviderDashboard: React.FC = () => {
  const { user } = useAuth();
  const [data, setData] = useState<any>(null);
  const [pricingSuggestions, setPricingSuggestions] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchProviderData();
  }, []);

  const fetchProviderData = async () => {
    try {
      const [dashData, pricing] = await Promise.all([
        dashboardAPI.getProvider(),
        aiAPI.smartMatch('plumbing', { latitude: 12.9716, longitude: 77.5946 }) // Mock for pricing context
      ]);
      setData(dashData);
      setPricingSuggestions({ suggested_rate: 650, market_average: 580 });
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#F9FAFB] py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        
        {/* Top Header: Stats Overview */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-10">
          <div className="bg-white p-6 rounded-[2rem] shadow-xl shadow-blue-900/5 border border-blue-50">
            <div className="flex justify-between items-start mb-4">
              <div className="p-3 bg-blue-50 text-blue-600 rounded-2xl">
                <DollarSign size={24} />
              </div>
              <span className="text-xs font-bold text-green-600 bg-green-50 px-2 py-1 rounded-full">+12.5%</span>
            </div>
            <p className="text-sm font-medium text-gray-500">Total Earnings</p>
            <h3 className="text-2xl font-black text-[#1E293B] mt-1">₹{data?.total_earnings?.toLocaleString() || '0'}</h3>
          </div>

          <div className="bg-white p-6 rounded-[2rem] shadow-xl shadow-purple-900/5 border border-purple-50">
            <div className="flex justify-between items-start mb-4">
              <div className="p-3 bg-purple-50 text-purple-600 rounded-2xl">
                <Route size={24} />
              </div>
              <span className="text-xs font-bold text-green-600 bg-green-50 px-2 py-1 rounded-full">{data?.route_efficiency > 90 ? 'Optimal' : 'Good'}</span>
            </div>
            <p className="text-sm font-medium text-gray-500">Route Efficiency</p>
            <h3 className="text-2xl font-black text-[#1E293B] mt-1">{data?.route_efficiency || 90}%</h3>
          </div>

          <div className="bg-white p-6 rounded-[2rem] shadow-xl shadow-orange-900/5 border border-orange-50">
            <div className="flex justify-between items-start mb-4">
              <div className="p-3 bg-orange-50 text-orange-600 rounded-2xl">
                <Star size={24} />
              </div>
              <span className="text-xs font-bold text-orange-600 bg-orange-100 px-2 py-1 rounded-full">Top 5%</span>
            </div>
            <p className="text-sm font-medium text-gray-500">QuickServe Score</p>
            <h3 className="text-2xl font-black text-[#1E293B] mt-1">{data?.quickserve_score || 85}/100</h3>
          </div>

          <div className="bg-white p-6 rounded-[2rem] shadow-xl shadow-green-900/5 border border-green-50">
            <div className="flex justify-between items-start mb-4">
              <div className="p-3 bg-green-50 text-green-600 rounded-2xl">
                <Users size={24} />
              </div>
              <span className="text-xs font-bold text-green-600 bg-green-50 px-2 py-1 rounded-full">Active</span>
            </div>
            <p className="text-sm font-medium text-gray-500">Repeat Customers</p>
            <h3 className="text-2xl font-black text-[#1E293B] mt-1">{data?.repeat_customer_rate || 0}%</h3>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Main Column: Calendar & Jobs */}
          <div className="lg:col-span-2 space-y-8">
            
            {/* AI Optimized Calendar */}
            <div className="bg-white rounded-[2.5rem] shadow-2xl shadow-gray-200/50 border border-gray-100 overflow-hidden">
              <div className="p-8 border-b border-gray-50 flex justify-between items-center">
                <h2 className="text-xl font-bold text-[#1E293B] flex items-center">
                  <Calendar className="mr-3 text-primary-500" />
                  AI Smart Schedule
                </h2>
                <div className="flex space-x-2">
                  <button className="px-4 py-2 bg-primary-50 text-primary-600 rounded-xl text-xs font-bold hover:bg-primary-100 transition-colors">Optimize Route</button>
                </div>
              </div>
              
              <div className="p-8">
                <div className="space-y-6">
                  {(data?.active_jobs || []).length > 0 ? (data.active_jobs.map((job: any, i: number) => (
                    <div key={job._id} className="flex items-center space-x-6 group cursor-pointer">
                      <div className="w-20 text-right">
                        <p className="text-sm font-black text-[#1E293B]">{9 + i}:00 AM</p>
                        <p className="text-[10px] font-bold text-gray-400 uppercase tracking-tighter">60 Mins</p>
                      </div>
                      <div className="relative w-4">
                        <div className="absolute top-0 bottom-0 left-1/2 -translate-x-1/2 w-0.5 bg-gray-100 group-last:bottom-1/2" />
                        <div className="relative w-4 h-4 rounded-full bg-white border-4 border-primary-500 z-10" />
                      </div>
                      <div className="flex-1 bg-gray-50 p-5 rounded-3xl group-hover:bg-primary-50 transition-all border border-transparent group-hover:border-primary-100">
                        <div className="flex justify-between items-start">
                          <div>
                            <h4 className="font-bold text-[#1E293B]">{job.category || job.service_name}</h4>
                            <p className="text-xs text-gray-500 flex items-center mt-1">
                              <MapPin size={12} className="mr-1" /> {10 + i * 2} km away (Optimized Path)
                            </p>
                          </div>
                          <span className="text-[10px] font-bold px-2 py-1 bg-white rounded-lg shadow-sm uppercase">{job.status}</span>
                        </div>
                      </div>
                    </div>
                  ))) : (
                    <div className="text-center py-10">
                      <p className="text-gray-400 font-bold">No active jobs scheduled for today.</p>
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Quick Management */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="bg-[#1E293B] p-8 rounded-[2.5rem] text-white shadow-2xl">
                <div className="flex items-center space-x-3 mb-6">
                  <Bot className="text-primary-400" />
                  <h3 className="font-bold">AI Bot Controls</h3>
                </div>
                <div className="space-y-4">
                  <div className="flex justify-between items-center p-4 bg-white/5 rounded-2xl border border-white/10">
                    <span className="text-sm font-medium">Auto-Accept Bookings</span>
                    <div className="w-10 h-6 bg-primary-500 rounded-full relative">
                      <div className="absolute right-1 top-1 w-4 h-4 bg-white rounded-full" />
                    </div>
                  </div>
                  <div className="flex justify-between items-center p-4 bg-white/5 rounded-2xl border border-white/10">
                    <span className="text-sm font-medium">Dynamic Pricing Aggression</span>
                    <span className="text-xs font-bold text-primary-400">BALANCED</span>
                  </div>
                </div>
              </div>

              <div className="bg-white p-8 rounded-[2.5rem] shadow-xl border border-gray-100">
                <div className="flex items-center space-x-3 mb-6">
                  <TrendingUp className="text-green-500" />
                  <h3 className="font-bold">Smart Pricing</h3>
                </div>
                <div className="p-4 bg-green-50 rounded-2xl border border-green-100 mb-4">
                  <p className="text-[10px] font-bold text-green-700 uppercase tracking-widest mb-1">AI Recommendation</p>
                  <p className="text-sm text-green-800">High demand in your area. Suggest increasing rate by <span className="font-black">15%</span> for weekend slots.</p>
                </div>
                <div className="flex justify-between items-end">
                  <div>
                    <p className="text-xs text-gray-400 font-bold uppercase tracking-tighter">Current Base</p>
                    <p className="text-2xl font-black text-[#1E293B]">₹{user?.provider_profile?.base_rate || '600'}/hr</p>
                  </div>
                  <button className="bg-[#1E293B] text-white px-6 py-2 rounded-xl text-xs font-bold hover:bg-black transition-all">Update Rates</button>
                </div>
              </div>
            </div>
          </div>

          {/* Sidebar: Chat & Portfolio */}
          <div className="space-y-8">
            
            {/* Customer Chat Preview */}
            <div className="bg-white p-8 rounded-[2.5rem] shadow-xl border border-gray-100">
              <div className="flex justify-between items-center mb-6">
                <h2 className="text-lg font-extrabold text-[#1E293B]">Recent Chats</h2>
                <MessageSquare size={20} className="text-primary-500" />
              </div>
              <div className="space-y-4">
                {[1, 2].map(i => (
                  <div key={i} className="flex items-center space-x-4 p-3 hover:bg-gray-50 rounded-2xl transition-colors cursor-pointer border border-transparent hover:border-gray-100">
                    <div className="w-12 h-12 rounded-full bg-gray-200" />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-bold text-[#1E293B] truncate">Sarah Wilson</p>
                      <p className="text-xs text-gray-500 truncate">Is it possible to come 30 mins early?</p>
                    </div>
                    {i === 1 && <div className="w-2 h-2 bg-primary-500 rounded-full" />}
                  </div>
                ))}
              </div>
              <button className="w-full mt-6 py-3 rounded-2xl bg-gray-50 text-[#1E293B] font-bold text-sm hover:bg-primary-600 hover:text-white transition-all">
                Open Messenger
              </button>
            </div>

            {/* Portfolio with AI Captions */}
            <div className="bg-white p-8 rounded-[2.5rem] shadow-xl border border-gray-100">
              <div className="flex justify-between items-center mb-6">
                <h2 className="text-lg font-extrabold text-[#1E293B]">Portfolio</h2>
                <ImageIcon size={20} className="text-purple-500" />
              </div>
              <div className="grid grid-cols-2 gap-3 mb-6">
                {[1, 2, 3, 4].map(i => (
                  <div key={i} className="aspect-square bg-gray-100 rounded-2xl border-2 border-dashed border-gray-200 flex items-center justify-center">
                    <Star size={16} className="text-gray-300" />
                  </div>
                ))}
              </div>
              <div className="p-4 bg-purple-50 rounded-2xl border border-purple-100">
                <p className="text-[10px] font-bold text-purple-700 uppercase tracking-widest flex items-center mb-1">
                  <Bot size={12} className="mr-1" /> AI Captioning Active
                </p>
                <p className="text-[10px] text-purple-600 leading-tight">Last upload: "Expert pipe installation with premium finish in residential bathroom."</p>
              </div>
              <button className="w-full mt-6 py-3 rounded-2xl bg-[#1E293B] text-white font-bold text-sm hover:shadow-lg transition-all">
                Upload New Work
              </button>
            </div>

          </div>
        </div>
      </div>
    </div>
  );
};

export default ProviderDashboard;
