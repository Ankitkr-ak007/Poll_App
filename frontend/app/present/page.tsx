"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";

export default function PresentPage() {
  const [poll, setPoll] = useState<any>(null);
  const [results, setResults] = useState({ option_a_count: 0, option_b_count: 0, total: 0 });

  useEffect(() => {
    // Initial fetch
    fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/poll`)
      .then(res => res.json())
      .then(data => {
        setPoll(data);
        if (data.id) {
          fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/admin/results`, {
            headers: {
              'Authorization': `Bearer ${localStorage.getItem('token')}` // Note: public shouldn't need this, but for simplicity we fetch if we can, or just wait for WS
            }
          })
          .then(res => res.json())
          .then(resData => {
            if (resData.option_a) {
              setResults({
                option_a_count: resData.option_a.count,
                option_b_count: resData.option_b.count,
                total: resData.total
              });
            }
          }).catch(e => console.error("Could not fetch initial results", e));
        }
      });
  }, []);

  useEffect(() => {
    if (!poll?.id) return;
    
    // WebSocket URL (replace http with ws)
    const wsUrl = process.env.NEXT_PUBLIC_API_URL?.replace("http", "ws") || "ws://localhost:8000";
    const ws = new WebSocket(`${wsUrl}/ws/results/${poll.id}`);
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === "vote") {
        setResults({
          option_a_count: data.option_a_count,
          option_b_count: data.option_b_count,
          total: data.total
        });
      } else if (data.type === "status_update") {
        setPoll((prev: any) => ({ ...prev, status: data.status }));
        if (data.reset) {
          setResults({ option_a_count: 0, option_b_count: 0, total: 0 });
        }
      }
    };
    
    return () => ws.close();
  }, [poll?.id]);

  if (!poll) {
    return <div className="flex h-screen items-center justify-center text-white bg-bg-dark font-outfit text-4xl">Loading...</div>;
  }

  const aPct = results.total === 0 ? 50 : (results.option_a_count / results.total) * 100;
  const bPct = results.total === 0 ? 50 : (results.option_b_count / results.total) * 100;

  return (
    <div className="min-h-screen bg-bg-dark text-white p-8 flex flex-col justify-center">
      <div className="max-w-6xl w-full mx-auto">
        <h1 className="text-6xl md:text-8xl text-center font-outfit font-bold mb-4 tracking-tight">
          {poll.question}
        </h1>
        <p className="text-center text-surface-highlight text-2xl font-inter mb-16 uppercase tracking-widest">
          {poll.status === "active" ? "Voting is Live" : poll.status === "closed" ? "Voting Closed" : "Get Ready"}
        </p>
        
        {/* Duel Meter */}
        <div className="relative h-64 md:h-96 w-full flex rounded-3xl overflow-hidden shadow-2xl bg-surface">
          <motion.div 
            className="h-full bg-brand flex flex-col justify-center items-start px-8 md:px-16"
            animate={{ width: `${aPct}%` }}
            transition={{ type: "spring", bounce: 0.2, duration: 0.8 }}
          >
            <div className="font-outfit font-black text-6xl md:text-9xl text-white opacity-90 drop-shadow-lg">
              {results.option_a_count}
            </div>
            <div className="font-inter text-2xl md:text-4xl font-medium mt-2 text-white opacity-80 uppercase">
              {poll.option_a_text}
            </div>
          </motion.div>
          
          <motion.div 
            className="h-full bg-surface-highlight flex flex-col justify-center items-end px-8 md:px-16"
            animate={{ width: `${bPct}%` }}
            transition={{ type: "spring", bounce: 0.2, duration: 0.8 }}
          >
            <div className="font-outfit font-black text-6xl md:text-9xl text-white opacity-90 drop-shadow-lg">
              {results.option_b_count}
            </div>
            <div className="font-inter text-2xl md:text-4xl font-medium mt-2 text-white opacity-80 uppercase">
              {poll.option_b_text}
            </div>
          </motion.div>
          
          {/* Center Divider Line */}
          <div className="absolute left-1/2 top-0 bottom-0 w-2 bg-white/20 -ml-1 backdrop-blur-sm shadow-[0_0_20px_rgba(255,255,255,0.3)]"></div>
        </div>
        
        <div className="mt-12 text-center text-surface-highlight font-inter text-xl">
          Total Votes: {results.total}
        </div>
      </div>
    </div>
  );
}
