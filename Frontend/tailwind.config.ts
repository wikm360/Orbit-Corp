import typography from "@tailwindcss/typography";
import type { Config } from "tailwindcss";

/**
 * Brand palette sampled from the Mehvar Gostar logo:
 *  - brand  (deep blue)  → frame + right mountain of the "M"
 *  - accent (yellow)     → left mountain
 *  - teal                → the highlight between the two peaks
 */
const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#eef0fb",
          100: "#dbdff6",
          200: "#b7bfee",
          300: "#8a97e2",
          400: "#5b6bd3",
          500: "#3446b8",
          600: "#22309e",
          700: "#182384",
          800: "#121a66",
          900: "#0c1247",
        },
        accent: {
          50: "#fefbe8",
          100: "#fdf5c2",
          300: "#f7e26b",
          400: "#efd23a",
          500: "#e8c523",
          600: "#c9a70f",
          700: "#9e820a",
        },
        teal: {
          50: "#ebfcfb",
          100: "#cbf7f4",
          300: "#6fe2dc",
          400: "#3fd0cb",
          500: "#25b8b4",
          600: "#1a9391",
          700: "#177574",
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
