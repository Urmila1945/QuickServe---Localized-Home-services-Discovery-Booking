import React, { useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, X, Check, Camera, Shield, ArrowRight } from 'lucide-react';
import toast from 'react-hot-toast';
import api from '../../services/api';

interface WorkVerificationProps {
  jobId: string;
  onSuccess: () => void;
  onClose: () => void;
}

const WorkVerification: React.FC<WorkVerificationProps> = ({ jobId, onSuccess, onClose }) => {
  const [beforeImage, setBeforeImage] = useState<File | null>(null);
  const [afterImage, setAfterImage] = useState<File | null>(null);
  const [isUploading, setIsUploading] = useState(false);

  const onDropBefore = (acceptedFiles: File[]) => setBeforeImage(acceptedFiles[0]);
  const onDropAfter = (acceptedFiles: File[]) => setAfterImage(acceptedFiles[0]);

  const { getRootProps: getBeforeProps, getInputProps: getBeforeInput } = useDropzone({
    onDrop: onDropBefore,
    accept: { 'image/*': [] },
    maxFiles: 1
  });

  const { getRootProps: getAfterProps, getInputProps: getAfterInput } = useDropzone({
    onDrop: onDropAfter,
    accept: { 'image/*': [] },
    maxFiles: 1
  });

  const handleSubmit = async () => {
    if (!beforeImage || !afterImage) {
      toast.error('Please upload both Before and After images');
      return;
    }

    setIsUploading(true);
    try {
      // Get current location for timestamped evidence
      navigator.geolocation.getCurrentPosition(async (pos) => {
        const formData = new FormData();
        formData.append('job_id', jobId);
        formData.append('before_image', beforeImage);
        formData.append('after_image', afterImage);
        formData.append('latitude', pos.coords.latitude.toString());
        formData.append('longitude', pos.coords.longitude.toString());

        await api.post('/api/verify/work', formData);
        toast.success('Work verified and evidence stored! Task completed.');
        onSuccess();
      }, () => {
        toast.error('Location access required for work verification.');
        setIsUploading(false);
      });
    } catch (err) {
      toast.error('Upload failed. Please try again.');
      setIsUploading(false);
    }
  };

  return (
    <div className="bg-white rounded-[32px] p-8 max-w-2xl w-full shadow-2xl border border-gray-100">
      <div className="flex items-center gap-4 mb-8">
        <div className="w-12 h-12 bg-teal-50 rounded-2xl flex items-center justify-center text-teal-600">
          <Shield size={24} />
        </div>
        <div>
          <h2 className="text-2xl font-black text-gray-900">Work Evidence & Verification</h2>
          <p className="text-gray-500 text-sm font-medium">Upload proof of work to complete the job and get paid.</p>
        </div>
        <button onClick={onClose} className="ml-auto text-gray-400 hover:text-gray-600">
          <X size={24} />
        </button>
      </div>

      <div className="grid md:grid-cols-2 gap-6 mb-8">
        {/* Before Image */}
        <div className="space-y-3">
          <label className="text-xs font-black text-gray-400 uppercase tracking-widest pl-1">Before Work</label>
          <div {...getBeforeProps()} className={`aspect-video rounded-2xl border-2 border-dashed flex flex-col items-center justify-center transition-all cursor-pointer overflow-hidden ${
            beforeImage ? 'border-teal-500 bg-teal-50' : 'border-gray-200 hover:border-teal-300 hover:bg-gray-50'
          }`}>
            <input {...getBeforeInput()} />
            {beforeImage ? (
              <img src={URL.createObjectURL(beforeImage)} className="w-full h-full object-cover" alt="Before" />
            ) : (
              <div className="text-center p-4">
                <Camera size={32} className="mx-auto text-gray-300 mb-2" />
                <p className="text-xs font-bold text-gray-500">Drop "Before" Image Here</p>
              </div>
            )}
          </div>
        </div>

        {/* After Image */}
        <div className="space-y-3">
          <label className="text-xs font-black text-gray-400 uppercase tracking-widest pl-1">After Completion</label>
          <div {...getAfterProps()} className={`aspect-video rounded-2xl border-2 border-dashed flex flex-col items-center justify-center transition-all cursor-pointer overflow-hidden ${
            afterImage ? 'border-teal-500 bg-teal-50' : 'border-gray-200 hover:border-teal-300 hover:bg-gray-50'
          }`}>
            <input {...getAfterInput()} />
            {afterImage ? (
              <img src={URL.createObjectURL(afterImage)} className="w-full h-full object-cover" alt="After" />
            ) : (
              <div className="text-center p-4">
                <Check size={32} className="mx-auto text-gray-300 mb-2" />
                <p className="text-xs font-bold text-gray-500">Drop "After" Image Here</p>
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="bg-teal-50 rounded-2xl p-5 mb-8 flex gap-4 items-start">
        <Shield size={18} className="text-teal-600 mt-0.5" />
        <p className="text-xs text-teal-800 font-medium leading-relaxed">
          <strong>Security Protocol:</strong> Your images are automatically timestamped and GPS-tagged. This data is cryptographically signed and stored to ensure the authenticity of your work.
        </p>
      </div>

      <button
        onClick={handleSubmit}
        disabled={isUploading || !beforeImage || !afterImage}
        className="w-full bg-teal-600 hover:bg-teal-700 disabled:opacity-50 text-white py-5 rounded-2xl font-black text-lg transition-all shadow-xl shadow-teal-200 flex items-center justify-center gap-3 active:scale-95"
      >
        {isUploading ? 'Warping Evidence...' : <><Check size={20} /> Verify & Complete Job <ArrowRight size={20} /></>}
      </button>
    </div>
  );
};

export default WorkVerification;
