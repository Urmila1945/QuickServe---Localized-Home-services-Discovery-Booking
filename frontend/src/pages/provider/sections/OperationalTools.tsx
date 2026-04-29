import React, { useState } from 'react';
import { Package, Users, Receipt, FileText, Map, AlertTriangle } from 'lucide-react';
import { inventoryItems, expenseLog } from '../../../data/mockDashboardData';
import toast from 'react-hot-toast';

const team = [
  { id:'tm1', name:'Raju Kumar',    role:'Apprentice',  jobs:12, earnings:14880, status:'active'  },
  { id:'tm2', name:'Sunil Sharma',  role:'Subcontractor',jobs:8, earnings:24800, status:'active'  },
  { id:'tm3', name:'Kiran Rao',     role:'Helper',      jobs:6,  earnings:7440,  status:'idle'    },
];

const expenseCategories = ['Fuel','Materials','Tools','Parking','Misc'];

const OperationalTools: React.FC = () => {
  const [activeOp, setActiveOp] = useState<'inventory'|'team'|'expense'|'invoice'|'route'>('inventory');
  const [inventory, setInventory] = useState(inventoryItems);
  const [newExpense, setNewExpense] = useState({ date:'', category:'Fuel', amount:'', desc:'' });
  const [expenses, setExpenses] = useState(expenseLog);

  const totalExpenses = expenses.reduce((s, e) => s + e.amount, 0);
  const lowStock = inventory.filter(i => i.qty <= i.minQty);

  const addExpense = () => {
    if (!newExpense.amount || !newExpense.date) { toast.error('Fill date and amount'); return; }
    setExpenses(prev => [...prev, { id:`exp${Date.now()}`, ...newExpense, amount: Number(newExpense.amount) }]);
    setNewExpense({ date:'', category:'Fuel', amount:'', desc:'' });
    toast.success('Expense logged');
  };

  const opTabs = [
    { key:'inventory', label:'Inventory', icon:'📦' },
    { key:'team',      label:'Team',      icon:'👷' },
    { key:'expense',   label:'Expenses',  icon:'🧾' },
    { key:'invoice',   label:'Invoices',  icon:'📄' },
    { key:'route',     label:'Routes',    icon:'🗺️' },
  ] as const;

  return (
    <div className="space-y-6">
      {/* Sub-tabs */}
      <div className="flex gap-2 bg-white rounded-2xl p-1.5 shadow-sm border border-gray-100 overflow-x-auto">
        {opTabs.map(t => (
          <button key={t.key} onClick={() => setActiveOp(t.key)}
            className={`flex items-center gap-1.5 px-4 py-2 rounded-xl font-bold text-sm whitespace-nowrap transition-all ${activeOp===t.key?'bg-teal-600 text-white shadow':'text-gray-500 hover:text-gray-800 hover:bg-gray-50'}`}>
            {t.icon} {t.label}
          </button>
        ))}
      </div>

      {/* Inventory */}
      {activeOp === 'inventory' && (
        <div className="space-y-4">
          {lowStock.length > 0 && (
            <div className="bg-red-50 border border-red-200 rounded-2xl p-4 flex items-center gap-3">
              <AlertTriangle size={18} className="text-red-500 shrink-0" />
              <div>
                <p className="font-black text-red-700 text-sm">Low Stock Alert!</p>
                <p className="text-xs text-red-500">{lowStock.map(i=>i.name).join(', ')} need restocking</p>
              </div>
            </div>
          )}
          <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
              <h3 className="font-black text-gray-900 text-lg flex items-center gap-2"><Package size={18} className="text-teal-600" /> Inventory</h3>
              <button onClick={() => toast.success('Inventory updated')} className="text-xs bg-teal-600 text-white font-black px-4 py-2 rounded-xl hover:bg-teal-700 transition-all">+ Add Item</button>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50">
                  <tr>{['Item','Qty','Min Stock','Unit','Supplier','Cost','Status'].map(h=>(
                    <th key={h} className="text-left py-3 px-4 font-black text-gray-400 text-xs uppercase tracking-wider">{h}</th>
                  ))}</tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {inventory.map(item => {
                    const low = item.qty <= item.minQty;
                    return (
                      <tr key={item.id} className={`transition-colors hover:bg-gray-50 ${low?'bg-red-50/30':''}`}>
                        <td className="py-3.5 px-4 font-bold text-gray-900 text-sm">{item.name}</td>
                        <td className="py-3.5 px-4">
                          <div className="flex items-center gap-2">
                            <button onClick={() => setInventory(prev=>prev.map(i=>i.id===item.id?{...i,qty:Math.max(0,i.qty-1)}:i))} className="w-6 h-6 bg-gray-100 rounded font-black text-gray-600 hover:bg-gray-200 text-xs">-</button>
                            <span className={`font-black text-sm w-8 text-center ${low?'text-red-600':'text-gray-900'}`}>{item.qty}</span>
                            <button onClick={() => setInventory(prev=>prev.map(i=>i.id===item.id?{...i,qty:i.qty+1}:i))} className="w-6 h-6 bg-gray-100 rounded font-black text-gray-600 hover:bg-gray-200 text-xs">+</button>
                          </div>
                        </td>
                        <td className="py-3.5 px-4 text-gray-500 text-sm">{item.minQty}</td>
                        <td className="py-3.5 px-4 text-gray-500 text-sm">{item.unit}</td>
                        <td className="py-3.5 px-4 text-gray-500 text-sm">{item.supplier}</td>
                        <td className="py-3.5 px-4 font-bold text-gray-700 text-sm">₹{item.cost}</td>
                        <td className="py-3.5 px-4">
                          <span className={`text-xs font-black px-2.5 py-1 rounded-full ${low?'bg-red-100 text-red-700':'bg-green-100 text-green-700'}`}>
                            {low?'Low Stock':'OK'}
                          </span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Team */}
      {activeOp === 'team' && (
        <div className="space-y-4">
          <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
            <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
              <h3 className="font-black text-gray-900 text-lg flex items-center gap-2"><Users size={18} className="text-blue-600" /> Team Management</h3>
              <button onClick={() => toast.success('Invite sent!')} className="text-xs bg-blue-600 text-white font-black px-4 py-2 rounded-xl hover:bg-blue-700 transition-all">+ Invite Member</button>
            </div>
            <div className="divide-y divide-gray-50">
              {team.map(m => (
                <div key={m.id} className="flex items-center justify-between px-6 py-4 hover:bg-gray-50 transition-colors">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-blue-100 rounded-xl flex items-center justify-center font-black text-blue-700 text-sm">
                      {m.name.split(' ').map(n=>n[0]).join('')}
                    </div>
                    <div>
                      <p className="font-bold text-gray-900 text-sm">{m.name}</p>
                      <p className="text-xs text-gray-400">{m.role} · {m.jobs} jobs this month</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    <div className="text-right">
                      <p className="font-black text-green-600 text-sm">₹{m.earnings.toLocaleString()}</p>
                      <p className="text-xs text-gray-400">earned</p>
                    </div>
                    <span className={`text-xs font-black px-2.5 py-1 rounded-full ${m.status==='active'?'bg-green-100 text-green-700':'bg-gray-100 text-gray-500'}`}>{m.status}</span>
                    <button onClick={() => toast.success(`Job assigned to ${m.name}`)} className="text-xs bg-teal-100 text-teal-700 font-black px-3 py-1.5 rounded-xl hover:bg-teal-200 transition-colors">Assign Job</button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Expenses */}
      {activeOp === 'expense' && (
        <div className="space-y-4">
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            {Object.entries(expenses.reduce<Record<string,number>>((acc,e)=>({...acc,[e.category]:(acc[e.category]||0)+e.amount}),{})).map(([cat,amt]) => (
              <div key={cat} className="bg-white rounded-2xl p-4 shadow-sm border border-gray-100 text-center">
                <p className="text-xl font-black text-gray-900">₹{amt.toLocaleString()}</p>
                <p className="text-xs font-bold text-gray-500 mt-0.5">{cat}</p>
              </div>
            ))}
            <div className="bg-orange-50 border border-orange-200 rounded-2xl p-4 text-center">
              <p className="text-xl font-black text-orange-700">₹{totalExpenses.toLocaleString()}</p>
              <p className="text-xs font-bold text-orange-600 mt-0.5">Total Expenses</p>
            </div>
          </div>
          {/* Add Expense Form */}
          <div className="bg-white rounded-2xl p-5 shadow-sm border border-gray-100">
            <h4 className="font-black text-gray-900 text-sm mb-4 flex items-center gap-2"><Receipt size={15} className="text-orange-500" /> Log Expense</h4>
            <div className="grid sm:grid-cols-2 gap-3 mb-3">
              <input type="date" value={newExpense.date} onChange={e=>setNewExpense(p=>({...p,date:e.target.value}))}
                className="px-3 py-2.5 rounded-xl border-2 border-gray-100 focus:border-teal-400 focus:outline-none text-sm font-medium" />
              <select value={newExpense.category} onChange={e=>setNewExpense(p=>({...p,category:e.target.value}))}
                className="px-3 py-2.5 rounded-xl border-2 border-gray-100 focus:border-teal-400 focus:outline-none text-sm font-medium bg-white">
                {expenseCategories.map(c=><option key={c}>{c}</option>)}
              </select>
              <input type="number" placeholder="Amount (₹)" value={newExpense.amount} onChange={e=>setNewExpense(p=>({...p,amount:e.target.value}))}
                className="px-3 py-2.5 rounded-xl border-2 border-gray-100 focus:border-teal-400 focus:outline-none text-sm font-medium" />
              <input type="text" placeholder="Description" value={newExpense.desc} onChange={e=>setNewExpense(p=>({...p,desc:e.target.value}))}
                className="px-3 py-2.5 rounded-xl border-2 border-gray-100 focus:border-teal-400 focus:outline-none text-sm font-medium" />
            </div>
            <button onClick={addExpense} className="bg-teal-600 hover:bg-teal-700 text-white px-6 py-2.5 rounded-xl font-black text-sm transition-all active:scale-95">Add Expense</button>
          </div>
          {/* Expense Log */}
          <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
            <div className="px-5 py-4 border-b border-gray-100"><h4 className="font-black text-gray-900 text-sm">Expense Log</h4></div>
            <div className="divide-y divide-gray-50">
              {expenses.slice().reverse().map(e => (
                <div key={e.id} className="flex items-center justify-between px-5 py-3.5 hover:bg-gray-50 transition-colors">
                  <div>
                    <p className="font-bold text-gray-900 text-sm">{e.desc}</p>
                    <p className="text-xs text-gray-400">{e.date} · {e.category}</p>
                  </div>
                  <span className="font-black text-red-600 text-sm">-₹{e.amount.toLocaleString()}</span>
                </div>
              ))}
            </div>
            <div className="px-5 py-3 bg-gray-50 flex justify-between items-center">
              <span className="text-xs font-black text-gray-500 uppercase">Tax Deductible Estimate</span>
              <span className="font-black text-purple-600">₹{Math.round(totalExpenses*0.3).toLocaleString()}</span>
            </div>
          </div>
        </div>
      )}

      {/* Invoice */}
      {activeOp === 'invoice' && (
        <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
          <h3 className="font-black text-gray-900 text-lg flex items-center gap-2 mb-5"><FileText size={18} className="text-green-600" /> Invoice Generator</h3>
          <div className="grid sm:grid-cols-2 gap-4 mb-5">
            {[{label:'Client Name',ph:'Anjali Singh'},{label:'Service',ph:'Electrical Wiring'},{label:'Date',ph:'', type:'date'},{label:'Amount (₹)',ph:'2500',type:'number'},{label:'GST %',ph:'18',type:'number'},{label:'Notes',ph:'Payment due within 7 days'}].map(f=>(
              <div key={f.label}>
                <label className="text-xs font-black text-gray-400 uppercase tracking-widest mb-1.5 block">{f.label}</label>
                <input type={f.type||'text'} placeholder={f.ph}
                  className="w-full px-4 py-2.5 rounded-xl border-2 border-gray-100 focus:border-teal-400 focus:outline-none text-sm font-medium" />
              </div>
            ))}
          </div>
          <div className="flex gap-3">
            <button onClick={() => toast.success('Invoice generated & sent with payment link!')}
              className="bg-teal-600 hover:bg-teal-700 text-white px-6 py-3 rounded-xl font-black text-sm transition-all active:scale-95">Generate & Send Invoice</button>
            <button onClick={() => toast.success('PDF downloaded!')}
              className="bg-gray-100 hover:bg-gray-200 text-gray-700 px-6 py-3 rounded-xl font-black text-sm transition-all">Download PDF</button>
          </div>
        </div>
      )}

      {/* Route */}
      {activeOp === 'route' && (
        <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
          <h3 className="font-black text-gray-900 text-lg flex items-center gap-2 mb-5"><Map size={18} className="text-blue-600" /> Daily Route Optimizer</h3>
          <p className="text-sm text-gray-500 mb-4 bg-blue-50 text-blue-700 px-4 py-3 rounded-xl font-bold">
            🤖 AI suggests optimal job ordering to minimize travel by 34% and save ₹830 in fuel today.
          </p>
          <div className="space-y-3">
            {[
              { stop:1, time:'9:00 AM',  client:'Anjali Singh',   area:'Indiranagar',   dist:'4.2 km', job:'Wiring check'     },
              { stop:2, time:'11:00 AM', client:'Ramesh Gupta',   area:'Koramangala',   dist:'3.1 km', job:'Fan installation' },
              { stop:3, time:'1:30 PM',  client:'Priya Mehta',    area:'HSR Layout',    dist:'5.8 km', job:'Switch repair'    },
              { stop:4, time:'4:00 PM',  client:'Meera Nair',     area:'JP Nagar',      dist:'6.2 km', job:'Circuit breaker'  },
            ].map(s => (
              <div key={s.stop} className="flex items-center gap-4 bg-gray-50 rounded-xl p-4">
                <div className="w-8 h-8 bg-teal-600 text-white rounded-full flex items-center justify-center font-black text-sm shrink-0">{s.stop}</div>
                <div className="flex-1">
                  <p className="font-bold text-gray-900 text-sm">{s.client} — {s.job}</p>
                  <p className="text-xs text-gray-400">{s.time} · {s.area} · +{s.dist}</p>
                </div>
              </div>
            ))}
          </div>
          <div className="mt-4 flex gap-3">
            <button onClick={() => toast.success('Route opened in Google Maps!')} className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-xl font-black text-sm transition-all flex items-center gap-2">
              <Map size={15} /> Open in Maps
            </button>
            <button onClick={() => toast.success('Route optimized!')} className="bg-green-600 hover:bg-green-700 text-white px-6 py-3 rounded-xl font-black text-sm transition-all">🤖 Re-Optimize</button>
          </div>
        </div>
      )}
    </div>
  );
};

export default OperationalTools;
