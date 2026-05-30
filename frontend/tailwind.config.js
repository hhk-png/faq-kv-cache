/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'dark-bg': '#0f1117',
        'dark-card': '#1a1d27',
        'dark-border': '#2d3143',
        'dark-text': '#e8eaed',
        'dark-text-secondary': '#9aa0a6',
        'accent': '#a78bfa',
        'accent-hover': '#c4b5fd',
        'success': '#34d399',
        'danger': '#f87171',
      },
      fontFamily: {
        sans: ['PingFang SC', 'Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      borderRadius: {
        'xl': '0.75rem',
        '2xl': '1rem',
      },
      boxShadow: {
        'card-hover': '0 0 20px rgba(167,139,250,0.05)',
        'glow': '0 0 20px rgba(167,139,250,0.15)',
      },
    },
  },
  plugins: [],
}
