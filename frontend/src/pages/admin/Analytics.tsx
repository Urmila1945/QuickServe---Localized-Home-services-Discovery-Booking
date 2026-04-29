import React, { useState, useEffect } from 'react';
import { BarChart, Bar, LineChart, Line, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { TrendingUp, Users, DollarSign, Activity, MapPin, Star, Clock, Zap } from 'lucide-react';
import { dashboardAPI } from '../../services/api';

const Analytics: React.FC = () => {
  const [timeRange, setTimeRange] = useState('7d');
  const [dashboardData, setDashboardData] = useState<any>(null);
  const [revenueData, setRevenueData] = useState<any[]>([]);
  const [categoryData, setCategoryData] = useState<any[]>([]);
  const [cityData, setCityData] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  useEffect(() => {
    const loadData = async () => {
      try {
        const dashDataRaw = await dashboardAPI.getAdmin();
        const dashData = dashDataRaw as any;
        setDashboardData(dashData);

        // weekly revenue trend from recent transactions
        const tx = dashData?.recent_transactions || [];
        const grouped: Record<string, { revenue: number; bookings: number }> = {};

        tx.forEach((t: any) => {
          const date = new Date(t.created_at).toLocaleDateString('en-US', { weekday: 'short' });
          if (!grouped[date]) grouped[date] = { revenue: 0, bookings: 0 };
          grouped[date].revenue += t.final_amount || t.amount || 0;
          grouped[date].bookings += 1;
        });

        const generatedRevenueData = Object.keys(grouped).map((day) => ({
          name: day,
          revenue: grouped[day].revenue,
          bookings: grouped[day].bookings,
        }));

        setRevenueData(generatedRevenueData.length ? generatedRevenueData : [
          { name: 'Mon', revenue: dashData?.today_revenue || 0, bookings: dashData?.today_bookings || 0 },
          { name: 'Tue', revenue: dashData?.today_revenue || 0, bookings: dashData?.today_bookings || 0 },
          { name: 'Wed', revenue: dashData?.today_revenue || 0, bookings: dashData?.today_bookings || 0 },
          { name: 'Thu', revenue: dashData?.today_revenue || 0, bookings: dashData?.today_bookings || 0 },
          { name: 'Fri', revenue: dashData?.today_revenue || 0, bookings: dashData?.today_bookings || 0 },
          { name: 'Sat', revenue: dashData?.today_revenue || 0, bookings: dashData?.today_bookings || 0 },
          { name: 'Sun', revenue: dashData?.today_revenue || 0, bookings: dashData?.today_bookings || 0 },
        ]);

        const categoryStats = dashData?.category_stats || [];
        const colors = ['#3B82F6', '#F59E0B', '#10B981', '#8B5CF6', '#EF4444', '#EC4899', '#F97316', '#6366F1'];
        setCategoryData(categoryStats.map((c: any, index: number) => ({ name: c._id || 'Unknown', value: c.total_bookings || 0, color: colors[index % colors.length] })));

        const cities = (dashData?.top_customers || []).slice(0, 4).map((c: any) => ({ city: c.name, users: c.analytics?.loyalty_points || 0, providers: c.analytics?.total_bookings || 0, revenue: c.analytics?.total_spent || 0 }));
        setCityData(cities.length ? cities : []);
      } catch (error) {
        console.error('Failed to fetch admin dashboard:', error);
      } finally {
        setIsLoading(false);
      }
    };

    loadData();
  }, []);


  const stats = [
    {
      title: 'Total Revenue',
      value: `₹ ${((dashboardData?.revenue?.total || 0) / 100000).toFixed(2)}M`,
      change: dashboardData ? `${((dashboardData?.revenue?.total || 0) / (dashboardData?.week_revenue || 1) * 100).toFixed(1)}%` : '0%',
      trend: 'up',
      icon: DollarSign,
      color: 'from-green-500 to-emerald-600',
    },
    {
      title: 'Active Users',
      value: `${((dashboardData?.users?.total || 0) / 1000).toFixed(1)}K`,
      change: dashboardData ? `${((dashboardData?.users?.customers || 0) / (dashboardData?.users?.providers || 1) * 100).toFixed(1)}%` : '0%',
      trend: 'up',
      icon: Users,
      color: 'from-blue-500 to-cyan-600',
    },
    {
      title: 'Total Bookings',
      value: `${dashboardData?.bookings?.total || 0}`,
      change: dashboardData ? `${(dashboardData?.bookings?.today || 0)} today` : '0 today',
      trend: 'up',
      icon: Activity,
      color: 'from-purple-500 to-pink-600',
    },
    {
      title: 'Completion Rate',
      value: dashboardData?.total_bookings ? `${Math.round((dashboardData.completed_bookings / dashboardData.total_bookings) * 100)}%` : '0%',
      change: 'steady',
      trend: 'up',
      icon: Clock,
      color: 'from-orange-500 to-red-600',
    },
  ];

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">📊 Analytics Dashboard</h1>
          <p className="text-gray-600">Real-time insights into your marketplace performance</p>
          
          {/* Time Range Selector */}
          <div className="mt-4 flex gap-2">
            {['24h', '7d', '30d', '90d'].map((range) => (
              <button
                key={range}
                onClick={() => setTimeRange(range)}
                className={`px-4 py-2 rounded-lg font-medium transition-all duration-300 ${
                  timeRange === range
                    ? 'bg-primary-500 text-white shadow-lg'
                    : 'bg-white text-gray-600 hover:bg-gray-100'
                }`}
              >
                {range}
              </button>
            ))}
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          {stats.map((stat, index) => (
            <div
              key={index}
              className="bg-white rounded-2xl shadow-lg p-6 hover:shadow-xl transition-all duration-300 hover:scale-105"
            >
              <div className="flex items-center justify-between mb-4">
                <div className={`w-12 h-12 bg-gradient-to-br ${stat.color} rounded-xl flex items-center justify-center`}>
                  <stat.icon className="w-6 h-6 text-white" />
                </div>
                <div className={`px-3 py-1 rounded-full text-sm font-semibold ${
                  stat.trend === 'up' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                }`}>
                  {stat.change}
                </div>
              </div>
              <p className="text-gray-600 text-sm mb-1">{stat.title}</p>
              <p className="text-3xl font-bold text-gray-900">{stat.value}</p>
            </div>
          ))}
        </div>

        {/* Charts Row 1 */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
          {/* Revenue Trend */}
          <div className="bg-white rounded-2xl shadow-lg p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-bold text-gray-900">📈 Revenue Trend</h2>
              <TrendingUp className="w-5 h-5 text-green-500" />
            </div>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={revenueData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="name" stroke="#888" />
                <YAxis stroke="#888" />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#fff', border: '2px solid #e5e7eb', borderRadius: '12px' }}
                />
                <Legend />
                <Line type="monotone" dataKey="revenue" stroke="#8B5CF6" strokeWidth={3} dot={{ r: 6 }} activeDot={{ r: 8 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>

          {/* Bookings Trend */}
          <div className="bg-white rounded-2xl shadow-lg p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-bold text-gray-900">📅 Bookings Trend</h2>
              <Activity className="w-5 h-5 text-blue-500" />
            </div>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={revenueData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="name" stroke="#888" />
                <YAxis stroke="#888" />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#fff', border: '2px solid #e5e7eb', borderRadius: '12px' }}
                />
                <Legend />
                <Bar dataKey="bookings" fill="#3B82F6" radius={[8, 8, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Charts Row 2 */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
          {/* Category Distribution */}
          <div className="bg-white rounded-2xl shadow-lg p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-bold text-gray-900">🎯 Category Distribution</h2>
              <Star className="w-5 h-5 text-yellow-500" />
            </div>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={categoryData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={(entry) => entry.name}
                  outerRadius={100}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {categoryData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
            <div className="grid grid-cols-2 gap-2 mt-4">
              {categoryData.map((cat, idx) => (
                <div key={idx} className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full" style={{ backgroundColor: cat.color }}></div>
                  <span className="text-xs text-gray-600">{cat.name}: {cat.value}</span>
                </div>
              ))}
            </div>
          </div>

          {/* City Performance */}
          <div className="bg-white rounded-2xl shadow-lg p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-bold text-gray-900">🗺️ City Performance</h2>
              <MapPin className="w-5 h-5 text-red-500" />
            </div>
            <div className="space-y-4">
              {cityData.map((city, index) => (
                <div key={index} className="border-b border-gray-100 pb-4 last:border-0">
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="font-bold text-gray-900">{city.city}</h3>
                    <span className="text-lg font-bold text-primary-600">
                      ₹ {(city.revenue / 100000).toFixed(1)}L
                    </span>
                  </div>
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <p className="text-gray-600">Users</p>
                      <p className="font-semibold text-gray-900">{(city.users / 1000).toFixed(1)}K</p>
                    </div>
                    <div>
                      <p className="text-gray-600">Providers</p>
                      <p className="font-semibold text-gray-900">{(city.providers / 1000).toFixed(1)}K</p>
                    </div>
                  </div>
                  <div className="mt-2 bg-gray-200 rounded-full h-2 overflow-hidden">
                    <div 
                      className="bg-gradient-to-r from-primary-500 to-purple-600 h-full rounded-full"
                      style={{ width: `${(city.revenue / 1250000) * 100}%` }}
                    ></div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Real-time Activity Feed */}
        <div className="bg-white rounded-2xl shadow-lg p-6">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-bold text-gray-900">⚡ Real-time Activity</h2>
            <Zap className="w-5 h-5 text-yellow-500 animate-pulse" />
          </div>
          <div className="space-y-3">
            {[
              { type: 'booking', user: 'Raj Kumar', service: 'Plumbing', time: '2 min ago', color: 'blue' },
              { type: 'completed', user: 'Priya Sharma', service: 'Cleaning', time: '5 min ago', color: 'green' },
              { type: 'emergency', user: 'Amit Patel', service: 'Electrical', time: '8 min ago', color: 'red' },
              { type: 'review', user: 'Sarah Johnson', service: 'Tutoring', time: '12 min ago', color: 'yellow' },
              { type: 'booking', user: 'Michael Chen', service: 'Repair', time: '15 min ago', color: 'blue' },
            ].map((activity, index) => (
              <div key={index} className="flex items-center gap-4 p-3 bg-gray-50 rounded-xl hover:bg-gray-100 transition-colors">
                <div className={`w-2 h-2 rounded-full bg-${activity.color}-500 animate-pulse`}></div>
                <div className="flex-1">
                  <p className="text-sm text-gray-900">
                    <span className="font-semibold">{activity.user}</span> {activity.type === 'booking' ? 'booked' : activity.type === 'completed' ? 'completed' : activity.type === 'emergency' ? 'requested emergency' : 'reviewed'} <span className="font-medium">{activity.service}</span>
                  </p>
                </div>
                <span className="text-xs text-gray-500">{activity.time}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Analytics;
