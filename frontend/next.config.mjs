/** @type {import('next').NextConfig} */
const nextConfig = {
  ...(process.env.TAURI_BUILD === 'true' ? {
    output: 'export',
    images: {
      unoptimized: true,
    },
  } : {
    async rewrites() {
      return [
        {
          source: '/api/settings/keys/:path*',
          destination: 'http://localhost:8000/api/settings/keys/:path*',
        },
      ];
    },
  })
};

export default nextConfig;
