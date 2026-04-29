import { Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from '@/lib/auth'
import ProtectedRoute from '@/components/ProtectedRoute'
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
import CareersPage from '@/pages/CareersPage'
import PortalPage from '@/pages/PortalPage'
import AgentDashboardPage from '@/pages/AgentDashboardPage'
import ActionsPage from '@/pages/ActionsPage'
import CustomersPage from '@/pages/CustomersPage'
import StaffPage from '@/pages/StaffPage'
import PeakHoursPage from '@/pages/PeakHoursPage'
import MarginsPage from '@/pages/MarginsPage'
import MenuEngineeringPage from '@/pages/MenuEngineeringPage'
import AnomaliesPage from '@/pages/AnomaliesPage'

function DashboardRoutes() {
  return (
    <>
      <Route index element={<OverviewPage />} />
      <Route path="revenue" element={<RevenuePage />} />
      <Route path="products" element={<ProductsPage />} />
      <Route path="inventory" element={<InventoryPage />} />
      <Route path="insights" element={<InsightsPage />} />
      <Route path="forecasts" element={<ForecastsPage />} />
      <Route path="agents" element={<AgentDashboardPage />} />
      <Route path="actions" element={<ActionsPage />} />
      <Route path="customers" element={<CustomersPage />} />
      <Route path="staff" element={<StaffPage />} />
      <Route path="peak-hours" element={<PeakHoursPage />} />
      <Route path="margins" element={<MarginsPage />} />
      <Route path="menu-matrix" element={<MenuEngineeringPage />} />
      <Route path="anomalies" element={<AnomaliesPage />} />
      <Route path="notifications" element={<NotificationsPage />} />
      <Route path="settings" element={<SettingsPage />} />
    </>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/landing" element={<LandingPage />} />
        <Route path="/onboarding" element={<OnboardingPage />} />
        <Route path="/careers" element={<CareersPage />} />
        <Route path="/portal" element={<PortalPage />} />
        <Route path="/portal/*" element={<PortalPage />} />

        {/* Demo — open access, no auth required */}
        <Route path="/demo" element={<Layout />}>
          {DashboardRoutes()}
        </Route>

        {/* App — protected, requires login */}
        <Route path="/app" element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }>
          {DashboardRoutes()}
        </Route>

        <Route path="/" element={<Navigate to="/landing" replace />} />
        <Route path="*" element={<Navigate to="/landing" replace />} />
      </Routes>
    </AuthProvider>
  )
}
