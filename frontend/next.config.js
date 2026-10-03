/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: "standalone",
  webpack: (config, { isServer }) => {
    // Handle crypto module for client-side
    if (!isServer) {
      config.resolve.fallback = {
        ...config.resolve.fallback,
        crypto: false, // Disable crypto for client-side
        fs: false, // Disable fs for client-side
        path: false, // Disable path for client-side
        stream: false, // Disable stream for client-side
      };
    }
    return config;
  },
  experimental: {
    serverComponentsExternalPackages: ['better-auth'],
  },
  swcMinify: false, // Disable SWC minification to avoid Unicode issues
};

module.exports = nextConfig;