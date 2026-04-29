import React, { useState, useEffect } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { 
  BarChart3, Users, ShieldAlert, Zap, Globe, 
  Settings, MessageSquare, AlertCircle, TrendingUp,
  Map as MapIcon, Percent, Activity, Search, ChevronRight,
  DollarSign, Star, Award, Package, Calendar, TrendingDown
} from 'lucide-react';
import { dashboardAPI } from '../../services/api';
import toast from 'react-hot-toast';

const AdminDashboard: React.FC = () => {
  const { user } = useAuth();
  const [data, setData] = useState<any>(null);
  const [emergencyMode, setEmergencyMode] = useState(false);
  const [commissionRate, setCommissionRate] = useState(15);
  const [activeTab, setActiveTab] = useState<'overview' | 'providers' | 'customers' | 'analytics'>('overview');
  const [searchQuery, setSearchQuery] = useState('');
  const [timeRange, setTimeRange] = useState('7d');

  useEffect(() => {
    fetchAdminData();
  }, []);

  const fetchAdminData = async () => {
    try {
      const dashData = await dashboardAPI.getAdmin();
      setData(dashData);
    } catch (err) {
      console.error(err);
      toast.error('Failed to load dashboard data');
    }
  };

  const toggleEmergency = () => {
    setEmergencyMode(!emergencyMode);
    toast(emergencyMode ? 'Emergency mode deactivated' : 'Emergency mode ACTIVATED', {
      icon: emergencyMode ? '✅' : '🚨',
      style: { background: emergencyMode ? '#fff' : '#fee2e2', color: emergencyMode ? '#000' : '#991b1b' }
    });
  };

  const filteredProviders = data?.all_providers?.filter((p: any) => 
    p.full_name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    p.email?.toLowerCase().includes(searchQuery.toLowerCase())
  ) || [];

  const filteredCustomers = data?.all_customers?.filter((c: any) => 
    c.full_name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    c.email?.toLowerCase().includes(searchQuery.toLowerCase())
  ) || [];

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-blue-50 py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        
        {/* Admin Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between mb-10 gap-6">
          <div>
            <h1 className="text-4xl font-black text-gray-900 tracking-tight">Admin Control Center</h1>
            <p className="text-gray-600 font-medium mt-2">Complete platform analytics and management</p>
          </div>
          
          <div className="flex items-center space-x-4">
            <div className={`flex items-center px-6 py-3 rounded-2xl border-2 transition-all ${emergencyMode ? 'bg-red-50 border-red-500 text-red-700' : 'bg-white border-gray-200 text-gray-500'}`}>
              <Zap size={20} className={`mr-3 ${emergencyMode ? 'animate-pulse fill-red-500' : ''}`} />
              <span className="font-bold mr-4 uppercase text-xs tracking-widest">Emergency</span>
              <button 
                onClick={toggleEmergency}
                className={`w-12 h-6 rounded-full relative transition-colors ${emergencyMode ? 'bg-red-500' : 'bg-gray-200'}`}
              >
                <div className={`absolute top-1 w-4 h-4 bg-white rounded-full transition-all ${emergencyMode ? 'right-1' : 'left-1'}`} />
              </button>
            </div>
          </div>
        </div>

        {/* KPI Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-10">
          <div className="bg-white p-6 rounded-3xl shadow-lg border border-gray-100">
            <div className="w-12 h-12 bg-blue-50 text-blue-600 rounded-2xl flex items-center justify-center mb-4">
              <DollarSign size={24} />
            </div>
            <p className="text-xs font-bold text-gray-400 uppercase tracking-widest">Total Revenue</p>
            <h3 className="text-3xl font-black text-gray-900 mt-1">₹{data?.total_revenue?.toLocaleString() || '0'}</h3>
            <p className="text-sm text-green-600 font-semibold mt-2">↑ ₹{data?.week_revenue || 0} this week</p>
          </div>

          <div className="bg-white p-6 rounded-3xl shadow-lg border border-gray-100">
            <div className="w-12 h-12 bg-purple-50 text-purple-600 rounded-2xl flex items-center justify-center mb-4">
              <Users size={24} />
            </div>
            <p className="text-xs font-bold text-gray-400 uppercase tracking-widest">Total Users</p>
            <h3 className="text-3xl font-black text-gray-900 mt-1">{(data?.total_users || 0) + (data?.total_providers || 0)}</h3>
            <p className="text-sm text-gray-600 font-semibold mt-2">{data?.total_users || 0} customers, {data?.total_providers || 0} providers</p>
          </div>

          <div className="bg-white p-6 rounded-3xl shadow-lg border border-gray-100">
            <div className="w-12 h-12 bg-green-50 text-green-600 rounded-2xl flex items-center justify-center mb-4">
              <Package size={24} />
            </div>
            <p className="text-xs font-bold text-gray-400 uppercase tracking-widest">Total Bookings</p>
            <h3 className="text-3xl font-black text-gray-900 mt-1">{data?.total_bookings || 0}</h3>
            <p className="text-sm text-green-600 font-semibold mt-2">↑ {data?.today_bookings || 0} today</p>
          </div>

          <div className="bg-white p-6 rounded-3xl shadow-lg border border-gray-100">
            <div className="w-12 h-12 bg-orange-50 text-orange-600 rounded-2xl flex items-center justify-center mb-4">
              <Activity size={24} />
            </div>
            <p className="text-xs font-bold text-gray-400 uppercase tracking-widest">Completion Rate</p>
            <h3 className="text-3xl font-black text-gray-900 mt-1">
              {data?.total_bookings ? Math.round((data.completed_bookings / data.total_bookings) * 100) : 0}%
            </h3>
            <p className="text-sm text-gray-600 font-semibold mt-2">{data?.completed_bookings || 0} completed</p>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="bg-white rounded-3xl shadow-lg border border-gray-100 mb-8 p-2">
          <div className="flex space-x-2">
            <button
              onClick={() => setActiveTab('overview')}
              className={`flex-1 flex items-center justify-center py-4 px-6 rounded-2xl font-bold text-sm transition-all ${
                activeTab === 'overview' 
                  ? 'bg-blue-600 text-white shadow-lg' 
                  : 'text-gray-600 hover:bg-gray-50 border border-transparent hover:border-gray-200'
              }`}
            >
              <BarChart3 size={18} className="mr-2" /> Overview
            </button>
            <button
              onClick={() => setActiveTab('providers')}
              className={`flex-1 flex items-center justify-center py-4 px-6 rounded-2xl font-bold text-sm transition-all ${
                activeTab === 'providers' 
                  ? 'bg-blue-600 text-white shadow-lg' 
                  : 'text-gray-600 hover:bg-gray-50 border border-transparent hover:border-gray-200'
              }`}
            >
              <Users size={18} className="mr-2" /> Providers ({data?.total_providers || 0})
            </button>
            <button
              onClick={() => setActiveTab('customers')}
              className={`flex-1 flex items-center justify-center py-4 px-6 rounded-2xl font-bold text-sm transition-all ${
                activeTab === 'customers' 
                  ? 'bg-blue-600 text-white shadow-lg' 
                  : 'text-gray-600 hover:bg-gray-50 border border-transparent hover:border-gray-200'
              }`}
            >
              <Globe size={18} className="mr-2" /> Customers ({data?.total_users || 0})
            </button>
            <button
              onClick={() => setActiveTab('analytics')}
              className={`flex-1 flex items-center justify-center py-4 px-6 rounded-2xl font-bold text-sm transition-all ${
                activeTab === 'analytics' 
                  ? 'bg-blue-600 text-white shadow-lg' 
                  : 'text-gray-600 hover:bg-gray-50 border border-transparent hover:border-gray-200'
              }`}
            >
              <Activity size={18} className="mr-2" /> Analytics
            </button>
          </div>
        </div>

        {/* Overview Tab */}
        {activeTab === 'overview' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            {/* Top Providers */}
            <div className="bg-white rounded-3xl shadow-lg border border-gray-100 p-8">
              <h2 className="text-2xl font-black text-gray-900 mb-6 flex items-center">
                <Award className="mr-3 text-yellow-500" size={28} />
                Top Earning Providers
              </h2>
              <div className="space-y-4">
                {data?.top_providers?.slice(0, 5).map((provider: any, idx: number) => (
                  <div key={provider._id} className="flex items-center justify-between p-4 bg-gray-50 rounded-2xl hover:bg-blue-50 transition-all">
                    <div className="flex items-center space-x-4">
                      <div className="w-10 h-10 bg-gradient-to-br from-blue-400 to-purple-500 rounded-full flex items-center justify-center text-white font-bold">
                        #{idx + 1}
                      </div>
                      <div>
                        <p className="font-bold text-gray-900">{provider.full_name}</p>
                        <p className="text-xs text-gray-500">{provider.email}</p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="text-lg font-black text-green-600">₹{provider.analytics?.total_earnings?.toFixed(2) || 0}</p>
                      <p className="text-xs text-gray-500">{provider.analytics?.completed_bookings || 0} bookings</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Top Customers */}
            <div className="bg-white rounded-3xl shadow-lg border border-gray-100 p-8">
              <h2 className="text-2xl font-black text-gray-900 mb-6 flex items-center">
                <Star className="mr-3 text-blue-500" size={28} />
                Top Spending Customers
              </h2>
              <div className="space-y-4">
                {data?.top_customers?.slice(0, 5).map((customer: any, idx: number) => (
                  <div key={customer._id} className="flex items-center justify-between p-4 bg-gray-50 rounded-2xl hover:bg-blue-50 transition-all">
                    <div className="flex items-center space-x-4">
                      <div className="w-10 h-10 bg-gradient-to-br from-green-400 to-blue-500 rounded-full flex items-center justify-center text-white font-bold">
                        #{idx + 1}
                      </div>
                      <div>
                        <p className="font-bold text-gray-900">{customer.full_name}</p>
                        <p className="text-xs text-gray-500 capitalize">{customer.analytics?.loyalty_tier || 'bronze'} tier</p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="text-lg font-black text-blue-600">₹{customer.analytics?.total_spent?.toFixed(2) || 0}</p>
                      <p className="text-xs text-gray-500">{customer.analytics?.total_bookings || 0} bookings</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Recent Transactions */}
            <div className="bg-white rounded-3xl shadow-lg border border-gray-100 p-8 lg:col-span-2">
              <h2 className="text-2xl font-black text-gray-900 mb-6">Recent Transactions</h2>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-gray-200">
                      <th className="text-left py-3 px-4 text-xs font-bold text-gray-500 uppercase">Transaction ID</th>
                      <th className="text-left py-3 px-4 text-xs font-bold text-gray-500 uppercase">Amount</th>
                      <th className="text-left py-3 px-4 text-xs font-bold text-gray-500 uppercase">Status</th>
                      <th className="text-left py-3 px-4 text-xs font-bold text-gray-500 uppercase">Date</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data?.recent_transactions?.map((txn: any) => (
                      <tr key={txn._id} className="border-b border-gray-100 hover:bg-gray-50">
                        <td className="py-4 px-4 font-mono text-sm text-gray-600">{txn._id.slice(-8)}</td>
                        <td className="py-4 px-4 font-bold text-gray-900">₹{txn.final_amount || txn.amount || 0}</td>
                        <td className="py-4 px-4">
                          <span className={`px-3 py-1 rounded-full text-xs font-bold ${
                            txn.status === 'completed' ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'
                          }`}>
                            {txn.status}
                          </span>
                        </td>
                        <td className="py-4 px-4 text-sm text-gray-600">{new Date(txn.created_at).toLocaleDateString()}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* Providers Tab */}
        {activeTab === 'providers' && (
          <div>
            <div className="bg-white rounded-3xl shadow-lg border border-gray-100 p-8 mb-6">
              <div className="relative">
                <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 text-gray-400" size={20} />
                <input
                  type="text"
                  placeholder="Search providers by name or email..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-12 pr-4 py-4 border-2 border-gray-200 rounded-2xl focus:outline-none focus:border-blue-500 font-medium"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 gap-6">
              {filteredProviders.map((provider: any) => (
                <div key={provider._id} className="bg-white rounded-3xl shadow-lg border border-gray-100 p-8 hover:shadow-xl transition-all">
                  <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
                    <div className="flex items-center space-x-6">
                      <div className="w-16 h-16 bg-gradient-to-br from-blue-400 to-purple-500 rounded-2xl flex items-center justify-center text-white text-2xl font-bold">
                        {provider.full_name?.charAt(0) || 'P'}
                      </div>
                      <div>
                        <h3 className="text-xl font-black text-gray-900">{provider.full_name}</h3>
                        <p className="text-sm text-gray-500">{provider.email}</p>
                        <p className="text-sm text-gray-500">{provider.phone}</p>
                      </div>
                    </div>

                    <div className="grid grid-cols-2 lg:grid-cols-4 gap-6">
                      <div className="text-center">
                        <p className="text-xs font-bold text-gray-400 uppercase mb-1">Earnings</p>
                    <p className="text-2xl font-black text-green-600">₹{provider.analytics?.total_earnings?.toFixed(0) || 0}</p>
                      </div>
                      <div className="text-center">
                        <p className="text-xs font-bold text-gray-400 uppercase mb-1">Bookings</p>
                        <p className="text-2xl font-black text-blue-600">{provider.analytics?.total_bookings || 0}</p>
                      </div>
                      <div className="text-center">
                        <p className="text-xs font-bold text-gray-400 uppercase mb-1">Rating</p>
                        <p className="text-2xl font-black text-yellow-600 flex items-center justify-center">
                          <Star size={20} className="fill-yellow-500 mr-1" />
                          {provider.analytics?.average_rating || 0}
                        </p>
                      </div>
                      <div className="text-center">
                        <p className="text-xs font-bold text-gray-400 uppercase mb-1">Completion</p>
                        <p className="text-2xl font-black text-purple-600">{provider.analytics?.completion_rate || 0}%</p>
                      </div>
                    </div>
                  </div>

                  <div className="mt-6 pt-6 border-t border-gray-100 grid grid-cols-2 lg:grid-cols-5 gap-4 text-sm">
                    <div>
                      <p className="text-gray-500 font-semibold">Completed</p>
                      <p className="font-bold text-gray-900">{provider.analytics?.completed_bookings || 0}</p>
                    </div>
                    <div>
                      <p className="text-gray-500 font-semibold">Pending</p>
                      <p className="font-bold text-gray-900">{provider.analytics?.pending_bookings || 0}</p>
                    </div>
                    <div>
                      <p className="text-gray-500 font-semibold">Cancelled</p>
                      <p className="font-bold text-gray-900">{provider.analytics?.cancelled_bookings || 0}</p>
                    </div>
                    <div>
                      <p className="text-gray-500 font-semibold">Reviews</p>
                      <p className="font-bold text-gray-900">{provider.analytics?.total_reviews || 0}</p>
                    </div>
                    <div>
                      <p className="text-gray-500 font-semibold">Services</p>
                      <p className="font-bold text-gray-900">{provider.analytics?.services_count || 0}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Customers Tab */}
        {activeTab === 'customers' && (
          <div>
            <div className="bg-white rounded-3xl shadow-lg border border-gray-100 p-8 mb-6">
              <div className="relative">
                <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 text-gray-400" size={20} />
                <input
                  type="text"
                  placeholder="Search customers by name or email..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-12 pr-4 py-4 border-2 border-gray-200 rounded-2xl focus:outline-none focus:border-blue-500 font-medium"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 gap-6">
              {filteredCustomers.map((customer: any) => (
                <div key={customer._id} className="bg-white rounded-3xl shadow-lg border border-gray-100 p-8 hover:shadow-xl transition-all">
                  <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
                    <div className="flex items-center space-x-6">
                      <div className="w-16 h-16 bg-gradient-to-br from-green-400 to-blue-500 rounded-2xl flex items-center justify-center text-white text-2xl font-bold">
                        {customer.full_name?.charAt(0) || 'C'}
                      </div>
                      <div>
                        <h3 className="text-xl font-black text-gray-900">{customer.full_name}</h3>
                        <p className="text-sm text-gray-500">{customer.email}</p>
                        <div className="flex items-center mt-2 space-x-2">
                          <Award size={16} className="text-yellow-500" />
                          <span className="text-sm font-bold text-gray-700 capitalize">{customer.analytics?.loyalty_tier || 'bronze'} Tier</span>
                          <span className="text-sm text-gray-500">• {customer.analytics?.loyalty_points || 0} pts</span>
                        </div>
                      </div>
                    </div>

                    <div className="grid grid-cols-2 lg:grid-cols-3 gap-6">
                      <div className="text-center">
                        <p className="text-xs font-bold text-gray-400 uppercase mb-1">Total Spent</p>
                        <p className="text-2xl font-black text-blue-600">₹{customer.analytics?.total_spent?.toFixed(0) || 0}</p>
                      </div>
                      <div className="text-center">
                        <p className="text-xs font-bold text-gray-400 uppercase mb-1">Bookings</p>
                        <p className="text-2xl font-black text-purple-600">{customer.analytics?.total_bookings || 0}</p>
                      </div>
                      <div className="text-center">
                        <p className="text-xs font-bold text-gray-400 uppercase mb-1">Avg Value</p>
                        <p className="text-2xl font-black text-green-600">₹{customer.analytics?.avg_booking_value?.toFixed(0) || 0}</p>
                      </div>
                    </div>
                  </div>

                  <div className="mt-6 pt-6 border-t border-gray-100 grid grid-cols-2 lg:grid-cols-4 gap-4 text-sm">
                    <div>
                      <p className="text-gray-500 font-semibold">Completed</p>
                      <p className="font-bold text-gray-900">{customer.analytics?.completed_bookings || 0}</p>
                    </div>
                    <div>
                      <p className="text-gray-500 font-semibold">Cancelled</p>
                      <p className="font-bold text-gray-900">{customer.analytics?.cancelled_bookings || 0}</p>
                    </div>
                    <div>
                      <p className="text-gray-500 font-semibold">Reviews Given</p>
                      <p className="font-bold text-gray-900">{customer.analytics?.reviews_given || 0}</p>
                    </div>
                    <div>
                      <p className="text-gray-500 font-semibold">Loyalty Points</p>
                      <p className="font-bold text-gray-900">{customer.analytics?.loyalty_points || 0}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Analytics Tab */}
        {activeTab === 'analytics' && (
          <div className="space-y-6">
            {/* Time Range Selector */}
            <div className="bg-white rounded-3xl shadow-lg border border-gray-100 p-6">
              <div className="flex items-center justify-between">
                <h2 className="text-2xl font-black text-gray-900">Platform Analytics</h2>
                <select 
                  value={timeRange}
                  onChange={(e) => setTimeRange(e.target.value)}
                  className="px-4 py-2 border-2 border-gray-200 rounded-xl font-bold focus:outline-none focus:border-blue-500"
                >
                  <option value="24h">Last 24 Hours</option>
                  <option value="7d">Last 7 Days</option>
                  <option value="30d">Last 30 Days</option>
                  <option value="90d">Last 90 Days</option>
                </select>
              </div>
            </div>

            {/* Revenue & Growth */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div className="bg-white rounded-3xl shadow-lg border border-gray-100 p-8">
                <h3 className="text-xl font-black text-gray-900 mb-6 flex items-center">
                  <TrendingUp className="mr-3 text-green-500" size={24} />
                  Revenue Growth
                </h3>
                <div className="space-y-4">
                  <div className="flex items-center justify-between p-4 bg-green-50 rounded-2xl">
                    <div>
                      <p className="text-sm text-gray-600 font-semibold">This Week</p>
                      <p className="text-2xl font-black text-green-600">₹{data?.week_revenue?.toLocaleString() || 0}</p>
                    </div>
                    <div className="text-green-600 font-bold text-lg">↑ 12%</div>
                  </div>
                  <div className="flex items-center justify-between p-4 bg-blue-50 rounded-2xl">
                    <div>
                      <p className="text-sm text-gray-600 font-semibold">This Month</p>
                      <p className="text-2xl font-black text-blue-600">₹{((data?.week_revenue || 0) * 4).toLocaleString()}</p>
                    </div>
                    <div className="text-blue-600 font-bold text-lg">↑ 8%</div>
                  </div>
                  <div className="flex items-center justify-between p-4 bg-purple-50 rounded-2xl">
                    <div>
                      <p className="text-sm text-gray-600 font-semibold">Average Order Value</p>
                      <p className="text-2xl font-black text-purple-600">₹{data?.total_bookings ? (data.total_revenue / data.total_bookings).toFixed(2) : 0}</p>
                    </div>
                    <div className="text-purple-600 font-bold text-lg">↑ 5%</div>
                  </div>
                </div>
              </div>

              <div className="bg-white rounded-3xl shadow-lg border border-gray-100 p-8">
                <h3 className="text-xl font-black text-gray-900 mb-6 flex items-center">
                  <Activity className="mr-3 text-blue-500" size={24} />
                  Platform Activity
                </h3>
                <div className="space-y-4">
                  <div className="flex items-center justify-between p-4 bg-gray-50 rounded-2xl">
                    <div>
                      <p className="text-sm text-gray-600 font-semibold">Active Providers</p>
                      <p className="text-2xl font-black text-gray-900">{Math.floor((data?.total_providers || 0) * 0.7)}</p>
                    </div>
                    <div className="text-green-600 font-bold">70%</div>
                  </div>
                  <div className="flex items-center justify-between p-4 bg-gray-50 rounded-2xl">
                    <div>
                      <p className="text-sm text-gray-600 font-semibold">Active Customers</p>
                      <p className="text-2xl font-black text-gray-900">{Math.floor((data?.total_users || 0) * 0.45)}</p>
                    </div>
                    <div className="text-green-600 font-bold">45%</div>
                  </div>
                  <div className="flex items-center justify-between p-4 bg-gray-50 rounded-2xl">
                    <div>
                      <p className="text-sm text-gray-600 font-semibold">Avg Response Time</p>
                      <p className="text-2xl font-black text-gray-900">12 min</p>
                    </div>
                    <div className="text-green-600 font-bold">↓ 3 min</div>
                  </div>
                </div>
              </div>
            </div>

            {/* Service Categories Performance */}
            <div className="bg-white rounded-3xl shadow-lg border border-gray-100 p-8">
              <h3 className="text-xl font-black text-gray-900 mb-6">Top Service Categories</h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {(data?.category_stats || []).map((category: any, idx: number) => (
                  <div key={idx} className="p-6 bg-gradient-to-br from-blue-50 to-purple-50 rounded-2xl">
                    <div className="flex items-center justify-between mb-4">
                      <h4 className="text-lg font-black text-gray-900">{category.name}</h4>
                      <span className="text-green-600 font-bold text-sm">↑ {category.growth}%</span>
                    </div>
                    <div className="space-y-2">
                      <div className="flex justify-between">
                        <span className="text-sm text-gray-600">Bookings</span>
                        <span className="font-bold text-gray-900">{category.bookings}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-sm text-gray-600">Revenue</span>
                        <span className="font-bold text-green-600">₹{category.revenue?.toLocaleString()}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* System Health */}
            <div className="bg-white rounded-3xl shadow-lg border border-gray-100 p-8">
              <h3 className="text-xl font-black text-gray-900 mb-6 flex items-center">
                <ShieldAlert className="mr-3 text-blue-500" size={24} />
                System Health
              </h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="text-center p-4 bg-green-50 rounded-xl">
                  <div className="text-3xl font-black text-green-600">{data?.system_health?.uptime || '99.9%'}</div>
                  <div className="text-sm text-gray-600 font-bold mt-1">Uptime</div>
                </div>
                <div className="text-center p-4 bg-blue-50 rounded-xl">
                  <div className="text-3xl font-black text-blue-600">{data?.system_health?.avg_load_time || '1.2s'}</div>
                  <div className="text-sm text-gray-600 font-bold mt-1">Avg Load Time</div>
                </div>
                <div className="text-center p-4 bg-purple-50 rounded-xl">
                  <div className="text-3xl font-black text-purple-600">{data?.system_health?.error_rate || '0.01%'}</div>
                  <div className="text-sm text-gray-600 font-bold mt-1">Error Rate</div>
                </div>
                <div className="text-center p-4 bg-orange-50 rounded-xl">
                  <div className="text-3xl font-black text-orange-600">{data?.system_health?.avg_rating || '4.8'}/5</div>
                  <div className="text-sm text-gray-600 font-bold mt-1">Avg Rating</div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default AdminDashboard;
