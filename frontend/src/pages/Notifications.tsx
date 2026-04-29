import React from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useTranslation } from 'react-i18next';
import DashboardLayout, { SidebarRole } from '../components/DashboardLayout';
import { Bell, CheckCircle, Gift, Wrench, ShieldAlert, Star, X, Calendar, MessageSquare } from 'lucide-react';
import toast from 'react-hot-toast';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { notificationsAPI } from '../services/api';
import { formatDistanceToNow } from 'date-fns';

export default function Notifications() {
  const { user } = useAuth();
  const { t } = useTranslation();
  const role = (user?.role as SidebarRole) || 'customer';
  const queryClient = useQueryClient();

  const { data: notifications = [], isLoading } = useQuery({
    queryKey: ['notifications'],
    queryFn: notificationsAPI.getNotifications,
  });

  const markAsReadMut = useMutation({
    mutationFn: notificationsAPI.markAsRead,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['notifications'] })
  });

  const markAllAsReadMut = useMutation({
    mutationFn: notificationsAPI.markAllAsRead,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
      toast.success('All notifications marked as read!');
    }
  });

  const deleteMut = useMutation({
    mutationFn: notificationsAPI.deleteNotification,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
    }
  });

  const unreadCount = notifications.filter((n: any) => !n.read).length;

  const getIconAndColor = (type: string) => {
    switch(type?.toLowerCase()) {
      case 'booking': return { icon: Calendar, color: 'text-blue-600', bg: 'bg-blue-100' };
      case 'reward': return { icon: Gift, color: 'text-yellow-600', bg: 'bg-yellow-100' };
      case 'system': return { icon: ShieldAlert, color: 'text-red-600', bg: 'bg-red-100' };
      case 'review': return { icon: Star, color: 'text-orange-600', bg: 'bg-orange-100' };
      case 'chat': return { icon: MessageSquare, color: 'text-purple-600', bg: 'bg-purple-100' };
      default: return { icon: Bell, color: 'text-teal-600', bg: 'bg-teal-100' };
    }
  };

  return (
    <DashboardLayout role={role} title="Notifications">
      <div className="max-w-4xl mx-auto space-y-6">
        
        {/* Header */}
        <div className="bg-white rounded-3xl p-6 md:p-8 shadow-sm border border-gray-100 flex flex-col md:flex-row items-start md:items-center justify-between gap-6 relative overflow-hidden">
          <div className="absolute top-0 right-0 w-64 h-64 bg-teal-50 rounded-full blur-3xl -translate-y-1/2 translate-x-1/3 opacity-60"></div>
          
          <div className="flex items-center gap-5 relative z-10">
            <div className="w-16 h-16 bg-gradient-to-br from-teal-400 to-teal-600 rounded-2xl flex items-center justify-center text-white shadow-lg shadow-teal-500/30">
              <Bell size={28} />
            </div>
            <div>
              <h1 className="text-2xl font-black text-gray-900 mb-1">{t('Notifications')}</h1>
              <p className="text-gray-500 font-medium">
                {isLoading ? 'Loading notifications...' : unreadCount > 0 
                  ? `You have ${unreadCount} unread message${unreadCount === 1 ? '' : 's'}` 
                  : 'You are all caught up!'}
              </p>
            </div>
          </div>
          
          {unreadCount > 0 && (
            <button 
              onClick={() => markAllAsReadMut.mutate()}
              disabled={markAllAsReadMut.isPending}
              className="relative z-10 flex items-center gap-2 px-5 py-2.5 bg-teal-50 text-teal-700 rounded-xl font-bold hover:bg-teal-100 transition-colors border border-teal-100 disabled:opacity-50"
            >
              <CheckCircle size={18} />
              Mark all as read
            </button>
          )}
        </div>

        {/* List */}
        <div className="bg-white rounded-3xl shadow-sm border border-gray-100 overflow-hidden">
          {isLoading ? (
            <div className="p-16 flex flex-col items-center justify-center text-center">
              <div className="w-10 h-10 border-4 border-teal-600/30 border-t-teal-600 rounded-full animate-spin mb-4" />
              <p className="text-gray-500">Fetching your notifications...</p>
            </div>
          ) : notifications.length === 0 ? (
            <div className="p-16 flex flex-col items-center justify-center text-center">
              <div className="w-24 h-24 bg-gray-50 rounded-full flex items-center justify-center mb-6">
                <Bell size={40} className="text-gray-300" />
              </div>
              <h3 className="text-xl font-black text-gray-900 mb-2">No notifications yet</h3>
              <p className="text-gray-500 max-w-sm">We'll let you know when there's an update on your bookings or account.</p>
            </div>
          ) : (
            <div className="divide-y divide-gray-50">
              {notifications.map((notif: any) => {
                const { icon: Icon, color, bg } = getIconAndColor(notif.type);
                const timeAgo = notif.created_at ? formatDistanceToNow(new Date(notif.created_at), { addSuffix: true }) : notif.time || 'recently';
                return (
                  <div 
                    key={notif._id || notif.id} 
                    className={`p-5 md:p-6 flex gap-4 md:gap-5 transition-colors ${notif.read ? 'bg-white hover:bg-gray-50' : 'bg-teal-50/30 hover:bg-teal-50/50'}`}
                  >
                    <div className={`w-12 h-12 rounded-full flex items-center justify-center flex-shrink-0 mt-1 ${bg} ${color}`}>
                      <Icon size={22} />
                    </div>
                    
                    <div className="flex-1 min-w-0">
                      <div className="flex flex-col md:flex-row md:items-center justify-between gap-1 md:gap-4 mb-1">
                        <h4 className={`text-base font-bold truncate ${notif.read ? 'text-gray-900' : 'text-gray-900'}`}>
                          {notif.title}
                        </h4>
                        <span className="text-xs font-bold text-gray-400 whitespace-nowrap capitalize">
                          {timeAgo}
                        </span>
                      </div>
                      <p className={`text-sm leading-relaxed ${notif.read ? 'text-gray-500' : 'text-gray-700 font-medium'}`}>
                        {notif.message}
                      </p>
                      
                      {!notif.read && (
                        <button 
                          onClick={() => markAsReadMut.mutate(notif._id || notif.id)}
                          disabled={markAsReadMut.isPending}
                          className="mt-3 text-xs font-black text-teal-600 hover:text-teal-800 uppercase tracking-wider disabled:opacity-50"
                        >
                          Mark as read
                        </button>
                      )}
                    </div>

                    <button 
                      onClick={() => deleteMut.mutate(notif._id || notif.id)}
                      disabled={deleteMut.isPending}
                      className="w-8 h-8 rounded-full flex items-center justify-center text-gray-300 hover:text-red-500 hover:bg-red-50 transition-colors flex-shrink-0 disabled:opacity-50"
                      title="Delete notification"
                    >
                      <X size={16} />
                    </button>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </DashboardLayout>
  );
}
