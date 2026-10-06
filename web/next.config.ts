import type { NextConfig } from "next";

const api = process.env.API_URL ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  // Browser calls /api/* on this origin; no CORS setup needed on FastAPI.
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${api}/:path*` }];
  },
  experimental: {
    // Analysis runs synchronously for up to 10 minutes; the proxy default is 30 s.
    proxyTimeout: 700_000,
  },
};

export default nextConfig;
