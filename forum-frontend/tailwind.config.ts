import type { Config } from "tailwindcss";

const config: Config = {
  // 基于 class 的暗色模式：在 <html> 上切换 .dark
  darkMode: "class",
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      // 将品牌 CSS 变量映射为 Tailwind 颜色 token
      colors: {
        aidev: {
          // 品牌主色阶（Indigo）
          "primary-50": "var(--aidev-primary-50)",
          "primary-100": "var(--aidev-primary-100)",
          "primary-200": "var(--aidev-primary-200)",
          "primary-300": "var(--aidev-primary-300)",
          "primary-400": "var(--aidev-primary-400)",
          "primary-500": "var(--aidev-primary-500)",
          "primary-600": "var(--aidev-primary-600)",
          "primary-700": "var(--aidev-primary-700)",
          "primary-800": "var(--aidev-primary-800)",
          "primary-900": "var(--aidev-primary-900)",
          primary: "var(--aidev-primary)",
          "primary-foreground": "var(--aidev-primary-foreground)",
          // 中性色阶
          "neutral-0": "var(--aidev-neutral-0)",
          "neutral-50": "var(--aidev-neutral-50)",
          "neutral-100": "var(--aidev-neutral-100)",
          "neutral-200": "var(--aidev-neutral-200)",
          "neutral-300": "var(--aidev-neutral-300)",
          "neutral-400": "var(--aidev-neutral-400)",
          "neutral-500": "var(--aidev-neutral-500)",
          "neutral-600": "var(--aidev-neutral-600)",
          "neutral-700": "var(--aidev-neutral-700)",
          "neutral-800": "var(--aidev-neutral-800)",
          "neutral-900": "var(--aidev-neutral-900)",
          // 语义别名
          background: "var(--aidev-background)",
          foreground: "var(--aidev-foreground)",
          card: "var(--aidev-card)",
          "card-foreground": "var(--aidev-card-foreground)",
          popover: "var(--aidev-popover)",
          "popover-foreground": "var(--aidev-popover-foreground)",
          muted: "var(--aidev-muted)",
          "muted-foreground": "var(--aidev-muted-foreground)",
          border: "var(--aidev-border)",
          input: "var(--aidev-input)",
          ring: "var(--aidev-ring)",
          // 状态语义色
          success: "var(--aidev-state-success)",
          "success-bg": "var(--aidev-state-success-bg)",
          warning: "var(--aidev-state-warning)",
          "warning-bg": "var(--aidev-state-warning-bg)",
          error: "var(--aidev-state-error)",
          "error-bg": "var(--aidev-state-error-bg)",
          info: "var(--aidev-state-info)",
          "info-bg": "var(--aidev-state-info-bg)",
        },
      },
      borderRadius: {
        sm: "var(--aidev-radius-sm)",
        md: "var(--aidev-radius-md)",
        lg: "var(--aidev-radius-lg)",
        full: "var(--aidev-radius-full)",
      },
      fontFamily: {
        sans: "var(--aidev-font-sans)",
        mono: "var(--aidev-font-mono)",
      },
      boxShadow: {
        sm: "var(--aidev-shadow-sm)",
        md: "var(--aidev-shadow-md)",
        lg: "var(--aidev-shadow-lg)",
        float: "var(--aidev-shadow-float)",
      },
      maxWidth: {
        content: "var(--aidev-max-content)",
      },
      height: {
        header: "var(--aidev-header-height)",
      },
      width: {
        sidebar: "var(--aidev-sidebar-width)",
      },
    },
  },
  plugins: [],
};

export default config;
