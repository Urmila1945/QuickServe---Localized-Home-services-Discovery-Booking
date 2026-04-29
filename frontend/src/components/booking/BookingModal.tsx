import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  X, Check, Shield, Loader, Clock,
  ChevronRight, CreditCard, Package
} from 'lucide-react';
import toast from 'react-hot-toast';
import { loadStripe } from '@stripe/stripe-js';
import {
  Elements,
  CardElement,
  useStripe,
  useElements,
} from '@stripe/react-stripe-js';
import type { Service } from '../../types';
import { useAuth } from '../../contexts/AuthContext';
import { slotsAPI, bookingsAPI, loyaltyAPI, receiptAPI } from '../../services/api';
import api from '../../services/api';
import { formatPriceINR } from '../../utils/currency';

// ── Stripe setup ────────────────────────────────────────────────────────
const STRIPE_PK = import.meta.env.VITE_STRIPE_PUBLISHABLE_KEY as string;
const stripePromise = STRIPE_PK ? loadStripe(STRIPE_PK) : null;

// ── Types ───────────────────────────────────────────────────────────────
type Step = 'schedule' | 'payment' | 'confirmed';

interface BookingModalProps {
  service: Service;
  onClose: () => void;
}

// ── Constants ───────────────────────────────────────────────────────────
const PAYMENT_METHODS = [
  { id: 'upi',        label: 'UPI',         icon: '📱', fee: 0,     recommended: true  },
  { id: 'card',       label: 'Card',        icon: '💳', fee: 0.029, recommended: false },
  { id: 'demo',       label: 'Demo Pay',    icon: '🧪', fee: 0,     recommended: false },
  { id: 'netbanking', label: 'Net Banking', icon: '🏦', fee: 0.015, recommended: false },
  { id: 'cod',        label: 'Cash',        icon: '💵', fee: 0,     recommended: false },
];

const MOCK_SLOTS = [
  { start_time: '09:00', is_available: true },
  { start_time: '10:00', is_available: true },
  { start_time: '11:00', is_available: true },
  { start_time: '14:00', is_available: true },
  { start_time: '15:00', is_available: true },
  { start_time: '16:00', is_available: true },
];

const getNextDays = (n = 7): Date[] =>
  Array.from({ length: n }, (_, i) => {
    const d = new Date();
    d.setDate(d.getDate() + i);
    return d;
  });

// ── Step Indicator ──────────────────────────────────────────────────────
const StepIndicator: React.FC<{ current: Step }> = ({ current }) => {
  const steps: { id: Step; label: string }[] = [
    { id: 'schedule',  label: 'Schedule' },
    { id: 'payment',   label: 'Payment'  },
    { id: 'confirmed', label: 'Done'     },
  ];
  const idx = (s: Step) => steps.findIndex(x => x.id === s);
  const ci = idx(current);
  return (
    <div className="flex items-center px-6 py-4 border-b border-gray-100">
      {steps.map((step, i) => (
        <React.Fragment key={step.id}>
          <div className="flex items-center gap-2">
            <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-black transition-all
              ${i < ci ? 'bg-green-500 text-white' : i === ci ? 'bg-teal-600 text-white' : 'bg-gray-100 text-gray-400'}`}>
              {i < ci ? <Check size={13} /> : i + 1}
            </div>
            <span className={`text-xs font-bold hidden sm:block
              ${i === ci ? 'text-teal-700' : i < ci ? 'text-green-600' : 'text-gray-400'}`}>
              {step.label}
            </span>
          </div>
          {i < steps.length - 1 && (
            <div className={`flex-1 h-0.5 mx-2 rounded-full transition-colors ${i < ci ? 'bg-green-400' : 'bg-gray-100'}`} />
          )}
        </React.Fragment>
      ))}
    </div>
  );
};

// ── Stripe Card Form (inner — needs Elements context) ───────────────────
interface StripeCardFormProps {
  clientSecret: string;
  paymentId: string;
  onSuccess: () => void;
  onError: (msg: string) => void;
  total: number;
}

const StripeCardForm: React.FC<StripeCardFormProps> = ({
  clientSecret, paymentId, onSuccess, onError, total
}) => {
  const stripe = useStripe();
  const elements = useElements();
  const [processing, setProcessing] = useState(false);

  const handleConfirm = async () => {
    if (!stripe || !elements) return;
    const cardEl = elements.getElement(CardElement);
    if (!cardEl) return;

    setProcessing(true);
    try {
      const { error, paymentIntent } = await stripe.confirmCardPayment(clientSecret, {
        payment_method: { card: cardEl },
      });

      if (error) {
        onError(error.message || 'Card payment failed');
        return;
      }

      if (paymentIntent?.status === 'succeeded') {
        // Notify backend to finalize
        await api.post(`/api/payments/confirm-payment/${paymentId}`, {
          stripe_payment_intent_id: paymentIntent.id,
          payment_details: { method: 'card', stripe_status: paymentIntent.status },
        });
        onSuccess();
      } else {
        onError(`Payment status: ${paymentIntent?.status}`);
      }
    } catch (err: any) {
      onError(err?.response?.data?.detail || 'Payment failed. Please try again.');
    } finally {
      setProcessing(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="bg-gray-50 border border-gray-200 rounded-xl p-4">
        <p className="text-xs font-black text-gray-400 uppercase tracking-widest mb-3">Card Details</p>
        <CardElement
          options={{
            style: {
              base: {
                fontSize: '16px',
                color: '#1f2937',
                fontFamily: 'system-ui, sans-serif',
                '::placeholder': { color: '#9ca3af' },
              },
              invalid: { color: '#ef4444' },
            },
          }}
        />
      </div>
      <p className="text-xs text-gray-400 text-center flex items-center justify-center gap-1">
        <Shield size={12} className="text-teal-500" /> Secured by Stripe • 256-bit encryption
      </p>
      <button
        onClick={handleConfirm}
        disabled={!stripe || processing}
        className="w-full bg-teal-600 disabled:bg-gray-400 hover:bg-teal-700 text-white py-4 rounded-xl font-black text-sm flex items-center justify-center gap-2 transition-all"
      >
        {processing ? (
          <Loader className="animate-spin" size={16} />
        ) : (
          <><CreditCard size={16} /> Pay {formatPriceINR(total)} Securely</>
        )}
      </button>
    </div>
  );
};

// ── Main Component ──────────────────────────────────────────────────────
const BookingModal: React.FC<BookingModalProps> = ({ service, onClose }) => {
  const { user } = useAuth();
  const navigate = useNavigate();

  const [step, setStep] = useState<Step>('schedule');
  const [selectedDate, setSelectedDate] = useState<Date>(getNextDays()[1]);
  const [selectedSlot, setSelectedSlot] = useState('');
  const [paymentMethod, setPaymentMethod] = useState('upi');
  const [paymentData, setPaymentData] = useState<any>(null);
  const [transactionId, setTransactionId] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [confirmation, setConfirmation] = useState<{
    bookingId: string; date: string; time: string; provider: string; total: number;
  } | null>(null);

  const days = getNextDays();
  const dateStr = selectedDate.toISOString().split('T')[0];

  // ── Queries ─────────────────────────────────────────────────────────
  const { data: slotsData, isLoading: slotsLoading } = useQuery({
    queryKey: ['slots', service.provider_id, dateStr],
    queryFn: () => slotsAPI.getAvailability(service.provider_id, dateStr),
    retry: 1,
  });

  const { data: loyaltyData } = useQuery({
    queryKey: ['loyalty-points'],
    queryFn: loyaltyAPI.getPoints,
    retry: 1,
    enabled: !!user,
  });

  const { data: pastBookings } = useQuery({
    queryKey: ['my-bookings'],
    queryFn: bookingsAPI.getUserBookings,
    enabled: !!user,
  });

  // ── Computed ────────────────────────────────────────────────────────
  const rawSlots = (slotsData as any)?.slots || slotsData || [];
  const slots = Array.isArray(rawSlots)
    ? rawSlots.map((s: any) => ({
        start_time: s.time || s.start_time || '',
        is_available: s.available ?? s.is_available ?? false,
      })).filter((x: any) => !!x.start_time)
    : MOCK_SLOTS;

  const loyaltyPoints = loyaltyData?.points || 0;

  // Discount logic for repeat bookings
  const isRepeatCustomer = pastBookings?.some((b: any) => b.service_id === service._id || b.service_id === (service as any).id);
  const originalPrice = service.price_per_hour || service.price || 600;
  const repeatDiscount = isRepeatCustomer ? originalPrice * 0.10 : 0;
  const servicePrice = originalPrice - repeatDiscount;

  const pm = PAYMENT_METHODS.find(m => m.id === paymentMethod) || PAYMENT_METHODS[0];
  const payFee = servicePrice * pm.fee;
  const gst = servicePrice * 0.18;
  const total = servicePrice + payFee + gst;

  const availableSlots = slots.filter((s: any) => s.is_available);
  const stripeEnabled = paymentData?.stripe_enabled && !!stripePromise;

  // ── Handlers ────────────────────────────────────────────────────────
  const handleContinueToPayment = () => {
    if (!user) { onClose(); toast.error('Please login to book a service'); navigate('/login'); return; }
    if (!selectedSlot) { toast.error('Please select a time slot'); return; }
    setStep('payment');
  };

  const finishBooking = (bookingId: string) => {
    setConfirmation({
      bookingId,
      date: selectedDate.toLocaleDateString('en-IN', { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric' }),
      time: selectedSlot,
      provider: service.provider_name || 'Your Provider',
      total,
    });
    setStep('confirmed');
    toast.success('Booking confirmed! 🎉');
  };

  /** Create the booking and payment intent, returns { bookingId, paymentId, paymentData } */
  const createBookingAndIntent = async (): Promise<{ bookingId: string; paymentId: string; intentData: any } | null> => {
    try {
      const booking = await bookingsAPI.create({
        service_id: service._id,
        provider_id: service.provider_id,
        scheduled_date: dateStr,
        scheduled_time: selectedSlot,
        total_amount: total,
        location: { latitude: 0, longitude: 0, address: 'Customer location' },
      } as any);

      const bookingId = booking._id || booking.id;

      const intentRes = await api.post('/api/payments/create-payment-intent', {
        booking_id: bookingId,
        payment_method: paymentMethod,
      });

      return { bookingId, paymentId: intentRes.data.payment_id, intentData: intentRes.data };
    } catch (err: any) {
      const msg = err?.response?.data?.detail || 'Could not create booking';
      toast.error(typeof msg === 'string' ? msg : 'Booking failed');
      return null;
    }
  };

  const handlePay = async () => {
    if (!user) { navigate('/login'); return; }
    setIsProcessing(true);

    try {
      // ── COD: just create booking, no payment intent ──
      if (paymentMethod === 'cod') {
        const booking = await bookingsAPI.create({
          service_id: service._id,
          provider_id: service.provider_id,
          scheduled_date: dateStr,
          scheduled_time: selectedSlot,
          total_amount: total,
          location: { latitude: 0, longitude: 0, address: 'Customer location' },
        } as any);
        finishBooking(booking._id || booking.id);
        return;
      }

      // ── Demo payment ──
      if (paymentMethod === 'demo') {
        const result = await createBookingAndIntent();
        if (!result) return;
        await api.post(`/api/payments/confirm-payment/${result.paymentId}`, {});
        finishBooking(result.bookingId);
        return;
      }

      // ── Card: if we already have intent data (Stripe or mock), handle confirm flow ──
      if (paymentMethod === 'card') {
        if (!paymentData) {
          // Step 1: Create booking + intent, show card form
          const result = await createBookingAndIntent();
          if (!result) return;
          setPaymentData({ ...result.intentData, _bookingId: result.bookingId, _paymentId: result.paymentId });
          // If not stripe_enabled, auto-confirm (mock/test mode)
          if (!result.intentData.stripe_enabled) {
            await api.post(`/api/payments/confirm-payment/${result.paymentId}`, {});
            finishBooking(result.bookingId);
          }
          // else: the StripeCardForm will call finishBooking via onSuccess
        }
        return; // Stripe form handles the rest
      }

      // ── UPI / Net Banking ──
      if (!paymentData) {
        // Step 1: Show QR / bank details
        const result = await createBookingAndIntent();
        if (!result) return;
        setPaymentData({ ...result.intentData, _bookingId: result.bookingId, _paymentId: result.paymentId });
        toast.success(`${paymentMethod.toUpperCase()} payment details generated!`);
      } else {
        // Step 2: Confirm after user entered transaction ID
        if (!transactionId.trim()) {
          toast.error('Please enter the transaction ID for verification');
          return;
        }
        const bookingId = paymentData._bookingId;
        const paymentId = paymentData._paymentId;
        await api.post(`/api/payments/confirm-payment/${paymentId}`, {
          transaction_id: transactionId,
          payment_details: { method: paymentMethod, tx_id: transactionId },
        });
        finishBooking(bookingId);
      }
    } catch (err: any) {
      const msg = err?.response?.data?.detail || 'Process failed. Please try again.';
      toast.error(typeof msg === 'string' ? msg : 'Action failed.');
    } finally {
      setIsProcessing(false);
    }
  };

  // ── Render ──────────────────────────────────────────────────────────
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ background: 'rgba(0,0,0,0.65)', backdropFilter: 'blur(6px)' }}
      onClick={e => e.target === e.currentTarget && onClose()}
    >
      <div className="bg-white rounded-3xl shadow-2xl w-full max-w-lg max-h-[92vh] overflow-y-auto">

        {/* Header */}
        <div className="bg-gradient-to-r from-teal-600 to-teal-800 rounded-t-3xl p-6 text-white relative">
          <button
            onClick={onClose}
            className="absolute top-4 right-4 w-8 h-8 bg-white/20 hover:bg-white/30 rounded-full flex items-center justify-center transition-all"
          >
            <X size={15} />
          </button>
          <p className="text-teal-200 text-xs font-black uppercase tracking-widest mb-1">Booking Request</p>
          <h2 className="font-black text-xl leading-tight pr-10">{service.name || service.title || 'Service'}</h2>
          <div className="flex items-center gap-4 mt-2 flex-wrap">
            <span className="text-teal-200 text-sm font-medium">{service.provider_name}</span>
            <span className="font-black text-white ml-auto text-lg">
              {formatPriceINR(servicePrice)}<span className="text-teal-300 text-sm font-medium">/hr</span>
            </span>
          </div>
        </div>

        <StepIndicator current={step} />

        <div className="p-6">

          {/* ── Step 1: Schedule ── */}
          {step === 'schedule' && (
            <div className="space-y-6">
              {/* Date picker */}
              <div>
                <label className="text-xs font-black text-gray-400 uppercase tracking-widest block mb-3">📅 Select Date</label>
                <div className="flex gap-2 overflow-x-auto pb-1">
                  {days.map((d, i) => {
                    const selected = selectedDate.toDateString() === d.toDateString();
                    return (
                      <button
                        key={i}
                        onClick={() => { setSelectedDate(d); setSelectedSlot(''); }}
                        className={`flex flex-col items-center min-w-[54px] px-3 py-3 rounded-2xl font-bold text-xs transition-all
                          ${selected ? 'bg-teal-600 text-white' : 'bg-gray-50 text-gray-600 border border-gray-100'}`}
                      >
                        <span className="text-[10px] uppercase font-black opacity-70">
                          {d.toLocaleDateString('en', { weekday: 'short' })}
                        </span>
                        <span className="text-2xl font-black mt-0.5">{d.getDate()}</span>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Slots */}
              <div>
                <label className="text-xs font-black text-gray-400 uppercase tracking-widest block mb-3">
                  <Clock size={12} className="inline mr-1" /> Available Slots
                </label>
                <div className="flex flex-wrap gap-2">
                  {slotsLoading ? (
                    <div className="w-full flex justify-center py-8">
                      <Loader className="animate-spin text-teal-500" size={24} />
                    </div>
                  ) : availableSlots.length > 0 ? (
                    availableSlots.map((slot: any) => (
                      <button
                        key={slot.start_time}
                        onClick={() => setSelectedSlot(slot.start_time)}
                        className={`relative px-4 py-2.5 rounded-2xl text-sm font-bold transition-all active:scale-95
                          ${selectedSlot === slot.start_time
                            ? 'bg-teal-600 text-white shadow-lg shadow-teal-200 ring-2 ring-teal-600 ring-offset-2'
                            : 'bg-white border border-gray-100 text-gray-700 hover:border-teal-300 hover:bg-teal-50 hover:text-teal-700'}`}
                      >
                        {slot.start_time}
                      </button>
                    ))
                  ) : (
                    <div className="w-full py-10 px-6 rounded-3xl border-2 border-dashed border-gray-100 flex flex-col items-center text-center bg-gray-50/50">
                      <div className="w-12 h-12 bg-gray-100 rounded-full flex items-center justify-center mb-3">
                        <Clock size={20} className="text-gray-400" />
                      </div>
                      <p className="font-black text-gray-900 text-sm">No Slots Available</p>
                      <p className="text-xs text-gray-400 font-medium mt-1">Provider is fully booked for this date.</p>
                    </div>
                  )}
                </div>
              </div>

              {/* Price summary */}
              <div className="bg-teal-50 rounded-2xl p-4 space-y-1.5 text-sm">
                <div className="flex justify-between text-gray-600"><span>Service</span><span className="font-bold">{formatPriceINR(originalPrice)}</span></div>
                {isRepeatCustomer && <div className="flex justify-between text-green-600 font-bold"><span>Repeat Booking (10% off)</span><span>-{formatPriceINR(repeatDiscount)}</span></div>}
                {pm.fee > 0 && <div className="flex justify-between text-gray-500"><span>Payment fee</span><span>{formatPriceINR(payFee)}</span></div>}
                <div className="flex justify-between text-gray-500"><span>GST (18%)</span><span>{formatPriceINR(gst)}</span></div>
                <div className="flex justify-between font-black text-gray-900 pt-1 border-t border-teal-200"><span>Total</span><span className="text-teal-700">{formatPriceINR(total)}</span></div>
              </div>

              <button
                onClick={handleContinueToPayment}
                className="w-full bg-teal-600 hover:bg-teal-700 text-white py-4 rounded-xl font-black text-sm transition-all flex items-center justify-center gap-2"
              >
                Continue to Payment <ChevronRight size={16} />
              </button>
            </div>
          )}

          {/* ── Step 2: Payment ── */}
          {step === 'payment' && (
            <div className="space-y-5">
              <button onClick={() => { setStep('schedule'); setPaymentData(null); setTransactionId(''); }}
                className="text-sm text-gray-400 font-bold">← Back</button>

              {/* Booking summary */}
              <div className="bg-teal-50 rounded-2xl p-4 flex justify-between items-center">
                <div>
                  <p className="font-black text-gray-900">
                    {selectedDate.toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })} at {selectedSlot}
                  </p>
                  <p className="text-xs text-gray-400">Escrow-protected booking · {loyaltyPoints} pts available</p>
                </div>
                <p className="font-black text-teal-600 text-lg">{formatPriceINR(total)}</p>
              </div>

              {/* Payment method selector */}
              <div>
                <label className="text-xs font-black text-gray-400 uppercase tracking-widest block mb-3">💳 Payment Method</label>
                <div className="grid grid-cols-5 gap-2">
                  {PAYMENT_METHODS.map(m => (
                    <button
                      key={m.id}
                      onClick={() => { setPaymentMethod(m.id); setPaymentData(null); setTransactionId(''); }}
                      className={`flex flex-col items-center p-3 rounded-xl border-2 text-xs font-bold transition-all
                        ${paymentMethod === m.id ? 'border-teal-500 bg-teal-50' : 'border-gray-100 hover:border-teal-200'}`}
                    >
                      <span className="text-xl mb-1">{m.icon}</span>
                      <span className="text-center leading-tight">{m.label}</span>
                      {m.recommended && <span className="text-[9px] text-teal-600 font-black mt-0.5">Best</span>}
                    </button>
                  ))}
                </div>
              </div>

              {/* ── Stripe Card Form ── */}
              {paymentMethod === 'card' && paymentData && stripeEnabled && (
                <div className="animate-in fade-in slide-in-from-bottom-2 duration-300">
                  <Elements stripe={stripePromise!} options={{ clientSecret: paymentData.client_secret }}>
                    <StripeCardForm
                      clientSecret={paymentData.client_secret}
                      paymentId={paymentData._paymentId}
                      total={total}
                      onSuccess={() => finishBooking(paymentData._bookingId)}
                      onError={msg => toast.error(msg)}
                    />
                  </Elements>
                </div>
              )}

              {/* ── UPI QR ── */}
              {paymentData && paymentMethod === 'upi' && (
                <div className="bg-teal-50 rounded-2xl p-6 text-center border border-teal-100 animate-in fade-in slide-in-from-bottom-2 duration-300">
                  <p className="text-sm font-black text-teal-800 mb-4">Scan QR to Pay</p>
                  <div className="w-40 h-40 bg-white mx-auto rounded-2xl flex items-center justify-center border border-teal-100">
                    <img
                      src={`https://api.qrserver.com/v1/create-qr-code/?size=150x150&data=${encodeURIComponent(paymentData.upi_qr)}`}
                      alt="UPI QR"
                      className="w-32 h-32"
                    />
                  </div>
                  <p className="mt-3 text-[10px] text-teal-500 font-bold truncate">{paymentData.upi_qr}</p>
                  <div className="mt-5 text-left">
                    <label className="text-[10px] font-black text-teal-700 uppercase tracking-widest block mb-2">
                      Enter Transaction ID (from your UPI app)
                    </label>
                    <input
                      type="text"
                      value={transactionId}
                      onChange={e => setTransactionId(e.target.value)}
                      placeholder="e.g. 123456789012"
                      className="w-full bg-white border-2 border-teal-100 focus:border-teal-500 rounded-xl px-4 py-3 text-sm font-bold outline-none transition-all"
                    />
                  </div>
                </div>
              )}

              {/* ── Net Banking Details ── */}
              {paymentData && paymentMethod === 'netbanking' && paymentData.bank_details && (
                <div className="bg-blue-50 rounded-2xl p-5 border border-blue-100 space-y-3 animate-in fade-in slide-in-from-bottom-2 duration-300">
                  <p className="text-sm font-black text-blue-800">Bank Transfer Details</p>
                  {[
                    ['A/C Name', paymentData.bank_details.account_name],
                    ['A/C Number', paymentData.bank_details.account_number],
                    ['IFSC', paymentData.bank_details.ifsc],
                    ['Bank', paymentData.bank_details.bank_name],
                  ].map(([l, v]) => (
                    <div key={l} className="flex justify-between items-center text-xs">
                      <span className="text-blue-500 font-bold uppercase">{l}</span>
                      <span className="font-black text-blue-900">{v}</span>
                    </div>
                  ))}
                  <div className="mt-4">
                    <label className="text-[10px] font-black text-blue-700 uppercase tracking-widest block mb-1">
                      Enter UTR / Transaction ID
                    </label>
                    <input
                      type="text"
                      value={transactionId}
                      onChange={e => setTransactionId(e.target.value)}
                      placeholder="Reference Number"
                      className="w-full bg-white border-2 border-blue-100 focus:border-blue-500 rounded-xl px-4 py-3 text-sm font-bold outline-none transition-all"
                    />
                  </div>
                </div>
              )}

              {/* ── Pay button (hidden for card+stripe — StripeCardForm has its own) ── */}
              {!(paymentMethod === 'card' && paymentData && stripeEnabled) && (
                <button
                  onClick={handlePay}
                  disabled={isProcessing}
                  className="w-full bg-teal-600 disabled:bg-gray-400 text-white py-4 rounded-xl font-black text-sm flex items-center justify-center gap-2 hover:bg-teal-700 transition-all"
                >
                  {isProcessing ? (
                    <Loader className="animate-spin" size={16} />
                  ) : (
                    <>
                      <Shield size={16} />
                      {paymentMethod === 'cod'
                        ? 'Confirm Cash Booking'
                        : paymentData
                        ? 'Confirm Payment'
                        : 'Generate Payment Details'}
                    </>
                  )}
                </button>
              )}
            </div>
          )}

          {/* ── Step 3: Confirmed ── */}
          {step === 'confirmed' && confirmation && (
            <div className="text-center py-4 space-y-6">
              <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mx-auto">
                <Check size={40} className="text-green-600" />
              </div>
              <h3 className="font-black text-2xl">Booking Confirmed! 🎉</h3>
              <div className="bg-gray-50 rounded-2xl p-5 text-left space-y-3">
                <div className="flex justify-between text-sm"><span className="text-gray-500">Date</span><span className="font-black">{confirmation.date}</span></div>
                <div className="flex justify-between text-sm"><span className="text-gray-500">Time</span><span className="font-black">{confirmation.time}</span></div>
                <div className="flex justify-between text-sm"><span className="text-gray-500">Provider</span><span className="font-black">{confirmation.provider}</span></div>
                <div className="flex justify-between text-sm"><span className="text-gray-500">Amount</span><span className="font-black text-teal-600">{formatPriceINR(confirmation.total)}</span></div>
              </div>
              <button
                onClick={() => window.open(receiptAPI.getBookingReceipt(confirmation.bookingId), '_blank')}
                className="w-full bg-blue-50 text-blue-800 py-3 rounded-xl font-black text-sm border border-blue-200 flex items-center justify-center gap-2 hover:bg-blue-100 transition-all"
              >
                <Package size={16} /> Download Signed Receipt
              </button>
              <button
                onClick={onClose}
                className="w-full bg-teal-600 hover:bg-teal-700 text-white py-4 rounded-xl font-black text-sm transition-all"
              >
                Done
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default BookingModal;
