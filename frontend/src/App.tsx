import { lazy, Suspense } from 'react'
import { Routes, Route, Navigate, Outlet } from 'react-router-dom'
import { Analytics } from '@vercel/analytics/react'
import { AuthProvider } from '@/lib/auth'
import { SalesAuthProvider } from '@/lib/sales-auth'
import ErrorBoundary from '@/components/ErrorBoundary'
import ProtectedRoute from '@/components/ProtectedRoute'
import Layout from '@/components/Layout'
import DemoLayout from '@/components/DemoLayout'

import CustomerLoginPage from '@/pages/customer/CustomerLoginPage'
import CustomerSignupPage from '@/pages/customer/CustomerSignupPage'
import CanadaLoginPage from '@/pages/customer/CanadaLoginPage'

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
import SpaceTab from '@/pages/SpaceTab'

const LandingPage = lazy(() => import('@/pages/LandingPage'))
const CanadaLayout = lazy(() => import('@/components/CanadaLayout'))
const CustomerOnboardingWizard = lazy(() => import('@/pages/customer/CustomerOnboardingWizard'))
const CareersPage = lazy(() => import('@/pages/CareersPage'))
const AdminPage = lazy(() => import('@/pages/AdminPage'))
const ITDashboardPage = lazy(() => import('@/pages/ITDashboardPage'))
const POSCoveragePage = lazy(() => import('@/pages/admin/POSCoveragePage'))

const SalesLayout = lazy(() => import('@/pages/sales/SalesLayout'))
const SalesLoginPage = lazy(() => import('@/pages/sales/SalesLoginPage'))
const SalesSignupPage = lazy(() => import('@/pages/sales/SalesSignupPage'))
const SalesDashboardPage = lazy(() => import('@/pages/sales/SalesDashboardPage'))
const SalesLeadsPage = lazy(() => import('@/pages/sales/LeadsPage'))
const SalesLeadDetailPage = lazy(() => import('@/pages/sales/LeadDetailPage'))
const SalesAccountsPage = lazy(() => import('@/pages/sales/AccountsPage'))
const SalesCreateCustomerPage = lazy(() => import('@/pages/sales/CreateCustomerPage'))
const SalesTeamPage = lazy(() => import('@/pages/sales/TeamManagementPage'))
const SalesTrainingPage = lazy(() => import('@/pages/sales/TrainingPage'))
const SalesSettingsPage = lazy(() => import('@/pages/sales/SalesSettingsPage'))

const CanadaLandingPage = lazy(() => import('@/pages/canada/CanadaLandingPage'))
const CanadaCareersPage = lazy(() => import('@/pages/canada/CanadaCareersPage'))
const CanadaSalesLayout = lazy(() => import('@/pages/canada/portal/CanadaSalesLayout'))
const CanadaPortalLoginPage = lazy(() => import('@/pages/canada/portal/CanadaPortalLoginPage'))
const CanadaPortalSignupPage = lazy(() => import('@/pages/canada/portal/CanadaPortalSignupPage'))
const CanadaSalesProtectedRoute = lazy(() => import('@/pages/canada/portal/CanadaSalesProtectedRoute'))
const CanadaPortalDashboardPage = lazy(() => import('@/pages/canada/portal/CanadaPortalDashboardPage'))
const CanadaPortalLeadsPage = lazy(() => import('@/pages/canada/portal/CanadaPortalLeadsPage'))
const CanadaPortalLeadDetailPage = lazy(() => import('@/pages/canada/portal/CanadaPortalLeadDetailPage'))
const CanadaPortalAccountsPage = lazy(() => import('@/pages/canada/portal/CanadaPortalAccountsPage'))
const CanadaPortalTeamPage = lazy(() => import('@/pages/canada/portal/CanadaPortalTeamPage'))
const CanadaPortalTrainingPage = lazy(() => import('@/pages/canada/portal/CanadaPortalTrainingPage'))
const CanadaPortalSettingsPage = lazy(() => import('@/pages/canada/portal/CanadaPortalSettingsPage'))
const CanadaPortalCreateCustomerPage = lazy(() => import('@/pages/canada/portal/CanadaPortalCreateCustomerPage'))


function CanadaProtectedRoute({ children }: { children: React.ReactNode }) {
  return <ProtectedRoute loginPath="/canada/login" allowSalesReps>{children}</ProtectedRoute>
}

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
      <Route path="space" element={<SpaceTab />} />
      <Route path="notifications" element={<NotificationsPage />} />
      <Route path="settings" element={<SettingsPage />} />
    </>
  )
}

function SalesProtectedRoute({ children }: { children: React.ReactNode }) {
  return <ProtectedRoute loginPath="/sales/login" allowSalesReps>{children}</ProtectedRoute>
}

export default function App() {
  return (
    <ErrorBoundary>
      <AuthProvider>
        <SalesAuthProvider>
          <Suspense fallback={<LazyFallback />}>
            <Routes>
              {/* ══════════════════════════════════════════════
                  PUBLIC PAGES — no auth required
                  ══════════════════════════════════════════════ */}
              <Route path="/" element={<LandingPage />} />
              <Route path="/landing" element={<LandingPage />} />
              <Route path="/careers" element={<CareersPage />} />

              {/* ══════════════════════════════════════════════
                  CUSTOMER ONBOARDING — public link from sales rep
                  ══════════════════════════════════════════════ */}
              <Route path="/onboard" element={
                <Suspense fallback={<LazyFallback />}>
                  <CustomerOnboardingWizard />
                </Suspense>
              } />

              {/* ══════════════════════════════════════════════
                  CUSTOMER AUTH — business owners
                  ══════════════════════════════════════════════ */}
              <Route path="/customer/login" element={<CustomerLoginPage />} />
              <Route path="/customer/signup" element={<CustomerSignupPage />} />

              <Route path="/customer/admin" element={
                <ProtectedRoute>
                  <AdminPage />
                </ProtectedRoute>
              } />

              {/* IT Health Dashboard — admin/owner only */}
              <Route path="/admin/it-health" element={
                <ProtectedRoute>
                  <Suspense fallback={<LazyFallback />}>
                    <Layout />
                  </Suspense>
                </ProtectedRoute>
              }>
                <Route index element={
                  <Suspense fallback={<LazyFallback />}>
                    <ITDashboardPage />
                  </Suspense>
                } />
              </Route>

              {/* POS Coverage — admin only */}
              <Route path="/admin/pos-coverage" element={
                <ProtectedRoute>
                  <Suspense fallback={<LazyFallback />}>
                    <Layout />
                  </Suspense>
                </ProtectedRoute>
              }>
                <Route index element={
                  <Suspense fallback={<LazyFallback />}>
                    <POSCoveragePage />
                  </Suspense>
                } />
              </Route>

              {/* Customer dashboard — protected, requires business owner auth */}
              <Route path="/app" element={
                <ProtectedRoute>
                  <Layout />
                </ProtectedRoute>
              }>
                {CustomerDashboardRoutes()}
              </Route>

              {/* Demo — open access, no auth required */}
              <Route path="/demo" element={<DemoLayout />}>
                {CustomerDashboardRoutes()}
                <Route path="pos-coverage" element={
                  <Suspense fallback={<LazyFallback />}>
                    <POSCoveragePage />
                  </Suspense>
                } />
              </Route>

              {/* ══════════════════════════════════════════════
                  CANADA — public pages
                  ══════════════════════════════════════════════ */}
              <Route path="/canada" element={<CanadaLandingPage />} />
              <Route path="/canada/landing" element={<CanadaLandingPage />} />
              <Route path="/canada/careers" element={<CanadaCareersPage />} />

              {/* ══════════════════════════════════════════════
                  CANADA — customer auth + dashboard
                  ══════════════════════════════════════════════ */}
              <Route path="/canada/login" element={<CanadaLoginPage />} />
              <Route path="/canada/dashboard" element={
                <CanadaProtectedRoute>
                  <Suspense fallback={<LazyFallback />}>
                    <CanadaLayout />
                  </Suspense>
                </CanadaProtectedRoute>
              }>
                {CustomerDashboardRoutes()}
              </Route>

              {/* ══════════════════════════════════════════════
                  CANADA — sales portal (native React CRM)
                  ══════════════════════════════════════════════ */}
              <Route path="/canada/portal/login" element={<CanadaPortalLoginPage />} />
              <Route path="/canada/portal/signup" element={<CanadaPortalSignupPage />} />
              <Route path="/canada/portal" element={
                <CanadaSalesProtectedRoute>
                  <Suspense fallback={<LazyFallback />}>
                    <CanadaSalesLayout />
                  </Suspense>
                </CanadaSalesProtectedRoute>
              }>
                <Route index element={<Navigate to="/canada/portal/dashboard" replace />} />
                <Route path="dashboard" element={<CanadaPortalDashboardPage />} />
                <Route path="leads" element={<CanadaPortalLeadsPage />} />
                <Route path="leads/:id" element={<CanadaPortalLeadDetailPage />} />
                <Route path="new-customer" element={<CanadaPortalCreateCustomerPage />} />
                <Route path="accounts" element={<CanadaPortalAccountsPage />} />
                <Route path="training" element={<CanadaPortalTrainingPage />} />
                <Route path="team" element={<CanadaPortalTeamPage />} />
                <Route path="settings" element={<CanadaPortalSettingsPage />} />
              </Route>

              {/* ══════════════════════════════════════════════
                  SALES CRM — native React portal
                  ══════════════════════════════════════════════ */}
              <Route path="/sales/login" element={<SalesLoginPage />} />
              <Route path="/sales/signup" element={<SalesSignupPage />} />
              <Route path="/sales" element={
                <SalesProtectedRoute>
                  <Suspense fallback={<LazyFallback />}>
                    <SalesLayout />
                  </Suspense>
                </SalesProtectedRoute>
              }>
                <Route index element={<Navigate to="/sales/dashboard" replace />} />
                <Route path="dashboard" element={<SalesDashboardPage />} />
                <Route path="leads" element={<SalesLeadsPage />} />
                <Route path="leads/:id" element={<SalesLeadDetailPage />} />
                <Route path="new-customer" element={<SalesCreateCustomerPage />} />
                <Route path="accounts" element={<SalesAccountsPage />} />
                <Route path="training" element={<SalesTrainingPage />} />
                <Route path="team" element={<SalesTeamPage />} />
                <Route path="settings" element={<SalesSettingsPage />} />
              </Route>

              {/* ══════════════════════════════════════════════
                  LEGACY REDIRECTS
                  ══════════════════════════════════════════════ */}
              <Route path="/get-started" element={<Navigate to="/customer/signup" replace />} />
              <Route path="/portal" element={<Navigate to="/customer/login" replace />} />
              <Route path="/portal/*" element={<Navigate to="/customer/login" replace />} />
              <Route path="/login" element={<Navigate to="/customer/login" replace />} />
              <Route path="/signup" element={<Navigate to="/customer/signup" replace />} />
              <Route path="/onboarding" element={<Navigate to="/customer/signup" replace />} />

              {/* Catch-all → landing page */}
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </Suspense>
        </SalesAuthProvider>
      </AuthProvider>
      <Analytics />
    </ErrorBoundary>
  )
}
