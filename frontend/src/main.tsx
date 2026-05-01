import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { H } from 'highlight.run'
import posthog from 'posthog-js'
import App from './App'
import './index.css'

const HIGHLIGHT_PROJECT_ID = import.meta.env.VITE_HIGHLIGHT_PROJECT_ID || ''
if (HIGHLIGHT_PROJECT_ID) {
  H.init(HIGHLIGHT_PROJECT_ID, {
    serviceName: 'meridian-dashboard',
    tracingOrigins: true,
    networkRecording: { enabled: true, recordHeadersAndBody: false },
    environment: import.meta.env.MODE,
  })
}

const POSTHOG_KEY = import.meta.env.VITE_POSTHOG_KEY || ''
if (POSTHOG_KEY) {
  posthog.init(POSTHOG_KEY, {
    api_host: import.meta.env.VITE_POSTHOG_HOST || 'https://us.i.posthog.com',
    capture_pageview: true,
    capture_pageleave: true,
  })
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>
)
