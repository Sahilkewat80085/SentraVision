/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          500: "#10b981",
          700: "#047857"
        }
      }
    }
  },
  plugins: []
};
