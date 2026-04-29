import React, { useState, useEffect, useRef } from 'react';
import { Bot, X, Send, Loader2, MessageSquare } from 'lucide-react';
import { aiAPI } from '../services/api';
import { useAuth } from '../contexts/AuthContext';

interface Message {
  id: string;
  text: string;
  isBot: boolean;
  timestamp: string;
}

const ChatbotWidget: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'welcome',
      text: "Hi there! I'm QuickServe AI. I can help you with bookings, tracking, finding services, or questions about the platform. How can I assist you today?",
      isBot: true,
      timestamp: new Date().toISOString()
    }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { user } = useAuth();

  useEffect(() => {
    if (isOpen) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, isOpen, isLoading]);

  const handleSend = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      text: input.trim(),
      isBot: false,
      timestamp: new Date().toISOString()
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      // Assuming aiAPI.chatbot returns { response: string, timestamp: string }
      const res = await aiAPI.chatbot(userMessage.text);
      const botMessage: Message = {
        id: (Date.now() + 1).toString(),
        text: res.response || "Sorry, I couldn't understand that.",
        isBot: true,
        timestamp: res.timestamp || new Date().toISOString()
      };
      setMessages(prev => [...prev, botMessage]);
    } catch (error) {
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        text: "I'm having trouble connecting right now. Please try again later.",
        isBot: true,
        timestamp: new Date().toISOString()
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const toggleWidget = () => setIsOpen(!isOpen);

  if (!isOpen) {
    return (
      <button
        onClick={toggleWidget}
        className="fixed bottom-6 right-6 bg-teal-600 hover:bg-teal-700 text-white w-14 h-14 rounded-full flex items-center justify-center shadow-2xl hover:scale-110 active:scale-95 transition-all z-50 animate-bounce"
        aria-label="Open AI Assistant"
      >
        <MessageSquare size={24} />
      </button>
    );
  }

  return (
    <div className="fixed bottom-6 right-6 w-[350px] sm:w-[400px] rounded-[2rem] shadow-2xl overflow-hidden z-50 flex flex-col border border-white/20 backdrop-blur-xl bg-white/95" style={{ height: '550px', maxHeight: '85vh', boxShadow: '0 25px 50px -12px rgba(13, 122, 127, 0.25)' }}>
      {/* Header */}
      <div className="bg-gradient-to-br from-teal-500 via-teal-600 to-teal-700 p-5 flex items-center justify-between shadow-lg relative overflow-hidden">
        <div className="absolute top-0 left-0 w-full h-full bg-white/10 blur-xl rounded-full translate-x-1/2 -translate-y-1/2 pointer-events-none" />
        <div className="flex items-center gap-4 text-white relative z-10">
          <div className="bg-white/20 p-2.5 rounded-2xl backdrop-blur-md shadow-inner border border-white/30">
            <Bot size={24} className="text-white drop-shadow-md" />
          </div>
          <div>
            <h3 className="font-extrabold text-base tracking-wide flex items-center gap-2">
              QuickServe AI
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-300 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-green-400"></span>
              </span>
            </h3>
            <p className="text-xs text-teal-100 font-medium">Smart Assistant</p>
          </div>
        </div>
        <button 
          onClick={toggleWidget}
          className="text-white hover:bg-white/20 p-2 rounded-xl transition-all hover:scale-110 active:scale-95 relative z-10"
        >
          <X size={20} />
        </button>
      </div>

      {/* Chat Area */}
      <div className="flex-1 overflow-y-auto p-5 bg-gradient-to-b from-gray-50/50 to-white/50 flex flex-col gap-4 custom-scrollbar">
        {messages.map((message) => (
          <div 
            key={message.id} 
            className={`flex ${message.isBot ? 'justify-start' : 'justify-end'} animate-in fade-in slide-in-from-bottom-2`}
          >
            <div 
              className={`max-w-[85%] px-5 py-3.5 text-[15px] leading-relaxed relative ${
                message.isBot 
                  ? 'bg-white text-gray-800 rounded-3xl rounded-tl-sm shadow-[0_4px_20px_-4px_rgba(0,0,0,0.05)] border border-gray-100/50' 
                  : 'bg-gradient-to-br from-teal-500 to-teal-600 text-white rounded-3xl rounded-tr-sm shadow-[0_4px_20px_-4px_rgba(13,122,127,0.3)]'
              }`}
            >
              <p>{message.text}</p>
            </div>
          </div>
        ))}
        {isLoading && (
          <div className="flex justify-start animate-in fade-in slide-in-from-bottom-2">
            <div className="bg-white border border-gray-100/50 rounded-3xl rounded-tl-sm px-5 py-4 shadow-[0_4px_20px_-4px_rgba(0,0,0,0.05)] flex items-center gap-3">
              <div className="flex space-x-1">
                <div className="w-2 h-2 bg-teal-400 rounded-full animate-bounce [animation-delay:-0.3s]"></div>
                <div className="w-2 h-2 bg-teal-400 rounded-full animate-bounce [animation-delay:-0.15s]"></div>
                <div className="w-2 h-2 bg-teal-400 rounded-full animate-bounce"></div>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="p-4 bg-white/80 backdrop-blur-md border-t border-gray-100/50 relative z-10">
        <form 
          onSubmit={handleSend}
          className="flex items-center gap-3 relative"
        >
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask me anything..."
            className="flex-1 bg-gray-50/80 border border-gray-200/60 focus:border-teal-400 focus:bg-white focus:outline-none focus:ring-4 focus:ring-teal-100/50 rounded-full pl-5 pr-12 py-3.5 text-sm transition-all shadow-inner font-medium placeholder:text-gray-400"
          />
          <button
            type="submit"
            disabled={!input.trim() || isLoading}
            className="absolute right-1.5 top-1/2 -translate-y-1/2 bg-teal-600 hover:bg-teal-700 disabled:bg-gray-300 disabled:hover:bg-gray-300 text-white p-2.5 rounded-full transition-all shrink-0 hover:shadow-lg disabled:shadow-none hover:scale-105 active:scale-95"
          >
            <Send size={16} className="ml-0.5" />
          </button>
        </form>
        <div className="text-center mt-3 flex items-center justify-center gap-1.5 opacity-60">
          <Bot size={10} className="text-teal-600" />
          <span className="text-[10px] text-gray-500 font-bold uppercase tracking-wider">
            Powered by QuickServe Engine
          </span>
        </div>
      </div>
    </div>
  );
};

export default ChatbotWidget;
