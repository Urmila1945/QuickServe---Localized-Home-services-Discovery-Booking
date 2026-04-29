import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { 
  Users, CheckCircle, XCircle, Star, Award, 
  Search, Shield, MapPin, TrendingUp, Clock,
  ExternalLink, Ban, AlertCircle, FileText
} from 'lucide-react';
import api from '../../../services/api';
import toast from 'react-hot-toast';

const AllProviders: React.FC = () => {
  const [searchTerm, setSearchTerm] = useState('');
  const queryClient = useQueryClient();

  const { data: usersData, isLoading } = useQuery({
    queryKey: ['admin-all-providers'],
    queryFn: () => api.get('/api/admin/users', { params: { role: 'provider', limit: 100 } }).then(r => r.data),
  });

  const providers = usersData?.users || [];

  const verifyMutation = useMutation({
    mutationFn: (id: string) => api.post(`/api/admin/providers/${id}/verify`),
    onSuccess: () => { toast.success('Provider verified!'); queryClient.invalidateQueries({ queryKey: ['admin-all-providers'] }); },
    onError:   () => toast.error('Verification failed'),
  });

  const suspendMutation = useMutation({
    mutationFn: ({ id, reason }: { id: string; reason: string }) =>
      api.post(`/api/admin/providers/${id}/suspend`, null, { params: { reason } }),
    onSuccess: () => { toast.success('Provider suspended.'); queryClient.invalidateQueries({ queryKey: ['admin-all-providers'] }); },
    onError:   () => toast.error('Suspension failed'),
  });

  const filteredProviders = providers.filter((p: any) => 
    !searchTerm || 
    p.full_name?.toLowerCase().includes(searchTerm.toLowerCase()) || 
    p.business_name?.toLowerCase().includes(searchTerm.toLowerCase()) || 
    p.email?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  if (isLoading) return <div className="p-10 text-center font-black text-gray-400">Loading Provider Directory...</div>;

  return (
    <div className="space-y-6">
      {/* Search & Stats Bar */}
      <div className="bg-white rounded-3xl p-6 shadow-sm border border-gray-100 flex flex-col md:flex-row items-center justify-between gap-6">
        <div className="relative flex-1 w-full">
          <Search size={18} className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400" />
          <input 
            type="text" 
            placeholder="Search by name, business, or email..."
            value={searchTerm}
            onChange={e => setSearchTerm(e.target.value)}
            className="w-full bg-gray-50 border-2 border-transparent focus:border-teal-500 rounded-2xl pl-12 pr-6 py-3.5 focus:outline-none transition-all font-bold text-sm"
          />
        </div>
        
        <div className="flex items-center gap-6 divide-x divide-gray-100">
          <div className="text-center px-4">
            <p className="text-2xl font-black text-gray-900 leading-none">{providers.length}</p>
            <p className="text-[10px] font-bold text-gray-400 uppercase tracking-widest mt-1">Total</p>
          </div>
          <div className="text-center px-4">
            <p className="text-2xl font-black text-teal-600 leading-none">{providers.filter((p:any)=>p.verified_by_admin).length}</p>
            <p className="text-[10px] font-bold text-teal-600 uppercase tracking-widest mt-1">Verified</p>
          </div>
          <div className="text-center px-4">
            <p className="text-2xl font-black text-red-500 leading-none">{providers.filter((p:any)=>p.suspended).length}</p>
            <p className="text-[10px] font-bold text-red-500 uppercase tracking-widest mt-1">Suspended</p>
          </div>
        </div>
      </div>

      {/* Providers Table */}
      <div className="bg-white rounded-[32px] shadow-sm border border-gray-100 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50/50">
              <tr>
                {['Provider Info', 'Status', 'Assessment Score', 'Experience', 'Rating & Jobs', 'Actions'].map(h => (
                  <th key={h} className="text-left py-4 px-6 font-black text-gray-400 text-[10px] uppercase tracking-[0.2em]">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {filteredProviders.map((p: any) => (
                <tr key={p._id} className="hover:bg-teal-50/30 transition-colors group">
                  <td className="py-5 px-6">
                    <div className="flex items-center gap-4">
                      <div className="w-12 h-12 bg-teal-100 rounded-2xl flex items-center justify-center font-black text-teal-700 text-lg group-hover:scale-110 transition-transform">
                        {p.full_name?.split(' ').map((n:any)=>n[0]).join('').slice(0,2)}
                      </div>
                      <div>
                        <div className="font-black text-gray-900 text-sm leading-tight">{p.full_name}</div>
                        <div className="text-xs text-gray-500 mt-0.5">{p.email}</div>
                        <div className="flex items-center gap-1.5 text-[10px] font-bold text-teal-600 uppercase tracking-widest mt-1">
                          <MapPin size={10} /> {p.city || 'Bangalore'}
                        </div>
                      </div>
                    </div>
                  </td>
                  <td className="py-5 px-6">
                    {p.verified_by_admin && !p.suspended ? (
                      <span className="bg-green-100 text-green-700 px-2.5 py-1 rounded-full text-[10px] font-black uppercase tracking-widest flex items-center gap-1.5 w-fit border border-green-200">
                        <CheckCircle size={12} /> Verified
                      </span>
                    ) : p.suspended ? (
                      <span className="bg-red-100 text-red-700 px-2.5 py-1 rounded-full text-[10px] font-black uppercase tracking-widest flex items-center gap-1.5 w-fit border border-red-200">
                        <Ban size={12} /> Suspended
                      </span>
                    ) : (
                      <span className="bg-yellow-100 text-yellow-700 px-2.5 py-1 rounded-full text-[10px] font-black uppercase tracking-widest flex items-center gap-1.5 w-fit border border-yellow-200 shadow-sm shadow-yellow-100">
                        <Clock size={12} /> Pending Approval
                      </span>
                    )}
                  </td>
                  <td className="py-5 px-6">
                    <div className="flex flex-col">
                      <div className="flex items-center gap-2">
                        <div className="h-2 w-16 bg-gray-100 rounded-full overflow-hidden">
                          <div 
                            className={`h-full rounded-full ${p.aptitude_score > 70 ? 'bg-teal-500' : p.aptitude_score > 40 ? 'bg-yellow-500' : 'bg-red-500'}`} 
                            style={{ width: `${p.aptitude_score || 0}%` }} 
                          />
                        </div>
                        <span className="text-xs font-black text-gray-900">{p.aptitude_score || 0}%</span>
                      </div>
                      <span className="text-[10px] font-black text-gray-400 uppercase tracking-[0.1em] mt-1.5">Aptitude Exam</span>
                    </div>
                  </td>
                  <td className="py-5 px-6">
                    <div className="font-black text-gray-900 text-sm">{p.experience_years || 0} Yrs</div>
                    <div className="text-[10px] font-bold text-gray-400 uppercase mt-0.5 tracking-widest">Industry Exp.</div>
                  </td>
                  <td className="py-5 px-6">
                    <div className="flex items-center gap-1.5 text-yellow-600 font-black">
                      <Star size={14} className="fill-yellow-600" />
                      {(p.rating ?? 0).toFixed(1)}
                    </div>
                    <div className="text-[10px] font-bold text-gray-400 mt-1 uppercase tracking-widest">
                      {p.bookings_count || 0} Jobs Done
                    </div>
                  </td>
                  <td className="py-5 px-6">
                    <div className="flex gap-2">
                      {!p.verified_by_admin && !p.suspended && (
                        <button 
                          onClick={() => verifyMutation.mutate(p._id)} 
                          className="bg-teal-600 hover:bg-teal-700 text-white px-3 py-2 rounded-xl font-black text-[10px] uppercase tracking-widest transition-all shadow-md active:scale-95"
                        >
                          Verify
                        </button>
                      )}
                      {!p.suspended && (
                        <button 
                          onClick={() => { const r = window.prompt('Suspension reason:'); if(r) suspendMutation.mutate({ id: p._id, reason: r }); }}
                          className="w-9 h-9 bg-gray-50 rounded-xl flex items-center justify-center text-gray-400 hover:bg-red-500 hover:text-white transition-all shadow-sm"
                        >
                          <Ban size={16} />
                        </button>
                      )}
                      <button 
                        onClick={() => toast.success('Profile summary opened')}
                        className="w-9 h-9 bg-gray-50 rounded-xl flex items-center justify-center text-gray-400 hover:bg-teal-600 hover:text-white transition-all shadow-sm"
                      >
                        <ExternalLink size={16} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default AllProviders;
