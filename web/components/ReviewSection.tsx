"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Review } from "@/lib/types";

const LANGS = [
  { code: "", label: "All languages" },
  { code: "en", label: "English" },
  { code: "pt", label: "Portuguese" },
  { code: "es", label: "Spanish" },
  { code: "fr", label: "French" },
];
const TOPICS = ["cleanliness", "location", "value", "staff", "noise"];
const SENTIMENTS = [
  { value: "", label: "All" },
  { value: "positive", label: "Positive" },
  { value: "negative", label: "Negative" },
];

const selectCls =
  "rounded-lg border border-line bg-surface px-3 py-1.5 text-sm outline-none focus:border-brand";

export function ReviewSection({ propertyId }: { propertyId: number }) {
  const [reviews, setReviews] = useState<Review[]>([]);
  const [lang, setLang] = useState("");
  const [topic, setTopic] = useState("");
  const [sentiment, setSentiment] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api
      .reviews(propertyId, {
        language: lang || undefined,
        topic: topic || undefined,
        sentiment: sentiment || undefined,
        limit: 30,
      })
      .then(setReviews)
      .finally(() => setLoading(false));
  }, [propertyId, lang, topic, sentiment]);

  return (
    <section>
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <h2 className="font-display text-xl font-700">Reviews</h2>
        <div className="flex flex-wrap gap-2">
          <select value={lang} onChange={(e) => setLang(e.target.value)} className={selectCls}>
            {LANGS.map((l) => <option key={l.code} value={l.code}>{l.label}</option>)}
          </select>
          <select value={topic} onChange={(e) => setTopic(e.target.value)} className={selectCls}>
            <option value="">All topics</option>
            {TOPICS.map((t) => <option key={t} value={t} className="capitalize">{t}</option>)}
          </select>
          <select value={sentiment} onChange={(e) => setSentiment(e.target.value)} className={selectCls}>
            {SENTIMENTS.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
          </select>
        </div>
      </div>

      {loading ? (
        <p className="text-sm text-muted">Loading reviews…</p>
      ) : reviews.length === 0 ? (
        <p className="text-sm text-muted">No reviews match these filters.</p>
      ) : (
        <div className="space-y-4">
          {reviews.map((r) => (
            <article key={r.id} id={`review-${r.id}`} className="border-b border-line pb-4 scroll-mt-20">
              <div className="mb-1 flex flex-wrap items-center gap-2 text-sm">
                <span className="font-600">{r.reviewer ?? "Guest"}</span>
                <span className="text-muted">{r.date}</span>
                {r.language && (
                  <span className="rounded bg-brand-soft px-1.5 py-0.5 text-[11px] uppercase text-brand">
                    {r.language}
                  </span>
                )}
                {r.sentiment && r.sentiment !== "neutral" && (
                  <span className={`rounded px-1.5 py-0.5 text-[11px] capitalize ${
                    r.sentiment === "positive"
                      ? "bg-green-100 text-green-700"
                      : "bg-red-100 text-red-700"
                  }`}>
                    {r.sentiment}
                  </span>
                )}
                {(r.aspects ?? []).map((a) => (
                  <span key={a} className="rounded bg-surface px-1.5 py-0.5 text-[11px] capitalize text-muted ring-1 ring-line">
                    {a}
                  </span>
                ))}
              </div>
              <p className="text-sm leading-relaxed text-ink/90">{r.text}</p>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
