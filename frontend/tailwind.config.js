/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'Menlo', 'monospace'],
      },
      colors: {
        studio: {
          950: '#090a0d',
          900: '#0e0f14',
          850: '#121318',
          800: '#181920',
          700: '#232530',
        }
      }
    },
  },
  plugins: [],
}
