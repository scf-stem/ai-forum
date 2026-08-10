/**
 * WeatherPreview · 天气风格化缩略
 * 蓝→浅蓝渐变 + 浮动光球 + 半透明玻璃温度卡 + 金色阳光
 */
export default function WeatherPreview() {
  return (
    <div
      className="relative w-full h-full rounded-[calc(var(--radius-card)-2px)] overflow-hidden"
      style={{
        background:
          'linear-gradient(135deg, #1e3a5f 0%, #4a6fa5 40%, #7eb8da 100%)',
      }}
    >
      {/* Floating orbs */}
      <div
        aria-hidden
        className="absolute rounded-full blur-[50px]"
        style={{
          width: '55%', height: '55%', top: '-10%', left: '-8%',
          background: 'radial-gradient(circle, rgba(255,216,107,0.68), transparent 70%)',
          animation: 'float-orb-a 14s ease-in-out infinite',
        }}
      />
      <div
        aria-hidden
        className="absolute rounded-full blur-[55px]"
        style={{
          width: '62%', height: '62%', bottom: '-18%', right: '-12%',
          background: 'radial-gradient(circle, rgba(126,184,218,0.6), transparent 70%)',
          animation: 'float-orb-b 18s ease-in-out infinite',
        }}
      />
      <div
        aria-hidden
        className="absolute rounded-full blur-[38px]"
        style={{
          width: '38%', height: '38%', top: '28%', right: '20%',
          background: 'radial-gradient(circle, rgba(255,255,255,0.28), transparent 70%)',
        }}
      />

      {/* Sun ray (top right) */}
      <div
        aria-hidden
        className="absolute rounded-full"
        style={{
          top: '-8%', right: '-6%',
          width: '38%', height: '38%',
          background:
            'radial-gradient(circle, rgba(255,216,107,0.55) 0%, rgba(255,216,107,0.18) 40%, transparent 70%)',
          filter: 'blur(2px)',
        }}
      />
      <div
        aria-hidden
        className="absolute rounded-full"
        style={{
          top: '6%', right: '6%', width: '36px', height: '36px',
          background: '#ffd86b',
          boxShadow: '0 0 22px 6px rgba(255, 216, 107, 0.5)',
        }}
      />

      {/* Location label */}
      <div className="absolute top-3 left-3 right-3 flex items-center justify-between">
        <div>
          <div
            className="text-[10px] sm:text-[11px] tracking-[0.22em] uppercase text-white/60"
            style={{ fontFamily: '"JetBrains Mono", monospace' }}
          >
            Shanghai
          </div>
          <div
            className="mt-0.5 text-[13px] sm:text-[15px] font-semibold text-white"
            style={{ fontFamily: '"Noto Sans SC", sans-serif' }}
          >
            上海 · 徐汇
          </div>
        </div>
        <span
          className="px-2 py-0.5 rounded-full text-[9px]"
          style={{
            fontFamily: '"JetBrains Mono", monospace',
            color: 'rgba(255,255,255,0.9)',
            background: 'rgba(255,255,255,0.1)',
            border: '1px solid rgba(255,255,255,0.18)',
            backdropFilter: 'blur(6px)',
          }}
        >
          08/10 · 周一
        </span>
      </div>

      {/* Main glass temp card */}
      <div
        className="absolute left-3 right-3 sm:left-5 sm:right-auto sm:w-[60%]"
        style={{
          bottom: '14px',
          padding: '12px 14px',
          borderRadius: '14px',
          background: 'rgba(255,255,255,0.14)',
          border: '1px solid rgba(255,255,255,0.22)',
          backdropFilter: 'blur(14px) saturate(150%)',
          WebkitBackdropFilter: 'blur(14px) saturate(150%)',
          boxShadow: '0 8px 32px rgba(0,0,0,0.14)',
        }}
      >
        <div className="flex items-end justify-between gap-2">
          <div>
            <div className="flex items-baseline gap-1">
              <span
                style={{
                  fontFamily: 'Cormorant Garamond, Georgia, serif',
                  fontStyle: 'italic',
                  fontWeight: 600,
                  fontSize: 'clamp(32px, 6vw, 48px)',
                  lineHeight: 0.9,
                  color: 'rgba(255,255,255,0.98)',
                  textShadow: '0 1px 10px rgba(255,216,107,0.15)',
                }}
              >
                26°
              </span>
              <span className="text-[12px] text-white/70" style={{ fontFamily: '"Noto Sans SC", sans-serif' }}>
                / 19°
              </span>
            </div>
            <div
              className="mt-1 text-[13px] text-white/92"
              style={{ fontFamily: '"Noto Sans SC", sans-serif', fontWeight: 500 }}
            >
              ☀︎ 晴 · 微风
            </div>
          </div>

          {/* 3 day mini strip */}
          <div className="flex gap-2 text-[10px] text-white/85" style={{ fontFamily: '"JetBrains Mono", monospace' }}>
            {[
              { d: '周二', t: '28°', i: '⛅' },
              { d: '周三', t: '24°', i: '🌦' },
              { d: '周四', t: '27°', i: '☁︎' },
            ].map(d => (
              <div
                key={d.d}
                className="flex flex-col items-center px-1.5 py-1 rounded-lg"
                style={{ background: 'rgba(255,255,255,0.08)' }}
              >
                <span className="opacity-70">{d.d}</span>
                <span className="my-0.5 text-[14px] leading-none">{d.i}</span>
                <span className="font-medium">{d.t}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Grain subtle */}
      <div
        aria-hidden
        className="absolute inset-0 pointer-events-none opacity-[0.06] mix-blend-overlay"
        style={{
          backgroundImage: `url("data:image/svg+xml;utf8,<svg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='3' stitchTiles='stitch'/></filter><rect width='100%25' height='100%25' filter='url(%23n)'/></svg>")`,
          backgroundSize: '200px 200px',
        }}
      />

      <style>{`
        @keyframes float-orb-a {
          0%,100% { transform: translate(0,0) scale(1); }
          50%     { transform: translate(20px, 24px) scale(1.08); }
        }
        @keyframes float-orb-b {
          0%,100% { transform: translate(0,0) scale(1); }
          50%     { transform: translate(-26px, -18px) scale(0.95); }
        }
      `}</style>
    </div>
  )
}
