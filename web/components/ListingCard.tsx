"use client";

import Link from "next/link";
import { Heart, Scale, Star } from "lucide-react";
import { useApp } from "@/lib/store";
import { amenityLabel, money, nightsBetween, valueBadge } from "@/lib/format";
import type { Listing } from "@/lib/types";

interface Props {
  listing: Listing;
  nights?: number;
}

export function ListingCard({ listing, nights = 0 }: Props) {
  const hoveredId = useApp((s) => s.hoveredId);
  const setHovered = useApp((s) => s.setHovered);
  const { wishlist, toggleWishlist, compare, toggleCompare } = useApp();

  const active = hoveredId === listing.id;
  const saved = !!wishlist[listing.id];
  const comparing = compare.includes(listing.id);
  const badge = valueBadge(listing.neighbourhood_price_pct);
  const total = listing.price && nights ? listing.price * nights : undefined;

  return (
    <article
      onMouseEnter={() => setHovered(listing.id)}
      onMouseLeave={() => setHovered(null)}
      className={`group flex gap-3 rounded-xl2 border bg-surface p-3 transition ${
        active ? "border-brand shadow-card" : "border-line hover:shadow-card"
      }`}
    >
      <Link href={`/property/${listing.id}`} className="relative h-28 w-36 shrink-0 overflow-hidden rounded-lg bg-brand-soft">
        {listing.photo_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={listing.photo_url} alt={listing.name}
            className="h-full w-full object-cover transition group-hover:scale-105" />
        ) : (
          <div className="flex h-full items-center justify-center text-xs text-muted">No photo</div>
        )}
      </Link>

      <div className="flex min-w-0 flex-1 flex-col">
        <div className="flex items-start justify-between gap-2">
          <Link href={`/property/${listing.id}`} className="min-w-0">
            <p className="text-xs text-muted">{listing.room_type} · {listing.neighbourhood}</p>
            <h3 className="truncate font-600 text-ink">{listing.name}</h3>
          </Link>
          <button onClick={() => toggleWishlist(listing)} aria-label="Save"
            className={saved ? "text-accent" : "text-muted hover:text-accent"}>
            <Heart size={18} fill={saved ? "currentColor" : "none"} />
          </button>
        </div>

        {badge && (
          <span className="mt-1 w-fit rounded-full bg-accent-soft px-2 py-0.5 text-[11px] font-600 text-accent">
            {badge}
          </span>
        )}

        {listing.rationale && (
          <p className="mt-1 line-clamp-1 text-xs text-muted">{listing.rationale}</p>
        )}

        <div className="mt-auto flex items-end justify-between pt-2">
          <div className="flex items-center gap-3 text-sm">
            {listing.rating != null && (
              <span className="flex items-center gap-1 font-600">
                <Star size={14} className="text-accent" fill="currentColor" />
                {listing.rating.toFixed(1)}
                <span className="font-400 text-muted">({listing.review_count})</span>
              </span>
            )}
            <button onClick={() => toggleCompare(listing.id)}
              className={`flex items-center gap-1 text-xs ${comparing ? "text-brand" : "text-muted hover:text-brand"}`}>
              <Scale size={13} /> {comparing ? "Comparing" : "Compare"}
            </button>
          </div>
          <div className="text-right">
            <p className="tnum font-700 text-ink">{money(listing.price)}<span className="text-sm font-400 text-muted"> /night</span></p>
            {total && <p className="tnum text-xs text-muted">{money(total)} for {nights} nights</p>}
          </div>
        </div>
      </div>
    </article>
  );
}
