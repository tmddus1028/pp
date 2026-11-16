import type { NextConfig } from "next";

const api = process.env.API_URL ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  // Browser calls /api/* on this origin; no CORS setup needed on FastAPI.
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${api}/:path*` }];
  },
  // Registration moved into a dialog on /cases; old links would otherwise hit /cases/[id] with id "new".
  async redirects() {
    return [{ source: "/cases/new", destination: "/cases", permanent: false }];
  },
  experimental: {
    // Analysis runs synchronously for up to 10 minutes; the proxy default is 30 s.
    proxyTimeout: 700_000,
  },
};

export default nextConfig;
