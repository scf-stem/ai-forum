import { useEffect, useState } from 'react'

const links = [
  { id: 'works',   label: 'Works'   },
  { id: 'about',   label: 'About'   },
  { id: 'contact', label: 'Contact' },
]

export default function Nav() {
  const [scrolled, setScrolled] = useState(false)

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 24)
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  return (
    <nav className={`nav ${scrolled ? 'nav--scrolled' : ''}`}>
      <div className="max-w-7xl mx-auto px-6 md:px-10 h-16 flex items-center justify-between">
        <a href="#top" className="flex items-center gap-2 group">
          <span
            className="font-[family-name:var(--font-display)] font-semibold text-[20px] tracking-tight"
            style={{ fontVariationSettings: '"opsz" 96, "wght" 600' }}
          >
            田鹏
          </span>
          <span className="text-[color:var(--color-accent)] text-lg transition-transform group-hover:rotate-90 duration-500">◇</span>
          <span className="eyebrow !tracking-[0.24em] !text-[10px] hidden sm:inline">Portfolio</span>
        </a>

        <ul className="hidden md:flex items-center gap-8">
          {links.map(l => (
            <li key={l.id}>
              <a
                href={`#${l.id}`}
                className="text-[13px] text-[color:var(--color-text-mid)] hover:text-[color:var(--color-text-bright)] transition-colors relative py-1 after:absolute after:left-0 after:-bottom-0.5 after:h-px after:w-0 after:bg-[color:var(--color-accent)] after:transition-all hover:after:w-full"
              >
                {l.label}
              </a>
            </li>
          ))}
        </ul>

        <a
          href="#works"
          className="md:hidden inline-flex items-center justify-center h-9 px-3 rounded-[var(--radius-pill)] border border-[color:var(--color-surface-border)] text-[12px] font-[family-name:var(--font-mono)] text-[color:var(--color-text-mid)]"
        >
          Works ↓
        </a>
      </div>
    </nav>
  )
}
