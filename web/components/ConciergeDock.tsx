"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { RefreshCw, Send, Sparkles, X } from "lucide-react";
import { useApp } from "@/lib/store";
import { streamConcierge } from "@/lib/stream";
import { money } from "@/lib/format";
import type { AgentStep, ConciergeResult, Itinerary, Listing } from "@/lib/types";
import { AgentSteps } from "./AgentSteps";

const EXAMPLES = [
  "A quiet 1-bed in Lisbon under €130 with a balcony for late June, and tell me which has the most consistent reviews",
  "Plan a 4-night Barcelona trip for a couple, one mid-range place near the metro and one splurge night with a view, budget €1000, avoid El Raval",
];

export function ConciergeDock({ city }: { city: string }) {
  const open = useApp((s) => s.conciergeOpen);
  const setOpen = useApp((s) => s.setConcierge);
  const [text, setText] = useState("");
  const [steps, setSteps] = useState<AgentStep[]>([]);
  const [result, setResult] = useState<ConciergeResult | null>(null);
  const [itinerary, setItinerary] = useState<Itinerary | null>(null);
  const [running, setRunning] = useState(false);
  const abort = useRef<AbortController | null>(null);

  // Keep an editable copy of the itinerary so stays can be swapped client-side.
  useEffect(() => setItinerary(result?.itinerary ?? null), [result]);

  const candidatesById = new Map((result?.candidates ?? []).map((c) => [c.id, c]));

  function swapStay(index: number) {
    if (!itinerary) return;
    const used = new Set(itinerary.stays.map((s) => s.property_id));
    const pool = (result?.candidates ?? []).filter((c) => !used.has(c.id));
    const next = pool[0];
    if (!next) return;
    const stays = itinerary.stays.map((s, i) =>
      i === index
        ? { ...s, property_id: next.id, nightly_price: next.price ?? s.nightly_price }
        : s,
    );
    const total = Math.round(stays.reduce((sum, s) => sum + (s.nightly_price || 0), 0));
    setItinerary({ ...itinerary, stays, total_cost: total });
  }

  async function ask(message: string) {
    if (!message.trim() || running) return;
    abort.current?.abort();
    abort.current = new AbortController();
    setSteps([]); setResult(null); setItinerary(null); setRunning(true);
    await streamConcierge(message, city, {
      onStep: (s) => setSteps((prev) => [...prev, s]),
      onResult: (r) => setResult(r),
      onError: () => setSteps((prev) => [...prev,
        { type: "step", node: "error", agent: "error", summary: "Something failed — try rephrasing." }]),
      signal: abort.current.signal,
    });
    setRunning(false);
  }

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-40 flex justify-end">
      <button className="flex-1 bg-ink/20" aria-label="Close concierge" onClick={() => setOpen(false)} />
      <section className="flex h-full w-full max-w-md flex-col bg-surface shadow-dock">
        <header className="flex items-center gap-2 border-b border-line px-5 py-4">
          <Sparkles size={18} className="text-accent" />
          <h2 className="font-display text-lg font-700">Concierge</h2>
          <button className="ml-auto text-muted hover:text-ink" onClick={() => setOpen(false)}>
            <X size={20} />
          </button>
        </header>

        <div className="flex-1 space-y-5 overflow-y-auto px-5 py-5">
          {steps.length === 0 && !result && (
            <div className="space-y-2">
              <p className="text-sm text-muted">Ask in plain language. Try:</p>
              {EXAMPLES.map((e) => (
                <button key={e} onClick={() => { setText(e); ask(e); }}
                  className="block w-full rounded-xl border border-line p-3 text-left text-sm text-ink hover:border-brand hover:bg-brand-soft">
                  {e}
                </button>
              ))}
            </div>
          )}

          {steps.length > 0 && <AgentSteps steps={steps} live={running} />}

          {result && (
            <div className="space-y-4">
              {result.answer && (
                <p className="rounded-xl bg-brand-soft p-3 text-sm text-ink">{result.answer}</p>
              )}

              {result.review_insights?.highlights?.length ? (
                <div className="space-y-2">
                  <h3 className="text-xs font-600 uppercase tracking-wide text-muted">Why, from reviews</h3>
                  {result.review_insights.highlights.map((h, i) => (
                    <div key={i} className="rounded-lg border border-line p-2.5 text-sm">
                      <p>{h.claim}</p>
                      <div className="mt-1 flex flex-wrap gap-1">
                        {h.review_ids.map((rid) => {
                          const pid = result.review_insights?.citations?.[String(rid)];
                          const cls =
                            "rounded bg-accent-soft px-1.5 py-0.5 text-[11px] font-600 text-accent";
                          return pid ? (
                            <Link key={rid} href={`/property/${pid}#review-${rid}`}
                              className={`${cls} underline-offset-2 hover:underline`}>
                              review #{rid}
                            </Link>
                          ) : (
                            <span key={rid} className={cls}>review #{rid}</span>
                          );
                        })}
                      </div>
                    </div>
                  ))}
                </div>
              ) : null}

              {itinerary?.stays?.length ? (
                <div className="space-y-2">
                  <h3 className="text-xs font-600 uppercase tracking-wide text-muted">
                    {itinerary.title} · {money(itinerary.total_cost)}
                  </h3>
                  {itinerary.stays.map((st, i) => {
                    const c = candidatesById.get(st.property_id) as Listing | undefined;
                    return (
                      <div key={i} className="rounded-lg border border-line p-2.5 text-sm">
                        <div className="flex items-center justify-between gap-2">
                          <Link href={`/property/${st.property_id}`} className="min-w-0 hover:underline">
                            <span className="font-600">Day {st.day}</span>
                            {c?.name ? <span className="block truncate">{c.name}</span> : null}
                          </Link>
                          <div className="flex shrink-0 items-center gap-2">
                            <span className="tnum font-700">{money(st.nightly_price)}</span>
                            <button onClick={() => swapStay(i)} title="Swap this stay"
                              className="rounded-full p-1 text-muted hover:bg-brand-soft hover:text-brand">
                              <RefreshCw size={14} />
                            </button>
                          </div>
                        </div>
                        <p className="mt-0.5 text-xs text-muted">{st.reason}</p>
                      </div>
                    );
                  })}
                </div>
              ) : null}

              {result.candidates?.length > 0 && (
                <div className="space-y-2">
                  <h3 className="text-xs font-600 uppercase tracking-wide text-muted">Matching stays</h3>
                  {result.candidates.slice(0, 6).map((c) => (
                    <Link key={c.id} href={`/property/${c.id}`}
                      onMouseEnter={() => useApp.getState().setHovered(c.id)}
                      onMouseLeave={() => useApp.getState().setHovered(null)}
                      className="flex items-center justify-between rounded-lg border border-line p-2.5 text-sm hover:border-brand">
                      <span className="min-w-0">
                        <span className="block truncate font-600">{c.name}</span>
                        <span className="block truncate text-xs text-muted">{c.rationale ?? c.neighbourhood}</span>
                      </span>
                      <span className="tnum shrink-0 pl-2 font-700">{money(c.price)}</span>
                    </Link>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        <div className="border-t border-line p-3">
          <div className="flex items-center gap-2 rounded-full border border-line px-3 py-1.5 focus-within:border-brand">
            <input value={text} onChange={(e) => setText(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && (ask(text), setText(""))}
              placeholder="Ask the concierge…"
              className="w-full bg-transparent text-sm outline-none placeholder:text-muted" />
            <button onClick={() => { ask(text); setText(""); }} disabled={running}
              className="text-brand disabled:opacity-50" aria-label="Send">
              <Send size={18} />
            </button>
          </div>
        </div>
      </section>
    </div>
  );
}
