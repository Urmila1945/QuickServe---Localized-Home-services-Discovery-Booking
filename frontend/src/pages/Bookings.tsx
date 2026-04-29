import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { bookingsAPI, receiptAPI } from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import DashboardLayout from '../components/DashboardLayout';
import { useTranslation } from 'react-i18next';
import { Calendar, Clock, CheckCircle, XCircle, AlertCircle, RefreshCw, Star, Download, CreditCard } from 'lucide-react';
import { formatPriceINR } from '../utils/currency';
import toast from 'react-hot-toast';
import ReviewModal from '../components/booking/ReviewModal';
import PaymentModal from '../components/payment/PaymentModal';

const statusConfig: Record<string, { label: string; color: string; icon: React.ElementType }> = {
  pending:     { label: 'Pending',     color: 'bg-yellow-100 text-yellow-700 border-yellow-200', icon: Clock        },
  confirmed:   { label: 'Confirmed',   color: 'bg-blue-100   text-blue-700   border-blue-200',   icon: CheckCircle  },
  in_progress: { label: 'In Progress', color: 'bg-orange-100 text-orange-700 border-orange-200', icon: AlertCircle  },
  completed:   { label: 'Completed',   color: 'bg-green-100  text-green-700  border-green-200',  icon: CheckCircle  },
  cancelled:   { label: 'Cancelled',   color: 'bg-red-100    text-red-700    border-red-200',    icon: XCircle      },
};

const categoryEmoji: Record<string, string> = {
  plumbing: '🔧', electrical: '⚡', cleaning: '🧹',
  repair: '🔨', tutoring: '📚', beauty: '💄', fitness: '💪', delivery: '📦',
};

const Bookings: React.FC = () => {
  const { user } = useAuth();
  const { t } = useTranslation();
  const [filterStatus, setFilterStatus] = useState('all');
  const [reviewBooking, setReviewBooking] = useState<any | null>(null);
  const [payBooking, setPayBooking] = useState<any | null>(null);

  const { data: bookingsData, isLoading } = useQuery({
    queryKey: ['user-bookings'],
    queryFn: bookingsAPI.getUserBookings,
    retry: 1,
  });

  const allBookings: any[] = (Array.isArray(bookingsData) ? bookingsData : (bookingsData as any)?.bookings) || [];
  const filtered = filterStatus === 'all' ? allBookings : allBookings.filter(b => b.status === filterStatus);

  const role = (user?.role as 'customer' | 'provider' | 'admin') || 'customer';

  return (
    <>
    {payBooking && (
      <PaymentModal
        bookingId={payBooking._id}
        serviceName={payBooking.service_name || 'Service'}
        amount={payBooking.price || payBooking.total_amount || 500}
        onSuccess={() => { setPayBooking(null); toast.success('Payment complete!'); }}
        onClose={() => setPayBooking(null)}
      />
    )}
    {reviewBooking && (
      <ReviewModal
        bookingId={reviewBooking._id}
        providerId={reviewBooking.provider_id || reviewBooking.provider || ''}
        serviceTitle={reviewBooking.service_name || `${reviewBooking.category} Service`}
        onClose={() => setReviewBooking(null)}
        onSuccess={() => setReviewBooking(null)}
      />
    )}
    <DashboardLayout role={role} title={t('My Bookings')}>
      <div className="p-6 space-y-6">

        {/* Filter Tabs */}
        <div className="flex gap-2 bg-white rounded-xl p-1.5 shadow-sm border border-gray-100 w-fit flex-wrap">
          {['all', 'pending', 'confirmed', 'in_progress', 'completed', 'cancelled'].map(s => (
            <button
              key={s}
              onClick={() => setFilterStatus(s)}
              className={`px-4 py-2 rounded-lg font-bold text-xs capitalize transition-all duration-200 ${
                filterStatus === s ? 'bg-teal-600 text-white shadow-md' : 'text-gray-500 hover:text-gray-800'
              }`}
            >
              {s === 'in_progress' ? t('In Progress') : s === 'all' ? t('All Services') : s === 'pending' ? t('Pending') : s === 'confirmed' ? t('Confirmed') : s === 'completed' ? t('Completed') : t('Cancelled')}
            </button>
          ))}
        </div>

        {/* Stats Row */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          {(['all', 'pending', 'confirmed', 'in_progress', 'completed'] as const).map(s => {
            const count = s === 'all' ? allBookings.length : allBookings.filter(b => b.status === s).length;
            return (
              <div key={s} className="bg-white rounded-xl p-4 shadow-sm border border-gray-100 text-center hover:shadow-md transition-all">
                <p className="text-2xl font-black text-gray-900">{count}</p>
                <p className="text-xs font-bold text-gray-400 capitalize mt-1">{s === 'in_progress' ? t('Active') : s === 'all' ? t('All Services') : s === 'pending' ? t('Pending') : s === 'confirmed' ? t('Confirmed') : t('Completed')}</p>
              </div>
            );
          })}
        </div>

        {/* Bookings List */}
        {isLoading ? (
          <div className="space-y-4">
            {[1,2,3].map(i => (
              <div key={i} className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100 animate-pulse">
                <div className="flex gap-4">
                  <div className="w-14 h-14 bg-gray-200 rounded-xl" />
                  <div className="flex-1 space-y-2">
                    <div className="h-4 bg-gray-200 rounded w-2/3" />
                    <div className="h-3 bg-gray-200 rounded w-1/2" />
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : filtered.length === 0 ? (
          <div className="bg-white rounded-2xl p-16 text-center shadow-sm border border-gray-100">
            <div className="text-6xl mb-4">📋</div>
            <p className="text-xl font-black text-gray-700 mb-2">{t('No bookings found')}</p>
            <p className="text-gray-400">{t('Try changing the filter or book a new service.')}</p>
          </div>
        ) : (
          <div className="space-y-3">
            {filtered.map((booking: any) => {
              const cfg = statusConfig[booking.status] || statusConfig.pending;
              const StatusIcon = cfg.icon;
              const emoji = categoryEmoji[booking.category] || '🔧';
              return (
                <div
                  key={booking._id}
                  className="bg-white rounded-2xl p-5 shadow-sm border border-gray-100 hover:shadow-md hover:border-teal-200 transition-all duration-200 group cursor-pointer flex items-center justify-between gap-4"
                >
                  <div className="flex items-center gap-4">
                    <div className="w-14 h-14 rounded-2xl bg-gray-50 flex items-center justify-center text-2xl group-hover:scale-110 transition-transform">
                      {emoji}
                    </div>
                    <div>
                      <p className="font-black text-gray-900">{booking.service_name || 'Service Booking'}</p>
                      <p className="text-sm text-gray-500 font-medium">{booking.provider || 'Provider Name'}</p>
                      <div className="flex items-center gap-2 mt-1">
                        <Calendar size={12} className="text-gray-400" />
                        <p className="text-xs text-gray-400">{booking.date || booking.created_at?.slice(0,10)}</p>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-4 flex-shrink-0">
                    <div className="text-right">
                      <p className="font-black text-gray-900">{formatPriceINR(booking.price || booking.total_amount || 0)}</p>
                      <p className="text-xs text-gray-400">{t('Total')}</p>
                    </div>
                    <span className={`flex items-center gap-1.5 text-xs font-bold px-3 py-1.5 rounded-full border ${cfg.color}`}>
                      <StatusIcon size={12} />
                      {cfg.label}
                    </span>
                      <div className="flex items-center gap-2 flex-wrap">
                        {booking.status === 'pending' && (
                          <button
                            onClick={e => { e.stopPropagation(); setPayBooking(booking); }}
                            className="flex items-center gap-1 text-teal-600 hover:text-teal-800 font-bold text-xs transition-colors"
                          >
                            <CreditCard size={13} /> {t('Pay Now')}
                          </button>
                        )}
                        {booking.status === 'completed' && (
                          <>
                            <button
                              onClick={e => { e.stopPropagation(); toast.success('Re-booked!'); }}
                              className="flex items-center gap-1 text-teal-600 hover:text-teal-800 font-bold text-xs transition-colors"
                            >
                              <RefreshCw size={13} /> {t('Reorder')}
                            </button>
                            <button
                              onClick={e => { e.stopPropagation(); setReviewBooking(booking); }}
                              className="flex items-center gap-1 text-yellow-600 hover:text-yellow-800 font-bold text-xs transition-colors"
                            >
                              <Star size={13} /> {t('Review')}
                            </button>
                            <button
                              onClick={e => { e.stopPropagation(); window.open(receiptAPI.generate(booking._id), '_blank'); }}
                              className="flex items-center gap-1 text-green-600 hover:text-green-800 font-bold text-xs transition-colors"
                            >
                              <Download size={13} /> {t('Receipt')}
                            </button>
                          </>
                        )}
                      </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </DashboardLayout>
    </>
  );
};

export default Bookings;
