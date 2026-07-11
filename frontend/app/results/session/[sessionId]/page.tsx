'use client';

import { useEffect, useState, use } from 'react';
import { Loader2, ArrowLeft, Trophy } from 'lucide-react';
import Link from 'next/link';

type LeaderboardEntry = {
  poll_id: string;
  question: string;
  winner_option: 'A' | 'B' | null;
  counts: { A: number; B: number; total: number } | null;
};

export default function SessionLeaderboardPage({ params }: { params: Promise<{ sessionId: string }> }) {
  const { sessionId } = use(params);
  const [polls, setPolls] = useState<LeaderboardEntry[]>([]);
  const [loading, setLoading] = useState(true);

  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  useEffect(() => {
    const fetchLeaderboard = async () => {
      try {
        const res = await fetch(`${API_URL}/api/results/session/${sessionId}`);
        if (res.ok) {
          setPolls(await res.json());
        }
      } catch (e) {
        console.error(e);
      }
      setLoading(false);
    };

    fetchLeaderboard();
  }, [sessionId, API_URL]);

  if (loading) {
    return (
      <div className="min-h-screen bg-bg-dark text-white flex items-center justify-center font-inter">
        <Loader2 className="w-10 h-10 text-brand animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-bg-dark text-white p-6 font-inter">
      <div className="max-w-3xl mx-auto mt-8">
        <div className="flex items-center gap-4 mb-8">
          <Link href="/" className="p-2 hover:bg-surface rounded-xl transition-colors">
            <ArrowLeft className="w-6 h-6 text-zinc-400" />
          </Link>
          <h1 className="text-3xl font-black font-outfit">Session Leaderboard</h1>
        </div>

        {polls.length === 0 ? (
          <div className="bg-surface p-10 rounded-[2rem] border border-surface-highlight text-center shadow-xl">
            <p className="text-zinc-400 text-lg">No closed rounds in this session yet.</p>
          </div>
        ) : (
          <div className="space-y-6">
            {polls.map((poll, idx) => (
              <Link href={`/results/${poll.poll_id}`} key={poll.poll_id} className="block group">
                <div className="bg-surface p-6 rounded-[1.5rem] border border-surface-highlight shadow-lg transition-all hover:border-zinc-500 hover:shadow-2xl">
                  <div className="flex items-start justify-between gap-6">
                    <div>
                      <div className="text-zinc-500 text-sm font-bold tracking-wider mb-2 uppercase">Round {polls.length - idx}</div>
                      <h2 className="text-xl font-bold font-outfit group-hover:text-brand transition-colors">{poll.question}</h2>
                    </div>
                    
                    {poll.winner_option && (
                      <div className="flex flex-col items-end text-right shrink-0">
                        <div className="flex items-center gap-2 text-amber-400 bg-amber-500/10 px-3 py-1 rounded-lg border border-amber-500/20 mb-2">
                          <Trophy className="w-4 h-4" />
                          <span className="text-sm font-bold uppercase">Winner: {poll.winner_option}</span>
                        </div>
                        {poll.counts && (
                          <div className="text-zinc-500 text-xs font-medium">
                            {poll.counts[poll.winner_option]} / {poll.counts.total} votes
                          </div>
                        )}
                      </div>
                    )}
                    
                    {!poll.winner_option && (
                      <div className="shrink-0">
                        <span className="text-zinc-500 text-sm font-bold uppercase px-3 py-1 bg-surface-highlight rounded-lg border border-zinc-700">Tie</span>
                      </div>
                    )}
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
