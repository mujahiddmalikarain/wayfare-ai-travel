"use client";

import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { useApp } from "@/lib/store";
import { TopBar } from "@/components/TopBar";
import { ListingCard } from "@/components/ListingCard";

export default function WishlistPage() {
  const wishlist = useApp((s) => s.wishlist);
  const items = Object.values(wishlist);

  return (
    <>
      <TopBar />
      <div className="mx-auto max-w-3xl px-4 py-6">
        <Link href="/search?city=Lisbon" className="mb-4 inline-flex items-center gap-1.5 text-sm text-muted hover:text-ink">
          <ArrowLeft size={16} /> Back to results
        </Link>
        <h1 className="mb-4 font-display text-2xl font-700">Saved stays</h1>
        {items.length === 0 ? (
          <p className="rounded-xl border border-line p-6 text-center text-sm text-muted">
            Nothing saved yet. Tap the heart on any stay to keep it here.
          </p>
        ) : (
          <div className="space-y-3">
            {items.map((l) => <ListingCard key={l.id} listing={l} />)}
          </div>
        )}
      </div>
    </>
  );
}
