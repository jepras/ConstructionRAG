import type { NextConfig } from "next";

const withBundleAnalyzer = require('@next/bundle-analyzer')({
  enabled: process.env.ANALYZE === 'true',
});

const nextConfig: NextConfig = {
  output: 'standalone',
  eslint: {
    // Disable ESLint for Docker builds to speed up process
    ignoreDuringBuilds: true,
  },
  typescript: {
    // Disable type checking during builds to speed up process
    ignoreBuildErrors: true,
  },
  experimental: {
    // Enable standalone output for Docker deployment
  },
  async rewrites() {
    return [
      {
        source: "/ingest/static/:path*",
        destination: "https://eu-assets.i.posthog.com/static/:path*",
      },
      {
        source: "/ingest/:path*",
        destination: "https://eu.i.posthog.com/:path*",
      },
    ];
  },
  // This is required to support PostHog trailing slash API requests
  skipTrailingSlashRedirect: true,
};

export default withBundleAnalyzer(nextConfig);
