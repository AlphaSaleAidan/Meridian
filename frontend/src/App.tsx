import { Routes, Route } from 'react-router-dom'
import Layout from '@/components/Layout'
import OverviewPage from '@/pages/OverviewPage'
import RevenuePage from '@/pages/RevenuePage'
import ProductsPage from '@/pages/ProductsPage'
import InsightsPage from '@/pages/InsightsPage'
import ForecastsPage from '@/pages/ForecastsPage'
import NotificationsPage from '@/pages/NotificationsPage'
import SettingsPage from '@/pages/SettingsPage'

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<OverviewPage />} />
        <Route path="/revenue" element={<RevenuePage />} />
        <Route path="/products" element={<ProductsPage />} />
        <Route path="/insights" element={<InsightsPage />} />
        <Route path="/forecasts" element={<ForecastsPage />} />
        <Route path="/notifications" element={<NotificationsPage />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Route>
    </Routes>
  )
}
