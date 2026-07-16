"use client";

import { useState, FormEvent } from "react";

interface Props {
  onScout: (query: string, depth: number) => void;
  scouting: boolean;
}

export default function SearchBar({ onScout, scouting }: Props) {
  const [query, setQuery] = useState("");
  const [depth, setDepth] = useState(3);

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!query.trim() || scouting) return;
    onScout(query.trim(), depth);
    setQuery("");
  }

  return (
    <div className="flex flex-col gap-3">
      <form onSubmit={handleSubmit} className="flex gap-3">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search Google Maps..."
          className="flex-1 rounded-xl border border-white/[0.08] bg-white/[0.04] backdrop-blur-sm px-4 py-3 text-sm text-white/80 placeholder-white/30 outline-none transition-all duration-200 focus:border-violet-500/40 focus:bg-white/[0.08] focus:shadow-lg focus:shadow-violet-500/5"
        />
        <button
          type="submit"
          disabled={scouting || !query.trim()}
          className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-violet-600 to-purple-600 px-6 py-3 text-sm font-semibold text-white shadow-sm transition-all duration-200 hover:from-violet-500 hover:to-purple-500 hover:shadow-lg hover:shadow-violet-500/20 disabled:opacity-40 disabled:hover:shadow-none"
        >
          {scouting ? (
            <>
              <div className="size-4 rounded-full border-2 border-white/30 border-t-white animate-spin" />
              Scouting...
            </>
          ) : (
            <>
              <svg className="size-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
              Scout
            </>
          )}
        </button>
      </form>
      <div className="flex items-center gap-3 px-1">
        <span className="text-xs text-white/40 font-medium">Scroll depth:</span>
        <input
          type="range"
          min={1}
          max={10}
          value={depth}
          onChange={(e) => setDepth(Number(e.target.value))}
          disabled={scouting}
          className="flex-1 h-1.5 rounded-full appearance-none bg-white/[0.08] cursor-pointer accent-violet-500"
        />
        <span className="text-xs text-white/60 font-semibold w-5 text-right">{depth}</span>
      </div>
    </div>
  );
}
