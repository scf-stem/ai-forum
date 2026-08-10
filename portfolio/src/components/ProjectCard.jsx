import { useRef } from 'react'

/**
 * ProjectCard · 通用项目卡片
 * props:
 *  - number: "01" | "02" | "03"   (章节号)
 *  - eyebrow: string              (mono 小标签, e.g. "Personal · 2026")
 *  - title: string                (中文名)
 *  - subtitle: string             (英文名/副标题, italic display)
 *  - description: string          (一句话简介)
 *  - tags: string[]               (技术/类型标签)
 *  - tone: 'accent' | 'magenta' | 'amber'  (对应主强调色)
 *  - href: string                 (点击跳转, e.g. "../accounting-tool.html")
 *  - previewHeightClass: string   (预览区高度, Tailwind h-*)
 *  - children: ReactNode          (CSS风格化预览组件)
 */
const toneChipMap = {
  accent:  'tag-chip--accent',
  magenta: 'tag-chip--magenta',
  amber:   'tag-chip--amber',
}

export default function ProjectCard({
  number,
  eyebrow,
  title,
  subtitle,
  description,
  tags,
  tone = 'accent',
  href,
  previewHeightClass = 'h-56 sm:h-64',
  children,
}) {
  const cardRef = useRef(null)

  const handleMouseMove = (e) => {
    const el = cardRef.current
    if (!el) return
    // Respect reduced-motion & touch devices (no mousemove on touch)
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
    if (window.matchMedia('(hover: none)').matches) return

    const rect = el.getBoundingClientRect()
    const x = e.clientX - rect.left
    const y = e.clientY - rect.top
    const cx = rect.width / 2
    const cy = rect.height / 2
    // Clamp to max ±4deg
    const rotateY = Math.max(-4, Math.min(4, ((x - cx) / cx) * 4))
    const rotateX = Math.max(-4, Math.min(4, -((y - cy) / cy) * 4))
    el.style.transform = `perspective(1100px) rotateX(${rotateX.toFixed(2)}deg) rotateY(${rotateY.toFixed(2)}deg) translateY(-4px)`
  }

  const handleMouseLeave = () => {
    const el = cardRef.current
    if (el) el.style.transform = ''
  }

  return (
    <a
      ref={cardRef}
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="project-card glass-card p-4 sm:p-5 block reveal group"
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      aria-label={`打开项目：${title} ${subtitle}`}
    >
      <div className="project-card__inner flex flex-col h-full gap-4">
        {/* top meta row */}
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-3">
            <span
              className="font-[family-name:var(--font-mono)] text-[11px] font-semibold tracking-wider px-2 py-0.5 rounded"
              style={{
                color: 'var(--color-text-bright)',
                background:
                  tone === 'accent'  ? 'var(--color-accent-soft)'  :
                  tone === 'magenta' ? 'var(--color-accent-2-soft)' :
                                       'var(--color-accent-3-soft)',
              }}
            >
              § {number}
            </span>
            <span className="eyebrow !text-[10px] !tracking-[0.2em]">{eyebrow}</span>
          </div>
          <span
            aria-hidden
            className="text-[14px] transition-transform duration-300 group-hover:translate-x-1 group-hover:-translate-y-1"
            style={{ color: 'var(--color-text-dim)' }}
          >
            ↗
          </span>
        </div>

        {/* preview */}
        <div className={`relative ${previewHeightClass} shrink-0`}>
          {children}
        </div>

        {/* title + description */}
        <div className="flex-1 min-h-0 flex flex-col">
          <div className="flex items-baseline flex-wrap gap-x-2 gap-y-1">
            <h3
              className="font-[family-name:var(--font-body)] font-semibold text-[19px] sm:text-[20px] text-[color:var(--color-text-bright)] leading-tight"
            >
              {title}
            </h3>
            <span
              style={{
                fontFamily: 'Fraunces, Georgia, serif',
                fontStyle: 'italic',
                fontVariationSettings: '"wght" 500',
                fontSize: '15px',
                color:
                  tone === 'accent'  ? 'var(--color-accent)'  :
                  tone === 'magenta' ? 'var(--color-accent-2)' :
                                       'var(--color-accent-3)',
              }}
            >
              {subtitle}
            </span>
          </div>
          <p className="mt-2 text-[13px] sm:text-[14px] leading-[1.7] text-[color:var(--color-text-mid)]">
            {description}
          </p>

          {/* tags */}
          {tags?.length > 0 && (
            <div className="mt-auto pt-4 flex flex-wrap gap-1.5">
              {tags.map((t, i) => (
                <span
                  key={t}
                  className={`tag-chip !text-[10px] !py-1 !px-2.5 ${i === 0 ? toneChipMap[tone] : ''}`}
                >
                  {t}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>
    </a>
  )
}
