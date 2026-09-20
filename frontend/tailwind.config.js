/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        paper: "#F5F6F2",
        ink: {
          DEFAULT: "#16213A",
          soft: "#3A4A66",
          faint: "#7C8AA3",
        },
        blueprint: {
          DEFAULT: "#1D5FA8",
          dark: "#164A85",
          light: "#E8F0FA",
        },
        signal: {
          DEFAULT: "#E8A33D",
          dark: "#C6821F",
          light: "#FCF1DE",
        },
        circuit: {
          DEFAULT: "#0F9B8E",
          light: "#E2F6F3",
        },
        graph: "#D8DEE9",
      },
      fontFamily: {
        sans: ["Space Grotesk", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "monospace"],
      },
      backgroundImage: {
        "grid-paper":
          "linear-gradient(to right, #D8DEE9 1px, transparent 1px), linear-gradient(to bottom, #D8DEE9 1px, transparent 1px)",
      },
      backgroundSize: {
        grid: "28px 28px",
      },
    },
  },
  plugins: [],
};
