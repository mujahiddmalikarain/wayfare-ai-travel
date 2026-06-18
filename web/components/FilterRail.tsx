"use client";

import { amenityLabel } from "@/lib/format";
import type { SearchParams } from "@/lib/types";

const ROOM_TYPES = ["Entire home/apt", "Private room", "Hotel room", "Shared room"];
const PROPERTY_TYPES = ["Entire rental unit", "Entire condo", "Private room in rental unit", "Entire loft", "Entire serviced apartment"];
const AMENITIES = ["wifi", "kitchen", "parking", "pool", "air_conditioning", "washer", "balcony", "workspace"];
const SORTS = [
  { value: "popularity", label: "Most reviewed" },
  { value: "price", label: "Price: low to high" },
  { value: "rating", label: "Top rated" },
  { value: "distance", label: "Distance" },
];

interface Props {
  filters: SearchParams;
  onChange: (patch: Partial<SearchParams>) => void;
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1.5">
      <label className="text-xs font-600 uppercase tracking-wide text-muted">{label}</label>
      {children}
    </div>
  );
}

export function FilterRail({ filters, onChange }: Props) {
  const toggleAmenity = (a: string) => {
    const set = new Set(filters.amenities ?? []);
    set.has(a) ? set.delete(a) : set.add(a);
    onChange({ amenities: [...set] });
  };

  const inputCls =
    "w-full rounded-lg border border-line bg-surface px-3 py-2 text-sm outline-none focus:border-brand";

  return (
    <aside className="space-y-5">
      <div className="grid grid-cols-2 gap-2">
        <Field label="Check in">
          <input type="date" value={filters.checkin ?? ""} className={inputCls}
            onChange={(e) => onChange({ checkin: e.target.value })} />
        </Field>
        <Field label="Check out">
          <input type="date" value={filters.checkout ?? ""} className={inputCls}
            onChange={(e) => onChange({ checkout: e.target.value })} />
        </Field>
      </div>

      <Field label="Guests">
        <div className="grid grid-cols-3 gap-2">
          {([
            ["adults", "Adults"],
            ["children", "Children"],
            ["rooms", "Rooms"],
          ] as const).map(([key, label]) => (
            <div key={key} className="space-y-1">
              <span className="text-[11px] text-muted">{label}</span>
              <input type="number" min={0} value={filters[key] ?? ""} placeholder="0"
                className={inputCls}
                onChange={(e) => onChange({ [key]: Number(e.target.value) || undefined })} />
            </div>
          ))}
        </div>
      </Field>

      <Field label={`Price per night · €${filters.min_price ?? 20}–€${filters.max_price ?? 1000}`}>
        <div className="space-y-2">
          <div className="flex items-center gap-1.5 text-[11px] text-muted">
            <span className="w-7">min</span>
            <input type="range" min={0} max={1000} step={10} value={filters.min_price ?? 0}
              className="w-full accent-brand"
              onChange={(e) => onChange({ min_price: Number(e.target.value) || undefined })} />
          </div>
          <div className="flex items-center gap-1.5 text-[11px] text-muted">
            <span className="w-7">max</span>
            <input type="range" min={20} max={1000} step={10} value={filters.max_price ?? 1000}
              className="w-full accent-brand"
              onChange={(e) => onChange({ max_price: Number(e.target.value) })} />
          </div>
        </div>
      </Field>

      <Field label="Minimum rating">
        <div className="flex gap-1.5">
          {[0, 4, 4.5, 4.8].map((r) => (
            <button key={r} onClick={() => onChange({ min_rating: r || undefined })}
              className={`flex-1 rounded-lg border px-2 py-1.5 text-sm ${
                (filters.min_rating ?? 0) === r
                  ? "border-brand bg-brand-soft font-600 text-brand"
                  : "border-line text-muted hover:border-brand"
              }`}>
              {r === 0 ? "Any" : `${r}+`}
            </button>
          ))}
        </div>
      </Field>

      <Field label="Room type">
        <select value={filters.room_type ?? ""} className={inputCls}
          onChange={(e) => onChange({ room_type: e.target.value || undefined })}>
          <option value="">Any room type</option>
          {ROOM_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
        </select>
      </Field>

      <Field label="Property type">
        <select value={filters.property_type ?? ""} className={inputCls}
          onChange={(e) => onChange({ property_type: e.target.value || undefined })}>
          <option value="">Any property type</option>
          {PROPERTY_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
        </select>
      </Field>

      <Field label="Amenities">
        <div className="flex flex-wrap gap-1.5">
          {AMENITIES.map((a) => {
            const on = (filters.amenities ?? []).includes(a);
            return (
              <button key={a} onClick={() => toggleAmenity(a)}
                className={`rounded-full border px-2.5 py-1 text-xs ${
                  on ? "border-brand bg-brand-soft font-600 text-brand" : "border-line text-muted hover:border-brand"
                }`}>
                {amenityLabel(a)}
              </button>
            );
          })}
        </div>
      </Field>

      <Field label="Sort by">
        <select value={filters.sort ?? "popularity"} className={inputCls}
          onChange={(e) => onChange({ sort: e.target.value })}>
          {SORTS.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
        </select>
      </Field>
    </aside>
  );
}
