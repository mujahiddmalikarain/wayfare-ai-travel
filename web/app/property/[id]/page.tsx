"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, Sparkles, Star } from "lucide-react";
import { api } from "@/lib/api";
import { amenityLabel, money, valueBadge } from "@/lib/format";
import type { DayAvailability, Listing } from "@/lib/types";
import { Gallery } from "@/components/Gallery";
import { AspectBars } from "@/components/AspectBars";
import { ReviewSection } from "@/components/ReviewSection";
import { BookingCard } from "@/components/BookingCard";
import { MiniMap } from "@/components/MiniMap";

export default function PropertyPage({ params }: { params: { id: string } }) {
  const id = Number(params.id);
  const [p, setP] = useState<Listing | null>(null);
  const [days, setDays] = useState<DayAvailability[]>([]);
  const [notFound, setNotFound] = useState(false);

  useEffect(() => {
    api.property(id).then(setP).catch(() => setNotFound(true));
    const start = new Date();
    const end = new Date(Date.now() + 30 * 86_400_000);
    api.availability(id, start.toISOString().slice(0, 10), end.toISOString().slice(0, 10))
      .then(setDays).catch(() => setDays([]));
  }, [id]);

  if (notFound) return <Centered>That stay couldn't be found.</Centered>;
  if (!p) return <Centered>Loading…</Centered>;

  const badge = valueBadge(p.neighbourhood_price_pct);
  const amenities = p.amenities ?? [];

  return (
    <div className="mx-auto max-w-5xl px-4 py-6">
      <Link href="/search?city=Lisbon" className="mb-4 inline-flex items-center gap-1.5 text-sm text-muted hover:text-ink">
        <ArrowLeft size={16} /> Back to results
      </Link>

      <Gallery photo={p.photo_url} name={p.name} />

      <div className="mt-5 grid grid-cols-1 gap-8 lg:grid-cols-[minmax(0,1fr)_340px]">
        <div className="space-y-8">
          <header>
            <p className="text-sm text-muted">{p.room_type} · {p.neighbourhood}, {p.city}</p>
            <h1 className="font-display text-2xl font-700">{p.name}</h1>
            <div className="mt-1 flex flex-wrap items-center gap-3 text-sm">
              {p.rating != null && (
                <span className="flex items-center gap-1 font-600">
                  <Star size={15} className="text-accent" fill="currentColor" />
                  {p.rating.toFixed(1)} <span className="font-400 text-muted">· {p.review_count} reviews</span>
                </span>
              )}
              <span className="text-muted">Up to {p.accommodates} guests · {p.bedrooms} bd · {p.beds} beds</span>
              {badge && <span className="rounded-full bg-accent-soft px-2 py-0.5 text-xs font-600 text-accent">{badge}</span>}
            </div>
          </header>

          {p.review_summary && (
            <div className="rounded-xl2 border border-accent/30 bg-accent-soft/50 p-4">
              <p className="mb-1 flex items-center gap-1.5 text-xs font-600 uppercase tracking-wide text-accent">
                <Sparkles size={14} /> What guests say
              </p>
              <p className="text-sm text-ink">{p.review_summary}</p>
            </div>
          )}

          {p.review_aspects && (
            <section>
              <h2 className="mb-3 font-display text-xl font-700">How it rates</h2>
              <AspectBars aspects={p.review_aspects} />
            </section>
          )}

          <section>
            <h2 className="mb-3 font-display text-xl font-700">Amenities</h2>
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
              {amenities.map((a) => (
                <span key={a} className="rounded-lg border border-line px-3 py-2 text-sm">{amenityLabel(a)}</span>
              ))}
            </div>
          </section>

          {p.lat != null && p.lng != null && (
            <section>
              <h2 className="mb-3 font-display text-xl font-700">Where you'll be</h2>
              <MiniMap lat={p.lat} lng={p.lng} />
            </section>
          )}

          {days.length > 0 && (
            <section>
              <h2 className="mb-3 font-display text-xl font-700">Next 30 days</h2>
              <div className="flex flex-wrap gap-1">
                {days.map((d) => (
                  <span key={d.date} title={d.date}
                    className={`h-7 w-7 rounded text-[10px] leading-7 text-center ${
                      d.available ? "bg-positive/15 text-positive" : "bg-line text-muted line-through"
                    }`}>
                    {d.date.slice(8)}
                  </span>
                ))}
              </div>
            </section>
          )}

          <ReviewSection propertyId={id} />
        </div>

        <div className="lg:sticky lg:top-6 lg:self-start">
          <BookingCard listing={p} />
        </div>
      </div>
    </div>
  );
}

function Centered({ children }: { children: React.ReactNode }) {
  return <div className="flex h-[60vh] items-center justify-center text-muted">{children}</div>;
}
