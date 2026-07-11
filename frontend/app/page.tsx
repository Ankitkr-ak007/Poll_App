'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { CheckCircle, Search, Loader2 } from 'lucide-react';

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
  const [submitting, setSubmitting] = useState(false);

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
    setSubmitting(true);

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
        if (poll) {
          localStorage.setItem(`vote_${poll.id}`, selectedOption);
        }
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
    setSubmitting(false);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-bg-dark text-white flex items-center justify-center font-inter">
        <Loader2 className="w-10 h-10 text-brand animate-spin" />
      </div>
    );
  }

  if (!poll || poll.status !== 'active') {
    return (
      <div className="min-h-screen bg-bg-dark text-white flex flex-col items-center justify-center p-6 text-center font-inter">
        <div className="bg-surface p-10 rounded-[2rem] border border-surface-highlight shadow-2xl max-w-lg w-full">
          <h1 className="text-3xl font-bold mb-3 text-white tracking-tight font-outfit">{poll?.status === 'closed' ? 'Voting is closed' : 'No active poll'}</h1>
          <p className="text-zinc-400 text-lg">Please wait for the admin to open the next round of voting.</p>
        </div>
      </div>
    );
  }

  if (statusMsg?.type === 'success') {
    return (
      <div className="min-h-screen bg-bg-dark text-white flex items-center justify-center p-6 font-inter">
        <motion.div 
          initial={{ scale: 0.9, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          className="bg-surface p-10 rounded-[2rem] border border-emerald-500/30 shadow-[0_0_40px_rgba(16,185,129,0.15)] text-center max-w-md w-full"
        >
          <div className="w-24 h-24 bg-emerald-500/20 rounded-full flex items-center justify-center mx-auto mb-8">
            <CheckCircle className="w-12 h-12 text-emerald-400" />
          </div>
          <h2 className="text-3xl font-bold text-emerald-400 mb-3 font-outfit">Vote Recorded</h2>
          <p className="text-zinc-300 text-lg">{statusMsg.text}</p>
          <p className="text-sm text-zinc-500 mt-8 font-medium">You can now close this tab.</p>
        </motion.div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-bg-dark text-white flex flex-col items-center justify-center p-4 sm:p-6 font-inter">
      <div className="w-full max-w-xl flex flex-col space-y-6">
        <div className="bg-surface p-6 sm:p-10 rounded-[2.5rem] border border-surface-highlight shadow-2xl">
          <h1 className="text-3xl sm:text-4xl font-black text-center mb-10 leading-tight tracking-tight font-outfit">
            {poll.question}
          </h1>

          <div className="space-y-8">
            {/* Identity Selection */}
            <div className="relative">
              <label className="block text-sm font-semibold text-zinc-400 mb-3 uppercase tracking-wider ml-2">Who are you?</label>
              {selectedParticipant ? (
                <div className="flex items-center justify-between p-5 bg-brand/10 border border-brand/30 rounded-2xl">
                  <span className="font-bold text-brand text-xl">{selectedParticipant.name}</span>
                  <button 
                    onClick={() => { setSelectedParticipant(null); setSearch(''); }} 
                    className="text-brand hover:text-brand-dark bg-brand/20 px-4 py-2 rounded-xl text-sm transition-colors font-semibold"
                  >
                    Change
                  </button>
                </div>
              ) : (
                <div className="relative">
                  <div className="relative">
                    <Search className="absolute left-5 top-1/2 -translate-y-1/2 text-zinc-500 w-6 h-6" />
                    <input
                      type="text"
                      value={search}
                      onChange={(e) => setSearch(e.target.value)}
                      placeholder="Search your name..."
                      className="w-full pl-14 pr-5 py-4 bg-bg-dark border border-surface-highlight rounded-2xl focus:outline-none focus:ring-2 focus:ring-brand/50 transition-all text-lg placeholder-zinc-500"
                    />
                  </div>
                  
                  <AnimatePresence>
                    {participants.length > 0 && (
                      <motion.ul 
                        initial={{ opacity: 0, y: -10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -10 }}
                        className="absolute z-10 w-full mt-2 bg-surface-highlight border border-zinc-700 rounded-2xl shadow-2xl max-h-60 overflow-y-auto overflow-hidden divide-y divide-zinc-700/50"
                      >
                        {participants.map(p => (
                          <li 
                            key={p.id} 
                            onClick={() => { setSelectedParticipant(p); setParticipants([]); }}
                            className="px-6 py-4 hover:bg-brand/20 hover:text-white cursor-pointer transition-colors font-medium text-lg text-zinc-300"
                          >
                            {p.name}
                          </li>
                        ))}
                      </motion.ul>
                    )}
                  </AnimatePresence>
                </div>
              )}
            </div>

            {/* Voting Options */}
            <div className="pt-2 space-y-4">
              <label className="block text-sm font-semibold text-zinc-400 mb-3 uppercase tracking-wider ml-2">Your Vote</label>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <button
                  onClick={() => setSelectedOption('A')}
                  className={`p-6 rounded-2xl font-bold text-xl transition-all duration-200 border-2 ${
                    selectedOption === 'A' 
                      ? 'bg-brand border-brand shadow-[0_0_30px_rgba(230,57,70,0.4)] text-white scale-[1.02]' 
                      : 'bg-bg-dark border-surface-highlight text-zinc-300 hover:bg-surface-highlight hover:border-zinc-500'
                  }`}
                >
                  {poll.option_a_text}
                </button>
                <button
                  onClick={() => setSelectedOption('B')}
                  className={`p-6 rounded-2xl font-bold text-xl transition-all duration-200 border-2 ${
                    selectedOption === 'B' 
                      ? 'bg-brand border-brand shadow-[0_0_30px_rgba(230,57,70,0.4)] text-white scale-[1.02]' 
                      : 'bg-bg-dark border-surface-highlight text-zinc-300 hover:bg-surface-highlight hover:border-zinc-500'
                  }`}
                >
                  {poll.option_b_text}
                </button>
              </div>
            </div>
            
            {statusMsg?.type === 'error' && (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="p-4 bg-red-500/10 border border-red-500/20 rounded-2xl">
                <p className="text-red-400 text-center font-medium">{statusMsg.text}</p>
              </motion.div>
            )}

            <button
              onClick={handleSubmit}
              disabled={!selectedParticipant || !selectedOption || submitting}
              className="w-full mt-4 bg-white text-bg-dark disabled:opacity-50 disabled:bg-surface-highlight disabled:text-zinc-500 py-5 rounded-2xl font-black text-lg transition-all active:scale-[0.98] disabled:active:scale-100 uppercase tracking-widest disabled:shadow-none shadow-[0_0_20px_rgba(255,255,255,0.1)] flex items-center justify-center"
            >
              {submitting ? <Loader2 className="w-6 h-6 animate-spin" /> : "Submit Vote"}
            </button>
          </div>
        </div>
        <p className="text-center text-zinc-500 text-sm font-medium">Your vote is bound to your name. You can only vote once.</p>
      </div>
    </div>
  );
}
