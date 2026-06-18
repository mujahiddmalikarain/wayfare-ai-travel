"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { money } from "@/lib/format";
import type { Listing, Quote } from "@/lib/types";

export function BookingCard({ listing }: { listing: Listing }) {
  const router = useRouter();
  const [checkin, setCheckin] = useState("");
  const [checkout, setCheckout] = useState("");
  const [quote, setQuote] = useState<Quote | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    if (!checkin || !checkout || checkout <= checkin) { setQuote(null); return; }
    api.quote(listing.id, checkin, checkout)
      .then((q) => { setQuote(q); setErr(null); })
      .catch(() => { setQuote(null); setErr("Those dates aren't available."); });
  }, [listing.id, checkin, checkout]);

  const reserve = () => {
    const params = new URLSearchParams({
      name: listing.name, checkin, checkout,
      total: String(quote?.total ?? ""), nights: String(quote?.nights ?? ""),
    });
    router.push(`/reserve/confirmation?${params.toString()}`);
  };

  const inputCls = "w-full rounded-lg border border-line px-3 py-2 text-sm outline-none focus:border-brand";

  return (
    <div className="rounded-xl2 border border-line bg-surface p-5 shadow-card">
      <p className="mb-3">
        <span className="tnum text-2xl font-700">{money(listing.price)}</span>
        <span className="text-muted"> / night</span>
      </p>

      <div className="grid grid-cols-2 gap-2">
        <input type="date" value={checkin} className={inputCls} onChange={(e) => setCheckin(e.target.value)} />
        <input type="date" value={checkout} className={inputCls} onChange={(e) => setCheckout(e.target.value)} />
      </div>

      {err && <p className="mt-2 text-sm text-accent">{err}</p>}

      {quote && (
        <dl className="mt-4 space-y-1.5 text-sm">
          <Row label={`${money(quote.nightly)} × ${quote.nights} nights`} value={money(quote.subtotal)} />
          <Row label="Cleaning fee" value={money(quote.cleaning_fee)} />
          <Row label="Taxes & fees" value={money(quote.taxes)} />
          <div className="my-2 border-t border-line" />
          <Row label="Total" value={money(quote.total)} bold />
        </dl>
      )}

      <button onClick={reserve} disabled={!quote}
        className="mt-4 w-full rounded-full bg-brand py-2.5 font-600 text-white transition hover:opacity-90 disabled:opacity-50">
        Reserve
      </button>
      <p className="mt-2 text-center text-xs text-muted">You won't be charged — demo booking.</p>
    </div>
  );
}

function Row({ label, value, bold }: { label: string; value: string; bold?: boolean }) {
  return (
    <div className={`flex justify-between ${bold ? "font-700" : "text-ink/90"}`}>
      <dt>{label}</dt>
      <dd className="tnum">{value}</dd>
    </div>
  );
}
