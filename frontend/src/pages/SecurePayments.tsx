import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Shield, Lock, CreditCard, RefreshCw, AlertCircle, CheckCircle } from 'lucide-react';

const PAYMENT_ICONS: Record<string, string> = {
  card: '💳', upi: '📱', netbanking: '🏦', wallet: '👛', cod: '💵',
};

const SecurePayments: React.FC = () => {
  const navigate = useNavigate();
  const [methods, setMethods] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selectedMethod, setSelectedMethod] = useState('upi');
  const [amount] = useState(750);

  const fetchMethods = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await fetch('http://localhost:8000/api/payments/methods/available');
      if (!res.ok) throw new Error('Failed');
      const data = await res.json();
      setMethods(data.methods || []);
    } catch {
      setError('Unable to load payment methods. Please check your connection.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchMethods(); }, []);

  const selected = methods.find(m => m.id === selectedMethod);
  const fee = selected ? amount * (selected.fee_percentage / 100) : 0;
  const gst = amount * 0.18;
  const total = amount + fee + gst;

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-gradient-to-r from-green-600 to-emerald-500 text-white py-16 px-4">
        <div className="max-w-5xl mx-auto">
          <button onClick={() => navigate(-1)} className="flex items-center gap-2 text-white/80 hover:text-white mb-6 transition-colors">
            <ArrowLeft className="w-5 h-5" /> Back
          </button>
          <div className="flex items-center gap-4 mb-4">
            <div className="w-16 h-16 bg-white/20 rounded-2xl flex items-center justify-center text-4xl">💳</div>
            <div>
              <h1 className="text-4xl font-bold">Secure Payments</h1>
              <p className="text-white/80 text-lg mt-1">Escrow-protected payments with instant refunds</p>
            </div>
          </div>
          <div className="flex gap-6 mt-6">
            {[['100%', 'Secure'], ['Escrow', 'Protected'], ['Instant', 'Refunds']].map(([val, label]) => (
              <div key={label} className="bg-white/20 rounded-xl px-5 py-3 text-center">
                <div className="text-2xl font-bold">{val}</div>
                <div className="text-sm text-white/80">{label}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="max-w-5xl mx-auto px-4 py-12 space-y-10">
        {/* Payment Methods */}
        <div className="bg-white rounded-2xl shadow-xl p-8">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-bold text-gray-900">Available Payment Methods</h2>
            <button onClick={fetchMethods} className="flex items-center gap-2 text-green-600 hover:text-green-800 font-semibold text-sm transition-colors">
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} /> Refresh
            </button>
          </div>

          {loading && (
            <div className="grid md:grid-cols-3 gap-4">
              {[...Array(5)].map((_, i) => <div key={i} className="h-20 bg-gray-100 rounded-xl animate-pulse" />)}
            </div>
          )}

          {error && !loading && (
            <div className="flex flex-col items-center gap-4 py-8 text-center">
              <AlertCircle className="w-10 h-10 text-red-400" />
              <p className="text-gray-600">{error}</p>
              <button onClick={fetchMethods} className="flex items-center gap-2 bg-green-600 text-white px-5 py-2 rounded-xl font-semibold hover:bg-green-700 transition-colors">
                <RefreshCw className="w-4 h-4" /> Retry
              </button>
            </div>
          )}

          {!loading && !error && (
            <div className="grid md:grid-cols-3 gap-4">
              {methods.map(m => (
                <button
                  key={m.id}
                  onClick={() => setSelectedMethod(m.id)}
                  className={`p-5 rounded-xl border-2 text-left transition-all ${
                    selectedMethod === m.id
                      ? 'border-green-500 bg-green-50 shadow-md'
                      : 'border-gray-200 hover:border-green-300'
                  }`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-2xl">{PAYMENT_ICONS[m.id] || '💰'}</span>
                    {m.recommended && (
                      <span className="text-xs bg-green-500 text-white px-2 py-0.5 rounded-full font-bold">Recommended</span>
                    )}
                    {selectedMethod === m.id && <CheckCircle className="w-5 h-5 text-green-500" />}
                  </div>
                  <p className="font-bold text-gray-900">{m.name}</p>
                  <p className="text-sm text-gray-500 mt-1">
                    {m.fee_percentage === 0 ? 'No extra fee' : `+${m.fee_percentage}% fee`}
                    {m.instant ? ' · Instant' : ' · 1-2 days'}
                  </p>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Payment Breakdown */}
        {!loading && !error && methods.length > 0 && (
          <div className="bg-white rounded-2xl shadow-xl p-8">
            <h2 className="text-xl font-bold text-gray-900 mb-6">Payment Breakdown</h2>
            <div className="max-w-sm space-y-3">
              {[
                ['Service Amount', `₹${amount}`],
                [`${selected?.name || ''} Fee`, fee > 0 ? `+₹${fee.toFixed(2)}` : 'Free'],
                ['GST (18%)', `+₹${gst.toFixed(2)}`],
              ].map(([label, value]) => (
                <div key={label} className="flex justify-between text-gray-700">
                  <span>{label}</span>
                  <span className={value.startsWith('+') ? 'text-gray-500' : 'font-semibold'}>{value}</span>
                </div>
              ))}
              <div className="border-t-2 border-gray-200 pt-3 flex justify-between font-black text-lg">
                <span>Total</span>
                <span className="text-green-600">₹{total.toFixed(2)}</span>
              </div>
            </div>
            <div className="mt-6 flex items-center gap-2 text-sm text-gray-500">
              <Lock className="w-4 h-4 text-green-500" />
              Funds held in escrow until service is completed
            </div>
          </div>
        )}

        {/* Escrow Flow */}
        <div className="bg-white rounded-2xl shadow-xl p-8">
          <h2 className="text-xl font-bold text-gray-900 mb-6">How Escrow Protection Works</h2>
          <div className="grid md:grid-cols-4 gap-4">
            {[
              { icon: '💳', step: '1', title: 'You Pay', desc: 'Payment is captured and held securely in escrow' },
              { icon: '🔒', step: '2', title: 'Funds Held', desc: 'Provider cannot access funds until job is done' },
              { icon: '✅', step: '3', title: 'Job Complete', desc: 'You confirm the service was completed satisfactorily' },
              { icon: '💸', step: '4', title: 'Provider Paid', desc: 'Funds are instantly released to the provider' },
            ].map(({ icon, step, title, desc }) => (
              <div key={step} className="text-center">
                <div className="w-14 h-14 bg-gradient-to-br from-green-500 to-emerald-600 rounded-2xl flex items-center justify-center text-2xl mx-auto mb-3 shadow-lg">
                  {icon}
                </div>
                <div className="text-xs font-bold text-green-500 mb-1">STEP {step}</div>
                <h3 className="font-bold text-gray-900 mb-1">{title}</h3>
                <p className="text-xs text-gray-500">{desc}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Security Badges */}
        <div className="grid md:grid-cols-3 gap-6">
          {[
            { icon: <Shield className="w-8 h-8 text-green-600" />, title: '256-bit SSL Encryption', desc: 'All transactions encrypted with bank-grade security' },
            { icon: <Lock className="w-8 h-8 text-blue-600" />, title: 'PCI DSS Compliant', desc: 'Meets the highest payment card industry standards' },
            { icon: <CreditCard className="w-8 h-8 text-purple-600" />, title: 'Instant Refunds', desc: 'Full refund within 24 hours if service is unsatisfactory' },
          ].map(({ icon, title, desc }) => (
            <div key={title} className="bg-white rounded-2xl shadow-lg p-6 flex gap-4 items-start hover:shadow-xl transition-shadow">
              <div className="shrink-0">{icon}</div>
              <div>
                <h3 className="font-bold text-gray-900 mb-1">{title}</h3>
                <p className="text-sm text-gray-600">{desc}</p>
              </div>
            </div>
          ))}
        </div>

        <div className="text-center">
          <button onClick={() => navigate('/services')} className="bg-gradient-to-r from-green-600 to-emerald-500 text-white px-10 py-4 rounded-full font-bold text-lg hover:opacity-90 transition-all hover:scale-105 shadow-xl">
            Book & Pay Securely →
          </button>
        </div>
      </div>
    </div>
  );
};

export default SecurePayments;
