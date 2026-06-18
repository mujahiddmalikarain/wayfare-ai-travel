import type { Config } from "tailwindcss";

// Colors are literal hex here (so opacity modifiers like bg-accent/30 work).
// The same values are mirrored as CSS variables in globals.css for hand-written
// CSS (focus ring, map markers) — keep the two in sync.
const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        paper: "#f4f6f9",
        surface: "#ffffff",
        ink: "#16243d",
        muted: "#64707f",
        line: "#e4e8ee",
        brand: "#1f3a5f",
        "brand-soft": "#eaf0f7",
        accent: "#d9883a",
        "accent-soft": "#fbf0e2",
        positive: "#1f9d72",
      },
      fontFamily: {
        display: ["var(--font-display)", "system-ui", "sans-serif"],
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
      },
      fontWeight: {
        "400": "400",
        "500": "500",
        "600": "600",
        "700": "700",
      },
      borderRadius: { xl2: "1.25rem" },
      boxShadow: {
        card: "0 1px 2px rgba(16,36,61,0.04), 0 8px 24px -12px rgba(16,36,61,0.18)",
        dock: "-16px 0 48px -24px rgba(16,36,61,0.35)",
      },
    },
  },
  plugins: [],
};

export default config;
