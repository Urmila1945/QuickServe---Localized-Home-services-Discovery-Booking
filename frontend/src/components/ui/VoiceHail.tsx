import React, { useState, useRef } from 'react';
import { MicrophoneIcon, StopIcon } from '@heroicons/react/24/solid';
import { useAuth } from '../../contexts/AuthContext';
import toast from 'react-hot-toast';

interface VoiceHailProps {
  onHailSent?: (hailId: string) => void;
}

export default function VoiceHail({ onHailSent }: VoiceHailProps) {
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const { user } = useAuth();

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;

      const audioChunks: BlobPart[] = [];
      
      mediaRecorder.ondataavailable = (event) => {
        audioChunks.push(event.data);
      };

      mediaRecorder.onstop = () => {
        const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
        setAudioBlob(audioBlob);
        stream.getTracks().forEach(track => track.stop());
      };

      mediaRecorder.start();
      setIsRecording(true);
      
      // Auto-stop after 15 seconds
      setTimeout(() => {
        if (mediaRecorderRef.current && isRecording) {
          stopRecording();
        }
      }, 15000);

    } catch (error) {
      toast.error('Could not access microphone');
      console.error('Error accessing microphone:', error);
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  const sendHail = async () => {
    if (!audioBlob || !user) return;

    setIsProcessing(true);
    
    try {
      // Get current location
      const position = await getCurrentPosition();
      
      const formData = new FormData();
      formData.append('audio_file', audioBlob, 'hail.wav');
      formData.append('latitude', position.coords.latitude.toString());
      formData.append('longitude', position.coords.longitude.toString());

      const response = await fetch('/api/hail/broadcast', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: formData
      });

      if (response.ok) {
        const result = await response.json();
        toast.success(`Hail sent to ${result.customers_notified} nearby customers!`);
        
        if (onHailSent) {
          onHailSent(result.hail_id);
        }
        
        // Reset state
        setAudioBlob(null);
      } else {
        throw new Error('Failed to send hail');
      }
    } catch (error) {
      toast.error('Failed to send voice hail');
      console.error('Error sending hail:', error);
    } finally {
      setIsProcessing(false);
    }
  };

  const getCurrentPosition = (): Promise<GeolocationPosition> => {
    return new Promise((resolve, reject) => {
      navigator.geolocation.getCurrentPosition(resolve, reject, {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 60000
      });
    });
  };

  if (user?.role !== 'provider') {
    return null;
  }

  return (
    <div className="bg-white rounded-lg shadow-lg p-6">
      <h3 className="text-lg font-semibold mb-4">🎤 Voice Hail Service</h3>
      
      <div className="text-center">
        {!audioBlob && (
          <div>
            <p className="text-gray-600 mb-4">
              Broadcast your voice to nearby customers within 0.2 miles
            </p>
            
            <button
              onClick={isRecording ? stopRecording : startRecording}
              disabled={isProcessing}
              className={`w-20 h-20 rounded-full flex items-center justify-center text-white text-2xl transition-all ${
                isRecording 
                  ? 'bg-red-600 hover:bg-red-700 animate-pulse' 
                  : 'bg-blue-600 hover:bg-blue-700'
              }`}
            >
              {isRecording ? <StopIcon className="w-8 h-8" /> : <MicrophoneIcon className="w-8 h-8" />}
            </button>
            
            <p className="text-sm text-gray-500 mt-2">
              {isRecording ? 'Recording... (max 15s)' : 'Tap to start recording'}
            </p>
          </div>
        )}

        {audioBlob && !isProcessing && (
          <div>
            <div className="mb-4">
              <div className="w-16 h-16 bg-green-100 rounded-full mx-auto flex items-center justify-center mb-2">
                ✅
              </div>
              <p className="text-green-600 font-medium">Recording ready to send!</p>
            </div>
            
            <div className="flex space-x-3 justify-center">
              <button
                onClick={sendHail}
                className="btn btn-primary px-6"
              >
                📢 Send Hail
              </button>
              <button
                onClick={() => setAudioBlob(null)}
                className="btn btn-secondary px-6"
              >
                🔄 Record Again
              </button>
            </div>
          </div>
        )}

        {isProcessing && (
          <div>
            <div className="w-16 h-16 bg-blue-100 rounded-full mx-auto flex items-center justify-center mb-2 animate-spin">
              🔄
            </div>
            <p className="text-blue-600">Processing and sending hail...</p>
          </div>
        )}
      </div>

      <div className="mt-6 p-4 bg-gray-50 rounded-lg">
        <h4 className="font-medium mb-2">💡 Tips for effective hails:</h4>
        <ul className="text-sm text-gray-600 space-y-1">
          <li>• Speak clearly and mention the service type</li>
          <li>• Include urgency level (emergency, urgent, etc.)</li>
          <li>• Mention your location if relevant</li>
          <li>• Keep it under 15 seconds</li>
        </ul>
      </div>
    </div>
  );
}

// Component for customers to view nearby hails
export function NearbyHails() {
  const [hails, setHails] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const { user } = useAuth();

  React.useEffect(() => {
    if (user?.role === 'customer') {
      fetchNearbyHails();
    }
  }, [user]);

  const fetchNearbyHails = async () => {
    try {
      const response = await fetch('/api/hail/active', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });
      
      if (response.ok) {
        const data = await response.json();
        setHails(data.nearby_hails || []);
      }
    } catch (error) {
      console.error('Error fetching hails:', error);
    } finally {
      setLoading(false);
    }
  };

  const respondToHail = async (hailId: string, message: string = "I need this service") => {
    try {
      const response = await fetch(`/api/hail/${hailId}/respond`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({ message })
      });

      if (response.ok) {
        toast.success('Response sent to provider!');
        fetchNearbyHails(); // Refresh list
      } else {
        throw new Error('Failed to respond');
      }
    } catch (error) {
      toast.error('Failed to respond to hail');
    }
  };

  if (user?.role !== 'customer' || loading) {
    return null;
  }

  if (hails.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow-lg p-6">
        <h3 className="text-lg font-semibold mb-4">📢 Nearby Service Hails</h3>
        <p className="text-gray-600 text-center">No active hails in your area</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-lg p-6">
      <h3 className="text-lg font-semibold mb-4">📢 Nearby Service Hails</h3>
      
      <div className="space-y-4">
        {hails.map((hail) => (
          <div key={hail.id} className="border rounded-lg p-4">
            <div className="flex justify-between items-start mb-2">
              <div>
                <h4 className="font-medium">{hail.provider_name}</h4>
                <p className="text-sm text-gray-600">⭐ {hail.provider_rating}/5</p>
              </div>
              <div className="text-right">
                <span className={`badge ${
                  hail.urgency === 'emergency' ? 'badge-danger' :
                  hail.urgency === 'high' ? 'badge-warning' : 'badge-secondary'
                }`}>
                  {hail.urgency}
                </span>
                <p className="text-sm text-gray-500 mt-1">
                  📍 {hail.distance}km away
                </p>
              </div>
            </div>
            
            <div className="mb-3">
              <p className="text-sm font-medium text-blue-600 mb-1">
                🎤 "{hail.transcription}"
              </p>
              <p className="text-sm text-gray-600">
                Service: {hail.service_type}
              </p>
            </div>
            
            <div className="flex space-x-2">
              <button
                onClick={() => respondToHail(hail.id)}
                className="btn btn-primary btn-sm flex-1"
              >
                🙋‍♀️ I Need This
              </button>
              <button
                onClick={() => respondToHail(hail.id, "Can you provide more details?")}
                className="btn btn-secondary btn-sm"
              >
                ❓ Ask Details
              </button>
            </div>
            
            <p className="text-xs text-gray-400 mt-2">
              Expires: {new Date(hail.expires_at).toLocaleTimeString()}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}