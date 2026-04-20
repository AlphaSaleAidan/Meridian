/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        meridian: {
          50: '#eef7ff',
          100: '#d9edff',
          200: '#bce0ff',
          300: '#8ecdff',
          400: '#59b0ff',
          500: '#338bff',
          600: '#1b6af5',
          700: '#1454e1',
          800: '#1744b6',
          900: '#193c8f',
          950: '#142657',
        },
        // Premium redesign tokens
        pm: {
          bg:      '#0A0A0B',
          surface: '#111113',
          border:  '#1F1F23',
          text:    '#F5F5F7',
          muted:   '#A1A1A8',
          violet:  '#7C5CFF',
          cyan:    '#4FE3C1',
        },
        slate: {
          850: '#172033',
          950: '#0b1120',
        },
      },
      fontFamily: {
        sans:  ['Geist Sans', 'Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono:  ['Geist Mono', 'JetBrains Mono', 'Fira Code', 'monospace'],
        serif: ['Instrument Serif', 'Georgia', 'serif'],
      },
      maxWidth: {
        content: '1240px',
      },
      spacing: {
        18: '4.5rem',
        22: '5.5rem',
      },
      backdropBlur: {
        '20': '20px',
      },
      animation: {
        'float': 'float 6s ease-in-out infinite',
        'float-slow': 'float-slow 8s ease-in-out infinite',
        'grain': 'grain 8s steps(10) infinite',
      },
      keyframes: {
        float: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-12px)' },
        },
        'float-slow': {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-8px)' },
        },
        grain: {
          '0%, 100%': { transform: 'translate(0, 0)' },
          '10%': { transform: 'translate(-5%, -10%)' },
          '30%': { transform: 'translate(3%, -15%)' },
          '50%': { transform: 'translate(12%, 9%)' },
          '70%': { transform: 'translate(9%, 4%)' },
          '90%': { transform: 'translate(-1%, 7%)' },
        },
      },
    },
  },
  plugins: [],
}
