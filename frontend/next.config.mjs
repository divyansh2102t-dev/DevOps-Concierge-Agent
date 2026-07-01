/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    return [
      {
        source: '/api/settings/keys/:path*',
        destination: 'http://localhost:8000/api/settings/keys/:path*',
      },
    ];
  },
};

export default nextConfig;
