"use client";

import { Suspense, useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import { useApp } from "@/lib/store";
import { nightsBetween } from "@/lib/format";
import type { Listing, SearchParams } from "@/lib/types";
import { TopBar } from "@/components/TopBar";
import { NLSearchBar } from "@/components/NLSearchBar";
import { FilterRail } from "@/components/FilterRail";
import { ListingCard } from "@/components/ListingCard";
import { ResultsMap } from "@/components/ResultsMap";

function withinBounds(l: Listing, b: ReturnType<typeof useApp.getState>["bounds"]) {
  if (!b || l.lat == null || l.lng == null) return true;
  return l.lng >= b.west && l.lng <= b.east && l.lat >= b.south && l.lat <= b.north;
}

function SearchInner() {
  const city = useApp((s) => s.city);
  const setCity = useApp((s) => s.setCity);

  const [filters, setFilters] = useState<SearchParams>({ city, sort: "popularity", page_size: 24 });
  const [results, setResults] = useState<Listing[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [fitKey, setFitKey] = useState(0);
  const bounds = useApp((s) => s.bounds);

  useEffect(() => {
    setFilters((f) => ({ ...f, city, page: 1 }));
    useApp.getState().setBounds(null);
  }, [city]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    api.search(filters)
      .then((r) => { if (!cancelled) { setResults(r.results); setTotal(r.total); setFitKey((k) => k + 1); } })
      .catch(() => !cancelled && setResults([]))
      .finally(() => !cancelled && setLoading(false));
    return () => { cancelled = true; };
  }, [filters]);

  const patch = (p: Partial<SearchParams>) => {
    if (p.city) setCity(p.city);
    setFilters((f) => ({ ...f, ...p, page: 1 }));
  };
  const nights = nightsBetween(filters.checkin, filters.checkout);
  const visible = useMemo(() => results.filter((l) => withinBounds(l, bounds)), [results, bounds]);

  return (
    <>
      <TopBar />
      <div className="mx-auto max-w-[1600px] px-4 py-4">
        <NLSearchBar city={city} onApply={patch} />
      </div>

      <div className="mx-auto grid max-w-[1600px] grid-cols-1 gap-5 px-4 pb-8 lg:grid-cols-[260px_minmax(0,1fr)_minmax(0,42%)]">
        <div className="hidden lg:block">
          <div className="sticky top-20">
            <FilterRail filters={filters} onChange={patch} />
          </div>
        </div>

        <div>
          <p className="mb-3 text-sm text-muted">
            {loading ? "Searching…" : `${total.toLocaleString()} stays in ${city}`}
            {bounds && visible.length !== results.length && ` · ${visible.length} in view`}
          </p>
          <div className="space-y-3">
            {visible.map((l) => <ListingCard key={l.id} listing={l} nights={nights} />)}
            {!loading && visible.length === 0 && (
              <p className="rounded-xl border border-line p-6 text-center text-sm text-muted">
                No stays match. Widen the map or loosen a filter.
              </p>
            )}
          </div>
          {total > results.length && (
            <button
              onClick={() => setFilters((f) => ({ ...f, page_size: (f.page_size ?? 24) + 24 }))}
              className="mt-5 w-full rounded-full border border-line py-2.5 text-sm font-600 hover:border-brand">
              Show more
            </button>
          )}
        </div>

        <div className="hidden lg:block">
          <div className="sticky top-20 h-[calc(100vh-6rem)]">
            <ResultsMap listings={results} fitKey={String(fitKey)} />
          </div>
        </div>
      </div>
    </>
  );
}

export default function SearchPage() {
  return (
    <Suspense fallback={<div className="p-8 text-muted">Loading…</div>}>
      <SearchInner />
    </Suspense>
  );
}
