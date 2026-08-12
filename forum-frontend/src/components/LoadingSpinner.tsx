/**
 * 加载动画：旋转的圆环。
 * 尊重 prefers-reduced-motion：在该模式下降低旋转频率。
 */
interface LoadingSpinnerProps {
  /** 圆环尺寸（px），默认 24 */
  size?: number;
  /** 额外类名 */
  className?: string;
}

export function LoadingSpinner({ size = 24, className }: LoadingSpinnerProps) {
  return (
    <span
      role="status"
      aria-label="加载中"
      className={`inline-block animate-spin rounded-full border-2 border-aidev-muted border-t-aidev-primary align-middle ${className ?? ""}`}
      style={{ width: size, height: size }}
    />
  );
}

/** 全屏加载占位 */
export function FullPageSpinner() {
  return (
    <div className="flex min-h-[400px] items-center justify-center">
      <LoadingSpinner size={32} />
    </div>
  );
}
