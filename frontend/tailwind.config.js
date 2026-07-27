/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
    "./electron/**/*.{js,ts}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
      },
      colors: {
        maya: {
          50:  "#f0f4ff",
          100: "#e0e9ff",
          200: "#c7d7fe",
          300: "#a5bcfc",
          400: "#8198f8",
          500: "#6370f1",
          600: "#4f4fe6",
          700: "#423ecb",
          800: "#3735a3",
          900: "#302f80",
          950: "#1e1c4b",
        },
      },
      backdropBlur: {
        xs: "2px",
      },
    },
  },
  plugins: [],
};
