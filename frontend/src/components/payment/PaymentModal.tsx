import React, { useState, useEffect } from 'react';
import { X, Copy, Check, QrCode, Building2, Download, Loader2, ArrowRight, CreditCard } from 'lucide-react';
import { QRCodeCanvas } from 'qrcode.react';
import toast from 'react-hot-toast';
import api, { receiptAPI } from '../../services/api';
import { formatPriceINR } from '../../utils/currency';

interface PaymentModalProps {
  bookingId: string;
  serviceName: string;
  amount: number;
  onSuccess: (paymentId: string) => void;
  onClose: () => void;
}

type PayMethod = 'upi' | 'bank' | 'card';
type LedgerStatus = 'pending' | 'in_progress' | 'paid' | 'receipt_generated';

const LEDGER_STEPS: { key: LedgerStatus; label: string }[] = [
  { key: 'pending',           label: 'Pending'    },
  { key: 'in_progress',       label: 'In Progress'},
  { key: 'paid',              label: 'Paid'       },
  { key: 'receipt_generated', label: 'Receipt'    },
];

const BANK = {
  account_name:   'QuickServe Solutions Pvt Ltd',
  account_number: '50200012345678',
  ifsc:           'HDFC0001234',
  bank_name:      'HDFC Bank',
};

const PaymentModal: React.FC<PaymentModalProps> = ({ bookingId, serviceName, amount, onSuccess, onClose }) => {
  const [method, setMethod]           = useState<PayMethod>('upi');
  const [upiString, setUpiString]     = useState('');
  const [paymentId, setPaymentId]     = useState('');
  const [clientSecret, setClientSecret] = useState('');
  const [stripeEnabled, setStripeEnabled] = useState(false);
  const [ledger, setLedger]           = useState<LedgerStatus>('pending');
  const [loading, setLoading]         = useState(true);
  const [confirming, setConfirming]   = useState(false);
  const [copied, setCopied]           = useState<string | null>(null);
  const [breakdown, setBreakdown]     = useState<any>(null);

  const gst   = amount * 0.18;
  const total = amount + gst;

  useEffect(() => {
    (async () => {
      try {
        const res = await api.post('/api/payments/create-payment-intent', {
          booking_id: bookingId, payment_method: method === 'card' ? 'card' : 'upi',
        });
        setPaymentId(res.data.payment_id);
        setClientSecret(res.data.client_secret || '');
        setStripeEnabled(res.data.stripe_enabled || false);
        setBreakdown(res.data.breakdown);
        const upi = res.data.upi_qr ||
          `upi://pay?pa=quickserve@hdfc&pn=QuickServe&am=${total.toFixed(2)}&tr=${bookingId}&cu=INR`;
        setUpiString(upi);
      } catch {
        setUpiString(`upi://pay?pa=quickserve@hdfc&pn=QuickServe&am=${total.toFixed(2)}&tr=${bookingId}&cu=INR`);
      } finally {
        setLoading(false);
      }
    })();
  }, [bookingId, total]);

  const copy = (text: string, key: string) => {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(key); toast.success('Copied!');
      setTimeout(() => setCopied(null), 2000);
    });
  };

  const confirmPayment = async () => {
    setConfirming(true);
    setLedger('in_progress');
    try {
      let pid = paymentId;
      if (pid) {
        await api.post(`/api/payments/confirm-payment/${pid}`, {
          payment_details: { method },
          stripe_payment_intent_id: clientSecret && stripeEnabled ? clientSecret.split('_secret_')[0] : undefined
        });
      } else {
        const res = await api.post('/api/payments/demo-transaction', {
          service_name: serviceName, amount, payment_method: method,
        });
        pid = res.data.payment_id;
        setPaymentId(pid);
      }
      setLedger('paid');
      setTimeout(() => { setLedger('receipt_generated'); toast.success('Payment confirmed! Receipt ready.'); onSuccess(pid); }, 1200);
    } catch (e: any) {
      toast.error(e.response?.data?.detail || 'Payment confirmation failed');
      setLedger('pending');
    } finally {
      setConfirming(false);
    }
  };

  const currentStep = LEDGER_STEPS.findIndex(s => s.key === ledger);

  const CopyRow = ({ label, value, field }: { label: string; value: string; field: string }) => (
    <div className="flex items-center justify-between bg-gray-50 rounded-xl px-4 py-3">
      <div>
        <p className="text-xs text-gray-400">{label}</p>
        <p className="font-bold text-gray-800 text-sm">{value}</p>
      </div>
      <button onClick={() => copy(value, field)} className="text-teal-600 hover:text-teal-800 p-1">
        {copied === field ? <Check size={16} className="text-green-500" /> : <Copy size={16} />}
      </button>
    </div>
  );

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-3xl shadow-2xl w-full max-w-md overflow-hidden">

        {/* Header */}
        <div className="bg-gradient-to-r from-teal-600 to-emerald-500 p-5 flex items-center justify-between">
          <div>
            <h2 className="text-white font-black text-lg">Secure Payment</h2>
            <p className="text-white/70 text-xs">{serviceName}</p>
          </div>
          <button onClick={onClose} className="text-white/70 hover:text-white"><X size={20} /></button>
        </div>

        {/* Ledger Pipeline */}
        <div className="px-5 pt-4">
          <div className="flex items-center">
            {LEDGER_STEPS.map((step, i) => (
              <React.Fragment key={step.key}>
                <div className="flex flex-col items-center">
                  <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-black transition-all ${
                    i <= currentStep ? 'bg-teal-600 text-white' : 'bg-gray-200 text-gray-400'
                  }`}>
                    {i < currentStep ? <Check size={12} /> : i + 1}
                  </div>
                  <p className={`text-xs mt-1 font-medium whitespace-nowrap ${i <= currentStep ? 'text-teal-600' : 'text-gray-400'}`}>
                    {step.label}
                  </p>
                </div>
                {i < LEDGER_STEPS.length - 1 && (
                  <div className={`flex-1 h-0.5 mb-4 mx-1 transition-all ${i < currentStep ? 'bg-teal-500' : 'bg-gray-200'}`} />
                )}
              </React.Fragment>
            ))}
          </div>
        </div>

        {/* Amount Breakdown */}
        <div className="mx-5 mt-3 bg-gray-50 rounded-2xl px-4 py-3 space-y-1">
          <div className="flex justify-between text-sm text-gray-500"><span>Service</span><span>{formatPriceINR(breakdown?.base_amount ?? amount)}</span></div>
          {breakdown?.discounts > 0 && (
            <div className="flex justify-between text-sm text-green-600"><span>Discount</span><span>-{formatPriceINR(breakdown.discounts)}</span></div>
          )}
          <div className="flex justify-between text-sm text-gray-500"><span>GST (18%)</span><span>{formatPriceINR(breakdown?.gst ?? gst)}</span></div>
          <div className="flex justify-between font-black text-gray-900 pt-2 border-t border-gray-200">
            <span>Total</span><span className="text-teal-600">{formatPriceINR(breakdown?.total ?? total)}</span>
          </div>
        </div>

        {/* Method Tabs */}
        <div className="flex gap-2 px-5 mt-4">
          {(['upi', 'card', 'bank'] as PayMethod[]).map(m => (
            <button key={m} onClick={() => setMethod(m)}
              className={`flex-1 flex items-center justify-center gap-1.5 py-2.5 rounded-xl text-xs font-bold transition-all ${
                method === m ? 'bg-teal-600 text-white shadow-md' : 'bg-gray-100 text-gray-500 hover:bg-gray-200'
              }`}>
              {m === 'upi' ? <><QrCode size={13} /> UPI</> : m === 'card' ? <><CreditCard size={13} /> Card</> : <><Building2 size={13} /> Bank</>}
            </button>
          ))}
        </div>

        {/* Payment Content */}
        <div className="px-5 py-4">
          {method === 'upi' && (
            <div className="flex flex-col items-center gap-3">
              {loading ? (
                <div className="w-48 h-48 bg-gray-100 rounded-2xl flex items-center justify-center">
                  <Loader2 size={32} className="animate-spin text-teal-500" />
                </div>
              ) : (
                <div className="p-3 bg-white border-4 border-teal-100 rounded-2xl">
                  <QRCodeCanvas value={upiString || 'https://quickserve.app'} size={180} />
                </div>
              )}
              <p className="text-xs text-gray-500 text-center">Scan with PhonePe · GPay · Paytm · Any UPI app</p>
              <button onClick={() => copy(upiString, 'upi')}
                className="flex items-center gap-1.5 text-xs text-teal-600 font-bold hover:text-teal-800">
                {copied === 'upi' ? <Check size={13} /> : <Copy size={13} />} Copy UPI Link
              </button>
            </div>
          )}
          {method === 'card' && (
            <div className="space-y-3">
              {stripeEnabled ? (
                <div className="bg-blue-50 border border-blue-200 rounded-xl p-4">
                  <p className="text-sm font-bold text-blue-800 mb-2">💳 Stripe Secure Card Payment</p>
                  <p className="text-xs text-blue-600">Payment Intent created. Use your Stripe test card:</p>
                  <code className="text-xs bg-white px-2 py-1 rounded mt-1 block font-mono">4242 4242 4242 4242</code>
                  <p className="text-xs text-blue-500 mt-1">Any future expiry · Any CVC · Any ZIP</p>
                </div>
              ) : (
                <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-4">
                  <p className="text-sm font-bold text-yellow-800">⚠️ Stripe not configured</p>
                  <p className="text-xs text-yellow-600 mt-1">Add your Stripe secret key to backend/.env to enable card payments. Using demo mode.</p>
                </div>
              )}
              <p className="text-xs text-gray-400 text-center">After completing payment, click "I Have Paid" below</p>
            </div>
          )}
          {method === 'bank' && (
            <div className="space-y-2">
              <CopyRow label="Account Name"   value={BANK.account_name}   field="name"  />
              <CopyRow label="Account Number" value={BANK.account_number} field="accno" />
              <CopyRow label="IFSC Code"      value={BANK.ifsc}           field="ifsc"  />
              <CopyRow label="Bank"           value={BANK.bank_name}      field="bank"  />
              <p className="text-xs text-gray-400 text-center pt-1">
                Use <strong>{bookingId.slice(-8).toUpperCase()}</strong> as payment reference
              </p>
            </div>
          )}
        </div>

        {/* CTA */}
        <div className="px-5 pb-5">
          {ledger === 'receipt_generated' ? (
            <button
              onClick={() => window.open(receiptAPI.generate(paymentId || bookingId), '_blank')}
              className="w-full flex items-center justify-center gap-2 bg-green-600 hover:bg-green-700 text-white py-3.5 rounded-2xl font-black text-sm transition-all"
            >
              <Download size={16} /> Download Receipt (PDF)
            </button>
          ) : (
            <button onClick={confirmPayment} disabled={confirming || loading}
              className="w-full flex items-center justify-center gap-2 bg-teal-600 hover:bg-teal-700 disabled:opacity-50 text-white py-3.5 rounded-2xl font-black text-sm transition-all">
              {confirming ? <Loader2 size={16} className="animate-spin" /> : <ArrowRight size={16} />}
              {confirming ? 'Confirming…' : 'I Have Paid'}
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default PaymentModal;
