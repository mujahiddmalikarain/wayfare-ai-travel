/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Listing photos come from arbitrary Airbnb CDNs; allow any https host.
  images: { remotePatterns: [{ protocol: "https", hostname: "**" }] },
};

export default nextConfig;
