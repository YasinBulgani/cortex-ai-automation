import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: "var(--bg)",
        "bg-subtle": "var(--bg-subtle)",
        fg: "var(--fg)",
        muted: "var(--muted)",
        "muted-fg": "var(--muted-fg)",
        border: "var(--border)",
        "border-strong": "var(--border-strong)",
        accent: "var(--accent)",
        "accent-fg": "var(--accent-fg)",
        "accent-subtle": "var(--accent-subtle)",
        ai: "var(--ai)",
        "ai-fg": "var(--ai-fg)",
        "ai-subtle": "var(--ai-subtle)",
        success: "var(--success)",
        "success-fg": "var(--success-fg)",
        "success-subtle": "var(--success-subtle)",
        warning: "var(--warning)",
        "warning-fg": "var(--warning-fg)",
        "warning-subtle": "var(--warning-subtle)",
        danger: "var(--danger)",
        "danger-fg": "var(--danger-fg)",
        "danger-subtle": "var(--danger-subtle)",
      },
      borderRadius: {
        DEFAULT: "var(--radius)",
        lg: "var(--radius-lg)",
      },
      fontFamily: {
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
      },
      boxShadow: {
        sm: "var(--shadow-sm)",
        elevated: "var(--shadow-elevated)",
        lg: "var(--shadow-lg)",
      },
    },
  },
  plugins: [],
};

export default config;
