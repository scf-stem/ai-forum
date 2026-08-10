import { useEffect, useRef } from 'react'

export default function Hero() {
  const titleRef = useRef(null)

  useEffect(() => {
    const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    const isTouch = window.matchMedia('(hover: none)').matches
    if (prefersReduced || isTouch) return

    const onScroll = () => {
      const el = titleRef.current
      if (!el) return
      const max = Math.min(window.scrollY, 500)
      const t = max / 500
      const wght = 900 - (900 - 400) * t
      const opsz = 144 - (144 - 36) * t
      const spacing = -0.03 + 0.02 * t
      el.style.fontVariationSettings = `"opsz" ${opsz | 0}, "wght" ${wght | 0}`
      el.style.letterSpacing = `${spacing}em`
    }
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  return (
    <section id="top" className="relative pt-10 sm:pt-16 pb-24 sm:pb-36">
      <div className="max-w-7xl mx-auto px-6 md:px-10">
        <div className="grid grid-cols-1 md:grid-cols-12 gap-10 md:gap-8 items-center">
          {/* Left 8 cols · text */}
          <div className="md:col-span-8 order-2 md:order-1">
            <div className="eyebrow mb-5 flex items-center gap-3">
              <span>§ 01</span>
              <span className="inline-block w-8 h-px bg-[color:var(--color-surface-border-strong)]"></span>
              <span>Portfolio / 2026</span>
            </div>

            <h1 ref={titleRef} className="hero-title text-[56px] sm:text-[76px] md:text-[104px] lg:text-[120px]">
              田鹏
              <br />
              <em>Product</em> Designer
            </h1>

            <p className="mt-7 max-w-xl text-[16px] sm:text-[17px] leading-[1.8] text-[color:var(--color-text-mid)]">
              用设计叙事，用代码造物。<br />
              资深产品设计师，专注医疗健康领域的用户研究与体验设计；
              同时热爱前端实现，将研究洞察转化为可感知的交互细节。
            </p>

            <div className="mt-8 flex flex-wrap gap-2">
              <span className="tag-chip tag-chip--accent">UX Research</span>
              <span className="tag-chip tag-chip--magenta">Product Design</span>
              <span className="tag-chip tag-chip--amber">Frontend Craft</span>
              <span className="tag-chip">Healthcare · SaaS</span>
            </div>

            <div className="mt-11 flex items-center gap-5">
              <a
                href="#works"
                className="group inline-flex items-center gap-2 h-11 px-5 rounded-[var(--radius-pill)] bg-[color:var(--color-accent)] text-[color:var(--color-bg-deep)] font-[family-name:var(--font-mono)] text-[13px] font-medium tracking-wide transition-transform hover:-translate-y-0.5 hover:shadow-[0_0_32px_-4px_var(--color-accent-soft)]"
              >
                查看作品
                <span className="transition-transform group-hover:translate-y-0.5">↓</span>
              </a>
              <a
                href="#about"
                className="inline-flex items-center gap-2 h-11 px-5 rounded-[var(--radius-pill)] border border-[color:var(--color-surface-border)] text-[color:var(--color-text-mid)] font-[family-name:var(--font-body)] text-[13px] transition-colors hover:text-[color:var(--color-text-bright)] hover:border-[color:var(--color-surface-border-strong)]"
              >
                关于我
              </a>
            </div>
          </div>

          {/* Right 4 cols · avatar */}
          <div className="md:col-span-4 order-1 md:order-2 md:pl-6 flex md:justify-end">
            <div className="relative">
              {/* halo */}
              <div
                aria-hidden
                className="absolute -inset-6 rounded-full blur-3xl opacity-40 pointer-events-none"
                style={{
                  background:
                    'radial-gradient(circle, var(--color-accent-soft), transparent 60%), radial-gradient(circle at 70% 30%, var(--color-accent-2-soft), transparent 55%)'
                }}
              />
              {/* ring */}
              <div
                aria-hidden
                className="absolute inset-0 rounded-full"
                style={{
                  padding: '1px',
                  background:
                    'linear-gradient(135deg, var(--color-accent) 0%, transparent 40%, var(--color-accent-2) 100%)',
                  WebkitMask:
                    'linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0)',
                  WebkitMaskComposite: 'xor',
                  maskComposite: 'exclude',
                }}
              />
              <img
                src="/xiaoxin.jpeg"
                alt="田鹏 · 头像"
                className="relative w-40 h-40 sm:w-48 sm:h-48 md:w-56 md:h-56 rounded-full object-cover"
                style={{ aspectRatio: '1 / 1' }}
              />
              {/* little tag chip */}
              <div
                className="absolute -bottom-2 -right-2 glass-card !py-1.5 !px-3 flex items-center gap-2"
                style={{ backdropFilter: 'blur(10px)' }}
              >
                <span className="w-2 h-2 rounded-full bg-[color:var(--color-accent)] animate-pulse" />
                <span className="font-[family-name:var(--font-mono)] text-[10px] text-[color:var(--color-text-bright)] tracking-wide">
                  AVAILABLE
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
