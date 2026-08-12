const skills = [
  { label: 'UX Research',     tone: 'accent'  },
  { label: 'User Interview',  tone: ''        },
  { label: 'Persona & JTBD',  tone: ''        },
  { label: 'Product Design',  tone: 'magenta' },
  { label: 'Design System',   tone: ''        },
  { label: 'Prototyping',     tone: ''        },
  { label: 'Healthcare UX',   tone: 'amber'   },
  { label: 'SaaS B2B',        tone: ''        },
  { label: 'HTML / CSS',      tone: 'accent'  },
  { label: 'React / Vite',    tone: ''        },
  { label: 'Tailwind CSS',    tone: ''        },
  { label: 'Canvas Animation',tone: 'magenta' },
]

const toneMap = {
  accent:  'tag-chip--accent',
  magenta: 'tag-chip--magenta',
  amber:   'tag-chip--amber',
  '':      '',
}

export default function About() {
  return (
    <section id="about" className="relative py-24 sm:py-32">
      <div className="max-w-7xl mx-auto px-6 md:px-10">
        <div className="grid grid-cols-1 md:grid-cols-12 gap-10 md:gap-12">
          {/* Eyebrow + marker rail (4 cols) */}
          <div className="md:col-span-4 md:sticky md:top-28 self-start reveal">
            <div className="eyebrow flex items-center gap-3 mb-5">
              <span className="section-number">§ 03</span>
              <span className="inline-block w-8 h-px bg-[color:var(--color-surface-border-strong)]"></span>
              <span>About Me</span>
            </div>
            <h2
              className="font-[family-name:var(--font-display)] text-[40px] sm:text-[48px] leading-[1.05] tracking-tight"
              style={{ fontVariationSettings: '"opsz" 96, "wght" 600' }}
            >
              把研究洞察<em style={{ fontStyle: 'italic', color: 'var(--color-accent-2)' }}>缝进</em>每一个像素。
            </h2>
          </div>

          {/* Body (8 cols) */}
          <div className="md:col-span-8 reveal">
            <div className="space-y-6 text-[16px] leading-[1.9] text-[color:var(--color-text-mid)] font-[family-name:var(--font-body)]">
              <p>
                过去<span className="text-[color:var(--color-text-bright)] font-medium"> 7 年+ </span>
                深耕医疗设备与健康科技领域的产品设计。主导过从 0 到 1 的设备端交互系统，
                也打磨过百万级 DAU 的 SaaS 数据后台；习惯用定性研究锚定方向，
                用定量数据验证决策。
              </p>
              <p>
                不满足于停留在高保真稿。近两年把触角延伸到前端实现，
                用 HTML / CSS / React / Canvas 亲手把设计稿落成可以运行的界面，
                相信只有经历过"写出代码的设计师"阶段，才能对细节有真正的体感。
              </p>
              <p>
                作品集里的三个小项目，是工作之余给自己出的三道练习题 —— 
                <span className="text-[color:var(--color-accent-3)]"> 三种完全不同的设计语言</span>，
                从纸感编辑到霓虹赛博再到玻璃拟态，每一次都想逼自己跳出惯性。
              </p>
            </div>

            {/* Skills wall */}
            <div className="mt-12">
              <div className="eyebrow mb-5">Capability Map / 能力图谱</div>
              <div className="flex flex-wrap gap-2">
                {skills.map(s => (
                  <span key={s.label} className={`tag-chip ${toneMap[s.tone]}`}>
                    {s.label}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
