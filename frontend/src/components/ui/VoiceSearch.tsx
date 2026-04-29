import React, { useState, useEffect } from 'react';
import { Mic, Square } from 'lucide-react';

interface VoiceSearchProps {
  onVoiceResult: (transcript: string) => void;
  placeholder?: string;
}

const VoiceSearch: React.FC<VoiceSearchProps> = ({ onVoiceResult, placeholder = "Try saying: 'Find plumber near me'" }) => {
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [recognition, setRecognition] = useState<SpeechRecognition | null>(null);

  useEffect(() => {
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      const recognitionInstance = new SpeechRecognition();
      
      recognitionInstance.continuous = false;
      recognitionInstance.interimResults = true;
      recognitionInstance.lang = 'en-US';

      recognitionInstance.onstart = () => {
        setIsListening(true);
      };

      recognitionInstance.onresult = (event) => {
        let finalTranscript = '';
        let interimTranscript = '';

        for (let i = event.resultIndex; i < event.results.length; i++) {
          const transcript = event.results[i][0].transcript;
          if (event.results[i].isFinal) {
            finalTranscript += transcript;
          } else {
            interimTranscript += transcript;
          }
        }

        setTranscript(finalTranscript || interimTranscript);
        
        if (finalTranscript) {
          onVoiceResult(finalTranscript);
        }
      };

      recognitionInstance.onend = () => {
        setIsListening(false);
      };

      recognitionInstance.onerror = (event) => {
        console.error('Speech recognition error:', event.error);
        setIsListening(false);
      };

      setRecognition(recognitionInstance);
    }
  }, [onVoiceResult]);

  const startListening = () => {
    if (recognition) {
      setTranscript('');
      recognition.start();
    }
  };

  const stopListening = () => {
    if (recognition) {
      recognition.stop();
    }
  };

  const isSupported = 'webkitSpeechRecognition' in window || 'SpeechRecognition' in window;

  if (!isSupported) {
    return null;
  }

  return (
    <div className="flex items-center space-x-2">
      <button
        onClick={isListening ? stopListening : startListening}
        className={`p-3 rounded-full transition-all duration-300 ${
          isListening
            ? 'bg-red-500 hover:bg-red-600 text-white animate-pulse'
            : 'bg-primary-500 hover:bg-primary-600 text-white hover:scale-105'
        }`}
        title={isListening ? 'Stop listening' : 'Start voice search'}
      >
        {isListening ? (
          <Square className="h-6 w-6" />
        ) : (
          <Mic className="h-6 w-6" />
        )}
      </button>
      
      {isListening && (
        <div className="flex items-center space-x-2 text-sm text-gray-600">
          <div className="flex space-x-1">
            <div className="w-2 h-2 bg-red-500 rounded-full animate-bounce"></div>
            <div className="w-2 h-2 bg-red-500 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
            <div className="w-2 h-2 bg-red-500 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
          </div>
          <span>Listening...</span>
        </div>
      )}
      
      {transcript && !isListening && (
        <div className="text-sm text-green-600 font-medium">
          Heard: "{transcript}"
        </div>
      )}
      
      {!isListening && !transcript && (
        <div className="text-xs text-gray-400">
          {placeholder}
        </div>
      )}
    </div>
  );
};

export default VoiceSearch;