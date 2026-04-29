import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { ShieldCheck, ShieldAlert, Loader2 } from 'lucide-react';
import api from '../services/api';

const ReceiptVerify: React.FC = () => {
  const { hash } = useParams<{ hash: string }>();
  const [status, setStatus] = useState<'loading' | 'valid' | 'invalid'>('loading');
  const [data, setData] = useState<any>(null);

  useEffect(() => {
    if (!hash) { setStatus('invalid'); return; }
    api.get(`/api/payments/verify/receipt/${hash}`)
      .then(r => { setData(r.data); setStatus('valid'); })
      .catch(() => setStatus('invalid'));
  }, [hash]);

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-3xl shadow-xl p-10 max-w-md w-full text-center">
        {status === 'loading' && (
          <>
            <Loader2 size={48} className="animate-spin text-teal-500 mx-auto mb-4" />
            <p className="font-bold text-gray-600">Verifying receipt…</p>
          </>
        )}
        {status === 'valid' && (
          <>
            <ShieldCheck size={56} className="text-green-500 mx-auto mb-4" />
            <h1 className="text-2xl font-black text-gray-900 mb-1">Receipt Verified ✓</h1>
            <p className="text-gray-500 text-sm mb-6">This document is authentic and has not been tampered with.</p>
            <div className="bg-gray-50 rounded-2xl p-5 text-left space-y-3">
              {[
                ['Transaction ID', data?.transaction_id],
                ['Amount',         `₹${data?.amount}`],
                ['Status',         data?.payment_status?.toUpperCase()],
                ['Date',           data?.date ? String(data.date).slice(0, 10) : '—'],
              ].map(([label, value]) => (
                <div key={label} className="flex justify-between text-sm">
                  <span className="text-gray-400 font-medium">{label}</span>
                  <span className="font-bold text-gray-800">{value}</span>
                </div>
              ))}
            </div>
            <div className="mt-5 bg-green-50 rounded-xl p-3">
              <p className="text-xs text-green-700 font-mono break-all">{hash}</p>
              <p className="text-xs text-green-600 mt-1 font-medium">SHA-256 Fingerprint</p>
            </div>
          </>
        )}
        {status === 'invalid' && (
          <>
            <ShieldAlert size={56} className="text-red-500 mx-auto mb-4" />
            <h1 className="text-2xl font-black text-gray-900 mb-1">Verification Failed</h1>
            <p className="text-gray-500 text-sm">This receipt hash was not found in our ledger. The document may be forged or tampered with.</p>
            <div className="mt-5 bg-red-50 rounded-xl p-3">
              <p className="text-xs text-red-600 font-mono break-all">{hash}</p>
            </div>
          </>
        )}
        <p className="text-xs text-gray-300 mt-6">QuickServe · Authenticated Receipt Engine</p>
      </div>
    </div>
  );
};

export default ReceiptVerify;
