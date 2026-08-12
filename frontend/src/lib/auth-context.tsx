"use client";

/**
 * 认证状态 Context。
 * 管理全局 currentUser 与 token，支持 SSR 首屏渲染时从 cookie 读取 token。
 * 提供 login / logout / updateUser 方法供页面消费。
 */
import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import {
  apiGet,
  getToken,
  setToken,
  clearToken,
  ApiRequestError,
} from "./api";
import type { User } from "./types";

interface AuthContextValue {
  currentUser: User | null;
  token: string | null;
  /** 是否正在加载用户信息（用于首屏骨架屏判断） */
  loading: boolean;
  /** 登录：写入 token 并拉取用户信息 */
  login: (token: string, user?: User) => Promise<void>;
  /** 登出：清除 token 与用户状态 */
  logout: () => void;
  /** 更新当前用户信息（如编辑个人资料后） */
  updateUser: (user: User) => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

interface AuthProviderProps {
  children: ReactNode;
  /** SSR 首屏渲染时由服务端通过 cookies() 注入的初始 token */
  initialToken?: string | null;
}

export function AuthProvider({
  children,
  initialToken,
}: AuthProviderProps) {
  // 初始 token：优先使用 SSR 注入值，否则客户端挂载后从 cookie 读取
  const [token, setTokenState] = useState<string | null>(initialToken ?? null);
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [loading, setLoading] = useState<boolean>(Boolean(initialToken));

  // 客户端挂载时：若未通过 SSR 注入 token，则从 cookie 读取
  useEffect(() => {
    if (initialToken) return;
    const cookieToken = getToken();
    if (cookieToken) {
      setTokenState(cookieToken);
      setLoading(true);
    }
    // 仅在挂载时执行一次
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // token 变化时拉取当前用户信息
  useEffect(() => {
    if (!token) {
      setCurrentUser(null);
      setLoading(false);
      return;
    }

    let cancelled = false;
    const fetchUser = async () => {
      try {
        const user = await apiGet<User>("/api/users/me");
        if (!cancelled) setCurrentUser(user);
      } catch (err) {
        // 401 表示 token 已失效，清除本地状态
        if (err instanceof ApiRequestError && err.status === 401) {
          clearToken();
          setTokenState(null);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    fetchUser();

    return () => {
      cancelled = true;
    };
  }, [token]);

  /** 登录：持久化 token 并触发用户信息拉取 */
  const login = async (newToken: string, user?: User) => {
    setToken(newToken);
    setTokenState(newToken);
    if (user) {
      setCurrentUser(user);
      setLoading(false);
    } else {
      setLoading(true);
    }
  };

  /** 登出：清除 token 与用户状态 */
  const logout = () => {
    clearToken();
    setTokenState(null);
    setCurrentUser(null);
  };

  /** 更新当前用户信息 */
  const updateUser = (user: User) => {
    setCurrentUser(user);
  };

  const value: AuthContextValue = {
    currentUser,
    token,
    loading,
    login,
    logout,
    updateUser,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

/** 获取认证上下文，未在 Provider 内使用时抛出明确错误 */
export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (ctx === undefined) {
    throw new Error("useAuth 必须在 AuthProvider 内部使用");
  }
  return ctx;
}
