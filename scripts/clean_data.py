"""Audit and clean Inside Airbnb CSVs with pandas.

Checks schema, dtypes, nulls, price format, date windows, and referential
integrity. Cleaning normalizes prices, fills blanks, trims calendar/reviews,
drops orphan rows, and removes stale .csv.gz shadow files.

Run from repo root:
    python scripts/clean_data.py --audit
    python scripts/clean_data.py --clean
    python scripts/clean_data.py --clean --days 7 --reviews-per-listing 5

Requires: pip install pandas
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CITIES = ("lisbon", "barcelona")

PRICE_RE = re.compile(r"^\$\d{1,3}(,\d{3})*\.\d{2}$|^\$\d+\.\d{2}$")


def resolved_path(city: str, name: str) -> Path:
    """Mirror ingestion/config.py city_file() — plain .csv wins over .csv.gz."""
    base = DATA / city
    gz, plain = base / f"{name}.csv.gz", base / f"{name}.csv"
    if plain.exists():
        return plain
    if gz.exists():
        return gz
    return plain


def remove_stale_gz(city: str, name: str) -> bool:
    gz = DATA / city / f"{name}.csv.gz"
    if gz.exists():
        gz.unlink()
        print(f"  removed stale {city}/{gz.name}")
        return True
    return False


def parse_price_num(raw: object) -> float | None:
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return None
    s = str(raw).strip()
    if not s:
        return None
    cleaned = s.replace("$", "").replace(",", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return None


def fmt_price(value: float) -> str:
    return f"${value:.2f}"


def dummy_price(listing_id: int) -> float:
    cents = 45_00 + (listing_id % 235) * 100 + (listing_id % 97)
    return cents / 100


def _blank_mask(series: pd.Series) -> pd.Series:
    return series.isna() | series.astype(str).str.strip().eq("")


def audit_shadow_files(city: str) -> list[str]:
    warnings: list[str] = []
    for kind in ("listings", "calendar", "reviews"):
        plain = DATA / city / f"{kind}.csv"
        gz = DATA / city / f"{kind}.csv.gz"
        if plain.exists() and gz.exists():
            picked = resolved_path(city, kind).name
            warnings.append(
                f"both {kind}.csv and {kind}.csv.gz exist; ingest uses {picked}"
            )
    return warnings


def audit_city(city: str, *, window_start: date, window_end: date) -> dict:
    report: dict = {"city": city, "files": {}, "warnings": audit_shadow_files(city)}

    listings_path = resolved_path(city, "listings")
    if not listings_path.exists():
        report["warnings"].append("listings file missing")
        return report

    listings = pd.read_csv(listings_path, low_memory=False)
    ids = set(listings["id"].astype("int64"))
    price_blank = _blank_mask(listings["price"]).sum()
    price_bad_fmt = (
        ~listings["price"].astype(str).str.strip().str.match(PRICE_RE, na=False)
        & ~_blank_mask(listings["price"])
    ).sum()
    lat_null = listings["latitude"].isna().sum() if "latitude" in listings.columns else 0

    report["files"]["listings"] = {
        "path": listings_path.name,
        "rows": len(listings),
        "cols": len(listings.columns),
        "dtypes": {c: str(listings[c].dtype) for c in ("id", "price", "latitude", "longitude") if c in listings.columns},
        "blank_price": int(price_blank),
        "nonstandard_price_fmt": int(price_bad_fmt),
        "null_lat": int(lat_null),
        "sample_prices": listings["price"].dropna().head(3).tolist(),
    }

    cal_path = resolved_path(city, "calendar")
    if cal_path.exists():
        cal = pd.read_csv(cal_path, low_memory=False)
        cal["date"] = pd.to_datetime(cal["date"], errors="coerce")
        in_window = cal["date"].between(
            pd.Timestamp(window_start), pd.Timestamp(window_end), inclusive="both"
        ).sum()
        orphan = (~cal["listing_id"].isin(ids)).sum()
        blank_cal_price = (
            _blank_mask(cal["price"]).sum() if "price" in cal.columns else "N/A"
        )
        report["files"]["calendar"] = {
            "path": cal_path.name,
            "rows": len(cal),
            "cols": list(cal.columns),
            "date_min": str(cal["date"].min())[:10] if cal["date"].notna().any() else None,
            "date_max": str(cal["date"].max())[:10] if cal["date"].notna().any() else None,
            "in_window": int(in_window),
            "orphan_listing_ids": int(orphan),
            "blank_price": blank_cal_price,
        }

    rev_path = resolved_path(city, "reviews")
    if rev_path.exists():
        rev = pd.read_csv(rev_path, usecols=["listing_id", "comments"], low_memory=False)
        blank_text = _blank_mask(rev["comments"]).sum()
        orphan_r = (~rev["listing_id"].isin(ids)).sum()
        report["files"]["reviews"] = {
            "path": rev_path.name,
            "rows": len(rev),
            "blank_comments": int(blank_text),
            "orphan_listing_ids": int(orphan_r),
        }

    return report


def print_audit(report: dict) -> None:
    city = report["city"]
    print(f"=== {city.upper()} ===")
    for w in report.get("warnings", []):
        print(f"  WARNING: {w}")
    for kind, info in report.get("files", {}).items():
        print(f"  {info.get('path', kind)}:")
        if kind == "listings":
            print(
                f"    rows={info['rows']:,}  cols={info['cols']}  "
                f"blank_price={info['blank_price']:,}  "
                f"nonstandard_price_fmt={info['nonstandard_price_fmt']:,}  "
                f"null_lat={info['null_lat']:,}"
            )
            print(f"    dtypes: {info['dtypes']}")
            print(f"    sample prices: {info['sample_prices']}")
        elif kind == "calendar":
            print(
                f"    rows={info['rows']:,}  dates={info['date_min']} -> {info['date_max']}  "
                f"in_window={info['in_window']:,}  orphan_ids={info['orphan_listing_ids']:,}  "
                f"blank_price={info['blank_price']}"
            )
            print(f"    columns: {', '.join(info['cols'])}")
        else:
            print(
                f"    rows={info['rows']:,}  blank_comments={info['blank_comments']:,}  "
                f"orphan_ids={info['orphan_listing_ids']:,}"
            )
    print()


def clean_listings(city: str) -> tuple[int, int]:
    path = DATA / city / "listings.csv"
    df = pd.read_csv(path, low_memory=False)

    nums = df["price"].map(parse_price_num)
    blank = nums.isna()
    filled = int(blank.sum())
    if filled:
        df.loc[blank, "price"] = df.loc[blank, "id"].astype(int).map(
            lambda i: fmt_price(dummy_price(i))
        )
        nums = df["price"].map(parse_price_num)

    canonical = nums.map(lambda n: fmt_price(n) if n is not None else None)
    normalized = int((df["price"] != canonical) & canonical.notna()).sum()
    df["price"] = canonical.where(canonical.notna(), df["price"])

    tmp = path.with_suffix(".csv.tmp")
    df.to_csv(tmp, index=False)
    tmp.replace(path)
    remove_stale_gz(city, "listings")
    return filled, normalized


def clean_calendar(
    city: str,
    *,
    listing_prices: dict[int, float],
    valid_ids: set[int],
    start: date,
    end: date,
) -> tuple[int, int]:
    path = DATA / city / "calendar.csv"
    df = pd.read_csv(path, low_memory=False)
    before = len(df)

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df[df["listing_id"].isin(valid_ids)]
    df = df[df["date"].between(pd.Timestamp(start), pd.Timestamp(end), inclusive="both")]

    if "price" not in df.columns:
        df["price"] = None

    blank = _blank_mask(df["price"])
    filled = 0
    if blank.any():
        pid = df.loc[blank, "listing_id"].astype(int)
        df.loc[blank, "price"] = pid.map(
            lambda i: fmt_price(listing_prices.get(i, dummy_price(i)))
        )
        filled = int(blank.sum())

    nums = df["price"].map(parse_price_num)
    df["price"] = nums.map(lambda n: fmt_price(n) if n is not None else None)

    df["date"] = df["date"].dt.strftime("%Y-%m-%d")
    tmp = path.with_suffix(".csv.tmp")
    df.to_csv(tmp, index=False)
    tmp.replace(path)
    remove_stale_gz(city, "calendar")
    return before, len(df)


def clean_reviews(city: str, *, valid_ids: set[int], cap: int) -> tuple[int, int]:
    path = DATA / city / "reviews.csv"
    df = pd.read_csv(path, low_memory=False)
    before = len(df)

    df = df[df["listing_id"].isin(valid_ids)]
    df = df[~_blank_mask(df["comments"])]

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.sort_values(["listing_id", "date"], ascending=[True, False])
    df = df.groupby("listing_id", sort=False).head(cap)
    df["date"] = df["date"].dt.strftime("%Y-%m-%d")

    tmp = path.with_suffix(".csv.tmp")
    df.to_csv(tmp, index=False)
    tmp.replace(path)
    remove_stale_gz(city, "reviews")
    return before, len(df)


def load_listing_prices(city: str) -> dict[int, float]:
    df = pd.read_csv(DATA / city / "listings.csv", usecols=["id", "price"], low_memory=False)
    prices: dict[int, float] = {}
    for _, row in df.iterrows():
        pid = int(row["id"])
        num = parse_price_num(row["price"])
        prices[pid] = num if num is not None else dummy_price(pid)
    return prices


def run_audit(*, days: int) -> None:
    start = date.today()
    end = start + timedelta(days=max(days - 1, 0))
    print(f"Data audit  ({DATA})")
    print(f"Calendar window: {start} -> {end} ({days} day(s), inclusive)\n")
    for city in CITIES:
        report = audit_city(city, window_start=start, window_end=end)
        print_audit(report)


def run_clean(*, days: int, reviews_per_listing: int) -> None:
    start = date.today()
    end = start + timedelta(days=max(days - 1, 0))
    print(f"Cleaning data in {DATA}")
    print(f"Calendar window: {start} -> {end}  |  reviews cap: {reviews_per_listing}/listing\n")

    total_cal_before = total_cal_after = 0
    total_rev_before = total_rev_after = 0

    for city in CITIES:
        listings_path = DATA / city / "listings.csv"
        if not listings_path.exists():
            print(f"skip {city}: no listings.csv", file=sys.stderr)
            continue

        filled, normalized = clean_listings(city)
        print(f"{city} listings: filled {filled:,} blank prices, normalized {normalized:,} formats")

        prices = load_listing_prices(city)
        valid_ids = set(prices.keys())

        cal_path = DATA / city / "calendar.csv"
        if cal_path.exists():
            before, after = clean_calendar(
                city,
                listing_prices=prices,
                valid_ids=valid_ids,
                start=start,
                end=end,
            )
            total_cal_before += before
            total_cal_after += after
            print(f"{city} calendar: {before:,} -> {after:,} rows")

        rev_path = DATA / city / "reviews.csv"
        if rev_path.exists():
            before, after = clean_reviews(city, valid_ids=valid_ids, cap=reviews_per_listing)
            total_rev_before += before
            total_rev_after += after
            print(f"{city} reviews: {before:,} -> {after:,} rows")

    print(f"\nTotal calendar: {total_cal_before:,} -> {total_cal_after:,}")
    print(f"Total reviews:  {total_rev_before:,} -> {total_rev_after:,}")
    print("\nPost-clean audit:")
    run_audit(days=days)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--audit", action="store_true", help="audit only (default if no --clean)")
    p.add_argument("--clean", action="store_true", help="clean CSVs then re-audit")
    p.add_argument("--days", type=int, default=7, help="calendar forward window (default 7)")
    p.add_argument(
        "--reviews-per-listing",
        type=int,
        default=5,
        help="max reviews per listing when cleaning (default 5)",
    )
    args = p.parse_args()

    if args.clean:
        run_clean(days=args.days, reviews_per_listing=args.reviews_per_listing)
    else:
        run_audit(days=args.days)


if __name__ == "__main__":
    main()
