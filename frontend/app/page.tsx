"use client";

import { useEffect, useState } from "react";

interface Lead {
  id: string;
  name: string;
  website: string | null;
  email: string | null;
  phone: string | null;
  address: string | null;
  status: string;
  created_at: string;
}

export default function Home() {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState<string | null>(null);

  useEffect(() => {
    fetch("http://localhost:8000/api/leads")
      .then((res) => res.json())
      .then((data) => {
        setLeads(data);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  async function handleDelete(id: string, e: React.MouseEvent) {
    e.stopPropagation();
    await fetch(`http://localhost:8000/api/leads/${id}`, { method: "DELETE" });
    setLeads((prev) => prev.filter((l) => l.id !== id));
  }

  const statusColor: Record<string, string> = {
    scouted: "from-sky-400 to-blue-500",
    enriched: "from-emerald-400 to-teal-500",
    failed: "from-rose-400 to-pink-500",
  };

  return (
    <div className="flex flex-col min-h-screen">
      <header className="backdrop-blur-md bg-white/40 border-b border-purple-200/60 px-6 py-5 sticky top-0 z-20">
        <div className="max-w-6xl mx-auto flex items-center gap-3">
          <div className="size-9 rounded-xl bg-gradient-to-br from-violet-500 to-fuchsia-500 flex items-center justify-center text-white font-bold text-sm shadow-lg shadow-violet-300/50 transition-transform duration-300 hover:scale-110">
            N
          </div>
          <h1 className="text-2xl font-bold bg-gradient-to-r from-violet-600 via-fuchsia-500 to-cyan-600 bg-clip-text text-transparent">
            NexusScout AI
          </h1>
          <span className="ml-auto text-sm text-violet-400 font-medium">
            Lead Dashboard
          </span>
        </div>
      </header>

      <main className="flex-1 max-w-6xl mx-auto w-full px-6 py-8">
        {loading ? (
          <div className="flex items-center justify-center h-64">
            <div className="size-10 rounded-full border-4 border-violet-300/40 border-t-violet-500 animate-spin" />
          </div>
        ) : leads.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-64 gap-4 text-violet-400 animate-fadeIn">
            <div className="size-16 rounded-2xl bg-white/60 shadow-lg shadow-violet-200/50 flex items-center justify-center text-3xl transition-transform duration-300 hover:scale-110">
              📡
            </div>
            <p className="text-lg font-semibold text-violet-600">No leads yet</p>
            <p className="text-sm text-violet-400">Run the scouter to start collecting leads</p>
          </div>
        ) : (
          <div className="grid gap-3">
            <div className="flex items-center justify-between mb-2">
              <h2 className="text-lg font-semibold text-violet-700">
                All Leads
              </h2>
              <span className="text-sm text-violet-400 font-medium bg-white/40 px-3 py-1 rounded-full">
                {leads.length} total
              </span>
            </div>
            {leads.map((lead, i) => {
              const isOpen = expanded === lead.id;
              return (
                <div
                  key={lead.id}
                  className="group animate-fadeIn rounded-2xl bg-white/60 backdrop-blur-sm border border-purple-200/60 transition-all duration-300 hover:bg-white/80 hover:border-violet-300 hover:shadow-lg hover:shadow-violet-200/50 hover:-translate-y-0.5"
                  style={{ animationDelay: `${i * 50}ms`, animationFillMode: "both" }}
                >
                  <button
                    onClick={() => setExpanded(isOpen ? null : lead.id)}
                    className="w-full text-left p-5 outline-none"
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1 min-w-0">
                        <h3 className="text-lg font-semibold text-violet-900 truncate transition-colors duration-200 group-hover:text-violet-700">
                          {lead.name}
                        </h3>
                        {lead.website && (
                          <a
                            href={lead.website}
                            target="_blank"
                            rel="noopener noreferrer"
                            onClick={(e) => e.stopPropagation()}
                            className="mt-1 inline-flex items-center gap-1.5 text-sm text-violet-500 hover:text-violet-700 transition-colors truncate max-w-full"
                          >
                            <svg className="size-3.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
                            </svg>
                            {lead.website.replace(/^https?:\/\//, "")}
                          </a>
                        )}
                        {lead.email && (
                          <p className="mt-1 text-sm text-violet-500 truncate">
                            {lead.email}
                          </p>
                        )}
                      </div>
                      <div className="flex items-center gap-2 shrink-0">
                        {lead.email && (
                          <a
                            href={`mailto:${lead.email}`}
                            onClick={(e) => e.stopPropagation()}
                            className="inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold text-white bg-gradient-to-r from-violet-500 to-fuchsia-500 shadow-sm transition-all duration-200 hover:scale-105 hover:shadow-md hover:shadow-violet-300/50"
                          >
                            <svg className="size-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                            </svg>
                            Contact
                          </a>
                        )}
                        <span
                          className={`inline-block rounded-full px-3 py-1 text-xs font-semibold text-white bg-gradient-to-r ${statusColor[lead.status] || "from-zinc-400 to-zinc-500"} shadow-sm transition-all duration-300 group-hover:scale-105`}
                        >
                          {lead.status}
                        </span>
                        <span className="text-xs text-violet-400 font-medium">
                          {new Date(lead.created_at).toLocaleDateString()}
                        </span>
                        <span
                          onClick={(e) => handleDelete(lead.id, e)}
                          className="cursor-pointer size-7 rounded-lg inline-flex items-center justify-center text-violet-400 hover:text-rose-500 hover:bg-rose-50 transition-all duration-200"
                        >
                          <svg className="size-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                          </svg>
                        </span>
                        <svg
                          className={`size-4 text-violet-400 transition-transform duration-300 ${isOpen ? "rotate-180" : ""}`}
                          fill="none"
                          viewBox="0 0 24 24"
                          stroke="currentColor"
                        >
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                        </svg>
                      </div>
                    </div>
                  </button>

                  <div
                    className={`overflow-hidden transition-all duration-300 ease-in-out ${
                      isOpen ? "max-h-96 opacity-100" : "max-h-0 opacity-0"
                    }`}
                  >
                    <div className="px-5 pb-5 pt-0 border-t border-purple-200/40">
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-4">
                        {lead.email && (
                          <div className="flex items-center gap-2 text-sm text-violet-700">
                            <span className="size-7 rounded-lg bg-gradient-to-br from-violet-400 to-fuchsia-400 flex items-center justify-center text-white text-xs shrink-0">@</span>
                            <a href={`mailto:${lead.email}`} className="truncate hover:text-violet-500 transition-colors">{lead.email}</a>
                          </div>
                        )}
                        {lead.phone && (
                          <div className="flex items-center gap-2 text-sm text-violet-700">
                            <span className="size-7 rounded-lg bg-gradient-to-br from-sky-400 to-blue-400 flex items-center justify-center text-white text-xs shrink-0">📞</span>
                            <span>{lead.phone}</span>
                          </div>
                        )}
                        {lead.address && (
                          <div className="flex items-center gap-2 text-sm text-violet-700 sm:col-span-2">
                            <span className="size-7 rounded-lg bg-gradient-to-br from-emerald-400 to-teal-400 flex items-center justify-center text-white text-xs shrink-0">📍</span>
                            <span>{lead.address}</span>
                          </div>
                        )}
                        {!lead.email && !lead.phone && !lead.address && (
                          <p className="text-sm text-violet-400 italic sm:col-span-2">
                            No additional details available
                          </p>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </main>

      <footer className="border-t border-purple-200/40 bg-white/30 backdrop-blur-sm px-6 py-4">
        <div className="max-w-6xl mx-auto text-center text-xs text-violet-400">
          NexusScout AI &mdash; Automated Lead Intelligence
        </div>
      </footer>

    </div>
  );
}
