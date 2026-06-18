import type {
  DayAvailability,
  Listing,
  NLSearchResponse,
  Quote,
  Review,
  SearchParams,
  SearchResponse,
} from "./types";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function get<T>(path: string, params?: object): Promise<T> {
  const url = new URL(`${BASE}${path}`);
  for (const [k, v] of Object.entries(params ?? {})) {
    if (v == null || v === "") continue;
    if (Array.isArray(v)) v.forEach((item) => url.searchParams.append(k, String(item)));
    else url.searchParams.set(k, String(v));
  }
  const res = await fetch(url.toString());
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json() as Promise<T>;
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json() as Promise<T>;
}

export const api = {
  base: BASE,
  search: (p: SearchParams) => get<SearchResponse>("/api/search", p),
  property: (id: number) => get<Listing>(`/api/properties/${id}`),
  reviews: (
    id: number,
    opts: { language?: string; topic?: string; sentiment?: string; limit?: number } = {},
  ) =>
    get<Review[]>(`/api/properties/${id}/reviews`, {
      language: opts.language,
      topic: opts.topic,
      sentiment: opts.sentiment,
      limit: opts.limit ?? 30,
    }),
  availability: (id: number, start: string, end: string) =>
    get<DayAvailability[]>(`/api/properties/${id}/availability`, { start, end }),
  quote: (id: number, checkin: string, checkout: string) =>
    get<Quote>(`/api/properties/${id}/quote`, { checkin, checkout }),
  nlSearch: (message: string, city?: string) =>
    post<NLSearchResponse>("/api/nl-search", { message, city }),
  compare: (ids: number[]) =>
    post<{ listings: Listing[]; verdict: string }>("/api/batch/compare", { ids }),
};
