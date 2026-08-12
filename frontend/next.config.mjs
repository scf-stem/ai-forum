/** @type {import('next').NextConfig} */
const nextConfig = {
  // 将 /api/* 请求代理到后端 FastAPI 服务，前端无需处理 CORS
  async rewrites() {
    const backendUrl = process.env.BACKEND_URL || "http://localhost:8000";
    return [
      {
        source: "/api/:path*",
        destination: `${backendUrl}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
