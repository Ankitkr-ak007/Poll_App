'use client';

import { useEffect, useState, use } from 'react';
import { motion } from 'framer-motion';
import { Loader2, Trophy, BarChart3 } from 'lucide-react';
import Link from 'next/link';

type PublicPollResult = {
  question: string;
  option_a_text: string;
  option_b_text: string;
  status: 'draft' | 'active' | 'closed';
  counts: { A: number; B: number; total: number };
  winner_option: 'A' | 'B' | null;
};

export default function PollResultsPage({ params }: { params: Promise<{ pollId: string }> }) {
  const { pollId } = use(params);
  const [result, setResult] = useState<PublicPollResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [userVote, setUserVote] = useState<string | null>(null);

  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  const WS_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000';

  useEffect(() => {
    // Check if user voted in this poll
    const vote = localStorage.getItem(`vote_${pollId}`);
    if (vote) setUserVote(vote);

    const fetchResult = async () => {
      try {
        const res = await fetch(`${API_URL}/api/results/${pollId}`);
        if (res.ok) {
          setResult(await res.json());
        }
      } catch (e) {
        console.error(e);
      }
      setLoading(false);
    };

    fetchResult();
  }, [pollId, API_URL]);

  useEffect(() => {
    if (!result || result.status === 'closed') return;

    let ws: WebSocket;
    let retryTimeout: NodeJS.Timeout;

    const connect = () => {
      ws = new WebSocket(`${WS_URL}/ws/poll/${pollId}`);
      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === 'vote') {
          setResult((prev) => prev ? {
            ...prev,
            counts: {
              A: data.option_a_count,
              B: data.option_b_count,
              total: data.total
            }
          } : null);
        } else if (data.type === 'status_update') {
          if (data.status === 'closed') {
            // Re-fetch to get final winner data
            fetch(`${API_URL}/api/results/${pollId}`)
              .then(r => r.json())
              .then(data => setResult(data));
          } else {
            setResult(prev => prev ? { ...prev, status: data.status } : null);
          }
        }
      };

      ws.onclose = () => {
        retryTimeout = setTimeout(connect, 3000);
      };
    };

    connect();

    return () => {
      if (ws) ws.close();
      clearTimeout(retryTimeout);
    };
  }, [pollId, WS_URL, API_URL, result?.status]);

  if (loading) {
    return (
      <div className="min-h-screen bg-bg-dark text-white flex items-center justify-center font-inter">
        <Loader2 className="w-10 h-10 text-brand animate-spin" />
      </div>
    );
  }

  if (!result) {
    return (
      <div className="min-h-screen bg-bg-dark text-white flex items-center justify-center font-inter">
        <div className="text-center bg-surface p-10 rounded-[2rem] border border-surface-highlight shadow-2xl">
          <h1 className="text-2xl font-bold mb-2">Poll Not Found</h1>
          <Link href="/" className="text-brand hover:underline mt-4 inline-block">Go Home</Link>
        </div>
      </div>
    );
  }

  const { A, B, total } = result.counts;
  const percentA = total > 0 ? Math.round((A / total) * 100) : 0;
  const percentB = total > 0 ? Math.round((B / total) * 100) : 0;

  const votedForWinner = result.status === 'closed' && result.winner_option && userVote === result.winner_option;

  return (
    <div className="min-h-screen bg-bg-dark text-white flex flex-col items-center p-6 font-inter">
      <div className="w-full max-w-2xl mt-8">
        
        {votedForWinner && (
          <motion.div 
            initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }}
            className="mb-6 p-4 bg-emerald-500/10 border border-emerald-500/30 rounded-2xl flex items-center gap-4 shadow-[0_0_30px_rgba(16,185,129,0.15)]"
          >
            <div className="bg-emerald-500/20 p-2 rounded-xl">
              <Trophy className="w-6 h-6 text-emerald-400" />
            </div>
            <div>
              <p className="font-bold text-emerald-400 text-lg">You voted for the winning side!</p>
              <p className="text-emerald-500/80 text-sm font-medium">Your vote helped secure this outcome.</p>
            </div>
          </motion.div>
        )}

        <div className="bg-surface p-8 sm:p-12 rounded-[2.5rem] border border-surface-highlight shadow-2xl relative overflow-hidden">
          {/* Status Badge */}
          <div className="absolute top-8 right-8 flex items-center gap-2">
            {result.status === 'active' ? (
              <span className="flex items-center gap-2 px-3 py-1.5 bg-brand/10 border border-brand/30 text-brand rounded-full text-xs font-bold uppercase tracking-wider">
                <span className="w-2 h-2 rounded-full bg-brand animate-pulse" />
                Live
              </span>
            ) : (
              <span className="px-3 py-1.5 bg-zinc-800 border border-zinc-700 text-zinc-400 rounded-full text-xs font-bold uppercase tracking-wider">
                Closed
              </span>
            )}
          </div>

          <h1 className="text-3xl sm:text-4xl font-black mb-12 font-outfit mt-4 pr-24">
            {result.question}
          </h1>

          <div className="space-y-8">
            {/* Option A */}
            <div className="relative">
              <div className="flex justify-between items-end mb-3 relative z-10">
                <div className="flex items-center gap-3">
                  <span className="text-xl font-bold">{result.option_a_text}</span>
                  {result.status === 'closed' && result.winner_option === 'A' && (
                    <span className="bg-amber-500/20 text-amber-400 text-xs font-bold uppercase px-2 py-1 rounded-lg border border-amber-500/30">Winner</span>
                  )}
                </div>
                <div className="text-right">
                  <span className="text-3xl font-black">{percentA}%</span>
                  <p className="text-zinc-500 text-sm font-medium">{A} votes</p>
                </div>
              </div>
              <div className="h-6 w-full bg-bg-dark rounded-full overflow-hidden border border-surface-highlight">
                <motion.div 
                  initial={{ width: 0 }}
                  animate={{ width: `${percentA}%` }}
                  transition={{ duration: 0.5, ease: "easeOut" }}
                  className={`h-full ${result.status === 'closed' && result.winner_option === 'A' ? 'bg-amber-500 shadow-[0_0_20px_rgba(245,158,11,0.5)]' : 'bg-brand'}`}
                />
              </div>
            </div>

            {/* Option B */}
            <div className="relative">
              <div className="flex justify-between items-end mb-3 relative z-10">
                <div className="flex items-center gap-3">
                  <span className="text-xl font-bold">{result.option_b_text}</span>
                  {result.status === 'closed' && result.winner_option === 'B' && (
                    <span className="bg-amber-500/20 text-amber-400 text-xs font-bold uppercase px-2 py-1 rounded-lg border border-amber-500/30">Winner</span>
                  )}
                </div>
                <div className="text-right">
                  <span className="text-3xl font-black">{percentB}%</span>
                  <p className="text-zinc-500 text-sm font-medium">{B} votes</p>
                </div>
              </div>
              <div className="h-6 w-full bg-bg-dark rounded-full overflow-hidden border border-surface-highlight">
                <motion.div 
                  initial={{ width: 0 }}
                  animate={{ width: `${percentB}%` }}
                  transition={{ duration: 0.5, ease: "easeOut" }}
                  className={`h-full ${result.status === 'closed' && result.winner_option === 'B' ? 'bg-amber-500 shadow-[0_0_20px_rgba(245,158,11,0.5)]' : 'bg-brand'}`}
                />
              </div>
            </div>
          </div>
          
          <div className="mt-12 text-center text-zinc-500 font-medium">
            Total Votes: {total}
          </div>
        </div>
      </div>
    </div>
  );
}
