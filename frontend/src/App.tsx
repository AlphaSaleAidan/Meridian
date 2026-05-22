import { lazy, Suspense } from 'react'
import { Routes, Route, Navigate, Outlet, useLocation } from 'react-router-dom'
import { Analytics } from '@vercel/analytics/react'
import { AuthProvider } from '@/lib/auth'
import { SalesAuthProvider } from '@/lib/sales-auth'
import { ToastProvider } from '@/components/Toast'
import ErrorBoundary from '@/components/ErrorBoundary'
import ProtectedRoute from '@/components/ProtectedRoute'
import Layout from '@/components/Layout'
import DemoLayout from '@/components/DemoLayout'
import { DemoContextProvider } from '@/lib/demo-context'
import BusinessTypeSelector from '@/components/BusinessTypeSelector'

import CustomerLoginPage from '@/pages/customer/CustomerLoginPage'
import CustomerSignupPage from '@/pages/customer/CustomerSignupPage'
import CanadaLoginPage from '@/pages/customer/CanadaLoginPage'
import CustomerPortalRedirect from '@/pages/customer/CustomerPortalRedirect'

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
import PhoneOrdersPage from '@/pages/PhoneOrdersPage'

const SchedulePage = lazy(() => import('@/pages/SchedulePage'))
const MyWebsitePage = lazy(() => import('@/pages/MyWebsitePage'))
const MerchantSitePage = lazy(() => import('@/pages/MerchantSitePage'))
const CameraAnalyticsDemoPage = lazy(() => import('@/pages/CameraAnalyticsDemoPage'))
const CameraIntelligencePage = lazy(() => import('@/pages/CameraIntelligencePage'))

const LandingPage = lazy(() => import('@/pages/LandingPage'))
const CanadaLayout = lazy(() => import('@/components/CanadaLayout'))
const CustomerOnboardingWizard = lazy(() => import('@/pages/customer/CustomerOnboardingWizard'))
const CareersPage = lazy(() => import('@/pages/CareersPage'))
const AdminPage = lazy(() => import('@/pages/AdminPage'))
const ITDashboardPage = lazy(() => import('@/pages/ITDashboardPage'))
const POSCoveragePage = lazy(() => import('@/pages/admin/POSCoveragePage'))
const EmailDashboardPage = lazy(() => import('@/pages/admin/EmailDashboardPage'))


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
const CanadaPortalCommissionsPage = lazy(() => import('@/pages/canada/portal/CanadaPortalCommissionsPage'))
const CanadaPortalSettingsPage = lazy(() => import('@/pages/canada/portal/CanadaPortalSettingsPage'))
const CanadaPortalCreateCustomerPage = lazy(() => import('@/pages/canada/portal/CanadaPortalCreateCustomerPage'))
const CanadaPortalOnboardingPage = lazy(() => import('@/pages/canada/portal/CanadaPortalOnboardingPage'))
const CanadaCustomerOnboardingWizard = lazy(() => import('@/pages/canada/portal/CanadaCustomerOnboardingWizard'))
const CanadaInvoicePage = lazy(() => import('@/pages/canada/CanadaInvoicePage'))
const CanadaSetupPage = lazy(() => import('@/pages/canada/CanadaSetupPage'))

const UnsubscribePage = lazy(() => import('@/components/compliance/UnsubscribePage'))

const USSalesLayout = lazy(() => import('@/pages/us/portal/USSalesLayout'))
const USPortalLoginPage = lazy(() => import('@/pages/us/portal/USPortalLoginPage'))
const USPortalSignupPage = lazy(() => import('@/pages/us/portal/USPortalSignupPage'))
const USSalesProtectedRoute = lazy(() => import('@/pages/us/portal/USSalesProtectedRoute'))
const USPortalDashboardPage = lazy(() => import('@/pages/us/portal/USPortalDashboardPage'))
const USPortalLeadsPage = lazy(() => import('@/pages/us/portal/USPortalLeadsPage'))
const USPortalLeadDetailPage = lazy(() => import('@/pages/us/portal/USPortalLeadDetailPage'))
const USPortalAccountsPage = lazy(() => import('@/pages/us/portal/USPortalAccountsPage'))
const USPortalTeamPage = lazy(() => import('@/pages/us/portal/USPortalTeamPage'))
const USPortalTrainingPage = lazy(() => import('@/pages/us/portal/USPortalTrainingPage'))
const USPortalCommissionsPage = lazy(() => import('@/pages/us/portal/USPortalCommissionsPage'))
const USPortalSettingsPage = lazy(() => import('@/pages/us/portal/USPortalSettingsPage'))
const USPortalCreateCustomerPage = lazy(() => import('@/pages/us/portal/USPortalCreateCustomerPage'))
const USPortalOnboardingPage = lazy(() => import('@/pages/us/portal/USPortalOnboardingPage'))
const USCustomerOnboardingWizard = lazy(() => import('@/pages/us/portal/USCustomerOnboardingWizard'))

const RestaurantsPage = lazy(() => import('@/pages/seo/RestaurantsPage'))
const CoffeeShopsPage = lazy(() => import('@/pages/seo/CoffeeShopsPage'))
const AutoShopsPage = lazy(() => import('@/pages/seo/AutoShopsPage'))
const FastFoodPage = lazy(() => import('@/pages/seo/FastFoodPage'))
const SmokeShopsPage = lazy(() => import('@/pages/seo/SmokeShopsPage'))
const SquareIntegrationPage = lazy(() => import('@/pages/seo/SquareIntegrationPage'))
const ToastIntegrationPage = lazy(() => import('@/pages/seo/ToastIntegrationPage'))
const CloverIntegrationPage = lazy(() => import('@/pages/seo/CloverIntegrationPage'))
const CityIndustryPage = lazy(() => import('@/pages/seo/CityIndustryPage'))


function CanadaProtectedRoute({ children }: { children: React.ReactNode }) {
  return <ProtectedRoute loginPath="/canada/login">{children}</ProtectedRoute>
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

function InlineFallback() {
  return (
    <div className="flex items-center justify-center py-20">
      <div className="w-6 h-6 rounded-md bg-[#1A8FD6]/15 border border-[#1A8FD6]/30 flex items-center justify-center animate-pulse">
        <span className="text-[#1A8FD6] font-bold text-[10px]">M</span>
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
      <Route path="camera-intelligence" element={<Suspense fallback={<InlineFallback />}><CameraIntelligencePage /></Suspense>} />
      <Route path="customers" element={<CustomersPage />} />
      <Route path="staff" element={<StaffPage />} />
      <Route path="peak-hours" element={<PeakHoursPage />} />
      <Route path="margins" element={<MarginsPage />} />
      <Route path="menu-matrix" element={<MenuEngineeringPage />} />
      <Route path="anomalies" element={<AnomaliesPage />} />
      <Route path="schedule" element={<Suspense fallback={<InlineFallback />}><SchedulePage /></Suspense>} />
      <Route path="space" element={<SpaceTab />} />
      <Route path="phone-orders" element={<PhoneOrdersPage />} />
      <Route path="my-website" element={<Suspense fallback={<InlineFallback />}><MyWebsitePage /></Suspense>} />
      <Route path="notifications" element={<NotificationsPage />} />
      <Route path="settings" element={<SettingsPage />} />
    </>
  )
}

function SubdomainRedirector() {
  const location = useLocation()
  const host = window.location.hostname

  // canada.meridian.tips → prepend /canada to path
  if (host === 'canada.meridian.tips' && !location.pathname.startsWith('/canada')) {
    const target = `/canada${location.pathname}${location.search}${location.hash}`
    return <Navigate to={target} replace />
  }

  return null
}

export default function App() {
  return (
    <ErrorBoundary>
      <AuthProvider>
        <SalesAuthProvider>
          <ToastProvider>
          <Suspense fallback={<LazyFallback />}>
            <SubdomainRedirector />
            <Routes>
              {/* ══════════════════════════════════════════════
                  PUBLIC PAGES — no auth required
                  ══════════════════════════════════════════════ */}
              <Route path="/" element={<LandingPage />} />
              <Route path="/landing" element={<LandingPage />} />
              <Route path="/careers" element={<CareersPage />} />

              {/* SEO — Industry landing pages */}
              <Route path="/for/restaurants" element={<RestaurantsPage />} />
              <Route path="/for/coffee-shops" element={<CoffeeShopsPage />} />
              <Route path="/for/auto-shops" element={<AutoShopsPage />} />
              <Route path="/for/fast-food" element={<FastFoodPage />} />
              <Route path="/for/smoke-shops" element={<SmokeShopsPage />} />

              {/* SEO — POS integration pages */}
              <Route path="/integrations/square" element={<SquareIntegrationPage />} />
              <Route path="/integrations/toast" element={<ToastIntegrationPage />} />
              <Route path="/integrations/clover" element={<CloverIntegrationPage />} />

              {/* SEO — Programmatic city x industry pages (160+) */}
              <Route path="/analytics/:industry/:citySlug" element={<CityIndustryPage />} />

              {/* PUBLIC MERCHANT WEBSITES — no auth */}
              <Route path="/sites/:slug" element={
                <Suspense fallback={<LazyFallback />}>
                  <MerchantSitePage />
                </Suspense>
              } />

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
              <Route path="/c/:token" element={<CustomerPortalRedirect />} />

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

              {/* Email Dashboard — admin only */}
              <Route path="/admin/email" element={
                <ProtectedRoute>
                  <Suspense fallback={<LazyFallback />}>
                    <Layout />
                  </Suspense>
                </ProtectedRoute>
              }>
                <Route index element={
                  <Suspense fallback={<LazyFallback />}>
                    <EmailDashboardPage />
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
                <Route path="camera-analytics" element={
                  <Suspense fallback={<LazyFallback />}>
                    <CameraAnalyticsDemoPage />
                  </Suspense>
                } />
              </Route>

              {/* ══════════════════════════════════════════════
                  CANADA — public pages
                  ══════════════════════════════════════════════ */}
              <Route path="/canada" element={<CanadaLandingPage />} />
              <Route path="/canada/landing" element={<CanadaLandingPage />} />
              <Route path="/canada/careers" element={<CanadaCareersPage />} />

              {/* Canada Demo — same dashboard with CAD currency */}
              <Route path="/canada/demo" element={<DemoLayout />}>
                {CustomerDashboardRoutes()}
                <Route path="camera-analytics" element={
                  <Suspense fallback={<LazyFallback />}>
                    <CameraAnalyticsDemoPage />
                  </Suspense>
                } />
              </Route>

              {/* ══════════════════════════════════════════════
                  CANADA — customer auth + dashboard
                  ══════════════════════════════════════════════ */}
              <Route path="/canada/login" element={<CanadaLoginPage />} />
              <Route path="/canada/setup" element={
                <Suspense fallback={<LazyFallback />}>
                  <CanadaSetupPage />
                </Suspense>
              } />
              <Route path="/canada/invoice/:invoiceId" element={<Suspense fallback={<LazyFallback />}><CanadaInvoicePage /></Suspense>} />
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
              <Route path="/canada/onboard" element={
                <Suspense fallback={<LazyFallback />}>
                  <CanadaCustomerOnboardingWizard />
                </Suspense>
              } />
              <Route path="/canada/portal/login" element={<CanadaPortalLoginPage />} />
              <Route path="/canada/portal/signup" element={<CanadaPortalSignupPage />} />
              <Route path="/canada/portal/onboarding" element={
                <CanadaSalesProtectedRoute>
                  <Suspense fallback={<LazyFallback />}>
                    <CanadaPortalOnboardingPage />
                  </Suspense>
                </CanadaSalesProtectedRoute>
              } />
              <Route path="/canada/portal" element={
                <CanadaSalesProtectedRoute>
                  <Suspense fallback={<LazyFallback />}>
                    <CanadaSalesLayout />
                  </Suspense>
                </CanadaSalesProtectedRoute>
              }>
                <Route index element={<Navigate to="/canada/portal/dashboard" replace />} />
                <Route path="dashboard" element={<Suspense fallback={<InlineFallback />}><CanadaPortalDashboardPage /></Suspense>} />
                <Route path="leads" element={<Suspense fallback={<InlineFallback />}><CanadaPortalLeadsPage /></Suspense>} />
                <Route path="leads/:id" element={<Suspense fallback={<InlineFallback />}><CanadaPortalLeadDetailPage /></Suspense>} />
                <Route path="new-customer" element={<Suspense fallback={<InlineFallback />}><CanadaPortalCreateCustomerPage /></Suspense>} />
                <Route path="accounts" element={<Suspense fallback={<InlineFallback />}><CanadaPortalAccountsPage /></Suspense>} />
                <Route path="commissions" element={<Suspense fallback={<InlineFallback />}><CanadaPortalCommissionsPage /></Suspense>} />
                <Route path="training" element={<Suspense fallback={<InlineFallback />}><CanadaPortalTrainingPage /></Suspense>} />
                <Route path="team" element={<Suspense fallback={<InlineFallback />}><CanadaPortalTeamPage /></Suspense>} />
                <Route path="settings" element={<Suspense fallback={<InlineFallback />}><CanadaPortalSettingsPage /></Suspense>} />
              </Route>

              {/* ══════════════════════════════════════════════
                  US — sales portal (native React CRM)
                  ══════════════════════════════════════════════ */}
              <Route path="/us/onboard" element={
                <Suspense fallback={<LazyFallback />}>
                  <USCustomerOnboardingWizard />
                </Suspense>
              } />
              <Route path="/us/portal/login" element={<Suspense fallback={<LazyFallback />}><USPortalLoginPage /></Suspense>} />
              <Route path="/us/portal/signup" element={<Suspense fallback={<LazyFallback />}><USPortalSignupPage /></Suspense>} />
              <Route path="/us/portal/onboarding" element={
                <Suspense fallback={<LazyFallback />}>
                  <USSalesProtectedRoute>
                    <USPortalOnboardingPage />
                  </USSalesProtectedRoute>
                </Suspense>
              } />
              <Route path="/us/portal" element={
                <Suspense fallback={<LazyFallback />}>
                  <USSalesProtectedRoute>
                    <USSalesLayout />
                  </USSalesProtectedRoute>
                </Suspense>
              }>
                <Route index element={<Navigate to="/us/portal/dashboard" replace />} />
                <Route path="dashboard" element={<Suspense fallback={<InlineFallback />}><USPortalDashboardPage /></Suspense>} />
                <Route path="leads" element={<Suspense fallback={<InlineFallback />}><USPortalLeadsPage /></Suspense>} />
                <Route path="leads/:id" element={<Suspense fallback={<InlineFallback />}><USPortalLeadDetailPage /></Suspense>} />
                <Route path="new-customer" element={<Suspense fallback={<InlineFallback />}><USPortalCreateCustomerPage /></Suspense>} />
                <Route path="accounts" element={<Suspense fallback={<InlineFallback />}><USPortalAccountsPage /></Suspense>} />
                <Route path="commissions" element={<Suspense fallback={<InlineFallback />}><USPortalCommissionsPage /></Suspense>} />
                <Route path="training" element={<Suspense fallback={<InlineFallback />}><USPortalTrainingPage /></Suspense>} />
                <Route path="team" element={<Suspense fallback={<InlineFallback />}><USPortalTeamPage /></Suspense>} />
                <Route path="settings" element={<Suspense fallback={<InlineFallback />}><USPortalSettingsPage /></Suspense>} />
              </Route>

              {/* Legacy /sales/* redirect to new US portal */}
              <Route path="/sales/*" element={<Navigate to="/us/portal" replace />} />

              {/* ══════════════════════════════════════════════
                  LEGACY REDIRECTS
                  ══════════════════════════════════════════════ */}
              <Route path="/try" element={<Navigate to="/canada/demo" replace />} />
              <Route path="/get-started" element={<Navigate to="/customer/signup" replace />} />
              <Route path="/portal" element={<Navigate to="/customer/login" replace />} />
              <Route path="/portal/*" element={<Navigate to="/customer/login" replace />} />
              <Route path="/login" element={<Navigate to="/customer/login" replace />} />
              <Route path="/signup" element={<Navigate to="/customer/signup" replace />} />
              <Route path="/onboarding" element={<Navigate to="/customer/signup" replace />} />

              {/* Unsubscribe -- public, no auth */}
              <Route path="/unsubscribe" element={<Suspense fallback={<LazyFallback />}><UnsubscribePage /></Suspense>} />

              {/* Catch-all → landing page */}
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </Suspense>
          </ToastProvider>
        </SalesAuthProvider>
      </AuthProvider>
      <Analytics />
    </ErrorBoundary>
  )
}
