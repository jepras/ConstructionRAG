import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: 'standalone',
  experimental: {
    // Enable standalone output for Docker deployment
  },
};

export default nextConfig;
