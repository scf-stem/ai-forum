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
  /** 关联的 AI 答案（仅提问帖可能有，无答案时为 null） */
  aiAnswer: AIAnswer | null;
}

/** AI 答案来源标注类型 */
export type AnswerSourceType = "forum" | "docs" | "blog" | "issue";

/** AI 答案来源标注 */
export interface AnswerSource {
  type: AnswerSourceType;
  title: string;
  snippet: string;
  url: string;
  /** 当来源为站内帖子时，记录对应帖子 ID */
  postId?: string | null;
}

/** AI 答案置信度 */
export type AIConfidence = "high" | "medium" | "low";

/** AI 答案检索路径 */
export type AIRetrievalPath = "forum" | "web" | "hybrid";

/** AI 答案状态 */
export type AIAnswerStatus =
  | "generating"
  | "published"
  | "verified"
  | "corrected"
  | "folded";

/** AI 答案 */
export interface AIAnswer {
  id: string;
  content: string;
  sources: AnswerSource[];
  confidence: AIConfidence;
  retrievalPath: AIRetrievalPath;
  status: AIAnswerStatus;
  modelName: string;
  /** token 用量明细，键名由后端决定（如 prompt_tokens、completion_tokens） */
  tokenUsage: Record<string, number>;
  createdAt: string;
  updatedAt: string;
}

/**
 * WebSocket 推送消息（AI 答案流式生成）。
 * - token：增量文本片段
 * - done：生成完成，携带完整内容与来源
 * - error：生成出错
 */
export type WSMessage =
  | { type: "token"; content: string }
  | {
      type: "done";
      content: string;
      sources: AnswerSource[];
      confidence: AIConfidence;
      retrievalPath: AIRetrievalPath;
    }
  | { type: "error"; message: string };

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
