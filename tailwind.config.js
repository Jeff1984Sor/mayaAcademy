/** @type {import('tailwindcss').Config} */
// Paleta do padrão MayaCorp (igual ao MayaJus/MayaFit).
module.exports = {
  content: ["./templates/**/*.html", "./**/templates/**/*.html", "./static/js/app/**/*.js", "./static/js/estudio/**/*.js"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        navy: { DEFAULT: "#1E2D6B", 50: "#EEF1FA", 100: "#DDE2F0", 600: "#1E2D6B", 700: "#18245A", 800: "#131C47" },
        indigo: { DEFAULT: "#7C8FFF", 100: "#E6EAFF", 200: "#C9D1FF", 300: "#A9B5FF", 400: "#7C8FFF", 500: "#5F74F5" },
        teal: { DEFAULT: "#1A8F5E", 50: "#E5F5EE", 100: "#DDF3E8", 600: "#1A8F5E", 700: "#146E48" },
        amber: { DEFAULT: "#F5A623", 50: "#FEF6E7", 100: "#FDECC8", 500: "#F5A623", 700: "#9A5F05" },
        perigo: { DEFAULT: "#C94343", 50: "#FBE4E4", 600: "#C94343", 700: "#A93636" },
        dark: { DEFAULT: "#0F1729", 800: "#17213B", 700: "#1F2B4A", 600: "#2C3A5E" },
        cinza: { DEFAULT: "#F7F8FC" },
      },
      fontFamily: {
        sans: ['"DM Sans"', "system-ui", "-apple-system", "Segoe UI", "Roboto", "Arial", "sans-serif"],
        mono: ['"JetBrains Mono"', "ui-monospace", "Consolas", "monospace"],
      },
    },
  },
  plugins: [],
};
