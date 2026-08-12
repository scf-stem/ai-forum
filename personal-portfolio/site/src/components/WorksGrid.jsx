import ProjectCard from './ProjectCard'
import FolioPreview from './previews/FolioPreview'
import SerpentPreview from './previews/SerpentPreview'
import WeatherPreview from './previews/WeatherPreview'

const projects = [
  {
    number: '01',
    eyebrow: 'Finance · Editorial',
    title: '账本',
    subtitle: 'Folio',
    description:
      '纸张质感的个人记账应用，Fraunces衬线字体搭配红绿收支语言，把数字变成一眼可读的财务故事。',
    tags: ['HTML / CSS', 'Vanilla JS', 'Editorial', 'Paper Texture'],
    tone: 'amber',
    href: './accounting-tool.html',
    previewHeightClass: 'h-64 sm:h-72 md:h-80',
    Preview: FolioPreview,
    gridSpan: 'md:col-span-7',
  },
  {
    number: '02',
    eyebrow: 'Game · Cyberpunk',
    title: '霓虹贪吃蛇',
    subtitle: 'Neon Serpent',
    description:
      'CRT终端质感的街机式贪吃蛇，霓虹青与品红的辉光网格、4档难度、穿墙地形，移动端支持滑动与虚拟方向键。',
    tags: ['Canvas 2D', 'Web Audio', 'Neon Glow', 'Responsive'],
    tone: 'magenta',
    href: './snake-game.html',
    previewHeightClass: 'h-64 sm:h-72 md:h-80',
    Preview: SerpentPreview,
    gridSpan: 'md:col-span-5',
  },
  {
    number: '03',
    eyebrow: 'Weather · Glassmorphism',
    title: '天气查询',
    subtitle: 'Weather Lens',
    description:
      '玻璃拟态天气面板，渐变背景随昼夜/晴雨动态切换，浮动光球配合金色阳光制造空气感。',
    tags: ['Glassmorphism', 'CSS Animation', 'Dynamic Theme', 'Cormorant Garamond'],
    tone: 'accent',
    href: './weather-app.html',
    previewHeightClass: 'h-60 sm:h-72 md:h-80',
    Preview: WeatherPreview,
    gridSpan: 'md:col-span-12',
  },
]

export default function WorksGrid() {
  return (
    <section id="works" className="relative py-20 sm:py-28">
      <div className="max-w-7xl mx-auto px-6 md:px-10">
        {/* Section header */}
        <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-5 mb-12 sm:mb-14 reveal">
          <div>
            <div className="eyebrow flex items-center gap-3 mb-4">
              <span className="section-number">§ 02</span>
              <span className="inline-block w-8 h-px bg-[color:var(--color-surface-border-strong)]"></span>
              <span>Selected Works / 2026</span>
            </div>
            <h2
              className="font-[family-name:var(--font-display)] text-[40px] sm:text-[56px] leading-[1.02] tracking-tight max-w-2xl"
              style={{ fontVariationSettings: '"opsz" 120, "wght" 600' }}
            >
              三个项目，
              <br />
              <em style={{ fontStyle: 'italic', color: 'var(--color-accent)' }}>三种</em>设计语言。
            </h2>
          </div>
          <p className="text-[14px] sm:text-[15px] leading-[1.8] text-[color:var(--color-text-mid)] max-w-sm">
            每一个项目都刻意选择了完全不同的视觉系统 —
            从纸的温度、霓虹的躁动，到玻璃的通透 — 点击卡片即可运行体验。
          </p>
        </div>

        {/* Bento grid */}
        <div className="grid grid-cols-1 md:grid-cols-12 gap-5 sm:gap-6 auto-rows-auto">
          {projects.map(p => {
            const { Preview } = p
            return (
              <article key={p.number} className={`${p.gridSpan} flex`}>
                <ProjectCard
                  number={p.number}
                  eyebrow={p.eyebrow}
                  title={p.title}
                  subtitle={p.subtitle}
                  description={p.description}
                  tags={p.tags}
                  tone={p.tone}
                  href={p.href}
                  previewHeightClass={p.previewHeightClass}
                >
                  <Preview />
                </ProjectCard>
              </article>
            )
          })}
        </div>
      </div>
    </section>
  )
}
