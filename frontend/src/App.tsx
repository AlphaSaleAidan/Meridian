import { Routes, Route, Navigate } from 'react-router-dom'
import Layout from '@/components/Layout'
import LandingPage from '@/pages/LandingPage'
import OnboardingPage from '@/pages/OnboardingPage'
import OverviewPage from '@/pages/OverviewPage'
import RevenuePage from '@/pages/RevenuePage'
import ProductsPage from '@/pages/ProductsPage'
import InsightsPage from '@/pages/InsightsPage'
import ForecastsPage from '@/pages/ForecastsPage'
import NotificationsPage from '@/pages/NotificationsPage'
import SettingsPage from '@/pages/SettingsPage'
import InventoryPage from '@/pages/InventoryPage'

export default function App() {
  return (
    <Routes>
      {/* Public pages */}
      <Route path="/landing" element={<LandingPage />} />
      <Route path="/onboarding" element={<OnboardingPage />} />

      {/* Dashboard (demo mode) */}
      <Route path="/demo" element={<Layout />}>
        <Route index element={<OverviewPage />} />
        <Route path="revenue" element={<RevenuePage />} />
        <Route path="products" element={<ProductsPage />} />
        <Route path="inventory" element={<InventoryPage />} />
        <Route path="insights" element={<InsightsPage />} />
        <Route path="forecasts" element={<ForecastsPage />} />
        <Route path="notifications" element={<NotificationsPage />} />
        <Route path="settings" element={<SettingsPage />} />
      </Route>

      {/* Dashboard (authenticated - future) */}
      <Route path="/app" element={<Layout />}>
        <Route index element={<OverviewPage />} />
        <Route path="revenue" element={<RevenuePage />} />
        <Route path="products" element={<ProductsPage />} />
        <Route path="inventory" element={<InventoryPage />} />
        <Route path="insights" element={<InsightsPage />} />
        <Route path="forecasts" element={<ForecastsPage />} />
        <Route path="notifications" element={<NotificationsPage />} />
        <Route path="settings" element={<SettingsPage />} />
      </Route>

      {/* Root → landing page */}
      <Route path="/" element={<Navigate to="/landing" replace />} />
      <Route path="*" element={<Navigate to="/landing" replace />} />
    </Routes>
  )
}
