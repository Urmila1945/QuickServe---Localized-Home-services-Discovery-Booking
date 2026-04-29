import React, { useState, useEffect } from 'react';
import { Calendar, Cloud, DollarSign, TrendingDown, Clock, Zap, Loader } from 'lucide-react';
import { slotsAPI } from '../../services/api';

interface TimeSlot {
  time: string;
  price: number;
  weather: string;
  demand: 'low' | 'medium' | 'high';
  discount?: number;
}

const SmartScheduler: React.FC = () => {
  const [selectedDate, setSelectedDate] = useState<string>(new Date().toISOString().split('T')[0]);
  const [selectedSlot, setSelectedSlot] = useState<TimeSlot | null>(null);
  const [timeSlots, setTimeSlots] = useState<TimeSlot[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    const fetchSlots = async () => {
      setLoading(true);
      try {
        const data = await slotsAPI.getSmartScheduling(selectedDate);
        setTimeSlots(data.slots || []);
      } catch (err) {
        console.error('Failed to fetch smart scheduling slots:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchSlots();
    setSelectedSlot(null);
  }, [selectedDate]);

  const getDemandColor = (demand: string) => {
    switch (demand) {
      case 'low': return 'bg-green-100 text-green-800 border-green-200';
      case 'medium': return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'high': return 'bg-red-100 text-red-800 border-red-200';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className="bg-white rounded-2xl shadow-xl p-8 max-w-4xl mx-auto">
      <div className="text-center mb-8">
        <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full mb-4">
          <Calendar className="w-8 h-8 text-white" />
        </div>
        <h3 className="text-2xl font-bold text-gray-900 mb-2">🧠 AI-Powered Smart Scheduling</h3>
        <p className="text-gray-600">Get the best price by booking during low-demand periods</p>
      </div>

      <div className="mb-6">
        <label className="block text-sm font-semibold text-gray-700 mb-2">Select Date</label>
        <input
          type="date"
          value={selectedDate}
          onChange={(e) => setSelectedDate(e.target.value)}
          min={new Date().toISOString().split('T')[0]}
          className="w-full px-4 py-3 border-2 border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
        />
      </div>

      <div className="mb-6">
        <div className="flex items-center justify-between mb-4">
          <h4 className="text-lg font-bold text-gray-900">Available Time Slots</h4>
          <div className="flex items-center gap-2 text-sm">
            <Cloud className="w-4 h-4 text-gray-600" />
            <span className="text-gray-600">Weather-optimized pricing</span>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {loading ? (
            <div className="col-span-1 md:col-span-2 flex justify-center py-12">
              <Loader className="w-8 h-8 text-primary-500 animate-spin" />
            </div>
          ) : timeSlots.map((slot, index) => (
            <button
              key={index}
              onClick={() => setSelectedSlot(slot)}
              className={`relative p-4 rounded-xl border-2 transition-all duration-300 text-left ${
                selectedSlot?.time === slot.time
                  ? 'border-primary-500 bg-primary-50 shadow-lg scale-105'
                  : 'border-gray-200 hover:border-primary-300 hover:shadow-md'
              }`}
            >
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <Clock className="w-5 h-5 text-gray-600" />
                  <span className="font-bold text-gray-900">{slot.time}</span>
                </div>
                <span className="text-lg font-bold text-gray-900">
                  ${slot.discount ? slot.price - (slot.price * slot.discount / 100) : slot.price}
                </span>
              </div>

              <div className="flex items-center justify-between mb-2">
                <span className="text-sm text-gray-600">{slot.weather}</span>
                <span className={`px-2 py-1 rounded-full text-xs font-medium border ${getDemandColor(slot.demand)}`}>
                  {slot.demand} demand
                </span>
              </div>

              {slot.discount && (
                <div className="flex items-center gap-2 mt-2 p-2 bg-green-50 rounded-lg border border-green-200">
                  <TrendingDown className="w-4 h-4 text-green-600" />
                  <span className="text-sm font-semibold text-green-700">
                    Save {slot.discount}% (${slot.price * slot.discount / 100})
                  </span>
                </div>
              )}

              {selectedSlot?.time === slot.time && (
                <div className="absolute -top-2 -right-2 bg-primary-500 text-white p-1 rounded-full">
                  <Zap className="w-4 h-4" />
                </div>
              )}
            </button>
          ))}
        </div>
      </div>

      {selectedSlot && (
        <div className="bg-gradient-to-r from-primary-500 to-purple-600 rounded-2xl p-6 text-white">
          <div className="flex items-center justify-between">
            <div>
              <h4 className="text-lg font-bold mb-2">✨ Optimized Booking Summary</h4>
              <p className="text-blue-100 mb-4">
                {selectedDate} at {selectedSlot.time} • {selectedSlot.weather}
              </p>
              <div className="flex items-center gap-6">
                <div>
                  <p className="text-sm text-blue-100">Base Price</p>
                  <p className="text-2xl font-bold">${selectedSlot.price}</p>
                </div>
                {selectedSlot.discount && (
                  <>
                    <div className="text-3xl">→</div>
                    <div>
                      <p className="text-sm text-blue-100">You Pay</p>
                      <p className="text-2xl font-bold text-yellow-300">
                        ${selectedSlot.price - (selectedSlot.price * selectedSlot.discount / 100)}
                      </p>
                    </div>
                  </>
                )}
              </div>
            </div>
            <button className="bg-white hover:bg-gray-100 text-primary-600 px-8 py-3 rounded-full font-bold transition-all duration-300 hover:scale-105 shadow-xl">
              Confirm Booking
            </button>
          </div>
        </div>
      )}

      <div className="mt-6 grid grid-cols-3 gap-4">
        <div className="text-center p-4 bg-green-50 rounded-xl border border-green-200">
          <DollarSign className="w-6 h-6 text-green-600 mx-auto mb-2" />
          <p className="text-sm text-gray-600">Avg Savings</p>
          <p className="text-xl font-bold text-green-600">18%</p>
        </div>
        <div className="text-center p-4 bg-blue-50 rounded-xl border border-blue-200">
          <Cloud className="w-6 h-6 text-blue-600 mx-auto mb-2" />
          <p className="text-sm text-gray-600">Weather Match</p>
          <p className="text-xl font-bold text-blue-600">95%</p>
        </div>
        <div className="text-center p-4 bg-purple-50 rounded-xl border border-purple-200">
          <Zap className="w-6 h-6 text-purple-600 mx-auto mb-2" />
          <p className="text-sm text-gray-600">Instant Match</p>
          <p className="text-xl font-bold text-purple-600">&lt; 2min</p>
        </div>
      </div>
    </div>
  );
};

export default SmartScheduler;
