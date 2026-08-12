/**
 * 全局 TypeScript 类型定义。
 * 对应后端数据模型，前后端共享同一套字段约定。
 * 字段命名与 PRD 第七章数据模型对齐。
 */

/** 用户角色：P1 开发者 / P2 零基础用户 */
export type UserRole = "developer" | "beginner";

/** 版块层级：入门区 / 深度区 */
export type BoardTier = "entry" | "deep";

/** 帖子类型：提问帖 / 分享帖 */
export type PostType = "question" | "share";

/** 帖子状态 */
export type PostStatus = "draft" | "published" | "archived";

/** 回复类型：补充 / 纠错 / 讨论 */
export type ReplyKind = "supplement" | "correction" | "discussion";

/** 投票方向 */
export type VoteDirection = "up" | "down";

/** 投票/举报目标类型 */
export type TargetType = "post" | "reply";

/** 用户 */
export interface User {
  id: string;
  username: string;
  email: string;
  avatar: string | null;
  role: UserRole;
  techStack: string[];
  bio: string | null;
  createdAt: string;
  lastActiveAt: string;
}

/** 当前登录用户（含敏感字段） */
export interface CurrentUser extends User {
  // 可扩展：通知未读数等
}

/** 版块 */
export interface Board {
  id: string;
  name: string;
  tier: BoardTier;
  description: string;
  sortOrder: number;
  postCount: number;
  followerCount: number;
  createdAt: string;
}

/** 帖子列表项（精简，用于 Feed 与列表） */
export interface PostListItem {
  id: string;
  title: string;
  type: PostType;
  tags: string[];
  voteCount: number;
  viewCount: number;
  replyCount: number;
  isFolded: boolean;
  createdAt: string;
  updatedAt: string;
  author: Pick<User, "id" | "username" | "avatar">;
  board: Pick<Board, "id" | "name" | "tier">;
}

/** 帖子详情 */
export interface PostDetail extends PostListItem {
  authorId: string;
  boardId: string;
  content: string;
  status: PostStatus;
  /** 当前用户对该帖子的投票方向（未登录或未投时为 null） */
  myVote: VoteDirection | null;
}

/** 回复 */
export interface Reply {
  id: string;
  postId: string;
  parentId: string | null;
  authorId: string;
  content: string;
  kind: ReplyKind;
  voteCount: number;
  isAccepted: boolean;
  isFolded: boolean;
  createdAt: string;
  updatedAt: string;
  author: Pick<User, "id" | "username" | "avatar">;
  /** 子回复（二级回复） */
  children?: Reply[];
  /** 当前用户对该回复的投票方向 */
  myVote: VoteDirection | null;
}

/** 分页响应 */
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
  hasMore: boolean;
}

/** 认证响应 */
export interface AuthResponse {
  accessToken: string;
  refreshToken: string;
  user: User;
}

/** 统一 API 错误结构 */
export interface ApiError {
  detail: string;
  code?: string;
}
