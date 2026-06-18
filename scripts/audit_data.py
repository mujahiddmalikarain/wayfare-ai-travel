"""Quick audit of task CSV data for Lisbon and Barcelona."""
from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CITIES = ("lisbon", "barcelona")
TODAY = date.today()
DEFAULT_DAYS = 7
END = TODAY + __import__("datetime").timedelta(days=max(DEFAULT_DAYS - 1, 0))


def parse_date(raw: str | None) -> date | None:
    if not raw:
        return None
    try:
        return date.fromisoformat(raw[:10])
    except ValueError:
        return None


def resolved_path(city: str, name: str) -> Path:
    """Mirror ingestion/config.py city_file() preference."""
    base = DATA / city
    gz, plain = base / f"{name}.csv.gz", base / f"{name}.csv"
    if plain.exists():
        return plain
    if gz.exists():
        return gz
    return gz


def audit_shadow_files(city: str) -> None:
    for kind in ("listings", "calendar", "reviews"):
        plain = DATA / city / f"{kind}.csv"
        gz = DATA / city / f"{kind}.csv.gz"
        if plain.exists() and gz.exists():
            picked = resolved_path(city, kind).name
            print(f"  WARNING: both {kind}.csv and {kind}.csv.gz exist; ingest uses {picked}")


def audit_listings(city: str) -> dict:
    path = DATA / city / "listings.csv"
    total = blank_price = 0
    sample_price = None
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        cols = reader.fieldnames or []
        for row in reader:
            total += 1
            p = (row.get("price") or "").strip()
            if not p:
                blank_price += 1
            elif sample_price is None:
                sample_price = (row["id"], p)
    return {
        "file": path.name,
        "rows": total,
        "cols": len(cols),
        "has_price_col": "price" in cols,
        "blank_price": blank_price,
        "sample": sample_price,
    }


def audit_calendar(city: str) -> dict:
    path = DATA / city / "calendar.csv"
    total = blank_price = in_window = 0
    min_d = max_d = None
    sample = None
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        cols = reader.fieldnames or []
        for row in reader:
            total += 1
            d = parse_date(row.get("date"))
            if d:
                min_d = d if min_d is None or d < min_d else min_d
                max_d = d if max_d is None or d > max_d else max_d
                if TODAY <= d <= END:
                    in_window += 1
            p = (row.get("price") or "").strip() if "price" in cols else None
            if p is not None and not p:
                blank_price += 1
            elif sample is None and p:
                sample = (row["listing_id"], row.get("date"), p)
    return {
        "file": path.name,
        "rows": total,
        "cols": list(cols),
        "has_price_col": "price" in cols,
        "blank_price": blank_price if "price" in cols else "N/A",
        "date_min": min_d,
        "date_max": max_d,
        "in_trim_window": in_window,
        "sample": sample,
    }


def audit_reviews(city: str) -> dict:
    path = DATA / city / "reviews.csv"
    total = blank_text = 0
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        cols = reader.fieldnames or []
        for row in reader:
            total += 1
            if not (row.get("comments") or row.get("text") or "").strip():
                blank_text += 1
    return {"file": path.name, "rows": total, "cols": len(cols), "blank_text": blank_text}


def main() -> None:
    print(f"Data audit  ({DATA})\n")
    for city in CITIES:
        print(f"=== {city.upper()} ===")
        audit_shadow_files(city)
        for kind, fn in [("listings", audit_listings), ("calendar", audit_calendar), ("reviews", audit_reviews)]:
            p = DATA / city / f"{kind}.csv"
            if not p.exists():
                print(f"  {kind}.csv: MISSING")
                continue
            info = fn(city)
            print(f"  {info['file']}:")
            if kind == "listings":
                print(f"    rows={info['rows']:,}  price_col={info['has_price_col']}  blank_price={info['blank_price']:,}")
                print(f"    sample id/price: {info['sample']}")
            elif kind == "calendar":
                print(f"    rows={info['rows']:,}  price_col={info['has_price_col']}  blank_price={info['blank_price']}")
                print(f"    dates: {info['date_min']} -> {info['date_max']}  (trim window rows={info['in_trim_window']:,})")
                print(f"    columns: {', '.join(info['cols'])}")
                print(f"    sample listing/date/price: {info['sample']}")
            else:
                print(f"    rows={info['rows']:,}  blank_text={info['blank_text']:,}")
        print()


if __name__ == "__main__":
    main()
