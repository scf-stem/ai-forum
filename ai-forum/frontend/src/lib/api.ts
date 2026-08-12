"use client";

/**
 * API 请求封装。
 * baseURL 为空字符串，所有 /api/* 请求经由 Next.js rewrites 代理到后端，
 * 前端无需处理跨域，也无需在后端配置 CORS（开发态）。
 * 401 时不自动跳转登录，由调用方决定如何处理。
 */

import { convertToCamelCase } from "./utils";

/** Token 在 cookie 中的键名 */
const TOKEN_COOKIE_KEY = "forum_token";

/** 统一 baseURL：走 Next.js 代理 */
const BASE_URL = "";

/** 默认请求超时时间 */
const DEFAULT_TIMEOUT_MS = 15000;

/** 统一请求异常 */
export class ApiRequestError extends Error {
  status: number;
  code?: string;

  constructor(message: string, status: number, code?: string) {
    super(message);
    this.name = "ApiRequestError";
    this.status = status;
    this.code = code;
  }
}

/**
 * 从 cookie 中读取认证 token。
 * 浏览器环境下 document.cookie 可用；SSR 时返回 null。
 */
export function getToken(): string | null {
  if (typeof document === "undefined") return null;

  const match = document.cookie
    .split("; ")
    .find((row) => row.startsWith(`${TOKEN_COOKIE_KEY}=`));
  return match ? decodeURIComponent(match.split("=")[1]) : null;
}

/**
 * 设置 token 到 cookie。
 * @param token 访问令牌
 * @param maxAge 有效期（秒），默认 7 天
 */
export function setToken(token: string, maxAge: number = 7 * 24 * 3600): void {
  if (typeof document === "undefined") return;
  document.cookie = `${TOKEN_COOKIE_KEY}=${encodeURIComponent(
    token
  )}; path=/; max-age=${maxAge}; SameSite=Lax`;
}

/** 清除 token cookie */
export function clearToken(): void {
  if (typeof document === "undefined") return;
  document.cookie = `${TOKEN_COOKIE_KEY}=; path=/; max-age=0; SameSite=Lax`;
}

/** 构建请求头，自动注入 Authorization */
function buildHeaders(customHeaders?: HeadersInit): HeadersInit {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...Object.fromEntries(
      customHeaders instanceof Headers
        ? customHeaders.entries()
        : Object.entries(customHeaders ?? {})
    ),
  };

  const token = getToken();
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  return headers;
}

/** 解析响应：非 2xx 抛出带状态码的异常；成功时将 snake_case 键转为 camelCase */
async function parseResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    // 401 时不自动跳转，由调用方处理
    let detail = `请求失败：${response.status} ${response.statusText}`;
    let code: string | undefined;
    try {
      const errorBody = await response.json();
      detail = errorBody.detail ?? detail;
      code = errorBody.code;
    } catch {
      // 响应体非 JSON，保留默认 detail
    }
    throw new ApiRequestError(detail, response.status, code);
  }

  // 处理无内容响应
  if (response.status === 204) {
    return undefined as T;
  }
  const rawData = await response.json();
  return convertToCamelCase<T>(rawData);
}

/**
 * 核心请求方法：支持超时控制。
 * @param url 请求路径，如 /api/boards
 * @param options fetch 配置
 */
async function request<T>(
  url: string,
  options: RequestInit = {}
): Promise<T> {
  // 超时控制：AbortController 在超时后中止请求
  const controller = new AbortController();
  const timeoutId = setTimeout(
    () => controller.abort(),
    DEFAULT_TIMEOUT_MS
  );

  try {
    const response = await fetch(`${BASE_URL}${url}`, {
      ...options,
      headers: buildHeaders(options.headers),
      signal: controller.signal,
    });
    return await parseResponse<T>(response);
  } finally {
    clearTimeout(timeoutId);
  }
}

/** GET 请求 */
export async function apiGet<T>(
  url: string,
  params?: Record<string, string | number | boolean | undefined>
): Promise<T> {
  let finalUrl = url;
  if (params) {
    // 过滤掉 undefined 值后拼接查询字符串
    const searchParams = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined) {
        searchParams.append(key, String(value));
      }
    });
    const query = searchParams.toString();
    if (query) finalUrl = `${url}?${query}`;
  }
  return request<T>(finalUrl, { method: "GET" });
}

/** POST 请求 */
export async function apiPost<T>(
  url: string,
  body?: unknown
): Promise<T> {
  return request<T>(url, {
    method: "POST",
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
}

/** PATCH 请求 */
export async function apiPatch<T>(
  url: string,
  body?: unknown
): Promise<T> {
  return request<T>(url, {
    method: "PATCH",
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
}

/** DELETE 请求 */
export async function apiDelete<T>(url: string): Promise<T> {
  return request<T>(url, { method: "DELETE" });
}
