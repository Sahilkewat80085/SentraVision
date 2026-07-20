/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,jsx,ts,tsx}"
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#ecfdf5",
          100: "#d1fae5",
          500: "#10b981",
          700: "#047857",
          900: "#064e3b"
        }
      },
      fontFamily: {
        sans: ["Segoe UI", "Inter", "system-ui", "sans-serif"]
      }
    }
  },
  plugins: []
};

