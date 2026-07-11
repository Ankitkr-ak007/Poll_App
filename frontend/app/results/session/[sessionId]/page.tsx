'use client';

import { useEffect, useState, use } from 'react';
import { Loader2, ArrowLeft, Trophy, BarChart3, Users, Lock } from 'lucide-react';
import Link from 'next/link';

type RoundRanking = {
  poll_id: string;
  question: string;
  option_a_text: string;
  option_b_text: string;
  counts: { A: number; B: number; total: number };
  percentages: { A: number; B: number };
  participation: { voted: number; total: number };
  result_label: 'A' | 'B' | null;
};

type SessionRankingResponse = {
  published: boolean;
  rounds: RoundRanking[] | null;
};

export default function SessionLeaderboardPage({ params }: { params: Promise<{ sessionId: string }> }) {
  const { sessionId } = use(params);
  const [data, setData] = useState<SessionRankingResponse | null>(null);
  const [loading, setLoading] = useState(true);

  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

  useEffect(() => {
    const fetchLeaderboard = async () => {
      try {
        const res = await fetch(`${API_URL}/api/results/session/${sessionId}`);
        if (res.ok) {
          setData(await res.json());
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

  if (!data?.published) {
    return (
      <div className="min-h-screen bg-bg-dark text-white flex flex-col items-center justify-center p-6 font-inter">
        <div className="max-w-md w-full bg-surface p-10 rounded-[2rem] border border-surface-highlight text-center shadow-2xl flex flex-col items-center">
          <div className="w-20 h-20 bg-zinc-800/50 rounded-full flex items-center justify-center mb-6 border border-zinc-700/50">
            <Lock className="w-10 h-10 text-zinc-400" />
          </div>
          <h1 className="text-2xl font-bold mb-3 font-outfit tracking-tight">Results Hidden</h1>
          <p className="text-zinc-400 text-lg">Results haven't been published yet. Please check back later when the organizers reveal them.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-bg-dark text-white p-6 font-inter">
      <div className="max-w-3xl mx-auto mt-8">
        <div className="flex items-center gap-4 mb-10">
          <Link href="/" className="p-3 hover:bg-surface rounded-xl transition-colors bg-surface-highlight border border-zinc-700">
            <ArrowLeft className="w-6 h-6 text-zinc-300" />
          </Link>
          <h1 className="text-4xl font-black font-outfit tracking-tight">Public Ranking</h1>
        </div>

        {!data.rounds || data.rounds.length === 0 ? (
          <div className="bg-surface p-10 rounded-[2rem] border border-surface-highlight text-center shadow-xl">
            <p className="text-zinc-400 text-lg">No rounds have been completed yet.</p>
          </div>
        ) : (
          <div className="space-y-8">
            {data.rounds.map((round, idx) => {
              const optionAWinner = round.result_label === 'A';
              const optionBWinner = round.result_label === 'B';
              
              return (
                <div key={round.poll_id} className="bg-surface p-8 rounded-[2rem] border border-surface-highlight shadow-xl">
                  <div className="flex justify-between items-start mb-6">
                    <div>
                      <div className="text-zinc-500 text-sm font-bold tracking-widest mb-2 uppercase flex items-center gap-2">
                        <span>Round {data.rounds!.length - idx}</span>
                        <span className="w-1.5 h-1.5 rounded-full bg-zinc-600"></span>
                        <span className="flex items-center gap-1.5"><Users size={14} /> {round.participation.voted} / {round.participation.total} voted</span>
                      </div>
                      <h2 className="text-2xl font-bold font-outfit text-white">{round.question}</h2>
                    </div>
                    {round.result_label ? (
                      <div className="flex items-center gap-2 px-4 py-2 rounded-xl border font-bold text-sm uppercase tracking-wide bg-brand/10 text-brand border-brand/20">
                        <Trophy size={16} />
                        Positive: {round.result_label === 'A' ? round.option_a_text : round.option_b_text}
                      </div>
                    ) : (
                      <div className="flex items-center gap-2 px-4 py-2 rounded-xl border border-zinc-700 bg-surface-highlight font-bold text-sm uppercase tracking-wide text-zinc-400">
                        <BarChart3 size={16} />
                        Tie
                      </div>
                    )}
                  </div>

                  <div className="space-y-5">
                    {/* Option A */}
                    <div className="relative">
                      <div className="flex justify-between mb-2 text-sm font-semibold">
                        <span className={optionAWinner ? "text-white" : "text-zinc-300"}>{round.option_a_text}</span>
                        <span className="text-zinc-400">{round.counts.A} ({round.percentages.A}%)</span>
                      </div>
                      <div className="h-3 w-full bg-bg-dark rounded-full overflow-hidden border border-surface-highlight">
                        <div 
                          className={`h-full rounded-full transition-all duration-1000 ${optionAWinner ? 'bg-brand' : 'bg-zinc-600'}`} 
                          style={{ width: `${round.percentages.A}%` }} 
                        />
                      </div>
                    </div>

                    {/* Option B */}
                    <div className="relative">
                      <div className="flex justify-between mb-2 text-sm font-semibold">
                        <span className={optionBWinner ? "text-white" : "text-zinc-300"}>{round.option_b_text}</span>
                        <span className="text-zinc-400">{round.counts.B} ({round.percentages.B}%)</span>
                      </div>
                      <div className="h-3 w-full bg-bg-dark rounded-full overflow-hidden border border-surface-highlight">
                        <div 
                          className={`h-full rounded-full transition-all duration-1000 ${optionBWinner ? 'bg-brand' : 'bg-zinc-600'}`} 
                          style={{ width: `${round.percentages.B}%` }} 
                        />
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
