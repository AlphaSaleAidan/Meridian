# Meridian — Stack Reference

## Bundler & Framework
- Vite + React + TypeScript (NOT Next.js)
- Entry: frontend/src/main.tsx
- Global styles: frontend/src/index.css
- Router: react-router-dom v6 (NOT Next.js file routing)

## Hosting
- Frontend: Railway (NOT Vercel)
- Backend: FastAPI on Railway (api.meridian.tips)
- DB: Supabase (PostgreSQL)
- Domain: meridian.tips

## Portals
- US landing: frontend/src/pages/LandingPage.tsx
- Canada landing: frontend/src/pages/canada/CanadaLandingPage.tsx
- Canada portal: frontend/src/pages/canada/portal/
- Province-based feature flags for Quebec Edition

## Font Stack
- Geist Sans + Geist Mono, self-hosted via npm (not CDN)

## Key Dependencies (check versions before upgrading)
- three: ^0.184.0 (@react-three/fiber ^8.17.10, @react-three/drei ^9.115.0)
- tailwindcss: ^3.4.3
- framer-motion: ^12.38.0
- lenis: ^1.3.23
- react: ^18.3.1
- vite: ^5.2.12
- typescript: ^5.4.5

## Backend
- FastAPI (Python) at src/api/routes/
- Routes: admin, billing, canada, careers, dashboard, email, oauth, onboarding
- Supabase client for DB access (not raw psycopg2)

## Common Mistakes to Avoid
- This is NOT Next.js — no `next/image`, no `next/link`, no `getServerSideProps`
- Frontend is NOT on Vercel — it's Railway
- Do NOT use CDN fonts — Geist is installed via npm
- Do NOT upgrade Three.js past 0.184 without checking r158+ breaking changes
- Always run `cat frontend/package.json` before adding dependencies
- Always run `cd frontend && npx tsc --noEmit` after frontend changes
