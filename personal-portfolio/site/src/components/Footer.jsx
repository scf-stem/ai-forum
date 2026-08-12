export default function Footer() {
  const year = new Date().getFullYear()

  const scrollTop = () => {
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  return (
    <footer id="contact" className="relative mt-10 border-t border-[color:var(--color-surface-border)]">
      <div className="max-w-7xl mx-auto px-6 md:px-10 py-14 sm:py-18">
        {/* Contact CTA band */}
        <div className="reveal grid grid-cols-1 md:grid-cols-12 gap-8 items-center pb-12 mb-10 border-b border-[color:var(--color-surface-border)]">
          <div className="md:col-span-8">
            <div className="eyebrow flex items-center gap-3 mb-4">
              <span className="section-number">§ 04</span>
              <span className="inline-block w-8 h-px bg-[color:var(--color-surface-border-strong)]"></span>
              <span>Get In Touch</span>
            </div>
            <h3
              className="font-[family-name:var(--font-display)] text-[36px] sm:text-[48px] leading-[1.05] tracking-tight"
              style={{ fontVariationSettings: '"opsz" 96, "wght" 600' }}
            >
              有想法？<em style={{ fontStyle: 'italic', color: 'var(--color-accent)' }}>聊聊。</em>
            </h3>
            <p className="mt-4 text-[color:var(--color-text-mid)] max-w-xl leading-[1.8]">
              不管是产品设计的合作、用户研究的探讨，还是单纯想交个朋友，都欢迎。
            </p>
          </div>
          <div className="md:col-span-4 md:text-right flex md:flex-col gap-3 md:gap-3 md:items-end">
            <div className="tag-chip tag-chip--accent !text-xs !py-2 !px-4">tianpeng@design.mail</div>
            <div className="tag-chip !text-xs !py-2 !px-4">WeChat · tianpeng_design</div>
            <div className="tag-chip tag-chip--magenta !text-xs !py-2 !px-4">Based in Shanghai</div>
          </div>
        </div>

        {/* Bottom row */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-6">
          <div className="flex items-center gap-2">
            <span
              className="font-[family-name:var(--font-display)] text-[18px] font-semibold"
              style={{ fontVariationSettings: '"opsz" 36, "wght" 600' }}
            >
              田鹏
            </span>
            <span className="text-[color:var(--color-accent)] text-base">◇</span>
            <span className="font-[family-name:var(--font-mono)] text-[12px] text-[color:var(--color-text-dim)] tracking-wider">
              © {year} · Made with ◇ + React + Tailwind
            </span>
          </div>

          <button
            onClick={scrollTop}
            className="group inline-flex items-center gap-2 h-10 px-4 rounded-[var(--radius-pill)] border border-[color:var(--color-surface-border)] text-[12px] font-[family-name:var(--font-mono)] text-[color:var(--color-text-mid)] hover:text-[color:var(--color-text-bright)] hover:border-[color:var(--color-accent-soft)] transition-all"
          >
            <span className="transition-transform group-hover:-translate-y-0.5">↑</span>
            回到顶部
          </button>
        </div>
      </div>
    </footer>
  )
}
