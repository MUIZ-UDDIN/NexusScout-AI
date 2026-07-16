"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { Lead, LeadStats } from "@/types/lead";
import StatsBar from "@/components/StatsBar";
import SearchBar from "@/components/SearchBar";

const API = "http://localhost:8001";

interface Section {
  id: string;
  name: string;
  search_query: string | null;
  lead_count: number;
}

export default function Home() {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [stats, setStats] = useState<LeadStats>({ total: 0, enriched: 0, failed: 0 });
  const [sections, setSections] = useState<Section[]>([]);
  const [currentSectionId, setCurrentSectionId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [scouting, setScouting] = useState(false);
  const [statusMsg, setStatusMsg] = useState("");
  const [statusProgress, setStatusProgress] = useState(0);
  const [statusTotal, setStatusTotal] = useState(0);
  const [toast, setToast] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [showSearchDropdown, setShowSearchDropdown] = useState(false);
  const [editingSection, setEditingSection] = useState<string | null>(null);
  const [editName, setEditName] = useState("");
  const [scoutingSectionId, setScoutingSectionId] = useState<string | null>(null);
  const [menuSectionId, setMenuSectionId] = useState<string | null>(null);
  const searchRef = useRef<HTMLDivElement>(null);

  const currentSection = sections.find((s) => s.id === currentSectionId);

  const filteredLeads = leads.filter((l) =>
    l.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const fetchSections = useCallback(async () => {
    const res = await fetch(`${API}/api/sections`);
    const data = await res.json();
    setSections(data);
    return data;
  }, []);

  const fetchLeads = useCallback(async (sectionId?: string) => {
    const url = sectionId ? `${API}/api/leads?section_id=${sectionId}` : `${API}/api/leads`;
    const res = await fetch(url);
    const data = await res.json();
    setLeads(data);
  }, []);

  const fetchStats = useCallback(async (sectionId?: string) => {
    const url = sectionId ? `${API}/api/leads/stats?section_id=${sectionId}` : `${API}/api/leads/stats`;
    const res = await fetch(url);
    const data = await res.json();
    setStats(data);
  }, []);

  async function refreshAll() {
    const data = await fetchSections();
    const id = currentSectionId || (data.length > 0 ? data[0].id : null);
    setCurrentSectionId(id);
    await Promise.all([fetchLeads(id ?? undefined), fetchStats(id ?? undefined)]);
  }

  useEffect(() => {
    (async () => {
      const data = await fetchSections();
      const id = data.length > 0 ? data[0].id : null;
      setCurrentSectionId(id);
      await Promise.all([fetchLeads(id ?? undefined), fetchStats(id ?? undefined)]);
      setLoading(false);
    })();
  }, [fetchLeads, fetchStats, fetchSections]);

  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => setToast(null), 4000);
    return () => clearTimeout(t);
  }, [toast]);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (searchRef.current && !searchRef.current.contains(e.target as Node))
        setShowSearchDropdown(false);
    }
    function handleKey(e: KeyboardEvent) {
      if (e.key === "Escape") { setShowSearchDropdown(false); setMenuSectionId(null); }
    }
    document.addEventListener("mousedown", handleClick);
    document.addEventListener("keydown", handleKey);
    return () => { document.removeEventListener("mousedown", handleClick); document.removeEventListener("keydown", handleKey); };
  }, []);

  async function handleScout(query: string, depth: number) {
    setScouting(true);
    setScoutingSectionId(currentSectionId);
    setStatusMsg("Starting...");
    setStatusProgress(0);
    setStatusTotal(0);
    setToast(null);
    try {
      await fetch(`${API}/api/scout`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, depth, section_id: currentSectionId }),
      });
    } catch {
      setScouting(false);
      setScoutingSectionId(null);
      setStatusMsg("");
      setToast("Failed to dispatch scout agent");
    }
  }

  useEffect(() => {
    if (!scouting) return;
    const interval = setInterval(async () => {
      try {
        const res = await fetch(`${API}/api/scout/status`);
        const s = await res.json();
        setStatusMsg(s.message || "");
        setStatusProgress(s.progress || 0);
        setStatusTotal(s.total || 0);
        if (!s.running) {
          setScouting(false);
          setScoutingSectionId(null);
          setStatusMsg("");
          setStatusProgress(0);
          setStatusTotal(0);
          refreshAll();
        }
      } catch {
        // ignore polling errors
      }
    }, 800);
    return () => clearInterval(interval);
  }, [scouting]);

  async function handleContact(lead: Lead, e: React.MouseEvent) {
    e.stopPropagation();
    await fetch(`${API}/api/leads/${lead.id}/contact`, { method: "POST" });
    setLeads((prev) =>
      prev.map((l) => (l.id === lead.id ? { ...l, status: "contacted" } : l))
    );
    setToast(`Contacted ${lead.name}`);
    await fetchStats(currentSectionId ?? undefined);
  }

  async function handleDelete(id: string, e: React.MouseEvent) {
    e.stopPropagation();
    try {
      const res = await fetch(`${API}/api/leads/${id}`, { method: "DELETE" });
      if (!res.ok) { setToast("Failed to delete"); return; }
      setToast("Lead deleted");
      await refreshAll();
    } catch {
      setToast("Network error while deleting");
    }
  }

  async function handleCreateSection() {
    const res = await fetch(`${API}/api/sections`, { method: "POST" });
    const created = await res.json();
    setCurrentSectionId(created.id);
    await fetchSections();
    await Promise.all([fetchLeads(created.id), fetchStats(created.id)]);
  }

  async function handleRenameSection(id: string) {
    if (!editName.trim()) return;
    await fetch(`${API}/api/sections/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: editName }),
    });
    setEditingSection(null);
    await fetchSections();
  }

  async function handleDeleteSection(id: string) {
    await fetch(`${API}/api/sections/${id}`, { method: "DELETE" });
    setCurrentSectionId((prev) => (prev === id ? null : prev));
    await refreshAll();
  }

  const statusColor: Record<string, string> = {
    scouted: "from-sky-500 to-blue-600",
    enriched: "from-emerald-500 to-teal-600",
    failed: "from-amber-500 to-orange-600",
    contacted: "from-violet-500 to-purple-600",
  };

  return (
    <div className="flex flex-col h-screen">
      <header className="shrink-0 border-b border-white/[0.06] bg-white/[0.02] backdrop-blur-md px-6 py-4">
        <div className="max-w-6xl mx-auto flex items-center gap-4">
          <div className="flex items-center gap-3 shrink-0">
            <div className="size-9 rounded-xl bg-gradient-to-br from-violet-600 to-purple-600 flex items-center justify-center text-white font-bold text-sm shadow-lg shadow-violet-500/20 transition-transform duration-300 hover:scale-110">
              N
            </div>
            <h1 className="text-2xl font-bold bg-gradient-to-r from-violet-300 via-purple-300 to-teal-300 bg-clip-text text-transparent">
              NexusScout AI
            </h1>
          </div>
          <div className="flex-1 max-w-md mx-auto relative" ref={searchRef}>
            <svg className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-white/30" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => { setSearchQuery(e.target.value); setShowSearchDropdown(true); }}
              onFocus={() => setShowSearchDropdown(true)}
              placeholder="Search leads..."
              className="w-full rounded-lg border border-white/[0.08] bg-white/[0.04] pl-9 pr-3 py-2 text-sm text-white/70 placeholder-white/30 outline-none transition-all duration-200 focus:border-violet-500/40 focus:bg-white/[0.08]"
            />
            {showSearchDropdown && searchQuery && filteredLeads.length > 0 && (
              <div className="absolute top-full mt-1 left-0 right-0 rounded-xl border border-white/[0.08] bg-zinc-900/95 backdrop-blur-md shadow-2xl shadow-black/40 z-50 max-h-60 overflow-y-auto">
                {filteredLeads.slice(0, 8).map((l) => (
                  <button
                    key={l.id}
                    onClick={() => { setSearchQuery(""); setShowSearchDropdown(false); }}
                    className="w-full text-left px-4 py-2.5 text-sm text-white/70 hover:bg-white/[0.06] transition-colors border-b border-white/[0.04] last:border-0 truncate"
                  >
                    {l.name}
                  </button>
                ))}
              </div>
            )}
          </div>
          <div className="flex items-center gap-3 shrink-0">
            <button
              onClick={refreshAll}
              className="inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold text-white/50 bg-white/[0.04] border border-white/[0.08] transition-all duration-200 hover:bg-white/[0.08] hover:text-white/70"
            >
              <svg className="size-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              Refresh
            </button>
            <span className="text-xs text-white/40 font-medium bg-white/[0.04] px-3 py-1 rounded-full">
              {filteredLeads.length} / {leads.length}
            </span>
          </div>
        </div>
      </header>

      <div className="flex flex-1 min-h-0">
        <aside className="shrink-0 w-56 border-r border-white/[0.06] bg-white/[0.01] overflow-y-auto p-3 flex flex-col gap-1">
          <div className="flex items-center justify-between mb-2 px-2">
            <span className="text-xs font-semibold text-white/40 uppercase tracking-wider">Sections</span>
            <button
              onClick={handleCreateSection}
              className="size-6 rounded-md flex items-center justify-center text-white/40 hover:text-white/70 hover:bg-white/[0.06] transition-all"
              title="New Tab"
            >
              <svg className="size-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
            </button>
          </div>
          {sections.map((s) => (
            <div
              key={s.id}
              className={`group flex items-center gap-2 rounded-lg px-3 py-2 text-sm cursor-pointer transition-all ${
                currentSectionId === s.id
                  ? "bg-violet-500/15 text-violet-300 border border-violet-500/20"
                  : "text-white/60 hover:bg-white/[0.04] border border-transparent"
              }`}
            >
              {editingSection === s.id ? (
                <input
                  value={editName}
                  onChange={(e) => setEditName(e.target.value)}
                  onBlur={() => handleRenameSection(s.id)}
                  onKeyDown={(e) => { if (e.key === "Enter") handleRenameSection(s.id); if (e.key === "Escape") setEditingSection(null); }}
                  className="flex-1 bg-transparent outline-none text-sm text-white/80"
                  autoFocus
                />
              ) : (
                <span
                  className="flex-1 truncate"
                  onClick={async () => { setCurrentSectionId(s.id); await Promise.all([fetchLeads(s.id), fetchStats(s.id)]); }}
                >
                  {s.name}
                </span>
              )}
              <span className="text-xs text-white/30 font-mono">{s.lead_count}</span>
              {editingSection !== s.id && (
                <div className="relative">
                  <button
                    onClick={(e) => { e.stopPropagation(); setMenuSectionId(menuSectionId === s.id ? null : s.id); }}
                    className="size-5 rounded flex items-center justify-center text-white/30 hover:text-white/70 hover:bg-white/[0.06]"
                  >
                    <svg className="size-3.5" fill="currentColor" viewBox="0 0 24 24">
                      <circle cx="12" cy="5" r="1.5" /><circle cx="12" cy="12" r="1.5" /><circle cx="12" cy="19" r="1.5" />
                    </svg>
                  </button>
                  {menuSectionId === s.id && (
                    <>
                      <div className="fixed inset-0 z-10" onClick={() => setMenuSectionId(null)} />
                      <div className="absolute right-0 top-full mt-1 z-20 w-28 rounded-xl border border-white/[0.08] bg-zinc-800/95 backdrop-blur-md shadow-2xl shadow-black/40 overflow-hidden">
                        <button
                          onClick={() => { setEditingSection(s.id); setEditName(s.name); setMenuSectionId(null); }}
                          className="w-full text-left px-3 py-2 text-sm text-white/70 hover:bg-white/[0.06] transition-colors flex items-center gap-2"
                        >
                          <svg className="size-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                          </svg>
                          Rename
                        </button>
                        <button
                          onClick={() => { handleDeleteSection(s.id); setMenuSectionId(null); }}
                          className="w-full text-left px-3 py-2 text-sm text-red-400 hover:bg-red-500/10 transition-colors flex items-center gap-2"
                        >
                          <svg className="size-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                          </svg>
                          Delete
                        </button>
                      </div>
                    </>
                  )}
                </div>
              )}
            </div>
          ))}
        </aside>

        <div className="flex flex-col flex-1 min-h-0">
          <main className="flex-1 overflow-y-auto min-h-0">
            <div className="max-w-4xl mx-auto w-full px-6 pt-4">
              <StatsBar stats={stats} />
            </div>

            <div className="max-w-4xl mx-auto w-full px-6 pb-2">
              {toast && (
                <div className="mb-3 rounded-xl bg-violet-500/10 border border-violet-500/20 px-4 py-3 text-sm text-violet-300 animate-fadeIn text-center">
                  {toast}
                </div>
              )}

              {scouting && statusMsg && currentSectionId === scoutingSectionId && (
                <div className="mb-3 rounded-xl bg-violet-500/10 border border-violet-500/20 px-4 py-3 text-sm text-violet-300 animate-fadeIn flex items-center gap-3">
                  <div className="size-4 rounded-full border-2 border-violet-300/30 border-t-violet-300 animate-spin shrink-0" />
                  <span className="flex-1">{statusMsg}</span>
                  {statusTotal > 0 && (
                    <span className="text-xs text-white/40 font-mono">{statusProgress}/{statusTotal}</span>
                  )}
                  <div className="w-24 h-1.5 rounded-full bg-white/[0.08] overflow-hidden">
                    <div className="h-full rounded-full bg-gradient-to-r from-violet-500 to-purple-500 transition-all duration-300"
                      style={{ width: `${statusTotal > 0 ? (statusProgress / statusTotal) * 100 : 0}%` }}
                    />
                  </div>
                </div>
              )}

              {loading ? (
                <div className="flex items-center justify-center h-64">
                  <div className="size-10 rounded-full border-4 border-violet-500/20 border-t-violet-500 animate-spin" />
                </div>
              ) : !currentSection ? (
                <div className="flex flex-col items-center justify-center h-64 gap-4 text-white/40 animate-fadeIn">
                  <div className="size-16 rounded-2xl bg-white/[0.04] border border-white/[0.06] flex items-center justify-center text-3xl">📂</div>
                  <p className="text-lg font-semibold text-white/60">No section selected</p>
                  <p className="text-sm text-white/40">Create a new tab or scout to get started</p>
                </div>
              ) : leads.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-64 gap-4 text-white/40 animate-fadeIn">
                  <div className="size-16 rounded-2xl bg-white/[0.04] border border-white/[0.06] flex items-center justify-center text-3xl">📡</div>
                  <p className="text-lg font-semibold text-white/60">{currentSection.name}</p>
                  <p className="text-sm text-white/40">Use the search bar below to start scouting</p>
                </div>
              ) : filteredLeads.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-64 gap-4 text-white/40 animate-fadeIn">
                  <div className="size-16 rounded-2xl bg-white/[0.04] border border-white/[0.06] flex items-center justify-center text-3xl">🔍</div>
                  <p className="text-lg font-semibold text-white/60">No leads match &quot;{searchQuery}&quot;</p>
                </div>
              ) : (
                <div className="grid gap-3 pb-2">
                  {filteredLeads.map((lead, i) => {
                    const isOpen = expanded === lead.id;
                    return (
                      <div key={lead.id}
                        className="group animate-fadeIn rounded-2xl bg-white/[0.04] border border-white/[0.06] transition-all duration-300 hover:bg-white/[0.07] hover:border-violet-500/30 hover:shadow-lg hover:shadow-violet-500/5 hover:-translate-y-0.5"
                        style={{ animationDelay: `${i * 50}ms`, animationFillMode: "both" }}
                      >
                        <button onClick={() => setExpanded(isOpen ? null : lead.id)}
                          className="w-full text-left p-5 outline-none"
                        >
                          <div className="flex items-start justify-between gap-4">
                            <div className="flex-1 min-w-0">
                              <h3 className="text-lg font-semibold text-white/80 truncate">{lead.name}</h3>
                              <p className="mt-1 text-xs text-white/30 truncate">Click to see details</p>
                            </div>
                            <div className="flex items-center gap-2 shrink-0">
                              {lead.email && lead.status !== "contacted" && (
                                <span onClick={(e) => handleContact(lead, e)}
                                  className="cursor-pointer inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold text-white bg-gradient-to-r from-violet-600 to-purple-600 shadow-sm transition-all duration-200 hover:from-violet-500 hover:to-purple-500 hover:shadow-lg hover:shadow-violet-500/20"
                                >
                                  <svg className="size-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                                  </svg>
                                  Contact
                                </span>
                              )}
                              <span className={`inline-block rounded-full px-3 py-1 text-xs font-semibold text-white bg-gradient-to-r ${statusColor[lead.status] || "from-zinc-500 to-zinc-600"} shadow-sm`}>
                                {lead.status}
                              </span>
                              <span className="text-xs text-white/40 font-medium">
                                {new Date(lead.created_at).toLocaleDateString()}
                              </span>
                              <span onClick={(e) => handleDelete(lead.id, e)}
                                className="cursor-pointer size-7 rounded-lg inline-flex items-center justify-center text-white/40 hover:text-red-400 hover:bg-red-500/10 transition-all duration-200"
                              >
                                <svg className="size-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                </svg>
                              </span>
                              <svg className={`size-4 text-white/40 transition-transform duration-300 ${isOpen ? "rotate-180" : ""}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                              </svg>
                            </div>
                          </div>
                        </button>

                        <div className={`overflow-hidden transition-all duration-300 ease-in-out ${isOpen ? "max-h-96 opacity-100" : "max-h-0 opacity-0"}`}>
                          <div className="px-5 pb-5 pt-0 border-t border-white/[0.06]">
                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-4">
                              <div className="flex items-center gap-2 text-sm text-white/60">
                                <span className="size-7 rounded-lg bg-gradient-to-br from-amber-500/30 to-orange-500/30 flex items-center justify-center text-white/70 text-xs shrink-0">🌐</span>
                                {lead.website ? (
                                  <a href={lead.website} target="_blank" rel="noopener noreferrer" className="truncate hover:text-violet-300 transition-colors">{lead.website.replace(/^https?:\/\//, "")}</a>
                                ) : <span className="text-white/30">No website exists</span>}
                              </div>
                              <div className="flex items-center gap-2 text-sm text-white/60">
                                <span className="size-7 rounded-lg bg-gradient-to-br from-violet-500/30 to-purple-500/30 flex items-center justify-center text-white/70 text-xs shrink-0">@</span>
                                {lead.email ? (
                                  <a href={`mailto:${lead.email}`} className="truncate hover:text-violet-300 transition-colors">{lead.email}</a>
                                ) : <span className="text-white/30">Email not found</span>}
                              </div>
                              <div className="flex items-center gap-2 text-sm text-white/60">
                                <span className="size-7 rounded-lg bg-gradient-to-br from-sky-500/30 to-blue-500/30 flex items-center justify-center text-white/70 text-xs shrink-0">📞</span>
                                <span className={lead.phone ? "" : "text-white/30"}>{lead.phone || "Phone number not mentioned"}</span>
                              </div>
                              <div className="flex items-center gap-2 text-sm text-white/60">
                                <span className="size-7 rounded-lg bg-gradient-to-br from-teal-500/30 to-emerald-500/30 flex items-center justify-center text-white/70 text-xs shrink-0">📍</span>
                                <span className={lead.address ? "" : "text-white/30"}>{lead.address || "Location not mentioned"}</span>
                              </div>
                            </div>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </main>

          <div className="shrink-0 border-t border-white/[0.06] bg-zinc-900/80 backdrop-blur-md px-6 py-3">
            <div className="max-w-4xl mx-auto w-full">
              <SearchBar onScout={handleScout} scouting={scouting && currentSectionId === scoutingSectionId} />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
