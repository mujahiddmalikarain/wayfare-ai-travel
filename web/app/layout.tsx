import type { Metadata } from "next";
import { Bricolage_Grotesque, Inter } from "next/font/google";
import "./globals.css";
import { CitySync } from "@/components/CitySync";
import { GlobalConcierge } from "@/components/GlobalConcierge";

const display = Bricolage_Grotesque({
  subsets: ["latin"],
  weight: ["500", "600", "700"],
  variable: "--font-display",
});
const sans = Inter({ subsets: ["latin"], variable: "--font-sans" });

export const metadata: Metadata = {
  title: "Wayfare — AI travel discovery",
  description: "Find stays with filters, a live map, and an AI concierge.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${display.variable} ${sans.variable}`}>
      <body>
        <CitySync />
        {children}
        <GlobalConcierge />
      </body>
    </html>
  );
}
