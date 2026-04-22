/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        meridian: {
          50: '#e6f5fc',
          100: '#c0e5f8',
          200: '#8dcef2',
          300: '#53b4ea',
          400: '#2da0e2',
          500: '#1A8FD6',
          600: '#1574B8',
          700: '#0F5A94',
          800: '#0B3D6B',
          900: '#072A4D',
          950: '#041A32',
        },
        // Premium redesign tokens – now blue-teal to match logo
        pm: {
          bg:      '#0A0A0B',
          surface: '#111113',
          border:  '#1F1F23',
          text:    '#F5F5F7',
          muted:   '#A1A1A8',
          blue:    '#1A8FD6',
          teal:    '#17C5B0',
          // Legacy aliases (kept for any remaining references)
          violet:  '#1A8FD6',
          cyan:    '#17C5B0',
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
