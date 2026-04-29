import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Search, Calendar, Clock, CheckCircle, XCircle,
  AlertCircle, ChevronDown, ChevronUp, Star, CreditCard,
  User, Briefcase, MapPin, DollarSign, Shield
} from 'lucide-react';
import api from '../../../services/api';
import { formatPriceINR } from '../../../utils/currency';

const STATUS_STYLES: Record<string, string> = {
  completed:   'bg-green-100 text-green-700 border-green-200',
  in_progress: 'bg-blue-100 text-blue-700 border-blue-200',
  confirmed:   'bg-teal-100 text-teal-700 border-teal-200',
  pending:     'bg-yellow-100 text-yellow-700 border-yellow-200',
  cancelled:   'bg-red-100 text-red-700 border-red-200',
};

const PAYMENT_STYLES: Record<string, string> = {
  completed: 'bg-green-100 text-green-700',
  paid:      'bg-green-100 text-green-700',
  pending:   'bg-yellow-100 text-yellow-700',
  refunded:  'bg-purple-100 text-purple-700',
  unpaid:    'bg-gray-100 text-gray-500',
};

const StatusBadge: React.FC<{ status: string }> = ({ status }) => (
  <span className={`px-2.5 py-1 rounded-full text-[10px] font-black uppercase tracking-widest border w-fit flex items-center gap-1 ${STATUS_STYLES[status] || 'bg-gray-100 text-gray-600 border-gray-200'}`}>
    {status === 'completed' && <CheckCircle size={10} />}
    {status === 'cancelled' && <XCircle size={10} />}
    {status === 'pending'   && <AlertCircle size={10} />}
    {status === 'in_progress' && <Clock size={10} />}
    {status.replace('_', ' ')}
  </span>
);

const InfoRow: React.FC<{ label: string; value: any; icon?: React.ReactNode }> = ({ label, value, icon }) => (
  <div className="flex items-start gap-2">
    {icon && <span className="text-gray-400 mt-0.5 flex-shrink-0">{icon}</span>}
    <div>
      <p className="text-[10px] font-black text-gray-400 uppercase tracking-widest">{label}</p>
      <p className="text-xs font-bold text-gray-800">{value ?? '—'}</p>
    </div>
  </div>
);

const AllBookings: React.FC = () => {
  const [statusFilter, setStatusFilter] = useState('all');
  const [searchTerm, setSearchTerm]     = useState('');
  const [page, setPage]                 = useState(1);
  const [expanded, setExpanded]         = useState<string | null>(null);

  const { data: bookingsData, isLoading } = useQuery({
    queryKey: ['admin-all-bookings', statusFilter, page],
    queryFn: () => api.get('/api/admin/bookings', {
      params: { status: statusFilter === 'all' ? undefined : statusFilter, page, limit: 50 }
    }).then(r => r.data),
  });

  const bookings: any[] = (bookingsData?.bookings || []).filter((b: any) =>
    !searchTerm ||
    b.service_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    b._id?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    b.customer_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    b.provider_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    b.category?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const total = bookingsData?.total || 0;

  if (isLoading) return (
    <div className="p-16 text-center">
      <div className="w-10 h-10 border-4 border-teal-600/30 border-t-teal-600 rounded-full animate-spin mx-auto mb-4" />
      <p className="font-black text-gray-400">Loading Bookings...</p>
    </div>
  );

  return (
    <div className="space-y-5">
      {/* Search & Filter Bar */}
      <div className="bg-white rounded-3xl p-5 shadow-sm border border-gray-100 flex flex-col md:flex-row items-center gap-4">
        <div className="relative flex-1 w-full">
          <Search size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Search by ID, service, customer, provider..."
            value={searchTerm}
            onChange={e => setSearchTerm(e.target.value)}
            className="w-full bg-gray-50 border-2 border-transparent focus:border-teal-500 rounded-2xl pl-11 pr-5 py-3 focus:outline-none font-bold text-sm transition-all"
          />
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          {['all', 'pending', 'confirmed', 'in_progress', 'completed', 'cancelled'].map(s => (
            <button
              key={s}
              onClick={() => { setStatusFilter(s); setPage(1); }}
              className={`px-3.5 py-2 rounded-xl text-[10px] font-black uppercase tracking-widest whitespace-nowrap transition-all ${
                statusFilter === s ? 'bg-teal-600 text-white shadow-md' : 'bg-gray-50 text-gray-500 hover:bg-gray-100'
              }`}
            >
              {s.replace('_', ' ')}
            </button>
          ))}
        </div>
      </div>

      {/* Summary counts */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: 'Total',       val: total,                                                                    color: 'text-gray-900',   bg: 'bg-white' },
          { label: 'Completed',   val: bookingsData?.bookings?.filter((b:any)=>b.status==='completed').length || 0,   color: 'text-green-600',  bg: 'bg-green-50' },
          { label: 'In Progress', val: bookingsData?.bookings?.filter((b:any)=>b.status==='in_progress').length || 0, color: 'text-blue-600',   bg: 'bg-blue-50' },
          { label: 'Pending',     val: bookingsData?.bookings?.filter((b:any)=>b.status==='pending').length || 0,     color: 'text-yellow-600', bg: 'bg-yellow-50' },
        ].map(s => (
          <div key={s.label} className={`${s.bg} rounded-2xl p-4 shadow-sm border border-gray-100 text-center`}>
            <p className={`text-2xl font-black ${s.color}`}>{s.val}</p>
            <p className="text-[10px] font-black text-gray-400 uppercase tracking-widest mt-1">{s.label}</p>
          </div>
        ))}
      </div>

      {/* Bookings List */}
      <div className="space-y-3">
        {bookings.length === 0 && (
          <div className="bg-white rounded-3xl p-16 text-center shadow-sm border border-gray-100">
            <p className="text-4xl mb-3">📋</p>
            <p className="font-black text-gray-500">No bookings found</p>
          </div>
        )}

        {bookings.map((b: any) => {
          const isOpen = expanded === b._id;
          return (
            <div key={b._id} className="bg-white rounded-3xl shadow-sm border border-gray-100 overflow-hidden hover:shadow-md transition-all">
              {/* Row Header */}
              <div
                className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-5 cursor-pointer"
                onClick={() => setExpanded(isOpen ? null : b._id)}
              >
                {/* Left: ID + Service */}
                <div className="flex items-center gap-4 min-w-0">
                  <div className="w-11 h-11 bg-teal-50 rounded-2xl flex items-center justify-center flex-shrink-0">
                    <Briefcase size={18} className="text-teal-600" />
                  </div>
                  <div className="min-w-0">
                    <p className="font-black text-gray-900 text-sm truncate">{b.service_name || b.category || 'Service'}</p>
                    <p className="text-[10px] font-bold text-gray-400 uppercase tracking-widest mt-0.5">
                      #{b._id.slice(-8).toUpperCase()} · {b.category || 'General'}
                    </p>
                  </div>
                </div>

                {/* Middle: Participants */}
                <div className="flex items-center gap-6 flex-shrink-0">
                  <div className="flex items-center gap-2">
                    <div className="w-7 h-7 bg-blue-100 rounded-full flex items-center justify-center">
                      <User size={12} className="text-blue-600" />
                    </div>
                    <div>
                      <p className="text-xs font-black text-gray-800 leading-tight">{b.customer_name || 'Customer'}</p>
                      <p className="text-[10px] text-gray-400">{b.customer_email || ''}</p>
                    </div>
                  </div>
                  <div className="text-gray-300 font-bold">→</div>
                  <div className="flex items-center gap-2">
                    <div className="w-7 h-7 bg-teal-100 rounded-full flex items-center justify-center">
                      <Briefcase size={12} className="text-teal-600" />
                    </div>
                    <div>
                      <p className="text-xs font-black text-gray-800 leading-tight">{b.provider_name || 'Provider'}</p>
                      <p className="text-[10px] text-gray-400">{b.provider_email || ''}</p>
                    </div>
                  </div>
                </div>

                {/* Right: Amount + Status + Toggle */}
                <div className="flex items-center gap-4 flex-shrink-0">
                  <div className="text-right">
                    <p className="font-black text-gray-900">{formatPriceINR(b.final_amount || b.final_price || b.amount || 0)}</p>
                    <p className="text-[10px] text-gray-400">{b.scheduled_date || new Date(b.created_at).toLocaleDateString()}</p>
                  </div>
                  <StatusBadge status={b.status} />
                  <div className="text-gray-400">
                    {isOpen ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
                  </div>
                </div>
              </div>

              {/* Expanded Detail Panel */}
              {isOpen && (
                <div className="border-t border-gray-100 bg-gray-50/50 p-6 grid grid-cols-1 md:grid-cols-3 gap-6">

                  {/* Booking Details */}
                  <div className="space-y-4">
                    <p className="text-[10px] font-black text-teal-600 uppercase tracking-[0.2em] mb-3">📋 Booking Details</p>
                    <InfoRow label="Booking ID"     value={b._id} />
                    <InfoRow label="Service"        value={b.service_name || b.category} icon={<Briefcase size={12} />} />
                    <InfoRow label="Category"       value={b.category} />
                    <InfoRow label="Status"         value={<StatusBadge status={b.status} />} />
                    <InfoRow label="Scheduled Date" value={b.scheduled_date} icon={<Calendar size={12} />} />
                    <InfoRow label="Scheduled Time" value={b.scheduled_time} icon={<Clock size={12} />} />
                    {b.location && (
                      <InfoRow label="Location" value={b.location?.address || `${b.location?.city || ''}`} icon={<MapPin size={12} />} />
                    )}
                    {b.notes && <InfoRow label="Notes" value={b.notes} />}
                    {b.review_rating && (
                      <div className="flex items-center gap-1 mt-1">
                        {[1,2,3,4,5].map(i => (
                          <Star key={i} size={12} className={i <= b.review_rating ? 'text-yellow-500 fill-yellow-500' : 'text-gray-300'} />
                        ))}
                        <span className="text-xs text-gray-500 ml-1">{b.review_comment}</span>
                      </div>
                    )}
                  </div>

                  {/* Customer Details */}
                  <div className="space-y-4">
                    <p className="text-[10px] font-black text-blue-600 uppercase tracking-[0.2em] mb-3">👤 Customer Info</p>
                    <InfoRow label="Name"       value={b.customer_name}   icon={<User size={12} />} />
                    <InfoRow label="Email"      value={b.customer_email} />
                    <InfoRow label="Phone"      value={b.customer_phone} />
                    <InfoRow label="Credits"    value={b.customer_credits != null ? `${b.customer_credits} credits` : '—'} />
                    <InfoRow label="Total Bookings"     value={b.customer_total_bookings} />
                    <InfoRow label="Completed Bookings" value={b.customer_completed_bookings} />

                    {/* Payment Details */}
                    <div className="pt-3 border-t border-gray-200 space-y-3">
                      <p className="text-[10px] font-black text-green-600 uppercase tracking-[0.2em]">💳 Payment</p>
                      <InfoRow label="Payment Status" value={
                        <span className={`px-2 py-0.5 rounded-full text-[10px] font-black ${PAYMENT_STYLES[b.payment_status] || 'bg-gray-100 text-gray-500'}`}>
                          {b.payment_status || 'unpaid'}
                        </span>
                      } icon={<CreditCard size={12} />} />
                      <InfoRow label="Method"        value={b.payment_method?.toUpperCase() || '—'} />
                      <InfoRow label="Total Amount"  value={formatPriceINR(b.final_amount || 0)} icon={<DollarSign size={12} />} />
                      <InfoRow label="GST"           value={formatPriceINR(b.gst_amount || 0)} />
                      <InfoRow label="Discount"      value={b.discount_amount ? formatPriceINR(b.discount_amount) : '—'} />
                      <InfoRow label="Platform Fee"  value={formatPriceINR(b.platform_fee || 0)} />
                      <InfoRow label="Escrow"        value={b.escrow_status || '—'} icon={<Shield size={12} />} />
                    </div>
                  </div>

                  {/* Provider Details */}
                  <div className="space-y-4">
                    <p className="text-[10px] font-black text-teal-600 uppercase tracking-[0.2em] mb-3">🔧 Provider Info</p>
                    <InfoRow label="Name"       value={b.provider_name}  icon={<Briefcase size={12} />} />
                    <InfoRow label="Email"      value={b.provider_email} />
                    <InfoRow label="Phone"      value={b.provider_phone} />
                    <InfoRow label="Rating"     value={
                      b.provider_rating ? (
                        <span className="flex items-center gap-1">
                          <Star size={11} className="text-yellow-500 fill-yellow-500" />
                          {Number(b.provider_rating).toFixed(1)}
                        </span>
                      ) : '—'
                    } />
                    <InfoRow label="Verified"   value={
                      <span className={`px-2 py-0.5 rounded-full text-[10px] font-black ${b.provider_verified ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'}`}>
                        {b.provider_verified ? '✓ Verified' : 'Pending'}
                      </span>
                    } icon={<Shield size={12} />} />
                    <InfoRow label="Specializations" value={(b.provider_specializations || []).join(', ') || '—'} />
                    <InfoRow label="Total Bookings"     value={b.provider_total_bookings} />
                    <InfoRow label="Completed Bookings" value={b.provider_completed_bookings} />
                    <InfoRow label="Total Earnings"     value={b.provider_total_earnings != null ? formatPriceINR(b.provider_total_earnings) : '—'} icon={<DollarSign size={12} />} />
                    <InfoRow label="Provider Payout (this booking)" value={b.provider_payout != null ? formatPriceINR(b.provider_payout) : '—'} />
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Pagination */}
      <div className="flex items-center justify-between bg-white rounded-2xl p-4 shadow-sm border border-gray-100">
        <p className="text-xs font-bold text-gray-500">Showing {bookings.length} of {total} bookings</p>
        <div className="flex items-center gap-2">
          <button disabled={page === 1} onClick={() => setPage(p => p - 1)}
            className="px-4 py-2 rounded-xl border-2 border-gray-200 text-xs font-black disabled:opacity-40 hover:border-teal-400 transition-all">
            ← Prev
          </button>
          <span className="text-xs font-black text-gray-600 px-2">Page {page}</span>
          <button disabled={bookings.length < 50} onClick={() => setPage(p => p + 1)}
            className="px-4 py-2 rounded-xl border-2 border-gray-200 text-xs font-black disabled:opacity-40 hover:border-teal-400 transition-all">
            Next →
          </button>
        </div>
      </div>
    </div>
  );
};

export default AllBookings;
