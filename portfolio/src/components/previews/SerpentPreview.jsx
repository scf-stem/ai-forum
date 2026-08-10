/**
 * SerpentPreview · 霓虹贪吃蛇风格化缩略
 * 深黑底 + 霓虹网格线 + 青色蛇身(3段带辉光) + 品红食物 + CRT扫描线
 */
export default function SerpentPreview() {
  return (
    <div
      className="relative w-full h-full rounded-[calc(var(--radius-card)-2px)] overflow-hidden"
      style={{
        background:
          'radial-gradient(ellipse at 20% 10%, rgba(176, 38, 255, 0.2), transparent 50%), radial-gradient(ellipse at 80% 90%, rgba(0, 240, 255, 0.15), transparent 50%), #05060f',
      }}
    >
      {/* Grid lines */}
      <div
        aria-hidden
        className="absolute inset-0"
        style={{
          backgroundImage: `
            linear-gradient(rgba(0,240,255,0.07) 1px, transparent 1px),
            linear-gradient(90deg, rgba(0,240,255,0.07) 1px, transparent 1px)
          `,
          backgroundSize: '20px 20px',
        }}
      />

      {/* Title chip */}
      <div className="absolute top-3 left-3 right-3 flex items-center justify-between">
        <span
          className="text-[10px] sm:text-[11px] font-bold tracking-[0.24em] text-[#00f0ff]"
          style={{
            fontFamily: 'Monoton, cursive',
            textShadow: '0 0 8px rgba(0,240,255,0.7), 0 0 20px rgba(0,240,255,0.35)',
            letterSpacing: '0.12em',
          }}
        >
          NEON
        </span>
        <span
          className="px-1.5 py-0.5 rounded text-[8px] sm:text-[9px]"
          style={{
            fontFamily: '"Share Tech Mono", monospace',
            background: 'rgba(255, 43, 214, 0.15)',
            color: '#ff2bd6',
            border: '1px solid rgba(255,43,214,0.3)',
            textShadow: '0 0 6px rgba(255,43,214,0.6)',
          }}
        >
          LV · 03
        </span>
      </div>

      {/* Score mono row */}
      <div
        className="absolute top-10 left-3 right-3 flex justify-between text-[9px] sm:text-[10px]"
        style={{ fontFamily: '"Share Tech Mono", monospace', color: '#6a7a9a' }}
      >
        <span>SCORE <b style={{ color: '#39ff14', textShadow: '0 0 6px rgba(57,255,20,0.5)' }}>0480</b></span>
        <span>BEST <b style={{ color: '#fff700' }}>1260</b></span>
      </div>

      {/* Playfield · snake + food (用比例定位) */}
      <div
        aria-hidden
        className="absolute"
        style={{
          left: '18%', top: '55%', width: '14px', height: '14px',
          borderRadius: '3px',
          background: '#00f0ff',
          boxShadow: '0 0 6px rgba(0,240,255,0.85), 0 0 18px rgba(0,240,255,0.5), inset 0 0 4px rgba(255,255,255,0.3)',
        }}
      />
      <div
        aria-hidden
        className="absolute"
        style={{
          left: 'calc(18% + 18px)', top: '55%', width: '14px', height: '14px',
          borderRadius: '3px',
          background: '#00f0ff',
          opacity: 0.88,
          boxShadow: '0 0 6px rgba(0,240,255,0.7), 0 0 14px rgba(0,240,255,0.4)',
        }}
      />
      <div
        aria-hidden
        className="absolute"
        style={{
          left: 'calc(18% + 36px)', top: 'calc(55% - 18px)', width: '14px', height: '14px',
          borderRadius: '3px',
          background: '#00f0ff',
          opacity: 0.75,
          boxShadow: '0 0 6px rgba(0,240,255,0.55), 0 0 12px rgba(0,240,255,0.3)',
        }}
      />
      {/* snake head (larger, eyes) */}
      <div
        aria-hidden
        className="absolute flex items-center justify-center"
        style={{
          left: 'calc(18% + 36px)', top: 'calc(55% - 36px)', width: '18px', height: '18px',
          borderRadius: '4px',
          background: '#39ff14',
          boxShadow: '0 0 8px rgba(57,255,20,0.9), 0 0 22px rgba(57,255,20,0.5), inset 0 0 4px rgba(255,255,255,0.3)',
        }}
      >
        <span className="flex gap-1">
          <span className="w-1 h-1 rounded-full bg-black" />
          <span className="w-1 h-1 rounded-full bg-black" />
        </span>
      </div>

      {/* Food (magenta diamond) */}
      <div
        aria-hidden
        className="absolute"
        style={{
          right: '22%', top: '38%', width: '16px', height: '16px',
          transform: 'rotate(45deg)',
          background: '#ff2bd6',
          boxShadow: '0 0 8px rgba(255,43,214,0.9), 0 0 24px rgba(255,43,214,0.55)',
          animation: 'pulse 1.4s ease-in-out infinite',
        }}
      />
      {/* Food 2 (red dot) */}
      <div
        aria-hidden
        className="absolute rounded-full"
        style={{
          left: '32%', top: '30%', width: '10px', height: '10px',
          background: '#ff1744',
          boxShadow: '0 0 6px rgba(255,23,68,0.9), 0 0 18px rgba(255,23,68,0.5)',
        }}
      />

      {/* CRT scanline sweeping */}
      <div
        aria-hidden
        className="absolute inset-x-0 h-[22%] pointer-events-none"
        style={{
          top: 0,
          background:
            'linear-gradient(180deg, transparent 0%, rgba(0,240,255,0.08) 50%, transparent 100%)',
          animation: 'scanline 3.5s linear infinite',
        }}
      />
      {/* subtle vignette */}
      <div
        aria-hidden
        className="absolute inset-0 pointer-events-none"
        style={{
          background:
            'radial-gradient(ellipse at center, transparent 45%, rgba(5,6,15,0.75) 100%)',
        }}
      />

      <style>{`
        @keyframes pulse {
          0%,100% { transform: rotate(45deg) scale(1); }
          50%     { transform: rotate(45deg) scale(1.22); }
        }
        @keyframes scanline {
          0%   { transform: translateY(-120%); }
          100% { transform: translateY(540%); }
        }
      `}</style>
    </div>
  )
}
