import typography from "@tailwindcss/typography";
import type { Config } from "tailwindcss";

/**
 * Brand colours are CSS variables (see globals.css) set per organisation from GET /branding:
 *  - brand  → deep ground colour (login panel, headings)
 *  - accent → secondary accent
 *  - teal   → the highlight colour used by buttons and links (the organisation's "highlight")
 *  - ground → the dark surfaces (sidebar, primary button)
 */
const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "rgb(var(--brand-50) / <alpha-value>)",
          100: "rgb(var(--brand-100) / <alpha-value>)",
          200: "rgb(var(--brand-200) / <alpha-value>)",
          300: "rgb(var(--brand-300) / <alpha-value>)",
          400: "rgb(var(--brand-400) / <alpha-value>)",
          500: "rgb(var(--brand-500) / <alpha-value>)",
          600: "rgb(var(--brand-600) / <alpha-value>)",
          700: "rgb(var(--brand-700) / <alpha-value>)",
          800: "rgb(var(--brand-800) / <alpha-value>)",
          900: "rgb(var(--brand-900) / <alpha-value>)",
        },
        accent: {
          50: "rgb(var(--accent-50) / <alpha-value>)",
          100: "rgb(var(--accent-100) / <alpha-value>)",
          200: "rgb(var(--accent-200) / <alpha-value>)",
          300: "rgb(var(--accent-300) / <alpha-value>)",
          400: "rgb(var(--accent-400) / <alpha-value>)",
          500: "rgb(var(--accent-500) / <alpha-value>)",
          600: "rgb(var(--accent-600) / <alpha-value>)",
          700: "rgb(var(--accent-700) / <alpha-value>)",
          800: "rgb(var(--accent-800) / <alpha-value>)",
          900: "rgb(var(--accent-900) / <alpha-value>)",
        },
        teal: {
          50: "rgb(var(--teal-50) / <alpha-value>)",
          100: "rgb(var(--teal-100) / <alpha-value>)",
          200: "rgb(var(--teal-200) / <alpha-value>)",
          300: "rgb(var(--teal-300) / <alpha-value>)",
          400: "rgb(var(--teal-400) / <alpha-value>)",
          500: "rgb(var(--teal-500) / <alpha-value>)",
          600: "rgb(var(--teal-600) / <alpha-value>)",
          700: "rgb(var(--teal-700) / <alpha-value>)",
          800: "rgb(var(--teal-800) / <alpha-value>)",
          900: "rgb(var(--teal-900) / <alpha-value>)",
        },
        ground: {
          DEFAULT: "rgb(var(--ground) / <alpha-value>)",
          button: "rgb(var(--ground-button) / <alpha-value>)",
        },
      },
      fontFamily: {
        sans: [
          "var(--font-vazirmatn)",
          "Vazirmatn",
          "Tahoma",
          "system-ui",
          "sans-serif",
        ],
      },
      boxShadow: {
        card: "0 10px 40px -12px rgba(18, 26, 102, 0.25)",
      },
      keyframes: {
        "fade-up": {
          "0%": { opacity: "0", transform: "translateY(12px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        float: {
          "0%, 100%": { transform: "translateY(0)" },
          "50%": { transform: "translateY(-10px)" },
        },
      },
      animation: {
        "fade-up": "fade-up 0.5s ease-out both",
        float: "float 6s ease-in-out infinite",
      },
    },
  },
  plugins: [typography],
};

export default config;
