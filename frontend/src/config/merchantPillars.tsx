import type { ComponentType, LazyExoticComponent } from 'react'
import {
  LayoutDashboard, Zap, Layers, Users, Phone, Video, Settings, Receipt,
  Contact, Lightbulb, Globe, CalendarClock, FileText,
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
const BookingsPage = lazyRetry(() => import('@/pages/BookingsPage'))
const BookingsSetupPage = lazyRetry(() => import('@/pages/BookingsSetupPage'))
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
const InvoicesPage = lazyRetry(() => import('@/pages/InvoicesPage'))
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

/**
 * Reorder a pillar list for a trade.
 *
 * A barbershop's Meridian should open on the book, not on inventory it does
 * not keep. Anything the pack does not name keeps its natural position after
 * the ones it does, so a new pillar added here later cannot vanish from a
 * trade's portal just because nobody updated the pack.
 */
export function orderPillars(pillars: Pillar[], order?: string[]): Pillar[] {
  if (!order || order.length === 0) return pillars
  const rank = new Map(order.map((path, i) => [path, i]))
  return [...pillars].sort((a, b) => {
    const ra = rank.has(a.path) ? rank.get(a.path)! : order.length + pillars.indexOf(a)
    const rb = rank.has(b.path) ? rank.get(b.path)! : order.length + pillars.indexOf(b)
    return ra - rb
  })
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
    flag: 'inventory',
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
    flag: 'schedule',
  },
  {
    path: 'phone',
    label: 'Phone Calls',
    icon: Phone,
    segments: [
      { view: 'orders', label: 'Phone Orders', Component: PhoneOrdersPage },
      { view: 'setup', label: 'Set up', Component: PhoneSetupWizard },
    ],
    flag: 'phoneCalls',
  },
  {
    // Reservations and appointments. Sits next to Phone Calls because that is
    // where most of them come from — the agent books straight into this book.
    path: 'bookings',
    label: 'Bookings',
    icon: CalendarClock,
    segments: [
      { view: 'book', label: "Today's Book", Component: BookingsPage },
      { view: 'setup', label: 'Set up', Component: BookingsSetupPage },
    ],
    flag: 'bookings',
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
    flag: 'camera',
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
    // The custom bill: the bulk order quoted on the phone, the wholesale
    // account — money that today leaves by PayPal link and never lands
    // beside the rest of the revenue. Asked for by name (Aidan, 2026-08-20,
    // for the online-store trades); shaped like a Stripe invoice so the real
    // send is wiring, not rework.
    path: 'invoices',
    label: 'Invoices',
    icon: FileText,
    comingSoon: true,
    sampleData: true,
    segments: [{ view: 'send', label: 'Send Invoice', Component: InvoicesPage }],
  },
  // Taxes & Expenses and My Website were here and are deliberately gone.
  // Aidan's call: a demo is a pitch, and two roadmap tabs a prospect cannot
  // buy today dilute the four that are actually the product. Neither page is
  // deleted — Taxes & Expenses still ships to real merchants through the
  // `taxExpenses` flag (on for /app, off for Canada), and the website pages
  // are still routed. They just no longer sit in a demo sidebar.
  //
  // Marketing (the content engine) was added here on 2026-08-20 and removed
  // the same day, by the same call — "too much". Do not re-add it; the page
  // stays routed at /content for anyone who goes looking.
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
