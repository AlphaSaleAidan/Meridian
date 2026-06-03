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
          // ── Phase 3: Canada portal palette ───────────────────────────────
          // Distinct from pm.bg/surface/border (which are neutral-dark).
          // The Canada sales portal is built on a green-tinted dark theme;
          // these tokens preserve that visual without forcing pm.* to shift.
          accent: '#00d4aa', // Canada brand accent (CTAs, focus, success)
          canada: {
            bg:           '#0a0f0d', // page background
            surface:      '#0f1512', // card / surface
            border:       '#1a2420', // border
            'text-muted': '#6b7a74', // muted body text on Canada dark
            'text-faint': '#4a5550', // faint label/secondary text
          },
          amber: {
            gold:   '#f0b429', // earned commissions, MRR target
            orange: '#f59e0b', // stale / urgent / past-due
          },
          purple: '#7c3aed', // admin / team violet (NOT pm.violet, which is the legacy pm.blue alias)
          indigo: '#7C5CFF', // pending payout (semantically distinct from pm.purple)
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
      // Phase 3: Canada portal type ramp. `2xs` absorbs the 10px+11px drift;
      // `sm-tight` preserves the deliberate 13px base used throughout the
      // onboarding wizard / new-customer flow.
      fontSize: {
        '2xs':      ['11px', { lineHeight: '14px' }],
        'sm-tight': ['13px', { lineHeight: '18px' }],
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
