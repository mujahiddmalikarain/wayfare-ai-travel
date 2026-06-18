export interface Listing {
  id: number;
  name: string;
  property_type?: string;
  room_type?: string;
  city: string;
  neighbourhood?: string;
  lat?: number;
  lng?: number;
  price?: number;
  beds?: number;
  bedrooms?: number;
  accommodates?: number;
  amenities?: string[];
  amenities_raw?: string[];
  photo_url?: string;
  rating?: number;
  review_count?: number;
  neighbourhood_price_pct?: number;
  review_summary?: string;
  review_aspects?: Record<string, number | null>;
  host_name?: string;
  similarity?: number;
  rationale?: string;
  distance_m?: number;
}

export interface SearchResponse {
  total: number;
  page: number;
  results: Listing[];
}

export interface NLSearchResponse extends SearchResponse {
  intent: Record<string, unknown>;
  applied_filters: Record<string, unknown>;
}

export interface Review {
  id: number;
  date?: string;
  reviewer?: string;
  rating?: number;
  text: string;
  language?: string;
  aspects?: string[];
  sentiment?: "positive" | "negative" | "neutral";
}

export interface Quote {
  nights: number;
  nightly: number;
  subtotal: number;
  cleaning_fee: number;
  taxes: number;
  total: number;
}

export interface DayAvailability {
  date: string;
  available: boolean;
  price?: number;
}

export interface Highlight {
  claim: string;
  review_ids: number[];
}

export interface ReviewInsight {
  summary: string;
  highlights: Highlight[];
  citations?: Record<string, number>; // review_id -> property_id
}

export interface ItineraryStay {
  day: number;
  property_id: number;
  reason: string;
  nightly_price: number;
}

export interface Itinerary {
  title: string;
  stays: ItineraryStay[];
  total_cost: number;
  notes: string;
}

export type AgentStep = {
  type: "step";
  node: string;
  agent: string;
  summary: string;
  data?: Record<string, unknown>;
};

export type ConciergeResult = {
  type: "result";
  request_id: string;
  answer: string;
  candidates: Listing[];
  review_insights?: ReviewInsight | null;
  itinerary?: Itinerary | null;
};

export interface SearchParams {
  city: string;
  checkin?: string;
  checkout?: string;
  guests?: number;
  adults?: number;
  children?: number;
  rooms?: number;
  min_price?: number;
  max_price?: number;
  min_rating?: number;
  room_type?: string;
  property_type?: string;
  amenities?: string[];
  near_lat?: number;
  near_lng?: number;
  sort?: string;
  page?: number;
  page_size?: number;
}
