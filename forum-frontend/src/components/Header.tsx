"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { apiGet, apiPost, ApiRequestError } from "@/lib/api";
import { clearToken } from "@/lib/api";
import type { Board } from "@/lib/types";
import { cn, getAvatarColor, getInitials } from "@/lib/utils";

/**
 * 顶部导航：固定高度 64px。
 * 左侧 Logo，中间版块下拉菜单，右侧登录/用户菜单。
 * 响应式：移动端版块菜单折叠为汉堡菜单。
 */

/** 版块列表响应结构 */
interface BoardsResponse {
  entry: Board[];
  deep: Board[];
}

export function Header() {
  const router = useRouter();
  const { currentUser, token, logout } = useAuth();

  const [boards, setBoards] = useState<BoardsResponse | null>(null);
  const [boardsOpen, setBoardsOpen] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [userMenuOpen, setUserMenuOpen] = useState(false);

  const boardsRef = useRef<HTMLDivElement>(null);
  const userMenuRef = useRef<HTMLDivElement>(null);

  // 首次挂载时获取版块列表
  useEffect(() => {
    let cancelled = false;
    apiGet<BoardsResponse>("/api/boards")
      .then((data) => {
        if (!cancelled) setBoards(data);
      })
      .catch(() => {
        // 版块加载失败不阻塞页面
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // 点击外部关闭下拉菜单
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (boardsRef.current && !boardsRef.current.contains(e.target as Node)) {
        setBoardsOpen(false);
      }
      if (userMenuRef.current && !userMenuRef.current.contains(e.target as Node)) {
        setUserMenuOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  /** 登出：调用后端 + 清除本地状态 + 跳转首页 */
  async function handleLogout() {
    try {
      await apiPost("/api/auth/logout", {});
    } catch {
      // 即使后端登出失败也清除本地状态
    }
    clearToken();
    logout();
    setUserMenuOpen(false);
    router.push("/");
  }

  /** 渲染版块列表项 */
  function renderBoardItems(list: Board[]) {
    return list.map((board) => (
      <li key={board.id}>
        <Link
          href={`/boards/${board.id}`}
          className="block rounded-md px-3 py-2 text-sm text-aidev-foreground transition hover:bg-aidev-muted"
          onClick={() => {
            setBoardsOpen(false);
            setMobileMenuOpen(false);
          }}
        >
          <span className="font-medium">{board.name}</span>
          {board.description && (
            <span className="mt-0.5 block text-xs text-aidev-muted-foreground line-clamp-1">
              {board.description}
            </span>
          )}
        </Link>
      </li>
    ));
  }

  return (
    <header className="sticky top-0 z-40 h-header border-b border-aidev-border bg-aidev-card/95 backdrop-blur">
      <div className="mx-auto flex h-full max-w-content items-center justify-between gap-4 px-4">
        {/* 左侧：Logo */}
        <Link
          href="/"
          className="flex items-center gap-2 text-lg font-bold text-aidev-foreground transition hover:text-aidev-primary"
        >
          <span className="inline-flex h-8 w-8 items-center justify-center rounded-md bg-aidev-primary text-sm text-aidev-primary-foreground">
            AI
          </span>
          <span className="hidden sm:inline">AI开发者论坛</span>
        </Link>

        {/* 中间：版块下拉菜单（桌面端） */}
        <nav className="hidden flex-1 items-center justify-center md:flex" aria-label="版块导航">
          <div ref={boardsRef} className="relative">
            <button
              type="button"
              className="flex items-center gap-1 rounded-md px-3 py-2 text-sm font-medium text-aidev-foreground transition hover:bg-aidev-muted"
              onClick={() => setBoardsOpen((v) => !v)}
              aria-expanded={boardsOpen}
              aria-haspopup="true"
            >
              版块
              <span aria-hidden="true" className={cn("transition", boardsOpen && "rotate-180")}>
                ▾
              </span>
            </button>

            {boardsOpen && (
              <div className="absolute left-1/2 top-full mt-1 w-80 -translate-x-1/2 rounded-lg border border-aidev-border bg-aidev-popover p-2 shadow-lg">
                {boards ? (
                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <p className="px-3 py-1 text-xs font-semibold text-aidev-muted-foreground">
                        入门区
                      </p>
                      <ul>{renderBoardItems(boards.entry)}</ul>
                    </div>
                    <div>
                      <p className="px-3 py-1 text-xs font-semibold text-aidev-muted-foreground">
                        深度区
                      </p>
                      <ul>{renderBoardItems(boards.deep)}</ul>
                    </div>
                  </div>
                ) : (
                  <p className="px-3 py-4 text-center text-sm text-aidev-muted-foreground">
                    加载中…
                  </p>
                )}
              </div>
            )}
          </div>
        </nav>

        {/* 右侧：操作区 */}
        <div className="flex items-center gap-2">
          {token && currentUser ? (
            // 已登录：发帖按钮 + 头像下拉菜单
            <>
              <Link
                href="/ask"
                className="hidden items-center rounded-md bg-aidev-primary px-4 py-2 text-sm font-medium text-aidev-primary-foreground shadow-sm transition hover:opacity-90 sm:inline-flex"
              >
                发帖
              </Link>

              <div ref={userMenuRef} className="relative">
                <button
                  type="button"
                  className="flex items-center rounded-full transition hover:opacity-80 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-aidev-ring"
                  onClick={() => setUserMenuOpen((v) => !v)}
                  aria-expanded={userMenuOpen}
                  aria-haspopup="true"
                  aria-label="用户菜单"
                >
                  {currentUser.avatar ? (
                    <img
                      src={currentUser.avatar}
                      alt={currentUser.username}
                      className="h-8 w-8 rounded-full object-cover"
                    />
                  ) : (
                    <span
                      className="inline-flex h-8 w-8 items-center justify-center rounded-full text-sm font-medium text-white"
                      style={{ backgroundColor: getAvatarColor(currentUser.username) }}
                    >
                      {getInitials(currentUser.username)}
                    </span>
                  )}
                </button>

                {userMenuOpen && (
                  <div className="absolute right-0 top-full mt-1 w-48 rounded-lg border border-aidev-border bg-aidev-popover p-2 shadow-lg">
                    <p className="border-b border-aidev-border px-3 py-2 text-sm font-medium text-aidev-foreground">
                      {currentUser.username}
                    </p>
                    <ul className="py-1">
                      <li>
                        <Link
                          href={`/users/${currentUser.username}`}
                          className="block rounded-md px-3 py-2 text-sm text-aidev-foreground transition hover:bg-aidev-muted"
                          onClick={() => setUserMenuOpen(false)}
                        >
                          个人主页
                        </Link>
                      </li>
                      <li>
                        <Link
                          href="/settings"
                          className="block rounded-md px-3 py-2 text-sm text-aidev-foreground transition hover:bg-aidev-muted"
                          onClick={() => setUserMenuOpen(false)}
                        >
                          设置
                        </Link>
                      </li>
                      <li>
                        <button
                          type="button"
                          className="block w-full rounded-md px-3 py-2 text-left text-sm text-aidev-error transition hover:bg-aidev-muted"
                          onClick={handleLogout}
                        >
                          登出
                        </button>
                      </li>
                    </ul>
                  </div>
                )}
              </div>
            </>
          ) : (
            // 未登录：登录/注册按钮
            <Link
              href="/auth"
              className="inline-flex items-center rounded-md bg-aidev-primary px-4 py-2 text-sm font-medium text-aidev-primary-foreground shadow-sm transition hover:opacity-90"
            >
              登录 / 注册
            </Link>
          )}

          {/* 移动端汉堡菜单按钮 */}
          <button
            type="button"
            className="inline-flex h-9 w-9 items-center justify-center rounded-md text-aidev-foreground transition hover:bg-aidev-muted md:hidden"
            onClick={() => setMobileMenuOpen((v) => !v)}
            aria-expanded={mobileMenuOpen}
            aria-label="切换菜单"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              {mobileMenuOpen ? (
                <path d="M6 18L18 6M6 6l12 12" strokeLinecap="round" />
              ) : (
                <path d="M4 6h16M4 12h16M4 18h16" strokeLinecap="round" />
              )}
            </svg>
          </button>
        </div>
      </div>

      {/* 移动端展开菜单 */}
      {mobileMenuOpen && (
        <nav className="border-t border-aidev-border bg-aidev-card px-4 py-3 md:hidden" aria-label="移动端版块导航">
          {token && currentUser && (
            <Link
              href="/ask"
              className="mb-3 block rounded-md bg-aidev-primary px-4 py-2 text-center text-sm font-medium text-aidev-primary-foreground"
              onClick={() => setMobileMenuOpen(false)}
            >
              发帖
            </Link>
          )}
          {boards && (
            <div className="space-y-3">
              <div>
                <p className="mb-1 text-xs font-semibold text-aidev-muted-foreground">入门区</p>
                <ul>{renderBoardItems(boards.entry)}</ul>
              </div>
              <div>
                <p className="mb-1 text-xs font-semibold text-aidev-muted-foreground">深度区</p>
                <ul>{renderBoardItems(boards.deep)}</ul>
              </div>
            </div>
          )}
        </nav>
      )}
    </header>
  );
}
