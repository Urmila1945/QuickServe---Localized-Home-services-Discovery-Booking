import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { chatAPI } from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import DashboardLayout from '../components/DashboardLayout';
import { Send, Search, Menu, X, Bot, Zap, RefreshCw } from 'lucide-react';
import { format } from 'date-fns';
import toast from 'react-hot-toast';

const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
const WS_BASE  = API_BASE.replace(/^http/, 'ws');

const Chat: React.FC = () => {
  const { user } = useAuth();
  const [selectedConv, setSelectedConv]   = useState<string | null>(null);
  const [message, setMessage]             = useState('');
  const [searchQuery, setSearchQuery]     = useState('');
  const [sidebarOpen, setSidebarOpen]     = useState(true);
  const [wsConnected, setWsConnected]     = useState(false);
  const [liveMessages, setLiveMessages]   = useState<Record<string, any[]>>({});
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const wsRef          = useRef<WebSocket | null>(null);
  const queryClient    = useQueryClient();

  // ── Fetch conversations ────────────────────────────────────────────────
  const { data: conversations = [], isLoading: convsLoading, refetch: refetchConvs } = useQuery({
    queryKey: ['conversations'],
    queryFn:  chatAPI.getConversations,
    refetchInterval: 10000, // poll every 10s as fallback
  });

  // ── Fetch messages for selected conversation ───────────────────────────
  const { data: fetchedMessages = [] } = useQuery({
    queryKey: ['messages', selectedConv],
    queryFn:  () => chatAPI.getMessages(selectedConv!),
    enabled:  !!selectedConv,
    onSuccess: (msgs: any[]) => {
      setLiveMessages(prev => ({ ...prev, [selectedConv!]: msgs }));
    },
  } as any);

  // Use ref for selectedConv to avoid reconnecting WS when it changes
  const selectedConvRef = useRef(selectedConv);
  useEffect(() => {
    selectedConvRef.current = selectedConv;
  }, [selectedConv]);

  // ── WebSocket connection ───────────────────────────────────────────────
  useEffect(() => {
    let isActive = true;

    const connectWS = () => {
      if (!user?._id || !isActive) return;
      const token = localStorage.getItem('token');
      const ws = new WebSocket(`${WS_BASE}/api/chat/ws/${user._id}${token ? `?token=${token}` : ''}`);

      ws.onopen = () => {
        if (!isActive) { ws.close(); return; }
        setWsConnected(true);
        // keep-alive ping every 25s
        const ping = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ type: 'ping' }));
          else clearInterval(ping);
        }, 25000);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'new_message') {
            const convId = data.conversation_id;
            const msg    = data.message;
            // Append to live messages
            setLiveMessages(prev => ({
              ...prev,
              [convId]: [...(prev[convId] || []), msg],
            }));
            // Refresh conversation list to update last_message
            queryClient.invalidateQueries({ queryKey: ['conversations'] });
            // Toast if not in that conversation
            if (convId !== selectedConvRef.current) {
              toast(`New message from ${msg.sender_name || 'someone'}`, { icon: '💬' });
            }
          }
        } catch { /* ignore parse errors */ }
      };

      ws.onclose = () => {
        if (!isActive) return;
        setWsConnected(false);
        wsRef.current = null;
        // Reconnect after 3s
        setTimeout(connectWS, 3000);
      };

      ws.onerror = () => ws.close();
      wsRef.current = ws;
    };

    connectWS();

    return () => { 
      isActive = false;
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [user?._id, queryClient]);

  // ── Send message mutation ──────────────────────────────────────────────
  const sendMutation = useMutation({
    mutationFn: ({ convId, text }: { convId: string; text: string }) =>
      chatAPI.sendMessage(convId, text),
    onMutate: ({ convId, text }) => {
      // Optimistic update
      const optimistic = {
        _id:       `opt-${Date.now()}`,
        sender_id: user?._id,
        message:   text,
        timestamp: new Date().toISOString(),
        optimistic: true,
      };
      setLiveMessages(prev => ({
        ...prev,
        [convId]: [...(prev[convId] || []), optimistic],
      }));
    },
    onSuccess: (saved: any, { convId }) => {
      // Replace optimistic with real message
      setLiveMessages(prev => ({
        ...prev,
        [convId]: (prev[convId] || []).map(m =>
          m.optimistic ? { ...saved, _id: saved._id } : m
        ),
      }));
      queryClient.invalidateQueries({ queryKey: ['conversations'] });
    },
    onError: (_err, { convId }) => {
      // Remove optimistic on error
      setLiveMessages(prev => ({
        ...prev,
        [convId]: (prev[convId] || []).filter(m => !m.optimistic),
      }));
      toast.error('Failed to send message');
    },
  });

  const handleSend = (e: React.FormEvent) => {
    e.preventDefault();
    if (!message.trim() || !selectedConv) return;
    sendMutation.mutate({ convId: selectedConv, text: message });
    setMessage('');
  };

  // ── Quick replies ──────────────────────────────────────────────────────
  const { data: quickRepliesData } = useQuery({
    queryKey: ['quick-replies'],
    queryFn:  chatAPI.getQuickReplies,
  });
  const quickReplies: string[] = quickRepliesData?.quick_replies || [];

  // ── Auto-scroll ────────────────────────────────────────────────────────
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [liveMessages, selectedConv]);

  // ── Select conversation ────────────────────────────────────────────────
  const selectConv = (convId: string) => {
    setSelectedConv(convId);
    if (window.innerWidth < 768) setSidebarOpen(false);
    // Load messages if not already loaded
    if (!liveMessages[convId]) {
      queryClient.invalidateQueries({ queryKey: ['messages', convId] });
    }
  };

  const filtered = (conversations as any[]).filter((c: any) =>
    !searchQuery || c.other_user?.name?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const currentMessages: any[] = liveMessages[selectedConv || ''] || fetchedMessages || [];
  const selectedConvData = (conversations as any[]).find((c: any) => c._id === selectedConv);
  const role = (user?.role as 'customer' | 'provider' | 'admin') || 'customer';

  return (
    <DashboardLayout role={role} title="Messages">
      <div className="flex h-[calc(100vh-65px)] overflow-hidden">

        {/* ── Sidebar ─────────────────────────────────────────────────── */}
        <div className={`${sidebarOpen ? 'w-72 lg:w-80' : 'w-0'} flex-shrink-0 bg-white border-r border-gray-100 flex flex-col transition-all duration-300 overflow-hidden`}>
          {/* Header */}
          <div className="p-4 border-b border-gray-100">
            <div className="flex items-center justify-between mb-3">
              <h2 className="font-black text-gray-900">Messages</h2>
              <div className="flex items-center gap-2">
                <div className={`w-2 h-2 rounded-full ${wsConnected ? 'bg-green-500 animate-pulse' : 'bg-gray-300'}`} title={wsConnected ? 'Live' : 'Reconnecting…'} />
                <button onClick={() => refetchConvs()} className="text-gray-400 hover:text-teal-600 transition-colors">
                  <RefreshCw size={14} />
                </button>
              </div>
            </div>
            <div className="relative">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
              <input
                type="text" value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                placeholder="Search conversations…"
                className="w-full pl-9 pr-4 py-2.5 bg-gray-50 text-sm rounded-xl border border-transparent focus:border-teal-300 focus:outline-none"
              />
            </div>
          </div>

          {/* Conversation list */}
          <div className="flex-1 overflow-y-auto divide-y divide-gray-50">
            {convsLoading && (
              <div className="p-6 text-center text-sm text-gray-400 font-medium">Loading…</div>
            )}
            {!convsLoading && filtered.length === 0 && (
              <div className="p-8 text-center">
                <p className="text-3xl mb-2">💬</p>
                <p className="text-sm font-bold text-gray-400">No conversations yet</p>
                <p className="text-xs text-gray-300 mt-1">Book a service to start chatting with a provider</p>
              </div>
            )}
            {filtered.map((conv: any) => {
              const unread = conv.unread_count?.[user?._id || ''] || 0;
              const isSelected = selectedConv === conv._id;
              return (
                <button
                  key={conv._id}
                  onClick={() => selectConv(conv._id)}
                  className={`w-full p-4 text-left hover:bg-gray-50 transition-all duration-150 ${isSelected ? 'bg-teal-50 border-l-4 border-teal-500' : ''}`}
                >
                  <div className="flex items-start gap-3">
                    <div className="w-11 h-11 rounded-full bg-gradient-to-br from-teal-400 to-teal-600 flex items-center justify-center text-white font-black text-sm flex-shrink-0">
                      {conv.other_user?.name?.charAt(0)?.toUpperCase() || '?'}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex justify-between items-baseline">
                        <p className="font-bold text-gray-900 text-sm truncate">{conv.other_user?.name || 'User'}</p>
                        {conv.last_message?.timestamp && (
                          <span className="text-[10px] text-gray-400 flex-shrink-0 ml-1">
                            {format(new Date(conv.last_message.timestamp), 'h:mm a')}
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-gray-500 truncate mt-0.5">
                        {conv.last_message?.text || 'No messages yet'}
                      </p>
                    </div>
                    {unread > 0 && (
                      <span className="w-5 h-5 bg-teal-600 text-white text-[10px] font-black rounded-full flex items-center justify-center flex-shrink-0">
                        {unread}
                      </span>
                    )}
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* ── Chat area ───────────────────────────────────────────────── */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {selectedConv ? (
            <>
              {/* Header */}
              <div className="bg-white border-b border-gray-100 px-5 py-3.5 flex items-center justify-between shadow-sm">
                <div className="flex items-center gap-3">
                  <button onClick={() => setSidebarOpen(!sidebarOpen)} className="text-gray-400 hover:text-gray-700 transition-colors">
                    {sidebarOpen ? <X size={18} /> : <Menu size={18} />}
                  </button>
                  <div className="w-10 h-10 rounded-full bg-gradient-to-br from-teal-400 to-teal-600 flex items-center justify-center text-white font-black text-sm">
                    {selectedConvData?.other_user?.name?.charAt(0)?.toUpperCase() || '?'}
                  </div>
                  <div>
                    <p className="font-black text-gray-900 text-sm">{selectedConvData?.other_user?.name || 'User'}</p>
                    <div className="flex items-center gap-1.5">
                      <div className={`w-1.5 h-1.5 rounded-full ${wsConnected ? 'bg-green-500' : 'bg-gray-300'}`} />
                      <p className="text-[10px] font-bold text-gray-400">{wsConnected ? 'Live' : 'Connecting…'}</p>
                    </div>
                  </div>
                </div>
              </div>

              {/* Messages */}
              <div className="flex-1 overflow-y-auto p-5 space-y-3 bg-gray-50">
                {currentMessages.length === 0 && (
                  <div className="flex flex-col items-center justify-center h-full gap-2 text-gray-400">
                    <p className="text-3xl">👋</p>
                    <p className="font-bold text-sm">Say hello to start the conversation</p>
                  </div>
                )}
                {currentMessages.map((msg: any) => {
                  const isOwn = msg.sender_id === user?._id;
                  return (
                    <div key={msg._id} className={`flex ${isOwn ? 'justify-end' : 'justify-start'}`}>
                      <div className="max-w-xs lg:max-w-md">
                        <div className={`rounded-2xl px-4 py-2.5 ${
                          isOwn
                            ? `bg-teal-600 text-white rounded-br-sm ${msg.optimistic ? 'opacity-70' : ''}`
                            : 'bg-white text-gray-900 rounded-bl-sm shadow-sm'
                        }`}>
                          <p className="text-sm leading-relaxed">{msg.message}</p>
                        </div>
                        <p className={`text-[10px] text-gray-400 mt-1 font-medium ${isOwn ? 'text-right' : 'text-left'}`}>
                          {format(new Date(msg.timestamp), 'h:mm a')}
                          {msg.optimistic && <span className="ml-1">·  sending…</span>}
                        </p>
                      </div>
                    </div>
                  );
                })}
                <div ref={messagesEndRef} />
              </div>

              {/* Quick replies */}
              {quickReplies.length > 0 && (
                <div className="bg-white border-t border-gray-50 px-4 py-2 flex gap-2 overflow-x-auto scrollbar-hidden">
                  {quickReplies.slice(0, 4).map((qr: string) => (
                    <button
                      key={qr}
                      onClick={() => { setMessage(qr); }}
                      className="flex-shrink-0 text-xs bg-gray-50 hover:bg-teal-50 hover:text-teal-700 border border-gray-200 hover:border-teal-300 text-gray-600 px-3 py-1.5 rounded-full font-medium transition-all"
                    >
                      {qr}
                    </button>
                  ))}
                </div>
              )}

              {/* Input */}
              <div className="bg-white border-t border-gray-100 p-4">
                <form onSubmit={handleSend} className="flex items-center gap-3">
                  <input
                    type="text" value={message}
                    onChange={e => setMessage(e.target.value)}
                    placeholder="Type a message…"
                    className="flex-1 bg-gray-50 border border-transparent focus:border-teal-300 rounded-full px-5 py-3 text-sm focus:outline-none transition-colors"
                  />
                  <button
                    type="submit"
                    disabled={!message.trim() || sendMutation.isPending}
                    className="w-11 h-11 bg-teal-600 hover:bg-teal-700 text-white rounded-full flex items-center justify-center disabled:opacity-40 transition-all hover:scale-110 active:scale-95 shadow-md"
                  >
                    <Send size={17} />
                  </button>
                </form>
              </div>
            </>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center bg-gray-50 gap-4">
              <div className="w-20 h-20 bg-teal-100 rounded-full flex items-center justify-center text-4xl">💬</div>
              <p className="font-black text-gray-700 text-xl">Your Messages</p>
              <p className="text-gray-400 text-sm text-center max-w-xs">
                {(conversations as any[]).length === 0
                  ? 'No conversations yet. Book a service to start chatting with a provider.'
                  : 'Select a conversation from the left to start messaging'}
              </p>
              <div className="flex items-center gap-2 text-xs text-gray-400 bg-white px-4 py-2 rounded-full border border-gray-100">
                <div className={`w-2 h-2 rounded-full ${wsConnected ? 'bg-green-500 animate-pulse' : 'bg-gray-300'}`} />
                {wsConnected ? 'Real-time messaging active' : 'Connecting to live chat…'}
              </div>
            </div>
          )}
        </div>
      </div>
    </DashboardLayout>
  );
};

export default Chat;
