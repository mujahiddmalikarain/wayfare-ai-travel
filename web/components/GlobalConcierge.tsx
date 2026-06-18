"use client";

import { Sparkles } from "lucide-react";
import { useApp } from "@/lib/store";
import { ConciergeDock } from "./ConciergeDock";

/**
 * Mounts the concierge on every page and adds a floating launcher, so it's
 * reachable even from pages without the TopBar (property, confirmation).
 */
export function GlobalConcierge() {
  const open = useApp((s) => s.conciergeOpen);
  const setOpen = useApp((s) => s.setConcierge);
  const city = useApp((s) => s.city);

  return (
    <>
      {!open && (
        <button
          onClick={() => setOpen(true)}
          aria-label="Open concierge"
          className="fixed bottom-5 right-5 z-30 flex items-center gap-2 rounded-full bg-brand px-4 py-3 text-sm font-600 text-white shadow-dock hover:opacity-90"
        >
          <Sparkles size={18} /> Concierge
        </button>
      )}
      <ConciergeDock city={city} />
    </>
  );
}
