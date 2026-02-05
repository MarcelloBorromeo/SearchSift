/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ["class"],
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Teal palette
        teal: {
          50: '#f0fdfa',
          100: '#ccfbf1',
          200: '#99f6e4',
          300: '#5eead4',
          400: '#2dd4bf',
          500: '#14b8a6',
          600: '#0d9488',
          700: '#0f766e',
          800: '#115e59',
          900: '#134e4a',
        },
        // Terracotta palette
        terracotta: {
          50: '#fdf4f3',
          100: '#fce8e6',
          200: '#f9d5d0',
          300: '#f4b5ac',
          400: '#ec8b7b',
          500: '#e07055',
          600: '#cc5540',
          700: '#ab4434',
          800: '#8e3b2f',
          900: '#76352c',
        },
        // Complementary accents
        sand: {
          50: '#fdfcfa',
          100: '#f7f4ef',
          200: '#ede6db',
          300: '#dfd3c3',
          400: '#cdb9a5',
          500: '#bda08a',
        },
        cream: '#faf7f2',
      },
      borderRadius: {
        lg: 'var(--radius)',
        md: 'calc(var(--radius) - 2px)',
        sm: 'calc(var(--radius) - 4px)',
      },
      backdropBlur: {
        xs: '2px',
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
}
