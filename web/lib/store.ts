import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import type { Listing } from "./types";

interface Bounds {
  west: number;
  south: number;
  east: number;
  north: number;
}

interface AppState {
  // list <-> map sync
  hoveredId: number | null;
  setHovered: (id: number | null) => void;
  bounds: Bounds | null;
  setBounds: (b: Bounds | null) => void;

  // wishlist
  wishlist: Record<number, Listing>;
  toggleWishlist: (l: Listing) => void;

  // compare (2–4)
  compare: number[];
  toggleCompare: (id: number) => void;

  // concierge dock
  conciergeOpen: boolean;
  setConcierge: (open: boolean) => void;

  // active search city (TopBar toggle + search stay in sync)
  city: string;
  setCity: (city: string) => void;
}

export const useApp = create<AppState>()(
  persist(
    (set, get) => ({
      hoveredId: null,
      setHovered: (id) => set({ hoveredId: id }),
      bounds: null,
      setBounds: (b) => set({ bounds: b }),

      wishlist: {},
      toggleWishlist: (l) =>
        set((s) => {
          const next = { ...s.wishlist };
          if (next[l.id]) delete next[l.id];
          else next[l.id] = l;
          return { wishlist: next };
        }),

      compare: [],
      toggleCompare: (id) => {
        const { compare } = get();
        if (compare.includes(id)) set({ compare: compare.filter((x) => x !== id) });
        else if (compare.length < 4) set({ compare: [...compare, id] });
      },

      conciergeOpen: false,
      setConcierge: (open) => set({ conciergeOpen: open }),

      city: "Lisbon",
      setCity: (city) => set({ city }),
    }),
    {
      name: "wayfare",
      storage: createJSONStorage(() => localStorage),
      // Persist only saved/compared selections; transient UI stays in memory.
      partialize: (s) => ({ wishlist: s.wishlist, compare: s.compare }),
    },
  ),
);
