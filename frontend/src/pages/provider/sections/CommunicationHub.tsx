import React, { useState } from 'react';
import { MessageSquare, Send, Mic, Globe, Mail, Phone, Inbox } from 'lucide-react';
import toast from 'react-hot-toast';

const conversations = [
  { id:'cv1', name:'Anjali Singh',    channel:'sms',   lastMsg:'Thanks! What time will you arrive?',          time:'10:32 AM', unread:2, avatar:'AS' },
  { id:'cv2', name:'Ramesh Gupta',    channel:'email', lastMsg:'Please bring the 16A switch as discussed.',   time:'9:15 AM',  unread:0, avatar:'RG' },
  { id:'cv3', name:'Priya Mehta',     channel:'app',   lastMsg:'Job done! Amazing work as always.',            time:'Yesterday',unread:1, avatar:'PM' },
  { id:'cv4', name:'Karan Dev',       channel:'app',   lastMsg:'Can you come tomorrow instead?',              time:'Dec 12',   unread:0, avatar:'KD' },
  { id:'cv5', name:'Meera Nair',      channel:'sms',   lastMsg:'Is GST invoice available?',                   time:'Dec 11',   unread:3, avatar:'MN' },
];

const quickReplies = [
  'I\'m on my way! ETA 20 minutes.',
  'Job completed. Please rate us 5 stars!',
  'Quote: ₹[AMOUNT] for [SERVICE]. GST included.',
  'Parts unavailable today. Can we reschedule?',
  'Payment link: quickserve.in/pay/[BOOKING_ID]',
  'Running 15 min late due to traffic. Apologies!',
];

const channelIcon: Record<string, React.ReactNode> = {
  sms:   <Phone size={11} />,
  email: <Mail size={11} />,
  app:   <MessageSquare size={11} />,
};
const channelStyle: Record<string, string> = {
  sms:   'bg-green-100 text-green-700',
  email: 'bg-blue-100 text-blue-700',
  app:   'bg-purple-100 text-purple-700',
};

const CommunicationHub: React.FC = () => {
  const [selected, setSelected] = useState(conversations[0].id);
  const [message, setMessage] = useState('');
  const [msgs, setMsgs] = useState<{text:string;me:boolean;time:string}[]>([
    { text:'Hi! I\'m on my way. Will arrive at 10 AM.', me:true,  time:'9:45 AM' },
    { text:'Thanks! What time will you arrive?',         me:false, time:'10:32 AM'},
  ]);
  const [isRecording, setIsRecording] = useState(false);
  const [langMode, setLangMode] = useState(false);

  const sendMsg = () => {
    if (!message.trim()) return;
    setMsgs(prev => [...prev, { text:message, me:true, time:new Date().toLocaleTimeString('en-IN',{hour:'2-digit',minute:'2-digit'}) }]);
    setMessage('');
  };

  const useQuickReply = (reply: string) => { setMessage(reply); };

  return (
    <div className="space-y-4">
      {/* Stats */}
      <div className="grid grid-cols-3 gap-4">
        {[
          { label:'Total Threads',   value:conversations.length, color:'text-blue-600',  bg:'bg-blue-50'  },
          { label:'Unread Messages', value:conversations.reduce((s,c)=>s+c.unread,0), color:'text-red-600', bg:'bg-red-50' },
          { label:'Avg Response',    value:'12 min', color:'text-green-600', bg:'bg-green-50' },
        ].map(s => (
          <div key={s.label} className={`${s.bg} rounded-2xl p-4 text-center`}>
            <p className={`text-2xl font-black ${s.color}`}>{s.value}</p>
            <p className="text-xs font-bold text-gray-500 mt-0.5">{s.label}</p>
          </div>
        ))}
      </div>

      <div className="grid lg:grid-cols-3 gap-4 h-[520px]">
        {/* Conversation List */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden flex flex-col">
          <div className="px-4 py-3 border-b border-gray-100">
            <div className="flex items-center gap-2 bg-gray-50 rounded-xl px-3 py-2">
              <Inbox size={13} className="text-gray-400" />
              <span className="text-xs font-bold text-gray-400">Unified Inbox</span>
            </div>
          </div>
          <div className="flex-1 overflow-y-auto divide-y divide-gray-50">
            {conversations.map(c => (
              <div key={c.id} onClick={() => setSelected(c.id)}
                className={`px-4 py-3 cursor-pointer transition-all hover:bg-gray-50 ${selected===c.id?'bg-teal-50 border-l-4 border-teal-500':''}`}>
                <div className="flex items-start gap-2.5">
                  <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-teal-400 to-teal-600 flex items-center justify-center text-white font-black text-xs shrink-0">
                    {c.avatar}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between">
                      <p className="font-bold text-gray-900 text-xs truncate">{c.name}</p>
                      <span className="text-[9px] text-gray-400 shrink-0 ml-1">{c.time}</span>
                    </div>
                    <p className="text-[10px] text-gray-400 truncate mt-0.5">{c.lastMsg}</p>
                    <div className="flex items-center justify-between mt-1">
                      <span className={`flex items-center gap-1 text-[9px] font-black px-1.5 py-0.5 rounded-full ${channelStyle[c.channel]}`}>
                        {channelIcon[c.channel]} {c.channel}
                      </span>
                      {c.unread > 0 && (
                        <span className="w-4 h-4 bg-red-500 text-white rounded-full text-[9px] font-black flex items-center justify-center">{c.unread}</span>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Chat Window */}
        <div className="lg:col-span-2 bg-white rounded-2xl shadow-sm border border-gray-100 flex flex-col overflow-hidden">
          {/* Header */}
          <div className="px-5 py-3 border-b border-gray-100 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 bg-teal-100 rounded-xl flex items-center justify-center font-black text-teal-700 text-xs">
                {conversations.find(c=>c.id===selected)?.avatar}
              </div>
              <div>
                <p className="font-black text-gray-900 text-sm">{conversations.find(c=>c.id===selected)?.name}</p>
                <p className="text-[10px] text-green-500 font-bold">Online</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <button onClick={() => { setLangMode(p=>!p); toast(langMode?'Translation off':'Auto-translate enabled!',{icon:'🌐'}); }}
                className={`flex items-center gap-1.5 text-xs font-black px-3 py-1.5 rounded-xl transition-all ${langMode?'bg-teal-600 text-white':'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}>
                <Globe size={12} /> Translate
              </button>
            </div>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-5 space-y-3">
            {msgs.map((m, i) => (
              <div key={i} className={`flex ${m.me?'justify-end':'justify-start'}`}>
                <div className={`max-w-[80%] px-4 py-2.5 rounded-2xl text-sm font-medium ${m.me?'bg-teal-600 text-white rounded-br-sm':'bg-gray-100 text-gray-800 rounded-bl-sm'}`}>
                  <p>{m.text}</p>
                  <p className={`text-[10px] mt-1 ${m.me?'text-teal-200':'text-gray-400'}`}>{m.time}</p>
                </div>
              </div>
            ))}
          </div>

          {/* Quick Replies */}
          <div className="px-4 py-2 border-t border-gray-50 overflow-x-auto flex gap-2 scrollbar-hidden">
            {quickReplies.slice(0,4).map((r,i) => (
              <button key={i} onClick={() => useQuickReply(r)}
                className="shrink-0 text-[10px] font-bold bg-teal-50 text-teal-700 px-3 py-1.5 rounded-full hover:bg-teal-100 transition-colors border border-teal-100 whitespace-nowrap">
                {r.length>30?r.slice(0,30)+'…':r}
              </button>
            ))}
          </div>

          {/* Input */}
          <div className="p-4 border-t border-gray-100 flex items-center gap-2">
            <button onClick={() => { setIsRecording(p=>!p); toast(isRecording?'Voice note transcribed!':'Recording started…',{icon:isRecording?'✅':'🎤'}); }}
              className={`w-10 h-10 rounded-xl flex items-center justify-center transition-all ${isRecording?'bg-red-500 text-white animate-pulse':'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}>
              <Mic size={16} />
            </button>
            <input value={message} onChange={e=>setMessage(e.target.value)}
              onKeyDown={e=>e.key==='Enter'&&sendMsg()}
              placeholder="Type a message…"
              className="flex-1 px-4 py-2.5 rounded-xl border-2 border-gray-100 focus:border-teal-400 focus:outline-none text-sm font-medium" />
            <button onClick={sendMsg} className="w-10 h-10 bg-teal-600 hover:bg-teal-700 text-white rounded-xl flex items-center justify-center transition-all active:scale-95">
              <Send size={15} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CommunicationHub;
