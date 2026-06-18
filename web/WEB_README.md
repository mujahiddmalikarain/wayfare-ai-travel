# Frontend (Next.js)

Booking-style product surface + the streaming AI concierge, talking to the
FastAPI backend.

## Design
- **Palette**: deep blue (trust) + honey amber (the AI/concierge accent) on cool
  paper — deliberately *not* the serif-on-cream default.
- **Type**: Bricolage Grotesque (display) + Inter (UI/data, tabular numerals).
- **Signature**: the concierge's live "thinking" stream — agent steps animate in
  along an amber thread as they arrive over SSE — plus filter chips that fill in
  to show what the AI understood from a natural-language query.

## Run
```bash
npm install
cp .env.example .env.local      # NEXT_PUBLIC_API_URL -> your backend
npm run dev                     # http://localhost:3000
```
The backend (api + db + redis) must be up and seeded first.

## What's here
- `app/search` — filters + NL search bar + **list ↔ map sync** (hover both ways,
  pan filters the list) + concierge dock. MapLibre with clustering + price markers.
- `app/property/[id]` — gallery, AI review summary, aspect bars, amenities,
  embedded map, 30-day availability, filterable reviews, sticky booking card with
  price breakdown → mocked **Reserve** → confirmation.
- `app/wishlist`, `app/compare` — saved stays and a 2–4 side-by-side compare with
  an AI verdict.
- `components/ConciergeDock` — SSE streaming of agent steps, final answer,
  candidate cards, review citations, and itineraries; openable from anywhere.

## Notes
- Map uses tokenless OpenStreetMap raster tiles for the demo; swap to a keyed
  tile provider (MapTiler/Stadia) for production traffic.
- Inside Airbnb ships one photo per listing, so the detail page presents a framed
  hero rather than a faked multi-photo carousel.
