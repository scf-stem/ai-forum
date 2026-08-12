/**
 * Weather Lens — 本地代理服务器
 * 功能：
 *   1. 静态服务 weather-app.html
 *   2. 代理 /api/qw/* 到和风天气 API（添加 X-QW-Api-Key Header，绕过浏览器 CORS）
 *
 * 用法：node server.js
 * 访问：http://localhost:8765
 */

const http = require('http');
const https = require('https');
const fs = require('fs');
const path = require('path');
const zlib = require('zlib');

const PORT = 8765;
const ROOT = __dirname;
const INDEX_FILE = path.join(ROOT, 'weather-app.html');

const QW_CONFIG = {
  weatherHost: 'ke78krj838.re.qweatherapi.com',
  geoHost:     'geoapi.qweather.com',
  key: 'b3283a3af2c4454e94077d7805b2d1d5',
};

// 根据路径判断目标 Host（Geo API 与 Weather API 分离）
function resolveHost(targetPath) {
  if (targetPath.startsWith('/v2/city/lookup')) return QW_CONFIG.geoHost;
  return QW_CONFIG.weatherHost;
}

const MIME = { '.html': 'text/html; charset=utf-8', '.js': 'application/javascript', '.css': 'text/css' };

function sendStatic(res, filePath) {
  fs.readFile(filePath, (err, data) => {
    if (err) {
      res.writeHead(500); res.end('Server Error'); return;
    }
    const ext = path.extname(filePath).toLowerCase();
    res.writeHead(200, {
      'Content-Type': MIME[ext] || 'application/octet-stream',
      'Cache-Control': 'no-cache',
    });
    res.end(data);
  });
}

function proxyQWeather(req, res) {
  const proxyPrefix = '/api/qw';
  let targetPath = req.url.substring(proxyPrefix.length) || '/';
  const targetHost = resolveHost(targetPath);

  const options = {
    hostname: targetHost,
    path: targetPath,
    method: 'GET',
    headers: {
      'X-QW-Api-Key': QW_CONFIG.key,
      'User-Agent': 'WeatherLens/1.0',
      'Accept': 'application/json',
      'Accept-Encoding': 'gzip, br',
    },
    timeout: 15000,
  };

  console.log(`[PROXY] ${req.method} → https://${targetHost}${targetPath}`);

  const proxyReq = https.request(options, (proxyRes) => {
    const chunks = [];
    const encoding = proxyRes.headers['content-encoding'];

    let stream = proxyRes;
    if (encoding === 'gzip') {
      stream = proxyRes.pipe(zlib.createGunzip());
    } else if (encoding === 'br') {
      stream = proxyRes.pipe(zlib.createBrotliDecompress());
    }

    stream.on('data', (chunk) => chunks.push(chunk));
    stream.on('end', () => {
      const body = Buffer.concat(chunks).toString('utf-8');
      let responseBody;
      try {
        const parsed = JSON.parse(body);
        responseBody = JSON.stringify(parsed);
      } catch {
        responseBody = body;
      }
      res.writeHead(proxyRes.statusCode, {
        'Content-Type': 'application/json; charset=utf-8',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type',
      });
      res.end(responseBody);
    });
  });

  proxyReq.on('error', (e) => {
    console.error('[PROXY ERROR]', e.message);
    res.writeHead(502, { 'Content-Type': 'application/json; charset=utf-8' });
    res.end(JSON.stringify({ code: 502, message: 'Proxy Error: ' + e.message }));
  });

  proxyReq.on('timeout', () => {
    proxyReq.destroy();
    res.writeHead(504, { 'Content-Type': 'application/json; charset=utf-8' });
    res.end(JSON.stringify({ code: 504, message: 'Gateway Timeout' }));
  });

  proxyReq.end();
}

const server = http.createServer((req, res) => {
  // CORS 预检
  if (req.method === 'OPTIONS') {
    res.writeHead(204, {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
    });
    res.end();
    return;
  }

  const url = new URL(req.url, `http://${req.headers.host}`);

  // 代理路由
  if (url.pathname.startsWith('/api/qw')) {
    const query = url.search || '';
    const combined = url.pathname + query;
    req.url = combined;
    proxyQWeather(req, res);
    return;
  }

  // 根路径 → 首页
  if (url.pathname === '/' || url.pathname === '/index.html') {
    sendStatic(res, INDEX_FILE);
    return;
  }

  // 静态文件
  const filePath = path.join(ROOT, url.pathname);
  fs.access(filePath, fs.constants.F_OK, (err) => {
    if (err) {
      res.writeHead(404); res.end('Not Found'); return;
    }
    sendStatic(res, filePath);
  });
});

server.listen(PORT, () => {
  console.log(`\n╔══════════════════════════════════════════╗`);
  console.log(`║  Weather Lens 代理服务器已启动              ║`);
  console.log(`║  本地访问: http://localhost:${PORT}          ║`);
  console.log(`║  天气API : ${QW_CONFIG.weatherHost}  ║`);
  console.log(`║  地理API : ${QW_CONFIG.geoHost}   ║`);
  console.log(`╚══════════════════════════════════════════╝\n`);
});