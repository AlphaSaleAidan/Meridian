import { type BusinessType, isCanadaPath } from './demo-context'

export interface ProductDef {
  name: string
  sku: string
  price: number
  category: string
  popularity: number
}

export interface RevenueConfig {
  weekdayMin: number
  weekdayMax: number
  weekendMin: number
  weekendMax: number
  avgTicketMin: number
  avgTicketMax: number
}

export interface StaffDef {
  name: string
  role: string
}

export interface BusinessProfile {
  businessName: string
  businessNameCA: string
  products: ProductDef[]
  revenue: RevenueConfig
  hourlyPattern: number[]
  peakLabel: string
  staff: StaffDef[]
  industryLabel: string
  topBundlePair: [string, string]
  deadStockItems: string[]
}

const COFFEE_SHOP: BusinessProfile = {
  businessName: 'Sunrise Coffee Co.',
  businessNameCA: 'Maple Leaf Café',
  industryLabel: 'Coffee Shop / Café',
  peakLabel: '7:00–10:00 AM',
  topBundlePair: ['Cappuccino', 'Croissant'],
  deadStockItems: ['Hot Chocolate', 'Banana Bread', 'Cookie', 'Chai Latte'],
  hourlyPattern: [
    0, 0, 0, 0, 0, 5,
    15, 45, 85, 70, 55, 65,
    80, 70, 50, 40, 35, 30,
    20, 10, 5, 0, 0, 0,
  ],
  revenue: {
    weekdayMin: 120000, weekdayMax: 200000,
    weekendMin: 180000, weekendMax: 260000,
    avgTicketMin: 850, avgTicketMax: 1200,
  },
  staff: [
    { name: 'Sarah M.', role: 'Barista Lead' },
    { name: 'James K.', role: 'Barista' },
    { name: 'Maria L.', role: 'Barista' },
    { name: 'Alex T.', role: 'Barista' },
    { name: 'Priya S.', role: 'Cashier' },
    { name: 'Tom B.', role: 'Barista (New)' },
  ],
  products: [
    { name: 'Espresso', sku: 'ESP-001', price: 350, category: 'drinks', popularity: 0.95 },
    { name: 'Cappuccino', sku: 'CAP-001', price: 525, category: 'drinks', popularity: 0.90 },
    { name: 'Iced Latte', sku: 'ICL-001', price: 575, category: 'drinks', popularity: 0.85 },
    { name: 'Cold Brew', sku: 'CDB-001', price: 500, category: 'drinks', popularity: 0.80 },
    { name: 'Matcha Latte', sku: 'MAT-001', price: 625, category: 'drinks', popularity: 0.65 },
    { name: 'Hot Chocolate', sku: 'HOT-001', price: 475, category: 'drinks', popularity: 0.50 },
    { name: 'Chai Latte', sku: 'CHA-001', price: 550, category: 'drinks', popularity: 0.55 },
    { name: 'Drip Coffee', sku: 'DRP-001', price: 275, category: 'drinks', popularity: 0.70 },
    { name: 'Blueberry Muffin', sku: 'MUF-001', price: 395, category: 'food', popularity: 0.75 },
    { name: 'Croissant', sku: 'CRO-001', price: 425, category: 'food', popularity: 0.80 },
    { name: 'Avocado Toast', sku: 'AVO-001', price: 895, category: 'food', popularity: 0.60 },
    { name: 'Breakfast Sandwich', sku: 'BKF-001', price: 795, category: 'food', popularity: 0.70 },
    { name: 'Banana Bread', sku: 'BAN-001', price: 375, category: 'food', popularity: 0.55 },
    { name: 'Cookie', sku: 'COK-001', price: 295, category: 'food', popularity: 0.45 },
  ],
}

const RESTAURANT: BusinessProfile = {
  businessName: 'Ember & Oak',
  businessNameCA: 'Northern Table',
  industryLabel: 'Full-Service Restaurant',
  peakLabel: '6:00–9:00 PM',
  topBundlePair: ['Caesar Salad', 'Ribeye Steak'],
  deadStockItems: ['Soup du Jour', 'Sparkling Water', 'Bruschetta', 'Tiramisu'],
  hourlyPattern: [
    0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 10, 35,
    60, 45, 15, 10, 15, 40,
    75, 90, 80, 45, 15, 0,
  ],
  revenue: {
    weekdayMin: 300000, weekdayMax: 550000,
    weekendMin: 550000, weekendMax: 800000,
    avgTicketMin: 2800, avgTicketMax: 4500,
  },
  staff: [
    { name: 'Marco V.', role: 'Head Chef' },
    { name: 'Lisa C.', role: 'Sous Chef' },
    { name: 'Daniel R.', role: 'Line Cook' },
    { name: 'Ashley N.', role: 'Server Lead' },
    { name: 'Kevin W.', role: 'Server' },
    { name: 'Mia H.', role: 'Host' },
  ],
  products: [
    { name: 'Ribeye Steak', sku: 'ENT-001', price: 3495, category: 'entrees', popularity: 0.85 },
    { name: 'Grilled Salmon', sku: 'ENT-002', price: 2895, category: 'entrees', popularity: 0.80 },
    { name: 'Chicken Marsala', sku: 'ENT-003', price: 2495, category: 'entrees', popularity: 0.75 },
    { name: 'Truffle Pasta', sku: 'ENT-004', price: 2295, category: 'entrees', popularity: 0.70 },
    { name: 'Caesar Salad', sku: 'APP-001', price: 1495, category: 'appetizers', popularity: 0.90 },
    { name: 'Soup du Jour', sku: 'APP-002', price: 995, category: 'appetizers', popularity: 0.65 },
    { name: 'Bruschetta', sku: 'APP-003', price: 1295, category: 'appetizers', popularity: 0.60 },
    { name: 'Wagyu Burger', sku: 'ENT-005', price: 1995, category: 'entrees', popularity: 0.55 },
    { name: 'Crème Brûlée', sku: 'DES-001', price: 1195, category: 'desserts', popularity: 0.50 },
    { name: 'Tiramisu', sku: 'DES-002', price: 1095, category: 'desserts', popularity: 0.45 },
    { name: 'House Wine', sku: 'BEV-001', price: 1200, category: 'beverages', popularity: 0.85 },
    { name: 'Craft Cocktail', sku: 'BEV-002', price: 1500, category: 'beverages', popularity: 0.75 },
    { name: 'Draft Beer', sku: 'BEV-003', price: 800, category: 'beverages', popularity: 0.80 },
    { name: 'Sparkling Water', sku: 'BEV-004', price: 400, category: 'beverages', popularity: 0.50 },
  ],
}

const FAST_FOOD: BusinessProfile = {
  businessName: 'Blaze Burger',
  businessNameCA: 'Great White Burger',
  industryLabel: 'Quick-Service Restaurant',
  peakLabel: '11:30 AM–1:30 PM',
  topBundlePair: ['Classic Burger', 'Fries (Reg)'],
  deadStockItems: ['Fish Filet', 'Apple Pie', 'Iced Tea', 'Breakfast Burrito'],
  hourlyPattern: [
    0, 0, 0, 0, 0, 5,
    15, 25, 30, 35, 50, 85,
    95, 80, 45, 30, 25, 35,
    55, 45, 25, 10, 0, 0,
  ],
  revenue: {
    weekdayMin: 250000, weekdayMax: 400000,
    weekendMin: 400000, weekendMax: 550000,
    avgTicketMin: 1000, avgTicketMax: 1600,
  },
  staff: [
    { name: 'Carlos M.', role: 'Shift Manager' },
    { name: 'Brittany J.', role: 'Grill Lead' },
    { name: 'DeShawn P.', role: 'Grill Cook' },
    { name: 'Hannah L.', role: 'Drive-Thru' },
    { name: 'Tyler R.', role: 'Cashier' },
    { name: 'Sophia K.', role: 'Prep Cook' },
  ],
  products: [
    { name: 'Classic Burger', sku: 'BUR-001', price: 699, category: 'burgers', popularity: 0.95 },
    { name: 'Cheeseburger', sku: 'BUR-002', price: 799, category: 'burgers', popularity: 0.90 },
    { name: 'Double Stack', sku: 'BUR-003', price: 999, category: 'burgers', popularity: 0.75 },
    { name: 'Chicken Sandwich', sku: 'CHK-001', price: 849, category: 'chicken', popularity: 0.80 },
    { name: 'Fish Filet', sku: 'FSH-001', price: 749, category: 'sandwiches', popularity: 0.45 },
    { name: 'Fries (Reg)', sku: 'SID-001', price: 349, category: 'sides', popularity: 0.92 },
    { name: 'Fries (Large)', sku: 'SID-002', price: 449, category: 'sides', popularity: 0.70 },
    { name: 'Onion Rings', sku: 'SID-003', price: 499, category: 'sides', popularity: 0.55 },
    { name: 'Milkshake', sku: 'BEV-001', price: 599, category: 'beverages', popularity: 0.65 },
    { name: 'Soft Drink', sku: 'BEV-002', price: 249, category: 'beverages', popularity: 0.88 },
    { name: 'Iced Tea', sku: 'BEV-003', price: 249, category: 'beverages', popularity: 0.50 },
    { name: 'Chicken Nuggets', sku: 'CHK-002', price: 699, category: 'chicken', popularity: 0.85 },
    { name: 'Breakfast Burrito', sku: 'BRK-001', price: 599, category: 'breakfast', popularity: 0.60 },
    { name: 'Apple Pie', sku: 'DES-001', price: 299, category: 'desserts', popularity: 0.40 },
  ],
}

const AUTO_SHOP: BusinessProfile = {
  businessName: 'Precision Auto Works',
  businessNameCA: 'True North Auto',
  industryLabel: 'Automotive Service',
  peakLabel: '10:00 AM–2:00 PM',
  topBundlePair: ['Oil Change (Synth)', 'Tire Rotation'],
  deadStockItems: ['Transmission Flush', 'Coolant Flush', 'Spark Plugs', 'Wiper Blades'],
  hourlyPattern: [
    0, 0, 0, 0, 0, 0,
    0, 10, 35, 60, 80, 85,
    50, 65, 80, 70, 55, 30,
    5, 0, 0, 0, 0, 0,
  ],
  revenue: {
    weekdayMin: 200000, weekdayMax: 500000,
    weekendMin: 80000, weekendMax: 200000,
    avgTicketMin: 8000, avgTicketMax: 25000,
  },
  staff: [
    { name: 'Mike D.', role: 'Master Technician' },
    { name: 'Jason R.', role: 'Lead Technician' },
    { name: 'Brandon S.', role: 'Technician A' },
    { name: 'Eric W.', role: 'Technician B' },
    { name: 'Nina P.', role: 'Service Advisor' },
    { name: 'Greg T.', role: 'Parts Counter' },
  ],
  products: [
    { name: 'Oil Change (Conv)', sku: 'SVC-001', price: 3999, category: 'maintenance', popularity: 0.95 },
    { name: 'Oil Change (Synth)', sku: 'SVC-002', price: 6999, category: 'maintenance', popularity: 0.85 },
    { name: 'Tire Rotation', sku: 'SVC-003', price: 2999, category: 'tires', popularity: 0.80 },
    { name: 'Brake Pad Replace', sku: 'SVC-004', price: 24999, category: 'brakes', popularity: 0.60 },
    { name: 'Air Filter', sku: 'SVC-005', price: 2499, category: 'filters', popularity: 0.75 },
    { name: 'Battery Replace', sku: 'SVC-006', price: 17999, category: 'electrical', popularity: 0.50 },
    { name: 'Wheel Alignment', sku: 'SVC-007', price: 8999, category: 'tires', popularity: 0.65 },
    { name: 'Transmission Flush', sku: 'SVC-008', price: 14999, category: 'fluids', popularity: 0.35 },
    { name: 'A/C Recharge', sku: 'SVC-009', price: 12999, category: 'hvac', popularity: 0.55 },
    { name: 'Coolant Flush', sku: 'SVC-010', price: 9999, category: 'fluids', popularity: 0.45 },
    { name: 'Spark Plugs', sku: 'SVC-011', price: 11999, category: 'engine', popularity: 0.40 },
    { name: 'Wiper Blades', sku: 'SVC-012', price: 2999, category: 'parts', popularity: 0.70 },
    { name: 'State Inspection', sku: 'SVC-013', price: 3499, category: 'compliance', popularity: 0.90 },
    { name: 'Diagnostic Scan', sku: 'SVC-014', price: 8999, category: 'diagnostics', popularity: 0.65 },
  ],
}

const SMOKE_SHOP: BusinessProfile = {
  businessName: 'Cloud 9 Smoke Shop',
  businessNameCA: 'Canuck Smoke Co.',
  industryLabel: 'Tobacco & Accessories',
  peakLabel: '2:00–6:00 PM',
  topBundlePair: ['Disposable Vape', 'E-Liquid (30ml)'],
  deadStockItems: ['Hookah Tobacco', 'Glass Pipe', 'CBD Gummies', 'Premium Cigar'],
  hourlyPattern: [
    0, 0, 0, 0, 0, 0,
    0, 0, 5, 15, 25, 35,
    45, 50, 55, 65, 70, 60,
    45, 35, 20, 10, 0, 0,
  ],
  revenue: {
    weekdayMin: 80000, weekdayMax: 160000,
    weekendMin: 120000, weekendMax: 220000,
    avgTicketMin: 1500, avgTicketMax: 3000,
  },
  staff: [
    { name: 'Dante W.', role: 'Store Manager' },
    { name: 'Jordan F.', role: 'Shift Lead' },
    { name: 'Kayla M.', role: 'Sales Associate' },
    { name: 'Chris B.', role: 'Sales Associate' },
    { name: 'Tamika J.', role: 'Stock Clerk' },
    { name: 'Ravi P.', role: 'Budtender' },
  ],
  products: [
    { name: 'Premium Cigarettes', sku: 'CIG-001', price: 1499, category: 'cigarettes', popularity: 0.90 },
    { name: 'Value Cigarettes', sku: 'CIG-002', price: 1099, category: 'cigarettes', popularity: 0.80 },
    { name: 'Disposable Vape', sku: 'VAP-001', price: 1299, category: 'vapes', popularity: 0.85 },
    { name: 'Vape Pod Kit', sku: 'VAP-002', price: 3499, category: 'vapes', popularity: 0.60 },
    { name: 'E-Liquid (30ml)', sku: 'VAP-003', price: 1999, category: 'vapes', popularity: 0.70 },
    { name: 'Rolling Papers', sku: 'ACC-001', price: 399, category: 'accessories', popularity: 0.75 },
    { name: 'Glass Pipe', sku: 'ACC-002', price: 2499, category: 'accessories', popularity: 0.55 },
    { name: 'Butane Lighter', sku: 'ACC-003', price: 599, category: 'accessories', popularity: 0.65 },
    { name: 'CBD Gummies', sku: 'CBD-001', price: 2999, category: 'cbd', popularity: 0.50 },
    { name: 'Hookah Tobacco', sku: 'HOK-001', price: 1899, category: 'hookah', popularity: 0.40 },
    { name: 'Premium Cigar', sku: 'CIG-003', price: 1599, category: 'cigars', popularity: 0.45 },
    { name: 'Cigarillo Pack', sku: 'CIG-004', price: 899, category: 'cigars', popularity: 0.70 },
    { name: 'Vape Coils', sku: 'VAP-004', price: 1499, category: 'vapes', popularity: 0.60 },
    { name: 'Grinder', sku: 'ACC-004', price: 1999, category: 'accessories', popularity: 0.50 },
  ],
}

const PROFILES: Record<BusinessType, BusinessProfile> = {
  coffee_shop: COFFEE_SHOP,
  restaurant: RESTAURANT,
  fast_food: FAST_FOOD,
  auto_shop: AUTO_SHOP,
  smoke_shop: SMOKE_SHOP,
}

export function getBusinessProfile(type: BusinessType): BusinessProfile {
  return PROFILES[type]
}

export function getProducts(type: BusinessType): ProductDef[] {
  return PROFILES[type].products
}

export function getRevenueConfig(type: BusinessType): RevenueConfig {
  return PROFILES[type].revenue
}

export function getHourlyPattern(type: BusinessType): number[] {
  return PROFILES[type].hourlyPattern
}

export function getStaff(type: BusinessType): StaffDef[] {
  return PROFILES[type].staff
}

export function getBusinessName(type: BusinessType): string {
  return isCanadaPath() ? PROFILES[type].businessNameCA : PROFILES[type].businessName
}
