import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Brand palette
        brand: {
          50:  "#eef2ff",
          100: "#e0e7ff",
          200: "#c7d2fe",
          300: "#a5b4fc",
          400: "#818cf8",
          500: "#6366f1",  // Primary
          600: "#4f46e5",
          700: "#4338ca",
          800: "#3730a3",
          900: "#312e81",
          950: "#1e1b4b",
        },
        // Surface system (dark-first)
        surface: {
          0:   "#111113",  // App background
          1:   "#18181b",  // Card surface
          2:   "#1c1c1f",  // Elevated card
          3:   "#27272a",  // Input / hover
          4:   "#3f3f46",  // Divider
        },
        // Semantic
        success: { DEFAULT: "#10b981", light: "#d1fae5" },
        warning: { DEFAULT: "#f59e0b", light: "#fef3c7" },
        danger:  { DEFAULT: "#ef4444", light: "#fee2e2" },
        info:    { DEFAULT: "#06b6d4", light: "#cffafe" },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "Fira Code", "monospace"],
      },
      fontSize: {
        "2xs": ["0.625rem", { lineHeight: "0.875rem" }],
      },
      borderRadius: {
        DEFAULT: "0.5rem",
        sm: "0.375rem",
        md: "0.5rem",
        lg: "0.75rem",
        xl: "1rem",
        "2xl": "1.25rem",
      },
      boxShadow: {
        card:    "0 1px 3px rgba(0,0,0,0.4), 0 1px 2px rgba(0,0,0,0.3)",
        "card-hover": "0 4px 12px rgba(0,0,0,0.5)",
        glow:    "0 0 20px rgba(99,102,241,0.15)",
        "glow-lg": "0 0 40px rgba(99,102,241,0.25)",
      },
      animation: {
        "fade-in":    "fadeIn 0.2s ease-out",
        "slide-up":   "slideUp 0.3s ease-out",
        "slide-in":   "slideIn 0.25s ease-out",
        "pulse-slow": "pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        "spin-slow":  "spin 2s linear infinite",
      },
      keyframes: {
        fadeIn: {
          "0%":   { opacity: "0" },
          "100%": { opacity: "1" },
        },
        slideUp: {
          "0%":   { transform: "translateY(8px)", opacity: "0" },
          "100%": { transform: "translateY(0)",   opacity: "1" },
        },
        slideIn: {
          "0%":   { transform: "translateX(-8px)", opacity: "0" },
          "100%": { transform: "translateX(0)",    opacity: "1" },
        },
      },
      backgroundImage: {
        "gradient-brand": "linear-gradient(135deg, #6366f1, #8b5cf6)",
        "gradient-dark":  "linear-gradient(180deg, #18181b 0%, #111113 100%)",
        "grid-pattern":   "radial-gradient(circle, #27272a 1px, transparent 1px)",
      },
    },
  },
  plugins: [],
};

export default config;
