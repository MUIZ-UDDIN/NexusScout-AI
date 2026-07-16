import { LeadStats } from "@/types/lead";

interface Props {
  stats: LeadStats;
}

const cards = [
  { label: "Total", key: "total" as const, gradient: "from-violet-500 to-purple-500" },
  { label: "Enriched", key: "enriched" as const, gradient: "from-emerald-400 to-teal-500" },
  { label: "Failed", key: "failed" as const, gradient: "from-amber-400 to-orange-500" },
];

export default function StatsBar({ stats }: Props) {
  return (
    <div className="grid grid-cols-3 gap-4 mb-6">
      {cards.map((c) => (
        <div
          key={c.key}
          className="rounded-2xl bg-white/[0.04] border border-white/[0.06] p-4 text-center transition-all duration-200 hover:bg-white/[0.08] hover:border-white/[0.12] hover:shadow-lg hover:shadow-violet-500/5"
        >
          <p className={`text-3xl font-bold bg-gradient-to-r ${c.gradient} bg-clip-text text-transparent`}>
            {stats[c.key]}
          </p>
          <p className="text-sm text-white/50 mt-1 font-medium">{c.label}</p>
        </div>
      ))}
    </div>
  );
}
