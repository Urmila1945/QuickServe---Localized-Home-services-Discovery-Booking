import React, { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { Camera, Check, MapPin, Shield, X, Upload, Star, Image } from 'lucide-react';
import toast from 'react-hot-toast';
import api from '../../services/api';

interface WorkGalleryProps {
  bookingId: string;
  providerId: string;
  onSuccess?: () => void;
  onClose?: () => void;
}

interface GalleryItem {
  _id: string;
  booking_id: string;
  images: { label: string; path: string }[];
  latitude: number;
  longitude: number;
  submitted_at: string;
  notes: string;
}

const WorkGallery: React.FC<WorkGalleryProps> = ({ bookingId, providerId, onSuccess, onClose }) => {
  const [beforeFile, setBeforeFile] = useState<File | null>(null);
  const [afterFile, setAfterFile] = useState<File | null>(null);
  const [notes, setNotes] = useState('');
  const [gps, setGps] = useState<{ lat: number; lng: number } | null>(null);
  const [gpsLoading, setGpsLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [gallery, setGallery] = useState<GalleryItem[]>([]);
  const [trustScore, setTrustScore] = useState<number | null>(null);
  const [tab, setTab] = useState<'upload' | 'gallery'>('upload');
  const [enteredOtp, setEnteredOtp] = useState('');

  const generateOTP = (id: string) => {
    if (!id) return '1234';
    let hash = 0;
    for (let i = 0; i < id.length; i++) hash = id.charCodeAt(i) + ((hash << 5) - hash);
    return (Math.abs(hash) % 9000 + 1000).toString();
  };
  const expectedOtp = generateOTP(bookingId);

  const onDropBefore = useCallback((files: File[]) => setBeforeFile(files[0] || null), []);
  const onDropAfter = useCallback((files: File[]) => setAfterFile(files[0] || null), []);

  const { getRootProps: beforeProps, getInputProps: beforeInput, isDragActive: beforeDrag } = useDropzone({
    onDrop: onDropBefore, accept: { 'image/*': [] }, maxFiles: 1,
  });
  const { getRootProps: afterProps, getInputProps: afterInput, isDragActive: afterDrag } = useDropzone({
    onDrop: onDropAfter, accept: { 'image/*': [] }, maxFiles: 1,
  });

  const captureGPS = () => {
    setGpsLoading(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setGps({ lat: pos.coords.latitude, lng: pos.coords.longitude });
        setGpsLoading(false);
        toast.success('GPS location captured!');
      },
      () => { toast.error('Location access denied'); setGpsLoading(false); },
      { timeout: 10000 }
    );
  };

  const loadGallery = async () => {
    try {
      const res = await api.get(`/api/work-verification/gallery/${providerId}`);
      setGallery(res.data.gallery || []);
      const ts = await api.get(`/api/work-verification/trust-score/${providerId}`);
      setTrustScore(ts.data.trust_score);
    } catch { /* silent */ }
  };

  const handleTabChange = (t: 'upload' | 'gallery') => {
    setTab(t);
    if (t === 'gallery') loadGallery();
  };

  const handleSubmit = async () => {
    if (!beforeFile || !afterFile) { toast.error('Upload both Before and After images'); return; }
    if (!gps) { toast.error('Capture GPS location first'); return; }
    if (enteredOtp !== expectedOtp) { toast.error('Invalid Completion OTP. Please check with the customer.'); return; }

    setSubmitting(true);
    try {
      const fd = new FormData();
      fd.append('booking_id', bookingId);
      fd.append('latitude', String(gps.lat));
      fd.append('longitude', String(gps.lng));
      fd.append('notes', notes);
      fd.append('before_image', beforeFile);
      fd.append('after_image', afterFile);

      const res = await api.post('/api/work-verification/verify-work', fd, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      toast.success(`Work verified! Trust score: ${res.data.trust_score}`);
      onSuccess?.();
    } catch (e: any) {
      toast.error(e.response?.data?.detail || 'Upload failed');
    } finally {
      setSubmitting(false);
    }
  };

  const DropZone = ({
    rootProps, inputProps, file, isDrag, label, icon: Icon,
  }: {
    rootProps: any; inputProps: any; file: File | null; isDrag: boolean; label: string; icon: React.ElementType;
  }) => (
    <div className="space-y-2">
      <p className="text-xs font-black text-gray-400 uppercase tracking-widest">{label}</p>
      <div
        {...rootProps}
        className={`aspect-video rounded-2xl border-2 border-dashed flex flex-col items-center justify-center cursor-pointer overflow-hidden transition-all ${
          file ? 'border-teal-500 bg-teal-50' : isDrag ? 'border-teal-400 bg-teal-50' : 'border-gray-200 hover:border-teal-300'
        }`}
      >
        <input {...inputProps} />
        {file ? (
          <img src={URL.createObjectURL(file)} className="w-full h-full object-cover" alt={label} />
        ) : (
          <div className="text-center p-4">
            <Icon size={32} className="mx-auto text-gray-300 mb-2" />
            <p className="text-xs font-bold text-gray-400">Drop or click to upload</p>
          </div>
        )}
      </div>
    </div>
  );

  return (
    <div className="bg-white rounded-3xl shadow-2xl border border-gray-100 max-w-2xl w-full overflow-hidden">
      {/* Header */}
      <div className="bg-gradient-to-r from-teal-600 to-emerald-500 p-6 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Shield className="text-white" size={24} />
          <div>
            <h2 className="text-white font-black text-lg">Work Evidence Gallery</h2>
            <p className="text-white/70 text-xs">Upload proof · GPS check-in · Build trust score</p>
          </div>
        </div>
        {onClose && <button onClick={onClose} className="text-white/70 hover:text-white"><X size={20} /></button>}
      </div>

      {/* Tabs */}
      <div className="flex border-b border-gray-100">
        {(['upload', 'gallery'] as const).map(t => (
          <button
            key={t}
            onClick={() => handleTabChange(t)}
            className={`flex-1 py-3 text-sm font-bold capitalize transition-colors ${
              tab === t ? 'text-teal-600 border-b-2 border-teal-600' : 'text-gray-400 hover:text-gray-600'
            }`}
          >
            {t === 'upload' ? <span className="flex items-center justify-center gap-2"><Upload size={14} /> Upload Evidence</span>
              : <span className="flex items-center justify-center gap-2"><Image size={14} /> My Gallery</span>}
          </button>
        ))}
      </div>

      <div className="p-6">
        {tab === 'upload' ? (
          <div className="space-y-5">
            {/* Before / After dropzones */}
            <div className="grid grid-cols-2 gap-4">
              <DropZone rootProps={beforeProps()} inputProps={beforeInput()} file={beforeFile} isDrag={beforeDrag} label="Before Work" icon={Camera} />
              <DropZone rootProps={afterProps()} inputProps={afterInput()} file={afterFile} isDrag={afterDrag} label="After Completion" icon={Check} />
            </div>

            {/* GPS Check-in */}
            <div className="flex items-center gap-3 bg-gray-50 rounded-2xl p-4">
              <MapPin size={18} className={gps ? 'text-teal-600' : 'text-gray-400'} />
              <div className="flex-1">
                {gps ? (
                  <p className="text-xs font-bold text-teal-700">
                    ✓ GPS: {gps.lat.toFixed(5)}, {gps.lng.toFixed(5)}
                  </p>
                ) : (
                  <p className="text-xs text-gray-500">GPS check-in required for proof of visit</p>
                )}
              </div>
              <button
                onClick={captureGPS}
                disabled={gpsLoading || !!gps}
                className="text-xs font-bold bg-teal-600 text-white px-3 py-1.5 rounded-lg disabled:opacity-50 hover:bg-teal-700 transition-colors"
              >
                {gpsLoading ? 'Locating…' : gps ? 'Captured ✓' : 'Check In'}
              </button>
            </div>

            <textarea
              value={notes}
              onChange={e => setNotes(e.target.value)}
              placeholder="Optional: describe the work done…"
              rows={2}
              className="w-full border border-gray-200 rounded-xl px-4 py-3 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-teal-400"
            />

            {/* OTP Input */}
            <div>
              <label className="block text-xs font-black text-gray-400 uppercase tracking-widest mb-2">Completion OTP</label>
              <div className="flex gap-3">
                <input
                  type="text"
                  maxLength={4}
                  value={enteredOtp}
                  onChange={e => setEnteredOtp(e.target.value.replace(/\D/g, ''))}
                  placeholder="Ask customer for 4-digit PIN"
                  className="flex-1 bg-gray-50 border-2 border-gray-100 focus:border-teal-400 rounded-xl px-4 py-3 text-lg font-mono tracking-widest focus:outline-none transition-colors"
                />
              </div>
            </div>

            <button
              onClick={handleSubmit}
              disabled={submitting || !beforeFile || !afterFile || !gps || enteredOtp.length !== 4}
              className="w-full bg-teal-600 hover:bg-teal-700 disabled:opacity-40 text-white py-4 rounded-2xl font-black text-sm transition-all flex items-center justify-center gap-2"
            >
              {submitting ? 'Submitting…' : <><Check size={16} /> Submit Work Evidence</>}
            </button>
          </div>
        ) : (
          <div className="space-y-4">
            {trustScore !== null && (
              <div className="bg-teal-50 rounded-2xl p-4 flex items-center gap-3">
                <Star size={20} className="text-teal-600" />
                <div>
                  <p className="text-xs text-gray-500">Trust Score</p>
                  <p className="text-2xl font-black text-teal-700">{trustScore}<span className="text-sm font-normal text-gray-400">/100</span></p>
                </div>
                <div className="flex-1 ml-2">
                  <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                    <div className="h-full bg-teal-500 rounded-full transition-all" style={{ width: `${trustScore}%` }} />
                  </div>
                  <p className="text-xs text-gray-400 mt-1">
                    Trust = 0.4×Rating + 0.3×Sentiment + 0.3×Gallery
                  </p>
                </div>
              </div>
            )}
            {gallery.length === 0 ? (
              <div className="text-center py-12 text-gray-400">
                <Image size={40} className="mx-auto mb-3 opacity-30" />
                <p className="font-bold">No gallery items yet</p>
                <p className="text-xs mt-1">Submit work evidence to build your gallery</p>
              </div>
            ) : (
              <div className="grid grid-cols-2 gap-3">
                {gallery.map(item => (
                  <div key={item._id} className="bg-gray-50 rounded-xl overflow-hidden border border-gray-100">
                    <div className="grid grid-cols-2 gap-0.5">
                      {item.images.map(img => (
                        <div key={img.label} className="aspect-square bg-gray-200 relative">
                          <span className="absolute top-1 left-1 text-xs bg-black/50 text-white px-1.5 py-0.5 rounded font-bold capitalize">
                            {img.label}
                          </span>
                        </div>
                      ))}
                    </div>
                    <div className="p-2">
                      <p className="text-xs text-gray-500 flex items-center gap-1">
                        <MapPin size={10} /> {item.latitude?.toFixed(3)}, {item.longitude?.toFixed(3)}
                      </p>
                      <p className="text-xs text-gray-400">{item.submitted_at?.slice(0, 10)}</p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default WorkGallery;
