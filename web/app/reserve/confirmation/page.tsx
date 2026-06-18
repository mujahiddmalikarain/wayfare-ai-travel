"use client";

import { Suspense } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { CheckCircle2 } from "lucide-react";
import { money } from "@/lib/format";

function Confirmation() {
  const p = useSearchParams();
  return (
    <div className="mx-auto flex min-h-screen max-w-lg flex-col items-center justify-center px-4 text-center">
      <CheckCircle2 size={56} className="text-positive" />
      <h1 className="mt-4 font-display text-2xl font-700">You're booked</h1>
      <p className="mt-1 text-muted">A demo reservation — no payment was taken.</p>

      <div className="mt-6 w-full rounded-xl2 border border-line bg-surface p-5 text-left shadow-card">
        <p className="font-600">{p.get("name")}</p>
        <dl className="mt-3 space-y-1.5 text-sm">
          <div className="flex justify-between"><dt className="text-muted">Check in</dt><dd>{p.get("checkin")}</dd></div>
          <div className="flex justify-between"><dt className="text-muted">Check out</dt><dd>{p.get("checkout")}</dd></div>
          <div className="flex justify-between"><dt className="text-muted">Nights</dt><dd>{p.get("nights")}</dd></div>
          <div className="my-2 border-t border-line" />
          <div className="flex justify-between font-700"><dt>Total</dt><dd className="tnum">{money(Number(p.get("total")))}</dd></div>
        </dl>
      </div>

      <Link href="/search?city=Lisbon" className="mt-6 rounded-full bg-brand px-5 py-2.5 font-600 text-white hover:opacity-90">
        Back to search
      </Link>
    </div>
  );
}

export default function Page() {
  return (
    <Suspense fallback={<div className="p-8 text-muted">Loading…</div>}>
      <Confirmation />
    </Suspense>
  );
}
