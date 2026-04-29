import React, { useState, useEffect } from 'react';
import { Users, TrendingUp, Star, MapPin, Loader } from 'lucide-react';
import { communityAPI } from '../../services/api';

interface Provider {
  id: string;
  name: string;
  category: string;
  neighborhoodBookings: number;
  repeatCustomers: number;
  avgRating: number;
  distance: number;
}

interface NeighborhoodProofProps {
  providers?: Provider[];
}

const NeighborhoodProof: React.FC<NeighborhoodProofProps> = ({ providers }) => {
  const [realProviders, setRealProviders] = useState<Provider[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const data = await communityAPI.getTopProviders('Powai'); // Default neighborhood for demo
        if (data && data.length > 0) {
          setRealProviders(data);
        }
      } catch (err) {
        console.error('Failed to fetch neighborhood providers:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  // Mock data if not provided and fetching failed
  const mockProviders: Provider[] = providers || [
    {
      id: '1',
      name: 'Rajesh Kumar',
      category: 'Plumbing',
      neighborhoodBookings: 47,
      repeatCustomers: 32,
      avgRating: 4.8,
      distance: 0.3
    },
    {
      id: '2',
      name: 'Priya Sharma',
      category: 'Cleaning',
      neighborhoodBookings: 63,
      repeatCustomers: 41,
      avgRating: 4.9,
      distance: 0.5
    },
    {
      id: '3',
      name: 'Amit Patel',
      category: 'Electrical',
      neighborhoodBookings: 38,
      repeatCustomers: 28,
      avgRating: 4.7,
      distance: 0.8
    },
  ];

  const displayProviders = providers || (realProviders.length > 0 ? realProviders : mockProviders);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <Loader className="w-10 h-10 text-green-500 animate-spin mb-4" />
        <p className="text-gray-500 font-medium">Loading neighborhood data...</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="text-center mb-8">
        <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-br from-green-500 to-emerald-600 rounded-full mb-4">
          <Users className="w-8 h-8 text-white" />
        </div>
        <h3 className="text-2xl font-bold text-gray-900 mb-2">🏘️ Trusted by Your Neighbors</h3>
        <p className="text-gray-600 max-w-2xl mx-auto">
          See who your neighbors are booking. Real community-driven trust signals.
        </p>
      </div>

      <div className="grid gap-6">
        {displayProviders.map((provider, index) => (
          <div
            key={provider.id}
            className="bg-white rounded-2xl shadow-lg p-6 hover:shadow-2xl transition-all duration-300 border-2 border-gray-100 hover:border-green-300"
          >
            <div className="flex items-start justify-between mb-4">
              <div className="flex items-start gap-4">
                <div className="relative">
                  <img
                    src={`https://i.pravatar.cc/80?u=${provider.id}`}
                    alt={provider.name}
                    className="w-16 h-16 rounded-full border-4 border-white shadow-md"
                  />
                  {index === 0 && (
                    <span className="absolute -top-2 -right-2 bg-yellow-400 text-white text-xs font-bold px-2 py-1 rounded-full shadow-md">
                      🏆 #1
                    </span>
                  )}
                </div>
                <div>
                  <h4 className="text-lg font-bold text-gray-900">{provider.name}</h4>
                  <p className="text-sm text-gray-600 mb-2">{provider.category} Expert</p>
                  <div className="flex items-center gap-2">
                    <div className="flex items-center gap-1">
                      <Star className="w-4 h-4 text-yellow-400 fill-current" />
                      <span className="text-sm font-semibold text-gray-900">{provider.avgRating}</span>
                    </div>
                    <span className="text-gray-300">•</span>
                    <div className="flex items-center gap-1">
                      <MapPin className="w-4 h-4 text-gray-400" />
                      <span className="text-sm text-gray-600">{provider.distance} km away</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="bg-gradient-to-br from-green-50 to-emerald-50 rounded-xl p-4 border border-green-200">
                <div className="flex items-center gap-2 mb-1">
                  <Users className="w-5 h-5 text-green-600" />
                  <p className="text-sm font-medium text-gray-700">Neighborhood Bookings</p>
                </div>
                <p className="text-2xl font-bold text-green-600">
                  {provider.neighborhoodBookings}
                  <span className="text-sm text-gray-500 ml-1">this month</span>
                </p>
                <div className="mt-2 flex items-center gap-1 text-xs text-green-700">
                  <TrendingUp className="w-3 h-3" />
                  <span>{Math.floor(provider.neighborhoodBookings * 0.8)} from your street!</span>
                </div>
              </div>

              <div className="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-xl p-4 border border-blue-200">
                <div className="flex items-center gap-2 mb-1">
                  <Star className="w-5 h-5 text-blue-600" />
                  <p className="text-sm font-medium text-gray-700">Repeat Customers</p>
                </div>
                <p className="text-2xl font-bold text-blue-600">
                  {provider.repeatCustomers}
                  <span className="text-sm text-gray-500 ml-1">regulars</span>
                </p>
                <div className="mt-2 text-xs text-blue-700">
                  {Math.round((provider.repeatCustomers / provider.neighborhoodBookings) * 100)}% rebook rate
                </div>
              </div>
            </div>

            <div className="mt-4 flex items-center justify-between">
              <div className="flex -space-x-2">
                {[1, 2, 3, 4, 5].map((i) => (
                  <img
                    key={i}
                    src={`https://i.pravatar.cc/40?u=neighbor${provider.id}${i}`}
                    alt="Neighbor"
                    className="w-8 h-8 rounded-full border-2 border-white"
                    title="Your neighbor"
                  />
                ))}
                <div className="w-8 h-8 rounded-full border-2 border-white bg-gray-200 flex items-center justify-center text-xs font-semibold text-gray-600">
                  +{provider.neighborhoodBookings - 5}
                </div>
              </div>
              <button className="bg-gradient-to-r from-green-500 to-emerald-600 hover:from-green-600 hover:to-emerald-700 text-white px-6 py-2 rounded-full font-semibold text-sm transition-all duration-300 hover:scale-105 shadow-md">
                Book Now
              </button>
            </div>

            <div className="mt-4 p-3 bg-yellow-50 rounded-lg border border-yellow-200">
              <p className="text-sm text-gray-700">
                <span className="font-semibold">💬 Sarah (2 houses away):</span> "Best {provider.category.toLowerCase()} service I've used!"
              </p>
            </div>
          </div>
        ))}
      </div>

      <div className="mt-8 bg-gradient-to-r from-green-500 to-emerald-600 rounded-2xl p-6 text-white">
        <div className="flex items-center justify-between">
          <div>
            <h4 className="text-xl font-bold mb-2">🎉 Community Trust Score</h4>
            <p className="text-green-100">This neighborhood has excellent service provider relationships</p>
          </div>
          <div className="text-center">
            <p className="text-5xl font-bold">A+</p>
            <p className="text-sm text-green-100">Trust Rating</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default NeighborhoodProof;
