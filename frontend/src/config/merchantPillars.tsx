import type { ComponentType, LazyExoticComponent } from 'react'
import {
  LayoutDashboard, Zap, Layers, Users, Phone, Video, Settings, Receipt,
  Contact, Lightbulb, Globe,
} from 'lucide-react'
import { lazyRetry } from '@/components/ErrorBoundary'
import type { ModuleFlags } from '@/config/moduleFlags'

/**
 * Merchant-portal information architecture for the trimmed Canada product.
 *
 * Three money pillars (INVENTORY, SCHEDULE, PHONE CALLS) + CAMERA (secondary)
 * + OVERVIEW (Home / Revenue) + SETTINGS. Each exposes sub-views via `?view=`,
 * composed from existing dashboard pages — no rewrites (disable-never-delete).
 *
 * The first segment is the pillar default. Pillars with a single segment hide
 * the segment bar. Camera is flagged `secondary` so the layout can group it
 * apart from the money pillars.
 */

type PageComponent = LazyExoticComponent<ComponentType>

const MerchantHomePage = lazyRetry(() => import('@/pages/canada/merchant/MerchantHomePage'))
const ActionsPage = lazyRetry(() => import('@/pages/ActionsPage'))
const InventoryPage = lazyRetry(() => import('@/pages/InventoryPage'))
const ProductsPage = lazyRetry(() => import('@/pages/ProductsPage'))
const MarginsPage = lazyRetry(() => import('@/pages/MarginsPage'))
const ForecastsPage = lazyRetry(() => import('@/pages/ForecastsPage'))
const MenuEngineeringPage = lazyRetry(() => import('@/pages/MenuEngineeringPage'))
const AnomaliesPage = lazyRetry(() => import('@/pages/AnomaliesPage'))
const SchedulePage = lazyRetry(() => import('@/pages/SchedulePage'))
const PeakHoursPage = lazyRetry(() => import('@/pages/PeakHoursPage'))
const StaffPage = lazyRetry(() => import('@/pages/StaffPage'))
const TeamManagementPage = lazyRetry(() => import('@/pages/team/TeamManagementPage'))
const TimeClockPage = lazyRetry(() => import('@/pages/team/TimeClockPage'))
const TeamChatPage = lazyRetry(() => import('@/pages/team/TeamChatPage'))
const ChatbotConfigPage = lazyRetry(() => import('@/pages/team/ChatbotConfigPage'))
const PhoneOrdersPage = lazyRetry(() => import('@/pages/PhoneOrdersPage'))
const PhoneSetupWizard = lazyRetry(() => import('@/pages/canada/merchant/PhoneSetupWizard'))
const CPAHandoffPage = lazyRetry(() => import('@/pages/canada/merchant/CPAHandoffPage'))
// Point to the in-app analytics view, NOT the SEO marketing page.
// The public SEO route (/features/camera-intelligence) keeps seo/CameraIntelligencePage.
const CameraIntelligencePage = lazyRetry(() => import('@/pages/CameraIntelligencePage'))
const LiveCamerasPage = lazyRetry(() => import('@/pages/LiveCamerasPage'))
const SettingsPage = lazyRetry(() => import('@/pages/SettingsPage'))
const NotificationsPage = lazyRetry(() => import('@/pages/NotificationsPage'))
const RevenuePage = lazyRetry(() => import('@/pages/RevenuePage'))
// Coming Soon previews — Canada demo only (see comingSoonPillars).
const CustomersPage = lazyRetry(() => import('@/pages/CustomersPage'))
const InsightsPage = lazyRetry(() => import('@/pages/InsightsPage'))
const MyWebsitePage = lazyRetry(() => import('@/pages/MyWebsitePage'))
const SiteCarePage = lazyRetry(() => import('@/pages/canada/merchant/SiteCarePage'))

export interface PillarSegment {
  view: string
  label: string
  Component: PageComponent
  desktopOnly?: boolean
}

export interface Pillar {
  /** Route segment under /canada/merchant. Empty string = index (Home). */
  path: string
  label: string
  icon: typeof LayoutDashboard
  /** Camera is a secondary tab, grouped apart from the money pillars. */
  secondary?: boolean
  /**
   * Roadmap preview — shown only in the Canada demo, under its own "Coming
   * Soon" heading, and never in a paying merchant's portal. The page renders
   * for real behind a banner saying it isn't live yet.
   */
  comingSoon?: boolean
  /** Coming Soon pages that render figures — the banner then says they're synthetic. */
  sampleData?: boolean
  segments: PillarSegment[]
  /** When set, the pillar is hidden if the corresponding module flag is false. */
  flag?: keyof ModuleFlags
}

export const merchantPillars: Pillar[] = [
  {
    path: '',
    label: 'Overview',
    icon: LayoutDashboard,
    segments: [
      { view: 'home', label: 'Home', Component: MerchantHomePage },
      { view: 'revenue', label: 'Revenue', Component: RevenuePage },
    ],
  },
  {
    path: 'actions',
    label: 'Top Actions',
    icon: Zap,
    flag: 'topActions',
    segments: [{ view: 'top', label: 'Top Actions', Component: ActionsPage }],
  },
  {
    path: 'inventory',
    label: 'Inventory',
    icon: Layers,
    segments: [
      { view: 'overview', label: 'Overview', Component: InventoryPage },
      { view: 'products', label: 'Products', Component: ProductsPage },
      { view: 'margins', label: 'Margins', Component: MarginsPage },
      { view: 'forecasts', label: 'Forecasts', Component: ForecastsPage },
      { view: 'menu', label: 'Menu Matrix', Component: MenuEngineeringPage, desktopOnly: true },
      { view: 'anomalies', label: 'Anomalies', Component: AnomaliesPage },
    ],
  },
  {
    // Renamed from "Schedule" → the owner's control center for scheduling AND
    // the whole team surface (roster/RBAC, time clock, chat, customer chatbot).
    // The "Team" management view sits immediately after "Staff" (Workstream 1a).
    path: 'schedule',
    label: 'Team Management',
    icon: Users,
    segments: [
      { view: 'builder', label: 'Schedule', Component: SchedulePage },
      { view: 'peak', label: 'Peak Hours', Component: PeakHoursPage },
      { view: 'staff', label: 'Staff', Component: StaffPage },
      { view: 'team', label: 'Team', Component: TeamManagementPage },
      { view: 'timeclock', label: 'Time Clock', Component: TimeClockPage },
      { view: 'chat', label: 'Chat', Component: TeamChatPage },
      { view: 'chatbot', label: 'Customer Bot', Component: ChatbotConfigPage },
    ],
  },
  {
    path: 'phone',
    label: 'Phone Calls',
    icon: Phone,
    segments: [
      { view: 'orders', label: 'Phone Orders', Component: PhoneOrdersPage },
      { view: 'setup', label: 'Set up', Component: PhoneSetupWizard },
    ],
  },
  {
    path: 'tax',
    label: 'Taxes & Expenses',
    icon: Receipt,
    flag: 'taxExpenses',
    segments: [{ view: 'handoff', label: 'CPA Handoff', Component: CPAHandoffPage }],
  },
  {
    path: 'camera',
    label: 'Camera',
    icon: Video,
    secondary: true,
    segments: [
      { view: 'live', label: 'Live', Component: LiveCamerasPage },
      { view: 'intelligence', label: 'Analytics', Component: CameraIntelligencePage },
    ],
  },
  {
    path: 'settings',
    label: 'Settings',
    icon: Settings,
    segments: [
      { view: 'general', label: 'General', Component: SettingsPage },
      { view: 'notifications', label: 'Notifications', Component: NotificationsPage },
    ],
  },
]

// Public demos keep the Camera pillar (Analytics) but drop the Live segment —
// no live-camera feed in the unauthenticated demo (US + Canada).
export const demoMerchantPillars: Pillar[] = merchantPillars.map(p =>
  p.path === 'camera'
    ? { ...p, segments: p.segments.filter(s => s.view !== 'live') }
    : p,
)

/**
 * Roadmap previews for the Canada demo only.
 *
 * These are built pages that the trimmed product does not ship yet, so a
 * prospect can see where Meridian is going without a paying merchant finding
 * a half-finished tab in their portal. They never enter `merchantPillars`, so
 * the live /canada/merchant and /us/merchant navs are untouched, and the
 * module flags stay off — this is a demo surface, not a soft launch.
 *
 * `Taxes & Expenses` reuses the `tax` path already defined above; the entry
 * here wins for the demo so it renders under the Coming Soon heading instead
 * of as a money pillar.
 */
export const comingSoonPillars: Pillar[] = [
  {
    path: 'insights',
    label: 'Insights',
    icon: Lightbulb,
    comingSoon: true,
    sampleData: true,
    segments: [{ view: 'insights', label: 'Insights', Component: InsightsPage }],
  },
  {
    path: 'customers',
    label: 'Customers',
    icon: Contact,
    comingSoon: true,
    sampleData: true,
    segments: [{ view: 'customers', label: 'Customers', Component: CustomersPage }],
  },
  {
    path: 'tax',
    label: 'Taxes & Expenses',
    icon: Receipt,
    comingSoon: true,
    sampleData: true,
    segments: [{ view: 'handoff', label: 'CPA Handoff', Component: CPAHandoffPage }],
  },
  {
    path: 'my-website',
    label: 'My Website',
    icon: Globe,
    comingSoon: true,
    segments: [
      // Managed sites first — that is the offer. The DIY builder stays visible
      // as the second segment; it is still under construction behind its own flag.
      { view: 'care', label: 'Site Care', Component: SiteCarePage },
      { view: 'builder', label: 'Builder', Component: MyWebsitePage },
    ],
  },
]

/** Public demo route set: the shipped demo pillars plus the roadmap previews. */
export const canadaDemoPillars: Pillar[] = [
  ...demoMerchantPillars.filter(p => !comingSoonPillars.some(c => c.path === p.path)),
  ...comingSoonPillars,
]

/**
 * US demo route set — the same as Canada's.
 *
 * /demo is documented as "mirroring /canada/demo", but it was wired to the bare
 * `demoMerchantPillars`, so a US prospect saw four fewer tabs than a Canadian
 * one: Insights, Customers, Taxes & Expenses and My Website were all missing.
 * Both public demos now show the same surface; the live merchant navs still
 * take `merchantPillars` and are unaffected.
 */
export const usDemoPillars: Pillar[] = canadaDemoPillars

export const MERCHANT_BASE_PATH = '/canada/merchant'
export const US_MERCHANT_BASE_PATH = '/us/merchant'
export const CANADA_DEMO_BASE_PATH = '/canada/demo'
