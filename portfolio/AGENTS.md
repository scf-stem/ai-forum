# AGENTS.md · 项目级行为规则

> 本文件向 AI 智能体提供项目行为指引，仅在当前项目中生效。
> 配套全局规则（基础交互、重构、Git）协同工作，不与之冲突。

## 1. 技术栈与项目结构

- 前端代码使用 **React 19 + Vite + Tailwind CSS v4** 技术栈，使用 JSX（非 TypeScript）。
- 主项目位于 `portfolio/` 目录；组件统一放在 `portfolio/src/components/`，项目卡片预览组件放在 `portfolio/src/components/previews/`。
- 独立的 HTML demo（如贪吃蛇、天气、账本）放在 `portfolio/public/` 下，作为静态资源直接访问。
- 新增依赖前需说明必要性，并通过 `portfolio/package.json` 管理。

## 2. React 组件与代码风格

- 组件采用函数式组件 + 默认导出，文件名使用 PascalCase（如 `ProjectCard.jsx`）。
- 使用 2 空格缩进，字符串使用单引号，语句末尾不加分号。
- Hooks 使用遵循 `react/rules-of-hooks` 与 `react/only-export-components`（见 `portfolio/.oxlintrc.json`）。
- Props 通过解构传入，并为复杂组件的 props 添加 JSDoc 注释说明类型与用途（参考 `portfolio/src/components/ProjectCard.jsx`）。
- 副作用必须清理：`addEventListener` 需在 `useEffect` 返回中 `removeEventListener`，定时器需 `clearTimeout/clearInterval`（参考 `portfolio/src/components/Hero.jsx`、`portfolio/src/components/Nav.jsx`）。

## 3. 样式与设计系统

- 颜色、字体、圆角、动画统一通过 Tailwind v4 的 `@theme` 块在 `portfolio/src/index.css` 中定义为 CSS 变量（如 `--color-accent`、`--font-display`、`--radius-card`）。
- 颜色使用 OKLCH 色彩空间定义，保持视觉一致性；不硬编码十六进制色值（独立 HTML demo 除外）。
- 在 JSX 中通过 Tailwind 任意值语法引用 CSS 变量，如 `bg-[color:var(--color-accent)]`、`font-[family-name:var(--font-mono)]`。
- 复用的视觉模式（玻璃卡片、标签芯片等）抽为工具类（如 `.glass-card`、`.tag-chip`），集中定义在 `portfolio/src/index.css` 的 UTILITY CLASSES 区块。

## 4. 响应式与可访问性

- 移动优先，断点顺序：默认 → `sm:` → `md:` → `lg:`；使用 `max-w-7xl mx-auto px-6 md:px-10` 作为标准页面容器。
- 交互元素需提供 `aria-label`，纯装饰元素需加 `aria-hidden`（参考 `portfolio/src/components/Hero.jsx`、`portfolio/src/components/ProjectCard.jsx`）。
- 鼠标驱动的动效（如 3D 倾斜、滚动变字重）必须检测 `prefers-reduced-motion: reduce` 与 `hover: none`，在用户偏好减少动效或触屏设备上提前返回、禁用该效果。
- 焦点状态使用 `:focus-visible` 统一样式，保持键盘可访问性。

## 5. 重构与质量保障

- 小步重构：每次只做一个小改动，然后测试；频繁提交，保持代码随时可工作。
- 重构前确保有足够的测试；每次修改后运行 `npm run lint` 与 `npm run build`（在 `portfolio/` 下）确保行为不变。
- 重构后进行代码审查，确保质量；不破坏现有视觉系统与组件对外 API。
- 若项目中存在大量不符合新规范的代码，明确向 AI 说明当前任务为"重构"，并强制要求遵循新规则。

## 6. Git 提交规范

- 每次完成新功能开发时自动提交一次 Git 版本。
- 提交信息使用中文，简明描述本次变更的目的（如"新增天气应用预览组件"）。
- 不提交 `node_modules/`、`dist/` 等构建产物（见 `portfolio/.gitignore`）。

## 7. 基础交互与语言

- 所有回答都使用中文表述。
- 如需提供代码，为关键逻辑和可能造成理解困难的部分添加简明的中文注释。
- 当生成的代码超过 20 行时，优先考虑是否可以进行适当的抽象或聚合。
