import React, { useState } from 'react';
import { Mic, MicOff, Zap } from 'lucide-react';
import toast from 'react-hot-toast';
import { servicesAPI } from '../../services/api';

interface VoiceHailProps {
  onHailComplete?: (serviceType: string, urgency: string) => void;
}

const VoiceHail: React.FC<VoiceHailProps> = ({ onHailComplete }) => {
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [processing, setProcessing] = useState(false);

  const startListening = () => {
    setIsListening(true);
    setTranscript('');
    
    // Mock voice recognition
    setTimeout(() => {
      const mockTranscripts = [
        "I need a plumber urgently, there's a leak!",
        "Emergency electrician needed right now",
        "Can someone clean my house today?",
        "Need a handyman for furniture assembly"
      ];
      const mockTranscript = mockTranscripts[Math.floor(Math.random() * mockTranscripts.length)];
      setTranscript(mockTranscript);
      setIsListening(false);
      processVoiceCommand(mockTranscript);
    }, 2000);
  };

  const stopListening = () => {
    setIsListening(false);
  };

  const processVoiceCommand = async (text: string) => {
    setProcessing(true);
    
    try {
      const data = await servicesAPI.voiceHail(text);
      const { service, urgency } = data;
      
      setProcessing(false);
      toast.success(`🎯 Found ${urgency === 'high' ? 'emergency' : ''} ${service} providers nearby!`);
      
      if (onHailComplete) {
        onHailComplete(service, urgency);
      }
    } catch {
      setProcessing(false);
      toast.error('Could not process voice command. Please try again.');
    }
  };



  return (
    <div className="bg-white rounded-2xl shadow-xl p-8 max-w-2xl mx-auto">
      <div className="text-center mb-6">
        <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-br from-red-500 to-orange-500 rounded-full mb-4">
          <Zap className="w-8 h-8 text-white" />
        </div>
        <h3 className="text-2xl font-bold text-gray-900 mb-2">🎤 Voice-Powered Emergency Hail</h3>
        <p className="text-gray-600">Just speak your emergency, and we'll find help instantly</p>
      </div>

      <div className="relative">
        <div className={`flex items-center justify-center p-12 rounded-2xl transition-all duration-300 ${
          isListening ? 'bg-red-50 border-4 border-red-500 animate-pulse' : 'bg-gray-50 border-4 border-gray-200'
        }`}>
          <button
            onClick={isListening ? stopListening : startListening}
            disabled={processing}
            className={`relative flex items-center justify-center w-32 h-32 rounded-full transition-all duration-300 ${
              isListening 
                ? 'bg-red-500 hover:bg-red-600 scale-110' 
                : 'bg-gradient-to-br from-primary-500 to-primary-700 hover:scale-105'
            } disabled:opacity-50 shadow-2xl`}
          >
            {isListening ? (
              <MicOff className="w-16 h-16 text-white animate-pulse" />
            ) : (
              <Mic className="w-16 h-16 text-white" />
            )}
            
            {isListening && (
              <span className="absolute -top-1 -right-1 flex h-6 w-6">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-6 w-6 bg-red-500"></span>
              </span>
            )}
          </button>
        </div>

        {isListening && (
          <div className="absolute -bottom-4 left-1/2 transform -translate-x-1/2 bg-white px-4 py-2 rounded-full shadow-lg border-2 border-red-500">
            <p className="text-sm font-medium text-red-600 flex items-center gap-2">
              <span className="w-2 h-2 bg-red-500 rounded-full animate-pulse"></span>
              Listening...
            </p>
          </div>
        )}
      </div>

      {transcript && (
        <div className="mt-6 p-4 bg-blue-50 rounded-xl border-2 border-blue-200">
          <p className="text-sm text-gray-600 mb-1 font-medium">You said:</p>
          <p className="text-lg text-gray-900">"{transcript}"</p>
        </div>
      )}

      {processing && (
        <div className="mt-6 flex items-center justify-center gap-3">
          <div className="loading-spinner w-6 h-6 border-4 border-primary-500 border-t-transparent"></div>
          <p className="text-gray-600 font-medium">🤖 AI analyzing your request...</p>
        </div>
      )}

      <div className="mt-8 grid grid-cols-2 gap-4">
        <div className="text-center p-4 bg-gradient-to-br from-green-50 to-green-100 rounded-xl">
          <p className="text-3xl font-bold text-green-600">&lt; 60s</p>
          <p className="text-sm text-gray-600">Avg Response Time</p>
        </div>
        <div className="text-center p-4 bg-gradient-to-br from-blue-50 to-blue-100 rounded-xl">
          <p className="text-3xl font-bold text-blue-600">98%</p>
          <p className="text-sm text-gray-600">Success Rate</p>
        </div>
      </div>

      <div className="mt-6 text-center">
        <p className="text-xs text-gray-500">
          💡 Tip: Say "Emergency" for priority matching with nearby providers
        </p>
      </div>
    </div>
  );
};

export default VoiceHail;
