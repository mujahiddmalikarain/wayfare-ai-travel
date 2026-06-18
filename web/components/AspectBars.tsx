"use client";

const ASPECTS = ["cleanliness", "location", "value", "staff", "noise"];

export function AspectBars({ aspects }: { aspects?: Record<string, number | null> }) {
  if (!aspects) return null;
  const present = ASPECTS.filter((a) => aspects[a] != null);
  if (present.length === 0) return null;

  return (
    <div className="grid grid-cols-2 gap-x-6 gap-y-3 sm:grid-cols-3">
      {present.map((a) => {
        const score = aspects[a] as number; // 1–5
        return (
          <div key={a}>
            <div className="mb-1 flex justify-between text-sm">
              <span className="capitalize text-ink">{a}</span>
              <span className="tnum font-600">{score.toFixed(1)}</span>
            </div>
            <div className="h-1.5 rounded-full bg-line">
              <div className="h-full rounded-full bg-brand" style={{ width: `${(score / 5) * 100}%` }} />
            </div>
          </div>
        );
      })}
    </div>
  );
}
