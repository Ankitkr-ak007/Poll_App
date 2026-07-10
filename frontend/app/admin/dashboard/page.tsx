'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { ExternalLink, Download } from 'lucide-react';

type Poll = {
  id: string;
  question: string;
  option_a_text: string;
  option_b_text: string;
  status: 'draft' | 'active' | 'closed';
};

type ParticipantStatus = {
  name: string;
  has_voted: boolean;
};

type PollResults = {
  option_a: { text: string; count: number };
  option_b: { text: string; count: number };
  total: number;
  participants: ParticipantStatus[];
};

export default function AdminDashboard() {
  const [token, setToken] = useState<string | null>(null);
  const router = useRouter();

  const [poll, setPoll] = useState<Poll | null>(null);
  const [results, setResults] = useState<PollResults | null>(null);
  
  // Edit Form State
  const [question, setQuestion] = useState('');
  const [optA, setOptA] = useState('');
  const [optB, setOptB] = useState('');

  // Participants State
  const [bulkNames, setBulkNames] = useState('');

  useEffect(() => {
    const t = localStorage.getItem('admin_token');
    if (!t) {
      router.push('/admin/login');
    } else {
      setToken(t);
      fetchPoll(t);
      fetchResults(t);
      const interval = setInterval(() => {
        fetchResults(t);
      }, 2000);
      return () => clearInterval(interval);
    }
  }, []);

  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  const authHeaders = {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  };

  const fetchPoll = async (t: string) => {
    const res = await fetch(`${API_URL}/api/admin/poll`, { headers: { 'Authorization': `Bearer ${t}` } });
    if (res.ok) {
      const data = await res.json();
      setPoll(data);
      setQuestion(data.question);
      setOptA(data.option_a_text);
      setOptB(data.option_b_text);
    }
  };

  const fetchResults = async (t: string) => {
    const res = await fetch(`${API_URL}/api/admin/results`, { headers: { 'Authorization': `Bearer ${t}` } });
    if (res.ok) {
      setResults(await res.json());
    } else if (res.status === 401 || res.status === 403) {
      router.push('/admin/login');
    }
  };

  const handleUpdatePoll = async () => {
    await fetch(`${API_URL}/api/admin/poll`, {
      method: 'PUT',
      headers: authHeaders,
      body: JSON.stringify({ question, option_a_text: optA, option_b_text: optB })
    });
    fetchPoll(token!);
  };

  const handleStatusChange = async (action: 'open' | 'close') => {
    await fetch(`${API_URL}/api/admin/poll/${action}`, { method: 'POST', headers: authHeaders });
    fetchPoll(token!);
  };

  const handleReset = async () => {
    if (confirm("Are you sure you want to reset the poll? This will clear all votes.")) {
      await fetch(`${API_URL}/api/admin/poll/reset`, {
        method: 'POST',
        headers: authHeaders,
        body: JSON.stringify({ confirm: true })
      });
      fetchPoll(token!);
      fetchResults(token!);
    }
  };

  const handleAddParticipants = async () => {
    const names = bulkNames.split('\n').filter(n => n.trim());
    if (names.length === 0) return;
    await fetch(`${API_URL}/api/admin/participants`, {
      method: 'POST',
      headers: authHeaders,
      body: JSON.stringify({ names })
    });
    setBulkNames('');
    fetchResults(token!);
  };
  
  const handleExportCSV = async () => {
    if (poll) {
      // Need to attach auth header for export
      const res = await fetch(`${API_URL}/api/admin/export/${poll.id}.csv`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `poll_results_${poll.id}.csv`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
      }
    }
  };

  if (!poll || !results) return (
    <div className="min-h-screen bg-bg-dark text-white flex items-center justify-center font-inter">
      <div className="animate-pulse flex flex-col items-center">
        <div className="w-12 h-12 border-4 border-brand border-t-transparent rounded-full animate-spin mb-4"></div>
        <p className="text-surface-highlight font-medium tracking-wide">Loading dashboard...</p>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-bg-dark text-white p-4 md:p-8 font-inter">
      <div className="max-w-6xl mx-auto space-y-8">
        <header className="flex flex-col md:flex-row justify-between items-start md:items-center bg-surface p-6 rounded-2xl border border-surface-highlight shadow-xl gap-4 md:gap-0">
          <div>
            <h1 className="text-3xl font-bold font-outfit tracking-tight">Poll Admin</h1>
            <div className="flex items-center gap-2 mt-2">
              <span className="text-zinc-400 text-sm font-medium">Status:</span>
              <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold uppercase tracking-wider border ${
                poll.status === 'draft' ? 'bg-zinc-800/50 text-zinc-300 border-zinc-700/50' : 
                poll.status === 'active' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20 animate-pulse' : 
                'bg-amber-500/10 text-amber-400 border-amber-500/20'
              }`}>
                {poll.status}
              </span>
            </div>
          </div>
          <div className="space-x-4 flex items-center">
            <button 
              onClick={() => window.open('/present', '_blank')}
              className="flex items-center gap-2 bg-surface-highlight hover:bg-zinc-600 px-4 py-2.5 rounded-xl font-semibold transition-all duration-200"
            >
              <ExternalLink size={18} />
              Present
            </button>
            {poll.status === 'draft' && (
              <button onClick={() => handleStatusChange('open')} className="bg-brand hover:bg-brand-dark px-6 py-2.5 rounded-xl font-semibold transition-all duration-200 active:scale-95 text-white">Open Voting</button>
            )}
            {poll.status === 'active' && (
              <button onClick={() => handleStatusChange('close')} className="bg-amber-600 hover:bg-amber-500 px-6 py-2.5 rounded-xl font-semibold transition-all duration-200 active:scale-95 text-white">Close Round</button>
            )}
            {poll.status === 'closed' && (
              <>
                <button onClick={handleExportCSV} className="flex items-center gap-2 bg-zinc-700 hover:bg-zinc-600 px-4 py-2.5 rounded-xl font-semibold transition-all duration-200">
                  <Download size={18} />
                  CSV
                </button>
                <button onClick={handleReset} className="bg-brand hover:bg-brand-dark px-6 py-2.5 rounded-xl font-semibold transition-all duration-200 active:scale-95 text-white">Reset Round</button>
              </>
            )}
          </div>
        </header>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          {/* Poll Configuration */}
          <div className="bg-surface p-6 rounded-2xl border border-surface-highlight shadow-xl flex flex-col">
            <h2 className="text-xl font-bold mb-6 border-b border-surface-highlight pb-3 tracking-tight font-outfit">Poll Settings</h2>
            <div className="space-y-5 flex-grow">
              <div>
                <label className="block text-sm font-medium text-zinc-400 mb-1.5 ml-1">Question</label>
                <input type="text" value={question} onChange={e => setQuestion(e.target.value)} disabled={poll.status !== 'draft'} className="w-full px-4 py-3 bg-bg-dark border border-surface-highlight rounded-xl disabled:opacity-50 disabled:cursor-not-allowed focus:ring-2 focus:ring-brand focus:border-brand outline-none transition-all placeholder-zinc-600" />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-zinc-400 mb-1.5 ml-1">Option A</label>
                  <input type="text" value={optA} onChange={e => setOptA(e.target.value)} disabled={poll.status !== 'draft'} className="w-full px-4 py-3 bg-bg-dark border border-surface-highlight rounded-xl disabled:opacity-50 disabled:cursor-not-allowed focus:ring-2 focus:ring-brand focus:border-brand outline-none transition-all placeholder-zinc-600" />
                </div>
                <div>
                  <label className="block text-sm font-medium text-zinc-400 mb-1.5 ml-1">Option B</label>
                  <input type="text" value={optB} onChange={e => setOptB(e.target.value)} disabled={poll.status !== 'draft'} className="w-full px-4 py-3 bg-bg-dark border border-surface-highlight rounded-xl disabled:opacity-50 disabled:cursor-not-allowed focus:ring-2 focus:ring-brand focus:border-brand outline-none transition-all placeholder-zinc-600" />
                </div>
              </div>
            </div>
            {poll.status === 'draft' && (
              <button onClick={handleUpdatePoll} className="w-full mt-6 bg-surface-highlight hover:bg-zinc-600 py-3 rounded-xl font-semibold transition-all duration-200 border border-surface-highlight hover:border-zinc-500">Save Changes</button>
            )}
          </div>

          {/* Live Results */}
          <div className="bg-surface p-6 rounded-2xl border border-surface-highlight shadow-xl">
            <h2 className="text-xl font-bold mb-6 border-b border-surface-highlight pb-3 tracking-tight font-outfit flex items-center justify-between">
              Live Results
              {poll.status === 'active' && <span className="flex h-3 w-3 relative"><span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span><span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-500"></span></span>}
            </h2>
            <div className="space-y-8">
              <div className="flex justify-between items-end bg-bg-dark p-4 rounded-xl border border-surface-highlight">
                <span className="text-zinc-400 font-medium">Total Votes Cast</span>
                <span className="text-4xl font-black font-outfit">{results.total}</span>
              </div>
              
              <div className="space-y-6">
                <div>
                  <div className="flex justify-between mb-2">
                    <span className="font-semibold text-zinc-200">{results.option_a.text}</span>
                    <span className="font-bold">{results.option_a.count} <span className="text-zinc-500 text-sm font-medium ml-1">({results.total ? Math.round((results.option_a.count / results.total) * 100) : 0}%)</span></span>
                  </div>
                  <div className="w-full bg-bg-dark rounded-full h-4 overflow-hidden border border-surface-highlight">
                    <div className="bg-brand h-full rounded-full transition-all duration-700 ease-out relative" style={{ width: `${results.total ? (results.option_a.count / results.total) * 100 : 0}%` }}>
                    </div>
                  </div>
                </div>

                <div>
                  <div className="flex justify-between mb-2">
                    <span className="font-semibold text-zinc-200">{results.option_b.text}</span>
                    <span className="font-bold">{results.option_b.count} <span className="text-zinc-500 text-sm font-medium ml-1">({results.total ? Math.round((results.option_b.count / results.total) * 100) : 0}%)</span></span>
                  </div>
                  <div className="w-full bg-bg-dark rounded-full h-4 overflow-hidden border border-surface-highlight">
                    <div className="bg-surface-highlight h-full rounded-full transition-all duration-700 ease-out relative" style={{ width: `${results.total ? (results.option_b.count / results.total) * 100 : 0}%` }}>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Roster Management */}
          <div className="bg-surface p-6 rounded-2xl border border-surface-highlight shadow-xl md:col-span-2">
            <h2 className="text-xl font-bold mb-6 border-b border-surface-highlight pb-3 tracking-tight font-outfit">Roster Management <span className="text-sm font-normal text-zinc-500 ml-2">({results.participants.length} total)</span></h2>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
              <div className="md:col-span-1 flex flex-col">
                <label className="block text-sm font-medium text-zinc-400 mb-2 ml-1">Bulk Add (one per line)</label>
                <textarea 
                  value={bulkNames} 
                  onChange={e => setBulkNames(e.target.value)}
                  className="w-full flex-grow min-h-[160px] px-4 py-3 bg-bg-dark border border-surface-highlight rounded-xl focus:ring-2 focus:ring-brand focus:border-brand outline-none resize-none transition-all placeholder-zinc-600 custom-scrollbar"
                  placeholder="John Doe&#10;Jane Smith"
                />
                <button onClick={handleAddParticipants} className="mt-4 w-full bg-surface-highlight hover:bg-zinc-600 py-3 rounded-xl font-semibold transition-all border border-surface-highlight shadow-sm active:scale-[0.98]">Add Participants</button>
              </div>
              
              <div className="md:col-span-2 bg-bg-dark rounded-xl border border-surface-highlight overflow-hidden flex flex-col h-[280px]">
                <div className="overflow-y-auto custom-scrollbar flex-grow p-1">
                  <table className="w-full text-left text-sm">
                    <thead className="sticky top-0 bg-bg-dark text-zinc-400 z-10 border-b border-surface-highlight">
                      <tr>
                        <th className="px-4 py-3 font-semibold tracking-wide">Name</th>
                        <th className="px-4 py-3 font-semibold tracking-wide text-right">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-surface-highlight">
                      {results.participants.map((p, idx) => (
                        <tr key={idx} className="hover:bg-surface transition-colors">
                          <td className="px-4 py-3 font-medium text-zinc-300">{p.name}</td>
                          <td className="px-4 py-3 text-right">
                            {p.has_voted ? (
                              <span className="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 shadow-[0_0_10px_rgba(16,185,129,0.1)]">Voted</span>
                            ) : (
                              <span className="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-bold bg-zinc-500/10 text-zinc-400 border border-zinc-600/30">Waiting</span>
                            )}
                          </td>
                        </tr>
                      ))}
                      {results.participants.length === 0 && (
                        <tr>
                          <td colSpan={2} className="px-4 py-8 text-center text-zinc-500">No participants added yet.</td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
