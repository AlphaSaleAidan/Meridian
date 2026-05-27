import { lazy, Suspense, useEffect } from 'react'
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

const CustomerLoginPage = lazy(() => import('@/pages/customer/CustomerLoginPage'))
const CustomerSignupPage = lazy(() => import('@/pages/customer/CustomerSignupPage'))
const CanadaLoginPage = lazy(() => import('@/pages/customer/CanadaLoginPage'))
const CustomerPortalRedirect = lazy(() => import('@/pages/customer/CustomerPortalRedirect'))

const OverviewPage = lazy(() => import('@/pages/OverviewPage'))
const RevenuePage = lazy(() => import('@/pages/RevenuePage'))
const ProductsPage = lazy(() => import('@/pages/ProductsPage'))
const InsightsPage = lazy(() => import('@/pages/InsightsPage'))
const ForecastsPage = lazy(() => import('@/pages/ForecastsPage'))
const NotificationsPage = lazy(() => import('@/pages/NotificationsPage'))
const SettingsPage = lazy(() => import('@/pages/SettingsPage'))
const InventoryPage = lazy(() => import('@/pages/InventoryPage'))
const AgentDashboardPage = lazy(() => import('@/pages/AgentDashboardPage'))
const ActionsPage = lazy(() => import('@/pages/ActionsPage'))
const CustomersPage = lazy(() => import('@/pages/CustomersPage'))
const StaffPage = lazy(() => import('@/pages/StaffPage'))
const PeakHoursPage = lazy(() => import('@/pages/PeakHoursPage'))
const MarginsPage = lazy(() => import('@/pages/MarginsPage'))
const MenuEngineeringPage = lazy(() => import('@/pages/MenuEngineeringPage'))
const AnomaliesPage = lazy(() => import('@/pages/AnomaliesPage'))
const SpaceTab = lazy(() => import('@/pages/SpaceTab'))
const PhoneOrdersPage = lazy(() => import('@/pages/PhoneOrdersPage'))

const SchedulePage = lazy(() => import('@/pages/SchedulePage'))
const MyWebsitePage = lazy(() => import('@/pages/MyWebsitePage'))
const MerchantSitePage = lazy(() => import('@/pages/MerchantSitePage'))
const CameraAnalyticsDemoPage = lazy(() => import('@/pages/CameraAnalyticsDemoPage'))

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
const WhatIsPosAnalyticsPage = lazy(() => import('@/pages/seo/WhatIsPosAnalyticsPage'))
const VsSpreadsheetsPage = lazy(() => import('@/pages/seo/VsSpreadsheetsPage'))
const VsToastAnalyticsPage = lazy(() => import('@/pages/seo/VsToastAnalyticsPage'))
const VsSquareAnalyticsPage = lazy(() => import('@/pages/seo/VsSquareAnalyticsPage'))
const VsCloverAnalyticsPage = lazy(() => import('@/pages/seo/VsCloverAnalyticsPage'))
const VsRestaurant365Page = lazy(() => import('@/pages/seo/VsRestaurant365Page'))
const VsMarketManPage = lazy(() => import('@/pages/seo/VsMarketManPage'))
const VsDorPage = lazy(() => import('@/pages/seo/VsDorPage'))
const VsPlacerAiPage = lazy(() => import('@/pages/seo/VsPlacerAiPage'))
const VsFootTrafficCountersPage = lazy(() => import('@/pages/seo/VsFootTrafficCountersPage'))
const CameraIntelligencePage = lazy(() => import('@/pages/seo/CameraIntelligencePage'))
const FAQHubPage = lazy(() => import('@/pages/seo/FAQHubPage'))
const BestAnalyticsSoftwarePage = lazy(() => import('@/pages/seo/BestAnalyticsSoftwarePage'))
const FoodCostCalculatorPage = lazy(() => import('@/pages/seo/FoodCostCalculatorPage'))
const PrimeCostCalculatorPage = lazy(() => import('./pages/seo/PrimeCostCalculatorPage'))
const MenuPricingCalculatorPage = lazy(() => import('./pages/seo/MenuPricingCalculatorPage'))
const PhoneAgentPage = lazy(() => import('./pages/seo/PhoneAgentPage'))
const BlogIndexPage = lazy(() => import('@/pages/blog/BlogIndexPage'))
const RestaurantProfitabilityArticle = lazy(() => import('@/pages/blog/RestaurantProfitabilityArticle'))
const FootTrafficAnalyticsArticle = lazy(() => import('@/pages/blog/FootTrafficAnalyticsArticle'))
const GuidesIndexPage = lazy(() => import('@/pages/guides/GuidesIndexPage'))
const GuidePage = lazy(() => import('@/pages/guides/GuidePage'))


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
      <Route index element={<Suspense fallback={<InlineFallback />}><OverviewPage /></Suspense>} />
      <Route path="revenue" element={<Suspense fallback={<InlineFallback />}><RevenuePage /></Suspense>} />
      <Route path="products" element={<Suspense fallback={<InlineFallback />}><ProductsPage /></Suspense>} />
      <Route path="inventory" element={<Suspense fallback={<InlineFallback />}><InventoryPage /></Suspense>} />
      <Route path="insights" element={<Suspense fallback={<InlineFallback />}><InsightsPage /></Suspense>} />
      <Route path="forecasts" element={<Suspense fallback={<InlineFallback />}><ForecastsPage /></Suspense>} />
      <Route path="agents" element={<Suspense fallback={<InlineFallback />}><AgentDashboardPage /></Suspense>} />
      <Route path="actions" element={<Suspense fallback={<InlineFallback />}><ActionsPage /></Suspense>} />
      <Route path="customers" element={<Suspense fallback={<InlineFallback />}><CustomersPage /></Suspense>} />
      <Route path="staff" element={<Suspense fallback={<InlineFallback />}><StaffPage /></Suspense>} />
      <Route path="peak-hours" element={<Suspense fallback={<InlineFallback />}><PeakHoursPage /></Suspense>} />
      <Route path="margins" element={<Suspense fallback={<InlineFallback />}><MarginsPage /></Suspense>} />
      <Route path="menu-matrix" element={<Suspense fallback={<InlineFallback />}><MenuEngineeringPage /></Suspense>} />
      <Route path="anomalies" element={<Suspense fallback={<InlineFallback />}><AnomaliesPage /></Suspense>} />
      <Route path="schedule" element={<Suspense fallback={<InlineFallback />}><SchedulePage /></Suspense>} />
      <Route path="space" element={<Suspense fallback={<InlineFallback />}><SpaceTab /></Suspense>} />
      <Route path="phone-orders" element={<Suspense fallback={<InlineFallback />}><PhoneOrdersPage /></Suspense>} />
      <Route path="my-website" element={<Suspense fallback={<InlineFallback />}><MyWebsitePage /></Suspense>} />
      <Route path="notifications" element={<Suspense fallback={<InlineFallback />}><NotificationsPage /></Suspense>} />
      <Route path="settings" element={<Suspense fallback={<InlineFallback />}><SettingsPage /></Suspense>} />
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

function useLenis() {
  useEffect(() => {
    let lenis: any = null
    let rafId: number | null = null
    let observer: MutationObserver | null = null

    observer = new MutationObserver(() => {
      const wrapper = document.querySelector('main')
      if (!wrapper || lenis) return
      observer?.disconnect()
      import('lenis').then((mod) => {
        const Lenis = mod.default
        lenis = new Lenis({
          lerp: 0.08,
          smoothWheel: true,
          wrapper: wrapper as HTMLElement,
          content: wrapper.firstElementChild as HTMLElement,
        })
        const raf = (time: number) => {
          lenis.raf(time)
          rafId = requestAnimationFrame(raf)
        }
        rafId = requestAnimationFrame(raf)
      })
    })
    observer.observe(document.body, { childList: true, subtree: true })

    return () => {
      observer?.disconnect()
      if (rafId !== null) cancelAnimationFrame(rafId)
      lenis?.destroy()
    }
  }, [])
}

export default function App() {
  useLenis()
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

              {/* SEO — Comparison & educational pages */}
              <Route path="/what-is-pos-analytics" element={<WhatIsPosAnalyticsPage />} />
              <Route path="/vs/spreadsheets" element={<VsSpreadsheetsPage />} />
              <Route path="/vs/toast-analytics" element={<VsToastAnalyticsPage />} />
              <Route path="/vs/square-analytics" element={<VsSquareAnalyticsPage />} />
              <Route path="/vs/clover-analytics" element={<VsCloverAnalyticsPage />} />
              <Route path="/vs/restaurant365" element={<VsRestaurant365Page />} />
              <Route path="/vs/marketman" element={<VsMarketManPage />} />
              <Route path="/vs/dor" element={<VsDorPage />} />
              <Route path="/vs/placer-ai" element={<VsPlacerAiPage />} />
              <Route path="/vs/foot-traffic-counters" element={<VsFootTrafficCountersPage />} />
              <Route path="/features/camera-intelligence" element={<CameraIntelligencePage />} />
              <Route path="/best-restaurant-analytics-software" element={<BestAnalyticsSoftwarePage />} />
              <Route path="/faq" element={<FAQHubPage />} />
              <Route path="/tools/food-cost-calculator" element={<FoodCostCalculatorPage />} />
              <Route path="/tools/prime-cost-calculator" element={<Suspense fallback={<div className="min-h-screen bg-zinc-950" />}><PrimeCostCalculatorPage /></Suspense>} />
              <Route path="/tools/menu-pricing-calculator" element={<Suspense fallback={<div className="min-h-screen bg-zinc-950" />}><MenuPricingCalculatorPage /></Suspense>} />
              <Route path="/features/phone-agent" element={<Suspense fallback={<div className="min-h-screen bg-zinc-950" />}><PhoneAgentPage /></Suspense>} />

              {/* Guides — intent-based SEO content */}
              <Route path="/guides" element={<GuidesIndexPage />} />
              <Route path="/guides/:slug" element={<GuidePage />} />

              {/* Blog */}
              <Route path="/blog" element={<BlogIndexPage />} />
              <Route path="/blog/how-to-know-if-restaurant-is-profitable" element={<RestaurantProfitabilityArticle />} />
              <Route path="/blog/restaurant-foot-traffic-analytics-guide" element={<FootTrafficAnalyticsArticle />} />

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
              <Route path="/customer/login" element={<Suspense fallback={<LazyFallback />}><CustomerLoginPage /></Suspense>} />
              <Route path="/customer/signup" element={<Suspense fallback={<LazyFallback />}><CustomerSignupPage /></Suspense>} />
              <Route path="/c/:token" element={<Suspense fallback={<LazyFallback />}><CustomerPortalRedirect /></Suspense>} />

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
              <Route path="/canada/login" element={<Suspense fallback={<LazyFallback />}><CanadaLoginPage /></Suspense>} />
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
