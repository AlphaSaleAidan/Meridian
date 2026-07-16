import { Suspense, useEffect } from 'react'
import { Routes, Route, Navigate, Outlet, useLocation } from 'react-router-dom'
import { AuthProvider } from '@/lib/auth'
import { SalesAuthProvider } from '@/lib/sales-auth'
import { ToastProvider } from '@/components/Toast'
import ErrorBoundary, { lazyRetry } from '@/components/ErrorBoundary'
import ProtectedRoute from '@/components/ProtectedRoute'
import Layout from '@/components/Layout'
import MerchantPillarPage from '@/pages/canada/merchant/MerchantPillarPage'
import { merchantPillars, demoMerchantPillars } from '@/config/merchantPillars'
import { DemoContextProvider } from '@/lib/demo-context'
import BusinessTypeSelector from '@/components/BusinessTypeSelector'
import CookieConsentBanner from '@/components/compliance/CookieConsentBanner'
import TrainingGate from '@/components/training/TrainingGate'
import { loadGA4, CONSENT_EVENT } from '@/lib/analytics'

const CustomerLoginPage = lazyRetry(() => import('@/pages/customer/CustomerLoginPage'))
const CustomerSignupPage = lazyRetry(() => import('@/pages/customer/CustomerSignupPage'))
const CanadaLoginPage = lazyRetry(() => import('@/pages/customer/CanadaLoginPage'))
const CustomerPortalRedirect = lazyRetry(() => import('@/pages/customer/CustomerPortalRedirect'))

const OverviewPage = lazyRetry(() => import('@/pages/OverviewPage'))
const RevenuePage = lazyRetry(() => import('@/pages/RevenuePage'))
const ProductsPage = lazyRetry(() => import('@/pages/ProductsPage'))
const InsightsPage = lazyRetry(() => import('@/pages/InsightsPage'))
const ForecastsPage = lazyRetry(() => import('@/pages/ForecastsPage'))
const NotificationsPage = lazyRetry(() => import('@/pages/NotificationsPage'))
const SettingsPage = lazyRetry(() => import('@/pages/SettingsPage'))
const InventoryPage = lazyRetry(() => import('@/pages/InventoryPage'))
const AgentDashboardPage = lazyRetry(() => import('@/pages/AgentDashboardPage'))
const ActionsPage = lazyRetry(() => import('@/pages/ActionsPage'))
const CustomersPage = lazyRetry(() => import('@/pages/CustomersPage'))
const StaffPage = lazyRetry(() => import('@/pages/StaffPage'))
const PeakHoursPage = lazyRetry(() => import('@/pages/PeakHoursPage'))
const MarginsPage = lazyRetry(() => import('@/pages/MarginsPage'))
const MenuEngineeringPage = lazyRetry(() => import('@/pages/MenuEngineeringPage'))
const AnomaliesPage = lazyRetry(() => import('@/pages/AnomaliesPage'))
const SpaceTab = lazyRetry(() => import('@/pages/SpaceTab'))
const PhoneOrdersPage = lazyRetry(() => import('@/pages/PhoneOrdersPage'))

const SchedulePage = lazyRetry(() => import('@/pages/SchedulePage'))
const CamConnectPage = lazyRetry(() => import('@/pages/CamConnectPage'))
const MyWebsitePage = lazyRetry(() => import('@/pages/MyWebsitePage'))
const MerchantSitePage = lazyRetry(() => import('@/pages/MerchantSitePage'))
const PublicMenuPage = lazyRetry(() => import('@/pages/PublicMenuPage'))
const ContentDashboardPage = lazyRetry(() => import('@/pages/ContentDashboardPage'))
const ContentSettingsPage = lazyRetry(() => import('@/pages/ContentSettingsPage'))

const LandingPage = lazyRetry(() => import('@/pages/LandingPage'))
const CanadaLayout = lazyRetry(() => import('@/components/CanadaLayout'))
const MerchantLayout = lazyRetry(() => import('@/components/MerchantLayout'))
const MerchantDemoLayout = lazyRetry(() => import('@/components/MerchantDemoLayout'))
const USMerchantDemoLayout = lazyRetry(() => import('@/components/USMerchantDemoLayout'))
const CustomerOnboardingWizard = lazyRetry(() => import('@/pages/customer/CustomerOnboardingWizard'))
const CareersPage = lazyRetry(() => import('@/pages/CareersPage'))
const AdminPage = lazyRetry(() => import('@/pages/AdminPage'))
const ITDashboardPage = lazyRetry(() => import('@/pages/ITDashboardPage'))
const POSCoveragePage = lazyRetry(() => import('@/pages/admin/POSCoveragePage'))
const EmailDashboardPage = lazyRetry(() => import('@/pages/admin/EmailDashboardPage'))


const CanadaLandingPage = lazyRetry(() => import('@/pages/canada/CanadaLandingPage'))
const CanadaCareersPage = lazyRetry(() => import('@/pages/canada/CanadaCareersPage'))
const CanadaSalesLayout = lazyRetry(() => import('@/pages/canada/portal/CanadaSalesLayout'))
const CanadaPortalLoginPage = lazyRetry(() => import('@/pages/canada/portal/CanadaPortalLoginPage'))
const CanadaPortalSignupPage = lazyRetry(() => import('@/pages/canada/portal/CanadaPortalSignupPage'))
const CanadaSalesProtectedRoute = lazyRetry(() => import('@/pages/canada/portal/CanadaSalesProtectedRoute'))
const CanadaPortalDashboardPage = lazyRetry(() => import('@/pages/canada/portal/CanadaPortalDashboardPage'))
const CanadaPortalLeadsPage = lazyRetry(() => import('@/pages/canada/portal/CanadaPortalLeadsPage'))
const CanadaPortalLeadDetailPage = lazyRetry(() => import('@/pages/canada/portal/CanadaPortalLeadDetailPage'))
const CanadaPortalAccountsPage = lazyRetry(() => import('@/pages/canada/portal/CanadaPortalAccountsPage'))
const CanadaPortalTeamPage = lazyRetry(() => import('@/pages/canada/portal/CanadaPortalTeamPage'))
const CanadaPortalTrainingPage = lazyRetry(() => import('@/pages/canada/portal/CanadaPortalTrainingPage'))
const CanadaPortalProposalsPage = lazyRetry(() => import('@/pages/canada/portal/CanadaPortalProposalsPage'))
const CanadaPortalSettingsPage = lazyRetry(() => import('@/pages/canada/portal/CanadaPortalSettingsPage'))
const CanadaPortalCreateCustomerPage = lazyRetry(() => import('@/pages/canada/portal/CanadaPortalCreateCustomerPage'))
const CanadaPortalOnboardingPage = lazyRetry(() => import('@/pages/canada/portal/CanadaPortalOnboardingPage'))
const CanadaCustomerOnboardingWizard = lazyRetry(() => import('@/pages/canada/portal/CanadaCustomerOnboardingWizard'))
const MerchantOnboardingWizard = lazyRetry(() => import('@/pages/canada/merchant/MerchantOnboardingWizard'))
const CanadaInvoicePage = lazyRetry(() => import('@/pages/canada/CanadaInvoicePage'))
const CanadaSetupPage = lazyRetry(() => import('@/pages/canada/CanadaSetupPage'))

const UnsubscribePage = lazyRetry(() => import('@/components/compliance/UnsubscribePage'))

const USSalesLayout = lazyRetry(() => import('@/pages/us/portal/USSalesLayout'))
const USPortalLoginPage = lazyRetry(() => import('@/pages/us/portal/USPortalLoginPage'))
const USPortalSignupPage = lazyRetry(() => import('@/pages/us/portal/USPortalSignupPage'))
const USSalesProtectedRoute = lazyRetry(() => import('@/pages/us/portal/USSalesProtectedRoute'))
const USPortalDashboardPage = lazyRetry(() => import('@/pages/us/portal/USPortalDashboardPage'))
const USPortalLeadsPage = lazyRetry(() => import('@/pages/us/portal/USPortalLeadsPage'))
const USPortalLeadDetailPage = lazyRetry(() => import('@/pages/us/portal/USPortalLeadDetailPage'))
const USPortalAccountsPage = lazyRetry(() => import('@/pages/us/portal/USPortalAccountsPage'))
const USPortalTeamPage = lazyRetry(() => import('@/pages/us/portal/USPortalTeamPage'))
const USPortalTrainingPage = lazyRetry(() => import('@/pages/us/portal/USPortalTrainingPage'))
const USPortalProposalsPage = lazyRetry(() => import('@/pages/us/portal/USPortalProposalsPage'))
const USPortalSettingsPage = lazyRetry(() => import('@/pages/us/portal/USPortalSettingsPage'))
const USPortalCreateCustomerPage = lazyRetry(() => import('@/pages/us/portal/USPortalCreateCustomerPage'))
const USPortalOnboardingPage = lazyRetry(() => import('@/pages/us/portal/USPortalOnboardingPage'))
const USCustomerOnboardingWizard = lazyRetry(() => import('@/pages/us/portal/USCustomerOnboardingWizard'))
const USLoginPage = lazyRetry(() => import('@/pages/customer/USLoginPage'))
const USSetupPage = lazyRetry(() => import('@/pages/customer/USSetupPage'))
const USInvoicePage = lazyRetry(() => import('@/pages/us/USInvoicePage'))
const USLayout = lazyRetry(() => import('@/components/USLayout'))
const USPortalBadgePage = lazyRetry(() => import('@/pages/us/portal/USPortalBadgePage'))
const CanadaPortalBadgePage = lazyRetry(() => import('@/pages/canada/portal/CanadaPortalBadgePage'))
const RepPublicBadgePage = lazyRetry(() => import('@/pages/RepPublicBadgePage'))
const WalletCardPage = lazyRetry(() => import('@/pages/WalletCardPage'))

const RestaurantsPage = lazyRetry(() => import('@/pages/seo/RestaurantsPage'))
const CoffeeShopsPage = lazyRetry(() => import('@/pages/seo/CoffeeShopsPage'))
const AutoShopsPage = lazyRetry(() => import('@/pages/seo/AutoShopsPage'))
const FastFoodPage = lazyRetry(() => import('@/pages/seo/FastFoodPage'))
const SmokeShopsPage = lazyRetry(() => import('@/pages/seo/SmokeShopsPage'))
const SquareIntegrationPage = lazyRetry(() => import('@/pages/seo/SquareIntegrationPage'))
const ToastIntegrationPage = lazyRetry(() => import('@/pages/seo/ToastIntegrationPage'))
const CloverIntegrationPage = lazyRetry(() => import('@/pages/seo/CloverIntegrationPage'))
const CityIndustryPage = lazyRetry(() => import('@/pages/seo/CityIndustryPage'))
const WhatIsPosAnalyticsPage = lazyRetry(() => import('@/pages/seo/WhatIsPosAnalyticsPage'))
const VsSpreadsheetsPage = lazyRetry(() => import('@/pages/seo/VsSpreadsheetsPage'))
const VsToastAnalyticsPage = lazyRetry(() => import('@/pages/seo/VsToastAnalyticsPage'))
const VsSquareAnalyticsPage = lazyRetry(() => import('@/pages/seo/VsSquareAnalyticsPage'))
const VsCloverAnalyticsPage = lazyRetry(() => import('@/pages/seo/VsCloverAnalyticsPage'))
const VsRestaurant365Page = lazyRetry(() => import('@/pages/seo/VsRestaurant365Page'))
const VsMarketManPage = lazyRetry(() => import('@/pages/seo/VsMarketManPage'))
const VsDorPage = lazyRetry(() => import('@/pages/seo/VsDorPage'))
const VsPlacerAiPage = lazyRetry(() => import('@/pages/seo/VsPlacerAiPage'))
const VsFootTrafficCountersPage = lazyRetry(() => import('@/pages/seo/VsFootTrafficCountersPage'))
const CameraIntelligencePage = lazyRetry(() => import('@/pages/seo/CameraIntelligencePage'))
const CameraIntelligenceDashboardPage = lazyRetry(() => import('@/pages/CameraIntelligencePage'))
const FAQHubPage = lazyRetry(() => import('@/pages/seo/FAQHubPage'))
const BestAnalyticsSoftwarePage = lazyRetry(() => import('@/pages/seo/BestAnalyticsSoftwarePage'))
const FoodCostCalculatorPage = lazyRetry(() => import('@/pages/seo/FoodCostCalculatorPage'))
const PrimeCostCalculatorPage = lazyRetry(() => import('./pages/seo/PrimeCostCalculatorPage'))
const MenuPricingCalculatorPage = lazyRetry(() => import('./pages/seo/MenuPricingCalculatorPage'))
const PhoneAgentPage = lazyRetry(() => import('./pages/seo/PhoneAgentPage'))
const BlogIndexPage = lazyRetry(() => import('@/pages/blog/BlogIndexPage'))
const RestaurantProfitabilityArticle = lazyRetry(() => import('@/pages/blog/RestaurantProfitabilityArticle'))
const FootTrafficAnalyticsArticle = lazyRetry(() => import('@/pages/blog/FootTrafficAnalyticsArticle'))
const GuidesIndexPage = lazyRetry(() => import('@/pages/guides/GuidesIndexPage'))
const GuidePage = lazyRetry(() => import('@/pages/guides/GuidePage'))
const FounderPage = lazyRetry(() => import('@/pages/about/FounderPage'))


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
      <Route path="camera-intelligence" element={<Suspense fallback={<InlineFallback />}><CameraIntelligenceDashboardPage /></Suspense>} />
      <Route path="my-website" element={<Suspense fallback={<InlineFallback />}><MyWebsitePage /></Suspense>} />
      <Route path="content" element={<Suspense fallback={<InlineFallback />}><ContentDashboardPage /></Suspense>} />
      <Route path="content/settings" element={<Suspense fallback={<InlineFallback />}><ContentSettingsPage /></Suspense>} />
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
  useEffect(() => {
    // Load GA4 if the visitor already consented (returning visitor), and whenever
    // consent is granted this session. No-op until VITE_GA4_ID is set + consent === 'all'.
    loadGA4()
    const onConsent = () => loadGA4()
    window.addEventListener(CONSENT_EVENT, onConsent)
    return () => window.removeEventListener(CONSENT_EVENT, onConsent)
  }, [])
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
              <Route path="/home" element={<LandingPage />} />
              <Route path="/landing" element={<Navigate to="/home" replace />} />
              {/* Zero-hardware camera connect (Path A): merchant opens this on a phone
                  they already own via a dashboard QR code. No app, no install. */}
              <Route path="/cam" element={<Suspense fallback={<LazyFallback />}><CamConnectPage /></Suspense>} />
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

              {/* About / founder — owned entity page for the company + CEO */}
              <Route path="/about" element={<FounderPage />} />
              <Route path="/founder" element={<Navigate to="/about" replace />} />

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

              {/* PUBLIC HOSTED MENUS — no auth. Same mechanism as /sites:
                  an SPA route served by the vercel.json catch-all rewrite. */}
              <Route path="/m/:slug" element={
                <Suspense fallback={<LazyFallback />}>
                  <PublicMenuPage />
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
              {/* US Demo — public merchant portal with synthetic USD data,
                  mirroring /canada/demo. The classic full-dashboard demo is
                  archived on branch archive/us-classic-portal-20260712. */}
              <Route path="/demo" element={
                <Suspense fallback={<LazyFallback />}>
                  <USMerchantDemoLayout />
                </Suspense>
              }>
                {demoMerchantPillars.map(pillar => (
                  <Route
                    key={pillar.path || '_home'}
                    index={pillar.path === ''}
                    path={pillar.path ? `${pillar.path}/*` : undefined}
                    element={<MerchantPillarPage pillar={pillar} />}
                  />
                ))}
              </Route>

              {/* ══════════════════════════════════════════════
                  CANADA — public pages
                  ══════════════════════════════════════════════ */}
              <Route path="/canada" element={<CanadaLandingPage />} />
              <Route path="/canada/landing" element={<CanadaLandingPage />} />
              <Route path="/canada/careers" element={<CanadaCareersPage />} />

              {/* Canada Demo — public merchant portal with synthetic CAD data (no auth, no tour) */}
              <Route path="/canada/demo" element={
                <Suspense fallback={<LazyFallback />}>
                  <MerchantDemoLayout />
                </Suspense>
              }>
                {demoMerchantPillars.map(pillar => (
                  <Route
                    key={pillar.path || '_home'}
                    index={pillar.path === ''}
                    path={pillar.path ? `${pillar.path}/*` : undefined}
                    element={<MerchantPillarPage pillar={pillar} />}
                  />
                ))}
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
                  CANADA — merchant portal (trimmed 3-pillar product)
                  ══════════════════════════════════════════════ */}
              <Route path="/canada/merchant/onboard" element={
                <CanadaProtectedRoute>
                  <Suspense fallback={<LazyFallback />}>
                    <MerchantOnboardingWizard />
                  </Suspense>
                </CanadaProtectedRoute>
              } />
              <Route path="/canada/merchant" element={
                <CanadaProtectedRoute>
                  <Suspense fallback={<LazyFallback />}>
                    <MerchantLayout />
                  </Suspense>
                </CanadaProtectedRoute>
              }>
                {merchantPillars.map(pillar => (
                  <Route
                    key={pillar.path || '_home'}
                    index={pillar.path === ''}
                    path={pillar.path ? `${pillar.path}/*` : undefined}
                    element={<MerchantPillarPage pillar={pillar} />}
                  />
                ))}
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
                <Route path="new-customer" element={<Suspense fallback={<InlineFallback />}><TrainingGate><CanadaPortalCreateCustomerPage /></TrainingGate></Suspense>} />
                <Route path="accounts" element={<Suspense fallback={<InlineFallback />}><CanadaPortalAccountsPage /></Suspense>} />
                <Route path="training" element={<Suspense fallback={<InlineFallback />}><CanadaPortalTrainingPage /></Suspense>} />
                <Route path="proposals" element={<Suspense fallback={<InlineFallback />}><CanadaPortalProposalsPage /></Suspense>} />
                <Route path="team" element={<Suspense fallback={<InlineFallback />}><CanadaPortalTeamPage /></Suspense>} />
                <Route path="settings" element={<Suspense fallback={<InlineFallback />}><CanadaPortalSettingsPage /></Suspense>} />
                <Route path="badge" element={<Suspense fallback={<InlineFallback />}><CanadaPortalBadgePage /></Suspense>} />
              </Route>

              {/* ══════════════════════════════════════════════
                  US — sales portal (native React CRM)
                  ══════════════════════════════════════════════ */}
              <Route path="/us/onboard" element={
                <Suspense fallback={<LazyFallback />}>
                  <USCustomerOnboardingWizard />
                </Suspense>
              } />
              {/* US — customer auth (returning login + first-login setup) */}
              <Route path="/us/login" element={<Suspense fallback={<LazyFallback />}><USLoginPage /></Suspense>} />
              <Route path="/us/setup" element={<Suspense fallback={<LazyFallback />}><USSetupPage /></Suspense>} />
              {/* Public invoice view — the /us/invoice/{number} links embedded in
                  US invoice PDFs previously fell through to the landing catch-all */}
              <Route path="/us/invoice/:invoiceId" element={<Suspense fallback={<LazyFallback />}><USInvoicePage /></Suspense>} />
              {/* ══════════════════════════════════════════════
                  US — merchant portal (3-pillar product, Canada parity)
                  ══════════════════════════════════════════════ */}
              <Route path="/us/merchant/onboard" element={
                <ProtectedRoute loginPath="/us/login">
                  <Suspense fallback={<LazyFallback />}>
                    <MerchantOnboardingWizard />
                  </Suspense>
                </ProtectedRoute>
              } />
              <Route path="/us/merchant" element={
                <ProtectedRoute loginPath="/us/login">
                  <Suspense fallback={<LazyFallback />}>
                    <MerchantLayout basePath="/us/merchant" />
                  </Suspense>
                </ProtectedRoute>
              }>
                {merchantPillars.map(pillar => (
                  <Route
                    key={pillar.path || '_home'}
                    index={pillar.path === ''}
                    path={pillar.path ? `${pillar.path}/*` : undefined}
                    element={<MerchantPillarPage pillar={pillar} />}
                  />
                ))}
              </Route>
              {/* US — dedicated customer dashboard (US-branded, full feature set) */}
              <Route path="/us/dashboard" element={
                <ProtectedRoute loginPath="/us/login">
                  <Suspense fallback={<LazyFallback />}>
                    <USLayout />
                  </Suspense>
                </ProtectedRoute>
              }>
                {CustomerDashboardRoutes()}
              </Route>
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
                <Route path="new-customer" element={<Suspense fallback={<InlineFallback />}><TrainingGate><USPortalCreateCustomerPage /></TrainingGate></Suspense>} />
                <Route path="accounts" element={<Suspense fallback={<InlineFallback />}><USPortalAccountsPage /></Suspense>} />
                <Route path="training" element={<Suspense fallback={<InlineFallback />}><USPortalTrainingPage /></Suspense>} />
                <Route path="proposals" element={<Suspense fallback={<InlineFallback />}><USPortalProposalsPage /></Suspense>} />
                <Route path="team" element={<Suspense fallback={<InlineFallback />}><USPortalTeamPage /></Suspense>} />
                <Route path="settings" element={<Suspense fallback={<InlineFallback />}><USPortalSettingsPage /></Suspense>} />
                <Route path="badge" element={<Suspense fallback={<InlineFallback />}><USPortalBadgePage /></Suspense>} />
              </Route>

              {/* Public rep badge + wallet card pages */}
              <Route path="/rep/:badgeId" element={<Suspense fallback={<LazyFallback />}><RepPublicBadgePage /></Suspense>} />
              <Route path="/wallet/:badgeId" element={<Suspense fallback={<LazyFallback />}><WalletCardPage /></Suspense>} />

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
            <CookieConsentBanner />
          </Suspense>
          </ToastProvider>
        </SalesAuthProvider>
      </AuthProvider>
    </ErrorBoundary>
  )
}
