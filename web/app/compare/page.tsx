"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, Sparkles, Star } from "lucide-react";
import { api } from "@/lib/api";
import { useApp } from "@/lib/store";
import { amenityLabel, money } from "@/lib/format";
import type { Listing } from "@/lib/types";
import { TopBar } from "@/components/TopBar";

export default function ComparePage() {
  const ids = useApp((s) => s.compare);
  const toggleCompare = useApp((s) => s.toggleCompare);
  const [listings, setListings] = useState<Listing[]>([]);
  const [verdict, setVerdict] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (ids.length < 2) { setListings([]); setVerdict(""); return; }
    setLoading(true);
    api.compare(ids)
      .then((r) => { setListings(r.listings); setVerdict(r.verdict); })
      .finally(() => setLoading(false));
  }, [ids]);

  const allAmenities = Array.from(new Set(listings.flatMap((l) => l.amenities ?? [])));

  return (
    <>
      <TopBar />
      <div className="mx-auto max-w-5xl px-4 py-6">
        <Link href="/search?city=Lisbon" className="mb-4 inline-flex items-center gap-1.5 text-sm text-muted hover:text-ink">
          <ArrowLeft size={16} /> Back to results
        </Link>
        <h1 className="mb-4 font-display text-2xl font-700">Compare stays</h1>

        {ids.length < 2 ? (
          <p className="rounded-xl border border-line p-6 text-center text-sm text-muted">
            Add 2–4 stays with the "Compare" button to see them side by side.
          </p>
        ) : (
          <>
            {(loading || verdict) && (
              <div className="mb-5 rounded-xl2 border border-accent/30 bg-accent-soft/50 p-4">
                <p className="mb-1 flex items-center gap-1.5 text-xs font-600 uppercase tracking-wide text-accent">
                  <Sparkles size={14} /> AI verdict
                </p>
                <p className="text-sm text-ink">{loading ? "Weighing the options…" : verdict}</p>
              </div>
            )}

            <div className="overflow-x-auto">
              <table className="w-full border-collapse text-sm">
                <tbody>
                  <Row label="">
                    {listings.map((l) => (
                      <td key={l.id} className="border border-line p-3 align-top">
                        <div className="aspect-video overflow-hidden rounded-lg bg-brand-soft">
                          {l.photo_url && /* eslint-disable-next-line @next/next/no-img-element */ (
                            <img src={l.photo_url} alt={l.name} className="h-full w-full object-cover" />
                          )}
                        </div>
                        <Link href={`/property/${l.id}`} className="mt-2 block font-600 hover:text-brand">{l.name}</Link>
                        <button onClick={() => toggleCompare(l.id)} className="text-xs text-muted hover:text-accent">Remove</button>
                      </td>
                    ))}
                  </Row>
                  <Row label="Price / night">
                    {listings.map((l) => <Cell key={l.id}><span className="tnum font-700">{money(l.price)}</span></Cell>)}
                  </Row>
                  <Row label="Rating">
                    {listings.map((l) => (
                      <Cell key={l.id}>
                        <span className="flex items-center gap-1">
                          <Star size={13} className="text-accent" fill="currentColor" />
                          {l.rating?.toFixed(1) ?? "—"} <span className="text-muted">({l.review_count})</span>
                        </span>
                      </Cell>
                    ))}
                  </Row>
                  <Row label="Neighbourhood">
                    {listings.map((l) => <Cell key={l.id}>{l.neighbourhood ?? "—"}</Cell>)}
                  </Row>
                  {allAmenities.map((a) => (
                    <Row key={a} label={amenityLabel(a)}>
                      {listings.map((l) => (
                        <Cell key={l.id}>{(l.amenities ?? []).includes(a) ? "✓" : "—"}</Cell>
                      ))}
                    </Row>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>
    </>
  );
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <tr>
      <th className="w-36 border border-line bg-paper p-3 text-left align-top font-600">{label}</th>
      {children}
    </tr>
  );
}
function Cell({ children }: { children: React.ReactNode }) {
  return <td className="border border-line p-3 align-top">{children}</td>;
}
