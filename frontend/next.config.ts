import type { NextConfig } from "next";

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
};

export default nextConfig;
