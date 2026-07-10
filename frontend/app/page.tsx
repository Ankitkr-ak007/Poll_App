'use client';

import { useState, useEffect } from 'react';

type Poll = {
  id: string;
  question: string;
  option_a_text: string;
  option_b_text: string;
  status: 'draft' | 'active' | 'closed';
};

type Participant = {
  id: string;
  name: string;
};

export default function VoterPage() {
  const [poll, setPoll] = useState<Poll | null>(null);
  const [search, setSearch] = useState('');
  const [participants, setParticipants] = useState<Participant[]>([]);
  const [selectedParticipant, setSelectedParticipant] = useState<Participant | null>(null);
  const [selectedOption, setSelectedOption] = useState<'A' | 'B' | null>(null);
  const [statusMsg, setStatusMsg] = useState<{ type: 'success' | 'error', text: string } | null>(null);
  const [loading, setLoading] = useState(true);

  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  useEffect(() => {
    fetchPoll();
    const interval = setInterval(fetchPoll, 5000);
    return () => clearInterval(interval);
  }, []);

  const fetchPoll = async () => {
    try {
      const res = await fetch(`${API_URL}/api/poll`);
      if (res.ok) {
        setPoll(await res.json());
      }
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  };

  useEffect(() => {
    if (search.length > 0 && !selectedParticipant) {
      const fetchParticipants = async () => {
        try {
          const res = await fetch(`${API_URL}/api/participants/search?q=${encodeURIComponent(search)}`);
          if (res.ok) {
            setParticipants(await res.json());
          }
        } catch (e) {
          console.error(e);
        }
      };
      const debounce = setTimeout(fetchParticipants, 300);
      return () => clearTimeout(debounce);
    } else {
      setParticipants([]);
    }
  }, [search, selectedParticipant]);

  const handleSubmit = async () => {
    if (!selectedParticipant || !selectedOption) return;
    setStatusMsg(null);

    try {
      const res = await fetch(`${API_URL}/api/vote`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          participant_id: selectedParticipant.id,
          option: selectedOption
        })
      });

      if (res.ok) {
        setStatusMsg({ type: 'success', text: 'Your vote has been recorded securely.' });
        setSelectedOption(null);
        setSelectedParticipant(null);
        setSearch('');
      } else {
        const data = await res.json();
        setStatusMsg({ type: 'error', text: data.detail || 'Failed to record vote' });
      }
    } catch (e) {
      setStatusMsg({ type: 'error', text: 'Network error occurred.' });
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-zinc-950 text-white flex items-center justify-center">
        <div className="animate-pulse w-10 h-10 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin"></div>
      </div>
    );
  }

  if (!poll || poll.status !== 'active') {
    return (
      <div className="min-h-screen bg-zinc-950 text-white flex flex-col items-center justify-center p-4 text-center">
        <div className="bg-zinc-900/50 p-10 rounded-3xl border border-zinc-800/50 shadow-2xl max-w-lg w-full backdrop-blur-sm">
          <div className="w-20 h-20 bg-zinc-800/50 rounded-full flex items-center justify-center mx-auto mb-6 shadow-inner">
            <svg className="w-10 h-10 text-zinc-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <h1 className="text-3xl font-bold mb-3 text-zinc-200 tracking-tight">{poll?.status === 'closed' ? 'Voting is closed' : 'No active poll'}</h1>
          <p className="text-zinc-500 text-lg">Please wait for the admin to open the next round of voting.</p>
        </div>
      </div>
    );
  }

  if (statusMsg?.type === 'success') {
    return (
      <div className="min-h-screen bg-zinc-950 text-white flex items-center justify-center p-4">
        <div className="bg-zinc-900 p-8 rounded-2xl border border-emerald-500/30 shadow-[0_0_30px_rgba(16,185,129,0.15)] text-center max-w-md w-full animate-in zoom-in duration-300">
          <div className="w-20 h-20 bg-emerald-500/20 rounded-full flex items-center justify-center mx-auto mb-6">
            <svg className="w-10 h-10 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <h2 className="text-3xl font-bold text-emerald-400 mb-2">Vote Recorded</h2>
          <p className="text-zinc-400">{statusMsg.text}</p>
          <p className="text-sm text-zinc-600 mt-6 font-medium">You can now close this tab.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-zinc-950 text-white flex flex-col items-center justify-center p-4 sm:p-8">
      <div className="w-full max-w-xl flex flex-col space-y-6">
        <div className="bg-zinc-900/80 backdrop-blur-md p-8 sm:p-10 rounded-3xl border border-zinc-800 shadow-2xl">
          <h1 className="text-2xl sm:text-3xl font-black text-center mb-10 leading-tight tracking-tight text-transparent bg-clip-text bg-gradient-to-br from-white to-zinc-400">
            {poll.question}
          </h1>

          <div className="space-y-6">
            <div className="relative">
              <label className="block text-sm font-semibold text-zinc-400 mb-2 uppercase tracking-wider ml-1">Who are you?</label>
              {selectedParticipant ? (
                <div className="flex items-center justify-between p-4 bg-indigo-500/10 border border-indigo-500/30 rounded-xl">
                  <span className="font-semibold text-indigo-300 text-lg">{selectedParticipant.name}</span>
                  <button 
                    onClick={() => { setSelectedParticipant(null); setSearch(''); }} 
                    className="text-indigo-400 hover:text-indigo-300 bg-indigo-500/20 px-3 py-1 rounded-lg text-sm transition-colors font-medium"
                  >
                    Change
                  </button>
                </div>
              ) : (
                <div className="relative">
                  <input
                    type="text"
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    placeholder="Search your name..."
                    className="w-full px-5 py-4 bg-zinc-800/80 border border-zinc-700/80 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500/50 transition-all text-lg placeholder-zinc-500 shadow-inner"
                  />
                  {participants.length > 0 && (
                    <ul className="absolute z-10 w-full mt-2 bg-zinc-800 border border-zinc-700 rounded-xl shadow-2xl max-h-60 overflow-y-auto overflow-hidden backdrop-blur-md divide-y divide-zinc-700/50">
                      {participants.map(p => (
                        <li 
                          key={p.id} 
                          onClick={() => { setSelectedParticipant(p); setParticipants([]); }}
                          className="px-5 py-3 hover:bg-indigo-500/20 hover:text-indigo-200 cursor-pointer transition-colors font-medium text-lg"
                        >
                          {p.name}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              )}
            </div>

            <div className="pt-2 space-y-3">
              <label className="block text-sm font-semibold text-zinc-400 mb-2 uppercase tracking-wider ml-1">Your Vote</label>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4">
                <button
                  onClick={() => setSelectedOption('A')}
                  className={`p-5 rounded-2xl font-bold text-lg transition-all duration-200 border-2 ${
                    selectedOption === 'A' 
                      ? 'bg-indigo-600 border-indigo-500 shadow-[0_0_20px_rgba(79,70,229,0.3)] text-white' 
                      : 'bg-zinc-800/50 border-zinc-700/50 text-zinc-300 hover:bg-zinc-700 hover:border-zinc-600'
                  }`}
                >
                  {poll.option_a_text}
                </button>
                <button
                  onClick={() => setSelectedOption('B')}
                  className={`p-5 rounded-2xl font-bold text-lg transition-all duration-200 border-2 ${
                    selectedOption === 'B' 
                      ? 'bg-purple-600 border-purple-500 shadow-[0_0_20px_rgba(147,51,234,0.3)] text-white' 
                      : 'bg-zinc-800/50 border-zinc-700/50 text-zinc-300 hover:bg-zinc-700 hover:border-zinc-600'
                  }`}
                >
                  {poll.option_b_text}
                </button>
              </div>
            </div>
            
            {statusMsg?.type === 'error' && (
              <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-xl">
                <p className="text-red-400 text-center font-medium">{statusMsg.text}</p>
              </div>
            )}

            <button
              onClick={handleSubmit}
              disabled={!selectedParticipant || !selectedOption}
              className="w-full mt-8 bg-zinc-100 text-zinc-900 disabled:opacity-50 disabled:bg-zinc-800 disabled:text-zinc-500 py-4 rounded-xl font-black text-lg transition-all active:scale-[0.98] disabled:active:scale-100 uppercase tracking-widest disabled:shadow-none shadow-[0_0_20px_rgba(255,255,255,0.1)]"
            >
              Submit Vote
            </button>
          </div>
        </div>
        <p className="text-center text-zinc-600 text-sm font-medium">Your vote is bound to your name. You can only vote once.</p>
      </div>
    </div>
  );
}
