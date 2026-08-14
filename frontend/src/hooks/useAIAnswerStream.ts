"use client";

/**
 * AI 答案流式接收 Hook。
 * - 当初始答案处于 generating 状态时，建立 WebSocket 接收流式 token。
 * - 收到 done 后更新完整答案并关闭连接。
 * - WebSocket 异常断开后，自动轮询帖子详情接口兜底获取最终结果。
 * - 提供 reconnect 方法供"重新生成"场景使用。
 */
import { useState, useEffect, useRef, useCallback } from "react";
import type { AIAnswer, WSMessage, PostDetail } from "@/lib/types";
import { apiGet } from "@/lib/api";

interface UseAIAnswerStreamOptions {
  postId: string;
  initialAIAnswer: AIAnswer | null;
}

interface UseAIAnswerStreamReturn {
  aiAnswer: AIAnswer | null;
  isStreaming: boolean;
  error: string | null;
  reconnect: () => void;
}

/** WebSocket 异常断开后的轮询间隔 */
const POLL_INTERVAL_MS = 3000;

/**
 * 构建 WebSocket 地址。
 * 开发环境直连后端 8000 端口（Next.js rewrites 仅代理 HTTP，不代理 WebSocket）；
 * 生产环境使用同源 wss（假设反代已配置）。
 * 优先读取 NEXT_PUBLIC_WS_BASE_URL 环境变量。
 */
function buildWsUrl(postId: string): string {
  const envWsBase = process.env.NEXT_PUBLIC_WS_BASE_URL;
  if (envWsBase) {
    return `${envWsBase}/api/ws/ai-answer/${postId}`;
  }

  if (typeof window === "undefined") return "";

  const { hostname, protocol } = window.location;
  const isDev = hostname === "localhost" || hostname === "127.0.0.1";

  if (isDev) {
    return `ws://localhost:8000/api/ws/ai-answer/${postId}`;
  }

  // 生产环境：同源 wss/ws（由反代转发到后端）
  const wsProtocol = protocol === "https:" ? "wss:" : "ws:";
  return `${wsProtocol}//${window.location.host}/api/ws/ai-answer/${postId}`;
}

/** 创建一个 generating 占位答案（重新生成时使用） */
function createGeneratingPlaceholder(prev: AIAnswer | null): AIAnswer {
  const now = new Date().toISOString();
  return {
    id: "",
    content: "",
    sources: [],
    confidence: "medium",
    retrievalPath: "forum",
    status: "generating",
    modelName: prev?.modelName ?? "",
    tokenUsage: {},
    correctedByReplyId: null,
    promptVersion: prev?.promptVersion ?? "answer-v1",
    myFeedback: null,
    helpfulCount: prev?.helpfulCount ?? 0,
    notHelpfulCount: prev?.notHelpfulCount ?? 0,
    createdAt: prev?.createdAt ?? now,
    updatedAt: now,
  };
}

export function useAIAnswerStream({
  postId,
  initialAIAnswer,
}: UseAIAnswerStreamOptions): UseAIAnswerStreamReturn {
  const [aiAnswer, setAiAnswer] = useState<AIAnswer | null>(initialAIAnswer);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // WebSocket 实例与轮询定时器
  const wsRef = useRef<WebSocket | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // 标记组件是否仍挂载，避免卸载后异步更新状态
  const mountedRef = useRef(true);
  // 当前 postId（供回调与轮询读取最新值）
  const postIdRef = useRef(postId);
  // 记录上一次的 initialAIAnswer 引用，避免重复同步
  const prevInitialRef = useRef(initialAIAnswer);

  /** 清理轮询定时器 */
  const clearPoll = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  /** 关闭 WebSocket 并移除所有监听 */
  const closeWs = useCallback(() => {
    const ws = wsRef.current;
    if (ws) {
      ws.onopen = null;
      ws.onmessage = null;
      ws.onerror = null;
      ws.onclose = null;
      try {
        ws.close();
      } catch {
        // 忽略关闭异常
      }
      wsRef.current = null;
    }
  }, []);

  /** 启动轮询：WebSocket 异常断开后兜底拉取最终答案 */
  const startPolling = useCallback(() => {
    clearPoll();
    pollRef.current = setInterval(async () => {
      if (!mountedRef.current) return;
      try {
        const post = await apiGet<PostDetail>(
          `/api/posts/${postIdRef.current}`
        );
        const answer = post.aiAnswer;
        // 状态不再是 generating 时，更新并停止轮询
        if (answer && answer.status !== "generating") {
          if (mountedRef.current) {
            setAiAnswer(answer);
            setIsStreaming(false);
          }
          clearPoll();
        }
      } catch {
        // 轮询单次失败静默，等待下一轮
      }
    }, POLL_INTERVAL_MS);
  }, [clearPoll]);

  /** 建立 WebSocket 连接 */
  const connect = useCallback(() => {
    if (!mountedRef.current) return;

    // 先清理旧连接与轮询
    closeWs();
    clearPoll();
    setError(null);
    setIsStreaming(true);

    const url = buildWsUrl(postIdRef.current);
    if (!url) return;

    let ws: WebSocket;
    try {
      ws = new WebSocket(url);
    } catch {
      setError("无法建立 WebSocket 连接");
      setIsStreaming(false);
      // 连接创建失败也走轮询兜底
      startPolling();
      return;
    }
    wsRef.current = ws;

    ws.onmessage = (event) => {
      if (!mountedRef.current) return;
      let msg: WSMessage;
      try {
        msg = JSON.parse(event.data as string);
      } catch {
        return;
      }

      switch (msg.type) {
        case "token":
          // 追加流式 token 到当前内容
          setAiAnswer((prev) =>
            prev
              ? { ...prev, content: prev.content + msg.content }
              : prev
          );
          break;
        case "done":
          // 生成完成：用服务端完整内容覆盖，更新来源与置信度
          setAiAnswer((prev) =>
            prev
              ? {
                  ...prev,
                  content: msg.content,
                  sources: msg.sources,
                  confidence: msg.confidence,
                  retrievalPath: msg.retrievalPath,
                  status: "published",
                  updatedAt: new Date().toISOString(),
                }
              : prev
          );
          setIsStreaming(false);
          // 正常关闭（code 1000），onclose 不会触发轮询
          try {
            ws.close(1000, "done");
          } catch {
            // 忽略
          }
          break;
        case "error":
          setError(msg.message);
          setIsStreaming(false);
          try {
            ws.close(1000, "error");
          } catch {
            // 忽略
          }
          break;
      }
    };

    ws.onerror = () => {
      if (!mountedRef.current) return;
      setError("WebSocket 连接出错");
    };

    ws.onclose = (event) => {
      if (!mountedRef.current) return;
      wsRef.current = null;
      // 非正常关闭（code !== 1000）：启动轮询兜底
      if (event.code !== 1000) {
        startPolling();
      } else {
        setIsStreaming(false);
      }
    };
  }, [closeWs, clearPoll, startPolling]);

  /**
   * 重新连接（重新生成场景）。
   * 将答案重置为 generating 占位状态，再建立新的 WebSocket。
   */
  const reconnect = useCallback(() => {
    setAiAnswer((prev) => createGeneratingPlaceholder(prev));
    setError(null);
    connect();
  }, [connect]);

  // 挂载/卸载与 postId 变化时：更新 ref 并清理
  useEffect(() => {
    mountedRef.current = true;
    postIdRef.current = postId;

    return () => {
      mountedRef.current = false;
      closeWs();
      clearPoll();
    };
  }, [postId, closeWs, clearPoll]);

  // initialAIAnswer 变化时同步状态（引用变化才触发）
  useEffect(() => {
    if (prevInitialRef.current === initialAIAnswer) return;
    prevInitialRef.current = initialAIAnswer;

    setAiAnswer(initialAIAnswer);
    setError(null);

    if (initialAIAnswer?.status === "generating") {
      connect();
    } else {
      closeWs();
      clearPoll();
      setIsStreaming(false);
    }
  }, [initialAIAnswer, connect, closeWs, clearPoll]);

  return { aiAnswer, isStreaming, error, reconnect };
}
