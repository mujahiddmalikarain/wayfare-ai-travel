"use client";

import { useState } from "react";
import { Search, Sparkles, X } from "lucide-react";
import { api } from "@/lib/api";
import { amenityLabel } from "@/lib/format";
import type { SearchParams } from "@/lib/types";

interface Props {
  city: string;
  onApply: (filters: Partial<SearchParams>) => void;
}

/** Free-text search that parses into structured filters and shows the chips
 *  the AI understood — the user always sees what was applied. */
export function NLSearchBar({ city, onApply }: Props) {
  const [text, setText] = useState("");
  const [chips, setChips] = useState<{ key: string; label: string }[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run() {
    if (!text.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const res = await api.nlSearch(text, city);
      const intent = res.intent as Record<string, unknown>;
      const next: { key: string; label: string }[] = [];
      if (intent.city) next.push({ key: "city", label: String(intent.city) });
      if (intent.max_price) next.push({ key: "max_price", label: `≤ €${intent.max_price}` });
      if (intent.room_type) next.push({ key: "room_type", label: String(intent.room_type) });
      if (intent.guests) next.push({ key: "guests", label: `${intent.guests} guests` });
      for (const a of (intent.amenities as string[]) ?? [])
        next.push({ key: `am-${a}`, label: amenityLabel(a) });
      for (const p of (intent.soft_preferences as string[]) ?? [])
        next.push({ key: `pref-${p}`, label: p });
      setChips(next);
      onApply(res.applied_filters as Partial<SearchParams>);
    } catch {
      setError("Couldn't parse that — try naming a city, dates, or a budget.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="w-full">
      <div className="flex items-center gap-2 rounded-full border border-line bg-surface px-4 py-2 shadow-card focus-within:border-brand">
        <Sparkles size={18} className="shrink-0 text-accent" />
        <input
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && run()}
          placeholder='Try: "quiet 1-bed under €130 with a balcony for late June"'
          className="w-full bg-transparent text-sm outline-none placeholder:text-muted"
        />
        <button
          onClick={run}
          disabled={loading}
          className="flex shrink-0 items-center gap-1.5 rounded-full bg-brand px-4 py-1.5 text-sm font-600 text-white disabled:opacity-60"
        >
          <Search size={15} /> {loading ? "Reading…" : "Search"}
        </button>
      </div>

      {error && <p className="mt-2 px-2 text-sm text-accent">{error}</p>}

      {chips.length > 0 && (
        <div className="mt-2 flex flex-wrap items-center gap-1.5 px-1">
          <span className="text-xs font-600 uppercase tracking-wide text-muted">
            Understood
          </span>
          {chips.map((c) => (
            <span
              key={c.key}
              className="step-in flex items-center gap-1 rounded-full bg-accent-soft px-2.5 py-1 text-xs font-600 text-accent"
            >
              {c.label}
            </span>
          ))}
          <button
            onClick={() => setChips([])}
            className="ml-1 text-muted hover:text-ink"
            aria-label="Clear understood filters"
          >
            <X size={14} />
          </button>
        </div>
      )}
    </div>
  );
}
