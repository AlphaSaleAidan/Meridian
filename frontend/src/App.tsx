import { lazy, Suspense } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from '@/lib/auth'
import { SalesAuthProvider } from '@/lib/sales-auth'
import ErrorBoundary from '@/components/ErrorBoundary'
import ProtectedRoute from '@/components/ProtectedRoute'
import SalesProtectedRoute from '@/components/SalesProtectedRoute'
import Layout from '@/components/Layout'
import SalesLayout from '@/components/SalesLayout'

import SalesLoginPage from '@/pages/sales/SalesLoginPage'
import SalesSignupPage from '@/pages/sales/SalesSignupPage'
import SalesDashboardPage from '@/pages/sales/SalesDashboardPage'
import LeadsPage from '@/pages/sales/LeadsPage'
import AccountsPage from '@/pages/sales/AccountsPage'
import TrainingPage from '@/pages/sales/TrainingPage'
import TeamManagementPage from '@/pages/sales/TeamManagementPage'
import SalesSettingsPage from '@/pages/sales/SalesSettingsPage'

import CustomerLoginPage from '@/pages/customer/CustomerLoginPage'
import CustomerSignupPage from '@/pages/customer/CustomerSignupPage'

import OverviewPage from '@/pages/OverviewPage'
import RevenuePage from '@/pages/RevenuePage'
import ProductsPage from '@/pages/ProductsPage'
import InsightsPage from '@/pages/InsightsPage'
import ForecastsPage from '@/pages/ForecastsPage'
import NotificationsPage from '@/pages/NotificationsPage'
import SettingsPage from '@/pages/SettingsPage'
import InventoryPage from '@/pages/InventoryPage'
import AgentDashboardPage from '@/pages/AgentDashboardPage'
import ActionsPage from '@/pages/ActionsPage'
import CustomersPage from '@/pages/CustomersPage'
import StaffPage from '@/pages/StaffPage'
import PeakHoursPage from '@/pages/PeakHoursPage'
import MarginsPage from '@/pages/MarginsPage'
import MenuEngineeringPage from '@/pages/MenuEngineeringPage'
import AnomaliesPage from '@/pages/AnomaliesPage'

const LandingPage = lazy(() => import('@/pages/LandingPage'))
const OnboardingPage = lazy(() => import('@/pages/OnboardingPage'))
const CareersPage = lazy(() => import('@/pages/CareersPage'))
const AdminPage = lazy(() => import('@/pages/AdminPage'))

function LazyFallback() {
  return (
    <div className="min-h-screen bg-[#0A0A0B] flex items-center justify-center">
      <div className="w-8 h-8 rounded-lg bg-[#1A8FD6]/15 border border-[#1A8FD6]/30 flex items-center justify-center animate-pulse">
        <span className="text-[#1A8FD6] font-bold text-sm">M</span>
      </div>
    </div>
  )
}

function CustomerDashboardRoutes() {
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
    <ErrorBoundary>
      <AuthProvider>
        <SalesAuthProvider>
          <Suspense fallback={<LazyFallback />}>
            <Routes>
              {/* ══════════════════════════════════════════════
                  SALES CRM (Internal — Sales Reps)
                  ══════════════════════════════════════════════ */}
              <Route path="/login" element={<SalesLoginPage />} />
              <Route path="/signup" element={<SalesSignupPage />} />

              <Route element={
                <SalesProtectedRoute>
                  <SalesLayout />
                </SalesProtectedRoute>
              }>
                <Route path="/dashboard" element={<SalesDashboardPage />} />
                <Route path="/leads" element={<LeadsPage />} />
                <Route path="/accounts" element={<AccountsPage />} />
                <Route path="/training" element={<TrainingPage />} />
                <Route path="/settings" element={<SalesSettingsPage />} />
                <Route path="/admin" element={<TeamManagementPage />} />
              </Route>

              <Route path="/onboarding" element={
                <SalesProtectedRoute>
                  <Suspense fallback={<LazyFallback />}>
                    <OnboardingPage />
                  </Suspense>
                </SalesProtectedRoute>
              } />

              <Route path="/setup" element={
                <SalesProtectedRoute>
                  <Suspense fallback={<LazyFallback />}>
                    <OnboardingPage />
                  </Suspense>
                </SalesProtectedRoute>
              } />

              {/* ══════════════════════════════════════════════
                  CUSTOMER APP (Business Owners)
                  ══════════════════════════════════════════════ */}
              <Route path="/customer/login" element={<CustomerLoginPage />} />
              <Route path="/customer/signup" element={<CustomerSignupPage />} />

              {/* Legacy /portal route — redirect to customer login */}
              <Route path="/portal" element={<Navigate to="/customer/login" replace />} />
              <Route path="/portal/*" element={<Navigate to="/customer/login" replace />} />

              <Route path="/customer/admin" element={
                <ProtectedRoute>
                  <AdminPage />
                </ProtectedRoute>
              } />

              {/* Customer dashboard — protected, requires customer auth */}
              <Route path="/app" element={
                <ProtectedRoute>
                  <Layout />
                </ProtectedRoute>
              }>
                {CustomerDashboardRoutes()}
              </Route>

              {/* Demo — open access, no auth required */}
              <Route path="/demo" element={<Layout />}>
                {CustomerDashboardRoutes()}
              </Route>

              {/* ══════════════════════════════════════════════
                  PUBLIC PAGES
                  ══════════════════════════════════════════════ */}
              <Route path="/landing" element={<LandingPage />} />
              <Route path="/careers" element={<CareersPage />} />

              {/* Default: sales reps go to login */}
              <Route path="/" element={<Navigate to="/login" replace />} />
              <Route path="*" element={<Navigate to="/login" replace />} />
            </Routes>
          </Suspense>
        </SalesAuthProvider>
      </AuthProvider>
    </ErrorBoundary>
  )
}
