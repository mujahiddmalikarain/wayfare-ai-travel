export const money = (n?: number, currency = "EUR") =>
  n == null
    ? "—"
    : new Intl.NumberFormat("en-US", {
        style: "currency",
        currency,
        maximumFractionDigits: 0,
      }).format(n);

export const amenityLabel = (token: string) =>
  token.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());

export const valueBadge = (pct?: number): string | null => {
  if (pct == null) return null;
  if (pct <= 0.25) return "Great value for the area";
  if (pct >= 0.85) return "Premium for the area";
  return null;
};

export const nightsBetween = (a?: string, b?: string): number => {
  if (!a || !b) return 0;
  const ms = new Date(b).getTime() - new Date(a).getTime();
  return Math.max(0, Math.round(ms / 86_400_000));
};
