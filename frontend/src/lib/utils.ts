/**
 * 通用工具函数：日期格式化、类名拼接、头像处理等。
 */

/** 拼接类名，自动过滤 falsy 值 */
export function cn(...classes: (string | false | null | undefined)[]): string {
  return classes.filter(Boolean).join(" ");
}

/**
 * 将 snake_case 字符串转换为 camelCase。
 * 例如：tech_stack → techStack, vote_count → voteCount, my_vote → myVote
 */
export function snakeToCamel(key: string): string {
  return key.replace(/_([a-z])/g, (_, letter) => letter.toUpperCase());
}

/**
 * 递归地将对象的所有键从 snake_case 转换为 camelCase。
 * 处理嵌套对象和数组。用于前后端数据契约转换（后端 snake_case → 前端 camelCase）。
 */
export function convertToCamelCase<T>(data: unknown): T {
  if (data === null || data === undefined) {
    return data as T;
  }
  if (Array.isArray(data)) {
    return data.map(convertToCamelCase) as T;
  }
  if (typeof data === "object" && data !== null) {
    const converted: Record<string, unknown> = {};
    for (const [key, value] of Object.entries(data as Record<string, unknown>)) {
      converted[snakeToCamel(key)] = convertToCamelCase(value);
    }
    return converted as T;
  }
  return data as T;
}

/** 日期格式化：zh-CN 本地化 */
const dateFormatter = new Intl.DateTimeFormat("zh-CN", {
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
});

/** 日期时间格式化：含时分 */
const dateTimeFormatter = new Intl.DateTimeFormat("zh-CN", {
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
});

/** 格式化为日期字符串 */
export function formatDate(date: string | Date): string {
  const d = typeof date === "string" ? new Date(date) : date;
  if (isNaN(d.getTime())) return "未知时间";
  return dateFormatter.format(d);
}

/** 格式化为日期时间字符串 */
export function formatDateTime(date: string | Date): string {
  const d = typeof date === "string" ? new Date(date) : date;
  if (isNaN(d.getTime())) return "未知时间";
  return dateTimeFormatter.format(d);
}

/** 相对时间格式化：刚刚 / x 分钟前 / x 小时前 / x 天前 / 具体日期 */
export function formatRelativeTime(date: string | Date): string {
  const d = typeof date === "string" ? new Date(date) : date;
  if (isNaN(d.getTime())) return "未知时间";

  const now = Date.now();
  const diff = now - d.getTime();
  const seconds = Math.floor(diff / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);
  const days = Math.floor(hours / 24);

  // 7 天内显示相对时间
  if (seconds < 60) return "刚刚";
  if (minutes < 60) return `${minutes} 分钟前`;
  if (hours < 24) return `${hours} 小时前`;
  if (days < 7) return `${days} 天前`;

  // 超过 7 天显示具体日期
  return formatDate(d);
}

/** 从用户名生成头像背景色（基于字符 hash） */
const AVATAR_COLORS = [
  "#4f46e5", "#059669", "#d97706", "#dc2626",
  "#2563eb", "#7c3aed", "#0891b2", "#db2777",
];

/** 获取头像背景色 */
export function getAvatarColor(username: string): string {
  let hash = 0;
  for (let i = 0; i < username.length; i++) {
    hash = username.charCodeAt(i) + ((hash << 5) - hash);
  }
  return AVATAR_COLORS[Math.abs(hash) % AVATAR_COLORS.length];
}

/** 获取用户名首字母（大写）作为头像 fallback */
export function getInitials(username: string): string {
  return username.charAt(0).toUpperCase();
}

/** 截断数字：1000 → 1k，10000 → 10k */
export function formatCount(count: number): string {
  if (count < 1000) return String(count);
  if (count < 10000) return `${(count / 1000).toFixed(1)}k`;
  return `${Math.floor(count / 1000)}k`;
}

/** 邮箱格式校验 */
export function isValidEmail(email: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

/** 密码强度校验：≥8 位且含字母与数字 */
export function isValidPassword(password: string): boolean {
  return password.length >= 8 && /[a-zA-Z]/.test(password) && /\d/.test(password);
}

/** 用户名校验：2-50 字符 */
export function isValidUsername(username: string): boolean {
  return username.length >= 2 && username.length <= 50;
}
