import type { ComponentType, LazyExoticComponent } from 'react'
import {
  LayoutDashboard, Zap, Layers, Calendar, Phone, Video, Settings, Receipt,
} from 'lucide-react'
import { lazyRetry } from '@/components/ErrorBoundary'

/**
 * Merchant-portal information architecture for the trimmed Canada product.
 *
 * Three money pillars (INVENTORY, SCHEDULE, PHONE CALLS) + CAMERA (secondary)
 * + HOME + SETTINGS. Each pillar exposes segmented sub-views via `?view=`,
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
const PhoneOrdersPage = lazyRetry(() => import('@/pages/PhoneOrdersPage'))
const PhoneSetupWizard = lazyRetry(() => import('@/pages/canada/merchant/PhoneSetupWizard'))
const CPAHandoffPage = lazyRetry(() => import('@/pages/canada/merchant/CPAHandoffPage'))
const CameraIntelligencePage = lazyRetry(() => import('@/pages/seo/CameraIntelligencePage'))
const SettingsPage = lazyRetry(() => import('@/pages/SettingsPage'))
const NotificationsPage = lazyRetry(() => import('@/pages/NotificationsPage'))

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
  segments: PillarSegment[]
}

export const merchantPillars: Pillar[] = [
  {
    path: '',
    label: 'Home',
    icon: LayoutDashboard,
    segments: [{ view: 'home', label: 'Home', Component: MerchantHomePage }],
  },
  {
    path: 'actions',
    label: 'Top Actions',
    icon: Zap,
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
    path: 'schedule',
    label: 'Schedule',
    icon: Calendar,
    segments: [
      { view: 'builder', label: 'Schedule', Component: SchedulePage },
      { view: 'peak', label: 'Peak Hours', Component: PeakHoursPage },
      { view: 'staff', label: 'Staff', Component: StaffPage },
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
    segments: [{ view: 'handoff', label: 'CPA Handoff', Component: CPAHandoffPage }],
  },
  {
    path: 'camera',
    label: 'Camera',
    icon: Video,
    secondary: true,
    segments: [{ view: 'intelligence', label: 'Camera', Component: CameraIntelligencePage }],
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

export const MERCHANT_BASE_PATH = '/canada/merchant'
