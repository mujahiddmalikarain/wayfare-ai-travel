"use client";

import { Brain, ListChecks, MapPinned, Route, Sparkles } from "lucide-react";
import type { AgentStep } from "@/lib/types";

const ICONS: Record<string, React.ReactNode> = {
  intent: <Brain size={15} />,
  retrieval: <MapPinned size={15} />,
  review: <ListChecks size={15} />,
  itinerary: <Route size={15} />,
};

export function AgentSteps({ steps, live }: { steps: AgentStep[]; live: boolean }) {
  return (
    <ol className="relative ml-2 space-y-3 border-l-2 border-accent/40 pl-5">
      {steps.map((s, i) => (
        <li key={i} className="step-in relative">
          <span className="absolute -left-[27px] flex h-6 w-6 items-center justify-center rounded-full bg-accent-soft text-accent ring-4 ring-surface">
            {ICONS[s.node] ?? <Sparkles size={15} />}
          </span>
          <p className="text-sm font-600 capitalize text-ink">{s.node}</p>
          <p className="text-xs text-muted">{s.summary}</p>
          {s.data?.top != null && (
            <p className="mt-0.5 text-xs text-muted">
              Top: {(s.data.top as string[]).join(", ")}
            </p>
          )}
        </li>
      ))}
      {live && (
        <li className="relative">
          <span className="thread-live absolute -left-[27px] flex h-6 w-6 items-center justify-center rounded-full bg-accent text-white ring-4 ring-surface">
            <Sparkles size={14} />
          </span>
          <p className="text-sm text-muted">Thinking…</p>
        </li>
      )}
    </ol>
  );
}
