import React, { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useTranslation } from 'react-i18next';
import DashboardLayout, { SidebarRole } from '../components/DashboardLayout';
import { User, Settings, Lock, Shield, CreditCard, Bell, Key, Save, Edit3 } from 'lucide-react';
import toast from 'react-hot-toast';
import api from '../services/api';

export default function Profile() {
  const { user } = useAuth();
  const { t } = useTranslation();
  const role = (user?.role as SidebarRole) || 'customer';

  const [activeTab, setActiveTab] = useState<'profile' | 'settings' | 'security'>('profile');

  // Password state
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [isChangingPassword, setIsChangingPassword] = useState(false);

  const handlePasswordChange = async (e: React.FormEvent) => {
    e.preventDefault();
    if (newPassword !== confirmPassword) {
      toast.error('New passwords do not match');
      return;
    }
    if (newPassword.length < 6) {
      toast.error('Password must be at least 6 characters');
      return;
    }

    try {
      setIsChangingPassword(true);
      await api.put('/api/auth/change-password', {
        current_password: currentPassword,
        new_password: newPassword
      });
      toast.success('Password updated successfully');
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed to update password');
    } finally {
      setIsChangingPassword(false);
    }
  };

  return (
    <DashboardLayout role={role} title="My Profile">
      <div className="max-w-5xl mx-auto">
        
        {/* Header */}
        <div className="bg-gradient-to-r from-teal-900 to-teal-800 rounded-3xl p-8 shadow-2xl relative overflow-hidden mb-8 text-white">
          <div className="absolute top-0 right-0 w-64 h-64 bg-teal-400 rounded-full blur-3xl opacity-20 -translate-y-1/2 translate-x-1/3"></div>
          
          <div className="relative z-10 flex flex-col md:flex-row items-center gap-6">
            <div className="w-24 h-24 rounded-full bg-white/10 border-4 border-white/20 flex items-center justify-center flex-shrink-0 backdrop-blur-sm overflow-hidden shadow-lg">
              {user?.profile_image ? (
                <img src={user.profile_image} alt={user.full_name} className="w-full h-full object-cover" />
              ) : (
                <User size={40} className="text-teal-100" />
              )}
            </div>
            <div className="text-center md:text-left">
              <h1 className="text-3xl font-black mb-1">{user?.full_name || 'My Profile'}</h1>
              <p className="text-teal-100/80 font-medium">{user?.email}</p>
              <div className="mt-4 flex flex-wrap gap-2 justify-center md:justify-start">
                <span className="px-3 py-1 bg-white/10 rounded-full text-xs font-bold uppercase tracking-wider backdrop-blur-sm border border-white/10">
                  {role} Account
                </span>
                {user?.is_verified && (
                  <span className="px-3 py-1 bg-green-500/20 text-green-300 rounded-full text-xs font-bold uppercase tracking-wider border border-green-500/20">
                    Verified
                  </span>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
          
          {/* Sidebar */}
          <div className="lg:col-span-1 space-y-2">
            {[
              { id: 'profile', label: 'Personal Info', icon: User },
              { id: 'settings', label: 'Preferences', icon: Settings },
              { id: 'security', label: 'Security & Password', icon: Lock },
            ].map((tab) => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id as any)}
                  className={`w-full flex items-center gap-3 px-5 py-4 rounded-2xl font-bold transition-all duration-200
                    ${isActive 
                      ? 'bg-teal-600 text-white shadow-lg shadow-teal-500/30' 
                      : 'bg-white text-gray-600 hover:bg-gray-50 border border-gray-100'}`}
                >
                  <Icon size={20} className={isActive ? 'text-teal-100' : 'text-gray-400'} />
                  {tab.label}
                </button>
              );
            })}
          </div>

          {/* Main Content */}
          <div className="lg:col-span-3">
            <div className="bg-white rounded-3xl p-6 md:p-8 shadow-sm border border-gray-100">
              
              {/* Profile Tab */}
              {activeTab === 'profile' && (
                <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
                  <div className="flex items-center justify-between mb-8">
                    <div>
                      <h2 className="text-2xl font-black text-gray-900">Personal Information</h2>
                      <p className="text-gray-500 font-medium">Manage your basic profile details</p>
                    </div>
                    <button className="p-2 bg-teal-50 text-teal-600 rounded-xl hover:bg-teal-100 transition-colors">
                      <Edit3 size={20} />
                    </button>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div>
                      <label className="block text-sm font-bold text-gray-700 mb-2">Full Name</label>
                      <input 
                        type="text" 
                        disabled 
                        value={user?.full_name || ''} 
                        className="w-full bg-gray-50 border border-gray-200 text-gray-500 rounded-xl px-4 py-3 font-medium"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-bold text-gray-700 mb-2">Email Address</label>
                      <input 
                        type="email" 
                        disabled 
                        value={user?.email || ''} 
                        className="w-full bg-gray-50 border border-gray-200 text-gray-500 rounded-xl px-4 py-3 font-medium"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-bold text-gray-700 mb-2">Phone Number</label>
                      <input 
                        type="tel" 
                        disabled 
                        value={user?.phone || 'Not provided'} 
                        className="w-full bg-gray-50 border border-gray-200 text-gray-500 rounded-xl px-4 py-3 font-medium"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-bold text-gray-700 mb-2">Role</label>
                      <input 
                        type="text" 
                        disabled 
                        value={user?.role?.toUpperCase() || ''} 
                        className="w-full bg-gray-50 border border-gray-200 text-gray-500 rounded-xl px-4 py-3 font-medium"
                      />
                    </div>
                  </div>
                </div>
              )}

              {/* Security Tab */}
              {activeTab === 'security' && (
                <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
                  <div>
                    <h2 className="text-2xl font-black text-gray-900 mb-2">Security Settings</h2>
                    <p className="text-gray-500 font-medium">Update your password and secure your account</p>
                  </div>

                  <form onSubmit={handlePasswordChange} className="max-w-md space-y-5">
                    <div>
                      <label className="block text-sm font-bold text-gray-700 mb-2">Current Password</label>
                      <div className="relative">
                        <Key size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400" />
                        <input 
                          type="password" 
                          required
                          value={currentPassword}
                          onChange={e => setCurrentPassword(e.target.value)}
                          className="w-full bg-white border border-gray-200 focus:border-teal-500 focus:ring-2 focus:ring-teal-500/20 rounded-xl pl-11 pr-4 py-3 font-medium transition-all"
                          placeholder="••••••••"
                        />
                      </div>
                    </div>

                    <div className="pt-4 border-t border-gray-100">
                      <label className="block text-sm font-bold text-gray-700 mb-2">New Password</label>
                      <div className="relative">
                        <Lock size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400" />
                        <input 
                          type="password" 
                          required
                          value={newPassword}
                          onChange={e => setNewPassword(e.target.value)}
                          className="w-full bg-white border border-gray-200 focus:border-teal-500 focus:ring-2 focus:ring-teal-500/20 rounded-xl pl-11 pr-4 py-3 font-medium transition-all"
                          placeholder="Must be at least 6 characters"
                        />
                      </div>
                    </div>

                    <div>
                      <label className="block text-sm font-bold text-gray-700 mb-2">Confirm New Password</label>
                      <div className="relative">
                        <Shield size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400" />
                        <input 
                          type="password" 
                          required
                          value={confirmPassword}
                          onChange={e => setConfirmPassword(e.target.value)}
                          className="w-full bg-white border border-gray-200 focus:border-teal-500 focus:ring-2 focus:ring-teal-500/20 rounded-xl pl-11 pr-4 py-3 font-medium transition-all"
                          placeholder="Re-enter new password"
                        />
                      </div>
                    </div>

                    <button 
                      type="submit" 
                      disabled={isChangingPassword}
                      className="w-full flex items-center justify-center gap-2 bg-teal-600 hover:bg-teal-700 text-white font-bold py-3.5 px-6 rounded-xl transition-all shadow-md shadow-teal-500/20 disabled:opacity-50 mt-4"
                    >
                      {isChangingPassword ? (
                        <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                      ) : (
                        <>
                          <Save size={18} />
                          Update Password
                        </>
                      )}
                    </button>
                  </form>
                </div>
              )}

              {/* Settings Tab */}
              {activeTab === 'settings' && (
                <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
                  <div>
                    <h2 className="text-2xl font-black text-gray-900 mb-2">App Preferences</h2>
                    <p className="text-gray-500 font-medium">Customize your QuickServe experience</p>
                  </div>

                  <div className="space-y-4">
                    {[
                      { icon: Bell, title: 'Push Notifications', desc: 'Receive alerts for booking updates and messages' },
                      { icon: CreditCard, title: 'Saved Payment Methods', desc: 'Manage your credit cards and UPI IDs' },
                      { icon: Shield, title: 'Two-Factor Authentication', desc: 'Add an extra layer of security to your account' }
                    ].map((item, i) => (
                      <div key={i} className="flex items-center justify-between p-5 bg-gray-50 rounded-2xl border border-gray-100">
                        <div className="flex items-center gap-4">
                          <div className="w-10 h-10 bg-white rounded-xl flex items-center justify-center shadow-sm text-teal-600">
                            <item.icon size={20} />
                          </div>
                          <div>
                            <h4 className="font-bold text-gray-900">{item.title}</h4>
                            <p className="text-sm text-gray-500 font-medium">{item.desc}</p>
                          </div>
                        </div>
                        <button className="text-teal-600 font-bold text-sm hover:text-teal-700 px-4 py-2 bg-teal-50 hover:bg-teal-100 rounded-lg transition-colors">
                          Manage
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              
            </div>
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}
