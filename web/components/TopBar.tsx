"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Heart, Scale, Sparkles } from "lucide-react";
import { useApp } from "@/lib/store";

const CITIES = ["Lisbon", "Barcelona"];

export function TopBar() {
  const city = useApp((s) => s.city);
  const setCity = useApp((s) => s.setCity);
  const wishlistCount = useApp((s) => Object.keys(s.wishlist).length);
  const compareCount = useApp((s) => s.compare.length);
  const setConcierge = useApp((s) => s.setConcierge);
  const router = useRouter();
  const pathname = usePathname();

  const pickCity = (next: string) => {
    if (next === city) return;
    setCity(next);
    useApp.getState().setBounds(null);
    const href = `/search?city=${next}`;
    if (pathname === "/search") router.replace(href, { scroll: false });
    else router.push(href);
  };

  return (
    <header className="sticky top-0 z-30 border-b border-line bg-surface/90 backdrop-blur">
      <div className="mx-auto flex h-14 max-w-[1600px] items-center gap-4 px-4">
        <Link href="/search?city=Lisbon" className="font-display text-lg font-700 text-brand">
          Wayfare
        </Link>

        <nav className="flex items-center gap-1 rounded-full border border-line p-0.5">
          {CITIES.map((c) => (
            <button
              key={c}
              type="button"
              onClick={() => pickCity(c)}
              className={`rounded-full px-3 py-1 text-sm transition ${
                city === c
                  ? "bg-brand font-600 text-white"
                  : "text-muted hover:text-ink"
              }`}
            >
              {c}
            </button>
          ))}
        </nav>

        <span className="hidden text-sm text-muted md:inline">
          stays, mapped and understood
        </span>
        <div className="ml-auto flex items-center gap-1">
          <Link
            href="/wishlist"
            className="flex items-center gap-1.5 rounded-full px-3 py-1.5 text-sm text-ink hover:bg-brand-soft"
          >
            <Heart size={16} /> {wishlistCount > 0 && <span>{wishlistCount}</span>}
          </Link>
          <Link
            href="/compare"
            className="flex items-center gap-1.5 rounded-full px-3 py-1.5 text-sm text-ink hover:bg-brand-soft"
          >
            <Scale size={16} /> {compareCount > 0 && <span>{compareCount}</span>}
          </Link>
          <button
            onClick={() => setConcierge(true)}
            className="flex items-center gap-1.5 rounded-full bg-brand px-3.5 py-1.5 text-sm font-600 text-white hover:opacity-90"
          >
            <Sparkles size={16} /> Concierge
          </button>
        </div>
      </div>
    </header>
  );
}
