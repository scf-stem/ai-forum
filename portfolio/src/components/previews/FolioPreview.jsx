/**
 * FolioPreview · 账本风格化缩略
 * 纸米色背景 + Fraunces衬线标题 + 3张统计卡(收入/支出/结余) + 收支列表mini
 */
export default function FolioPreview() {
  return (
    <div
      className="relative w-full h-full rounded-[calc(var(--radius-card)-2px)] overflow-hidden"
      style={{
        background: '#EAE3D2',
        backgroundImage: `
          radial-gradient(circle at 20% 10%, rgba(122,46,46,.035), transparent 42%),
          radial-gradient(circle at 80% 90%, rgba(46,107,79,.04), transparent 48%)
        `,
      }}
    >
      <div className="absolute inset-0 flex flex-col p-4 sm:p-5">
        {/* Header */}
        <div className="flex items-end justify-between mb-3">
          <div className="flex items-baseline gap-2">
            <span
              className="font-[family-name:var(--font-display)] text-[18px] sm:text-[20px] font-semibold text-[#181B22] leading-none"
              style={{ fontFamily: 'Fraunces, Georgia, serif', fontVariationSettings: '"opsz" 72, "wght" 600' }}
            >
              账本<span className="text-[#7A2E2E]">·</span>
            </span>
            <span
              className="font-[family-name:var(--font-display)] text-[14px] text-[#181B22]"
              style={{ fontFamily: 'Fraunces, Georgia, serif', fontStyle: 'italic', fontVariationSettings: '"wght" 500' }}
            >
              Folio
            </span>
          </div>
          <span
            className="text-[9px] sm:text-[10px] text-[#74695A] tracking-[0.14em] uppercase"
            style={{ fontFamily: 'IBM Plex Mono, monospace' }}
          >
            2026 · 08
          </span>
        </div>

        {/* 3 stat cards */}
        <div className="grid grid-cols-3 gap-1.5 sm:gap-2 mb-3">
          {/* Income */}
          <div
            className="rounded-md p-2"
            style={{
              background: '#F5F1E6',
              border: '1px solid #DCD4C0',
              boxShadow: '0 1px 0 rgba(24,27,34,.03)',
            }}
          >
            <div className="text-[7px] sm:text-[8px] uppercase tracking-widest text-[#74695A]" style={{ fontFamily: 'IBM Plex Mono, monospace' }}>收入</div>
            <div className="mt-1 text-[12px] sm:text-[14px] font-semibold" style={{ color: '#2E6B4F', fontFamily: 'IBM Plex Mono, monospace' }}>
              +12,480
            </div>
            <div className="mt-1.5 h-0.5 rounded-full" style={{ background: '#DCE8E0' }}>
              <div className="h-full rounded-full" style={{ width: '72%', background: '#2E6B4F' }} />
            </div>
          </div>
          {/* Expense */}
          <div
            className="rounded-md p-2"
            style={{
              background: '#F5F1E6',
              border: '1px solid #DCD4C0',
              boxShadow: '0 1px 0 rgba(24,27,34,.03)',
            }}
          >
            <div className="text-[7px] sm:text-[8px] uppercase tracking-widest text-[#74695A]" style={{ fontFamily: 'IBM Plex Mono, monospace' }}>支出</div>
            <div className="mt-1 text-[12px] sm:text-[14px] font-semibold" style={{ color: '#A8472E', fontFamily: 'IBM Plex Mono, monospace' }}>
              -6,320
            </div>
            <div className="mt-1.5 h-0.5 rounded-full" style={{ background: '#EAD6CC' }}>
              <div className="h-full rounded-full" style={{ width: '38%', background: '#A8472E' }} />
            </div>
          </div>
          {/* Balance (dark) */}
          <div
            className="rounded-md p-2"
            style={{
              background: '#181B22',
              border: '1px solid #181B22',
            }}
          >
            <div className="text-[7px] sm:text-[8px] uppercase tracking-widest" style={{ color: '#B9AE96', fontFamily: 'IBM Plex Mono, monospace' }}>结余</div>
            <div className="mt-1 text-[12px] sm:text-[14px] font-semibold text-[#EAE3D2]" style={{ fontFamily: 'IBM Plex Mono, monospace' }}>
              38,960
            </div>
            <div className="mt-1.5 h-0.5 rounded-full" style={{ background: '#3a3d45' }}>
              <div className="h-full rounded-full" style={{ width: '56%', background: '#7A2E2E' }} />
            </div>
          </div>
        </div>

        {/* Mini list of entries */}
        <div className="flex-1 flex flex-col gap-1.5">
          {[
            { c: '#2E6B4F', l: '设计外包收入', r: '+ 8,000', dot: 'bg-[#2E6B4F]' },
            { c: '#A8472E', l: '房租 · 八月',      r: '- 3,200', dot: 'bg-[#A8472E]' },
            { c: '#A8472E', l: '咖啡 & 书籍',     r: '-   286', dot: 'bg-[#A8472E]' },
            { c: '#2E6B4F', l: '理财产品分红',    r: '+   640', dot: 'bg-[#2E6B4F]' },
          ].map((item, i) => (
            <div
              key={i}
              className="flex items-center justify-between py-1.5 px-2 rounded-md"
              style={{
                background: '#F5F1E6',
                border: '1px solid #DCD4C0',
              }}
            >
              <div className="flex items-center gap-2 min-w-0">
                <span className={`w-1.5 h-1.5 rounded-full ${item.dot} shrink-0`} />
                <span
                  className="truncate text-[10px] sm:text-[11px] text-[#3A3D45]"
                  style={{ fontFamily: 'Inter, system-ui, sans-serif' }}
                >
                  {item.l}
                </span>
              </div>
              <span
                className="shrink-0 text-[10px] sm:text-[11px] font-medium"
                style={{ color: item.c, fontFamily: 'IBM Plex Mono, monospace' }}
              >
                {item.r}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Paper grain subtle */}
      <div
        aria-hidden
        className="absolute inset-0 pointer-events-none opacity-[0.06] mix-blend-multiply"
        style={{
          backgroundImage: `url("data:image/svg+xml;utf8,<svg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='3' stitchTiles='stitch'/></filter><rect width='100%25' height='100%25' filter='url(%23n)'/></svg>")`,
          backgroundSize: '180px 180px',
        }}
      />
    </div>
  )
}
