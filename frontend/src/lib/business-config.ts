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

// Retail with a clock on it: the expensive stock is cold-stored with lot
// numbers and expiry dates, and the business is the monthly reorder call.
const PEPTIDE_SHOP: BusinessProfile = {
  businessName: 'Apex Peptide Supply',
  businessNameCA: 'Northern Peptide Co.',
  industryLabel: 'Online Peptide & Wellness Store',
  // Online orders peak in the evening, after work — the pattern a walk-in
  // shop never sees. The site takes orders around the clock; the bench ships
  // them 9-5.
  peakLabel: '7:00–10:00 PM',
  topBundlePair: ['BPC-157 5mg', 'Bacteriostatic Water 30ml'],
  deadStockItems: ['Epitalon 10mg', 'Collagen Peptide Powder', 'Creatine Gummies', 'Vial Travel Case'],
  hourlyPattern: [
    5, 5, 0, 0, 0, 5,
    10, 20, 25, 30, 35, 40,
    45, 40, 35, 30, 35, 45,
    60, 80, 90, 70, 35, 15,
  ],
  revenue: {
    weekdayMin: 90000, weekdayMax: 180000,
    weekendMin: 70000, weekendMax: 140000,
    avgTicketMin: 6000, avgTicketMax: 12000,
  },
  // An online store's whole roster: nobody stands at a register.
  staff: [
    { name: 'Marcus D.', role: 'Owner / Operator' },
    { name: 'Elena V.', role: 'Fulfillment Lead' },
    { name: 'Tyler S.', role: 'Customer Support' },
    { name: 'Priya N.', role: 'Inventory & Receiving' },
  ],
  products: [
    { name: 'BPC-157 5mg', sku: 'PEP-001', price: 5499, category: 'peptides', popularity: 0.90 },
    { name: 'TB-500 5mg', sku: 'PEP-002', price: 6499, category: 'peptides', popularity: 0.75 },
    { name: 'GHK-Cu 50mg', sku: 'PEP-003', price: 4999, category: 'peptides', popularity: 0.60 },
    { name: 'Epitalon 10mg', sku: 'PEP-004', price: 5999, category: 'peptides', popularity: 0.35 },
    { name: 'NAD+ 500mg', sku: 'PEP-005', price: 8999, category: 'peptides', popularity: 0.55 },
    { name: 'Glutathione 600mg', sku: 'PEP-006', price: 4499, category: 'peptides', popularity: 0.50 },
    { name: 'Bacteriostatic Water 30ml', sku: 'SUP-001', price: 1499, category: 'supplies', popularity: 0.85 },
    { name: 'Insulin Syringe 10-Pack', sku: 'SUP-002', price: 899, category: 'supplies', popularity: 0.70 },
    { name: 'Alcohol Prep Pads 100ct', sku: 'SUP-003', price: 599, category: 'supplies', popularity: 0.65 },
    { name: 'Vial Travel Case', sku: 'SUP-004', price: 2499, category: 'supplies', popularity: 0.30 },
    { name: 'Collagen Peptide Powder', sku: 'WEL-001', price: 3499, category: 'wellness', popularity: 0.45 },
    { name: 'Creatine Gummies', sku: 'WEL-002', price: 2999, category: 'wellness', popularity: 0.40 },
    { name: 'Electrolyte Sticks 20ct', sku: 'WEL-003', price: 1999, category: 'wellness', popularity: 0.55 },
  ],
}


/**
 * The service trades.
 *
 * Every one of these SELLS PRODUCT as well as time — which is the whole reason
 * they keep the Inventory pillar. A barbershop's retail shelf and its blade
 * consumption are real margin; a med spa's injectables are the most expensive
 * stock in this file. Demoing them with a coffee shop's croissants would have
 * told a prospect the product was not built for them.
 *
 * Prices are US cents. The Canadian demo multiplies them at read time
 * (getCurrencyMultiplier), so nothing here is duplicated per market.
 */
const BARBERSHOP: BusinessProfile = {
  businessName: 'The Fade Room',
  businessNameCA: 'The Fade Room',
  industryLabel: 'Barbershop / Salon',
  peakLabel: '4:00–7:00 PM',
  topBundlePair: ['Haircut', 'Beard Trim'],
  deadStockItems: ['Hair Tonic', 'Straight Razor', 'Shave Brush'],
  hourlyPattern: [
    0, 0, 0, 0, 0, 0,
    0, 0, 0, 35, 55, 60,
    70, 65, 60, 70, 85, 95,
    80, 45, 10, 0, 0, 0,
  ],
  revenue: {
    weekdayMin: 90000, weekdayMax: 150000,
    weekendMin: 160000, weekendMax: 240000,
    avgTicketMin: 3500, avgTicketMax: 6500,
  },
  staff: [
    { name: 'Marco R.', role: 'Master Barber' },
    { name: 'Dee W.', role: 'Barber' },
    { name: 'Sol P.', role: 'Barber' },
    { name: 'Nia K.', role: 'Apprentice' },
  ],
  products: [
    { name: 'Haircut', sku: 'CUT-001', price: 3500, category: 'services', popularity: 0.95 },
    { name: 'Skin Fade', sku: 'FAD-001', price: 4500, category: 'services', popularity: 0.85 },
    { name: 'Cut & Beard', sku: 'CBD-001', price: 5500, category: 'services', popularity: 0.75 },
    { name: 'Beard Trim', sku: 'BRD-001', price: 2000, category: 'services', popularity: 0.70 },
    { name: 'Hot Towel Shave', sku: 'SHV-001', price: 4000, category: 'services', popularity: 0.45 },
    { name: 'Matte Pomade', sku: 'POM-001', price: 2200, category: 'retail', popularity: 0.60 },
    { name: 'Beard Oil', sku: 'OIL-001', price: 2600, category: 'retail', popularity: 0.55 },
    { name: 'Clay Paste', sku: 'CLY-001', price: 2400, category: 'retail', popularity: 0.50 },
    { name: 'Shampoo 250ml', sku: 'SHP-001', price: 1900, category: 'retail', popularity: 0.45 },
    { name: 'Hair Tonic', sku: 'TON-001', price: 2100, category: 'retail', popularity: 0.20 },
    { name: 'Clipper Blades', sku: 'BLD-001', price: 3200, category: 'supplies', popularity: 0.35 },
    { name: 'Straight Razor', sku: 'RAZ-001', price: 4800, category: 'retail', popularity: 0.15 },
    { name: 'Shave Brush', sku: 'BRS-001', price: 2900, category: 'retail', popularity: 0.12 },
  ],
}

const NAIL_STUDIO: BusinessProfile = {
  businessName: 'Lacquer Lash Bar',
  businessNameCA: 'Lacquer Lash Bar',
  industryLabel: 'Nail & Lash Studio',
  peakLabel: '11:00 AM–3:00 PM',
  topBundlePair: ['Gel Manicure', 'Pedicure'],
  deadStockItems: ['Nail Art Kit', 'Cuticle Oil', 'Toe Separators'],
  hourlyPattern: [
    0, 0, 0, 0, 0, 0,
    0, 0, 0, 40, 65, 85,
    90, 85, 80, 70, 65, 55,
    40, 20, 5, 0, 0, 0,
  ],
  revenue: {
    weekdayMin: 110000, weekdayMax: 190000,
    weekendMin: 200000, weekendMax: 300000,
    avgTicketMin: 5500, avgTicketMax: 11000,
  },
  staff: [
    { name: 'Mia T.', role: 'Lead Technician' },
    { name: 'Jordan A.', role: 'Nail Technician' },
    { name: 'Alexis N.', role: 'Lash Technician' },
    { name: 'Sam D.', role: 'Nail Technician' },
  ],
  products: [
    { name: 'Gel Manicure', sku: 'GEL-001', price: 5500, category: 'services', popularity: 0.95 },
    { name: 'Full Set', sku: 'SET-001', price: 9500, category: 'services', popularity: 0.80 },
    { name: 'Fill', sku: 'FIL-001', price: 6500, category: 'services', popularity: 0.85 },
    { name: 'Lash Extensions', sku: 'LSH-001', price: 15000, category: 'services', popularity: 0.60 },
    { name: 'Pedicure', sku: 'PED-001', price: 6000, category: 'services', popularity: 0.70 },
    { name: 'Gel Polish', sku: 'PLS-001', price: 1400, category: 'supplies', popularity: 0.65 },
    { name: 'Acrylic Powder', sku: 'ACR-001', price: 3200, category: 'supplies', popularity: 0.60 },
    { name: 'Lash Tray', sku: 'TRY-001', price: 2800, category: 'supplies', popularity: 0.50 },
    { name: 'Cuticle Oil', sku: 'CUT-002', price: 1200, category: 'retail', popularity: 0.25 },
    { name: 'Nail Art Kit', sku: 'ART-001', price: 3600, category: 'retail', popularity: 0.15 },
    { name: 'Toe Separators', sku: 'SEP-001', price: 600, category: 'supplies', popularity: 0.18 },
  ],
}

const MED_SPA: BusinessProfile = {
  businessName: 'Northline Aesthetics',
  businessNameCA: 'Northline Aesthetics',
  industryLabel: 'Med Spa / Aesthetics',
  peakLabel: '12:00–4:00 PM',
  topBundlePair: ['Consultation', 'Injectables'],
  deadStockItems: ['Body Wrap Kit', 'Peel Sample Pack'],
  hourlyPattern: [
    0, 0, 0, 0, 0, 0,
    0, 0, 0, 45, 65, 75,
    85, 90, 85, 75, 60, 40,
    15, 0, 0, 0, 0, 0,
  ],
  revenue: {
    weekdayMin: 280000, weekdayMax: 520000,
    weekendMin: 320000, weekendMax: 600000,
    avgTicketMin: 18000, avgTicketMax: 65000,
  },
  staff: [
    { name: 'Dr. Elise F.', role: 'Medical Director' },
    { name: 'Hana O.', role: 'Nurse Injector' },
    { name: 'Ruth A.', role: 'Aesthetician' },
    { name: 'Kit L.', role: 'Front of House' },
  ],
  products: [
    { name: 'Consultation', sku: 'CON-001', price: 0, category: 'services', popularity: 0.90 },
    { name: 'Injectables', sku: 'INJ-001', price: 65000, category: 'services', popularity: 0.70 },
    { name: 'Laser Session', sku: 'LAS-001', price: 30000, category: 'services', popularity: 0.55 },
    { name: 'Facial', sku: 'FAC-001', price: 18000, category: 'services', popularity: 0.80 },
    { name: 'Chemical Peel', sku: 'PEL-001', price: 22000, category: 'services', popularity: 0.45 },
    { name: 'Filler Syringe', sku: 'FLR-001', price: 42000, category: 'supplies', popularity: 0.60 },
    { name: 'Serum 30ml', sku: 'SER-001', price: 9500, category: 'retail', popularity: 0.50 },
    { name: 'SPF 50', sku: 'SPF-001', price: 4800, category: 'retail', popularity: 0.55 },
    { name: 'Retinol Cream', sku: 'RET-001', price: 8800, category: 'retail', popularity: 0.40 },
    { name: 'Peel Sample Pack', sku: 'PSP-001', price: 3200, category: 'retail', popularity: 0.10 },
    { name: 'Body Wrap Kit', sku: 'WRP-001', price: 5400, category: 'retail', popularity: 0.08 },
  ],
}

const DETAILING: BusinessProfile = {
  businessName: 'Apex Auto Detail',
  businessNameCA: 'Apex Auto Detail',
  industryLabel: 'Auto Detailing',
  peakLabel: '9:00 AM–2:00 PM',
  topBundlePair: ['Full Detail', 'Ceramic Coating'],
  deadStockItems: ['Trim Restorer', 'Headlight Kit'],
  hourlyPattern: [
    0, 0, 0, 0, 0, 0,
    0, 25, 70, 90, 85, 80,
    75, 70, 65, 55, 40, 20,
    5, 0, 0, 0, 0, 0,
  ],
  revenue: {
    weekdayMin: 150000, weekdayMax: 280000,
    weekendMin: 260000, weekendMax: 420000,
    avgTicketMin: 12000, avgTicketMax: 40000,
  },
  staff: [
    { name: 'Cole B.', role: 'Lead Detailer' },
    { name: 'Ravi M.', role: 'Detailer' },
    { name: 'Tash G.', role: 'Detailer' },
  ],
  products: [
    { name: 'Wash and Wax', sku: 'WSH-001', price: 12000, category: 'services', popularity: 0.90 },
    { name: 'Interior and Exterior', sku: 'INT-001', price: 22000, category: 'services', popularity: 0.80 },
    { name: 'Full Detail', sku: 'FUL-001', price: 40000, category: 'services', popularity: 0.55 },
    { name: 'Ceramic Coating', sku: 'CER-001', price: 90000, category: 'services', popularity: 0.25 },
    { name: 'Coating Bottle 50ml', sku: 'CTB-001', price: 22000, category: 'supplies', popularity: 0.30 },
    { name: 'Clay Bar', sku: 'CLB-001', price: 1800, category: 'supplies', popularity: 0.55 },
    { name: 'Polish Compound', sku: 'POL-001', price: 3400, category: 'supplies', popularity: 0.60 },
    { name: 'Microfibre x12', sku: 'MFB-001', price: 2600, category: 'supplies', popularity: 0.70 },
    { name: 'Tyre Dressing', sku: 'TYR-001', price: 1500, category: 'supplies', popularity: 0.50 },
    { name: 'Trim Restorer', sku: 'TRM-001', price: 2200, category: 'retail', popularity: 0.12 },
    { name: 'Headlight Kit', sku: 'HDL-001', price: 3900, category: 'retail', popularity: 0.10 },
  ],
}

const MOBILE_DETAILING: BusinessProfile = {
  ...DETAILING,
  businessName: 'Roadside Shine Mobile',
  businessNameCA: 'Roadside Shine Mobile',
  industryLabel: 'Mobile Detailing',
  // Fewer jobs a day than a two-bay shop: the van can only be in one place.
  revenue: {
    weekdayMin: 90000, weekdayMax: 180000,
    weekendMin: 160000, weekendMax: 260000,
    avgTicketMin: 12000, avgTicketMax: 38000,
  },
  staff: [
    { name: 'Cole B.', role: 'Owner / Detailer' },
    { name: 'Ravi M.', role: 'Detailer' },
  ],
}


const PIZZERIA: BusinessProfile = {
  businessName: "Tony's Pizzeria",
  businessNameCA: "Tony's Pizzeria",
  industryLabel: 'Pizza Shop',
  peakLabel: '5:00–8:00 PM',
  topBundlePair: ['Large Pepperoni', 'Garlic Knots'],
  deadStockItems: ['Anchovy Topping', 'Diet Root Beer'],
  hourlyPattern: [
    0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 45,
    60, 40, 25, 30, 55, 90,
    100, 85, 60, 35, 10, 0,
  ],
  revenue: {
    weekdayMin: 190000, weekdayMax: 320000,
    weekendMin: 340000, weekendMax: 520000,
    avgTicketMin: 2400, avgTicketMax: 4600,
  },
  staff: [
    { name: 'Tony R.', role: 'Owner / Pizzaiolo' },
    { name: 'Dana K.', role: 'Counter' },
    { name: 'Marco S.', role: 'Driver' },
    { name: 'Priya N.', role: 'Driver' },
    { name: 'Owen B.', role: 'Kitchen' },
  ],
  products: [
    { name: 'Large Pepperoni', sku: 'PEP-L', price: 2400, category: 'pizza', popularity: 0.95 },
    { name: 'Large Cheese', sku: 'CHE-L', price: 2100, category: 'pizza', popularity: 0.90 },
    { name: 'Meat Feast', sku: 'MEA-L', price: 2900, category: 'pizza', popularity: 0.70 },
    { name: 'Veggie Supreme', sku: 'VEG-L', price: 2600, category: 'pizza', popularity: 0.55 },
    { name: 'Family Deal', sku: 'FAM-001', price: 4500, category: 'deals', popularity: 0.65 },
    { name: 'Garlic Knots', sku: 'KNO-006', price: 700, category: 'sides', popularity: 0.80 },
    { name: 'Buffalo Wings', sku: 'WIN-008', price: 1100, category: 'sides', popularity: 0.75 },
    { name: 'Mozzarella Sticks', sku: 'MOZ-006', price: 800, category: 'sides', popularity: 0.60 },
    { name: 'Caesar Salad', sku: 'CAE-001', price: 900, category: 'sides', popularity: 0.40 },
    { name: 'Coke 2L', sku: 'COK-2L', price: 400, category: 'drinks', popularity: 0.70 },
    { name: 'Diet Root Beer', sku: 'DRB-001', price: 400, category: 'drinks', popularity: 0.12 },
    { name: 'Anchovy Topping', sku: 'ANC-001', price: 200, category: 'toppings', popularity: 0.08 },
    { name: 'Extra Cheese', sku: 'XCH-001', price: 250, category: 'toppings', popularity: 0.65 },
  ],
}

const GOLF_COURSE: BusinessProfile = {
  businessName: 'Fairway Pines Golf Club',
  businessNameCA: 'Cedar Creek Golf Club',
  industryLabel: 'Golf Course',
  peakLabel: '7:00–11:00 AM',
  topBundlePair: ['18 Holes', 'Cart Rental'],
  deadStockItems: ['Logo Windbreaker', 'Golf Umbrella', 'Bucket Hat'],
  // A course's day is front-loaded harder than any trade here: the morning
  // tee sheet decides the whole day, with a smaller wave after work for nine.
  hourlyPattern: [
    0, 0, 0, 0, 0, 10,
    45, 90, 100, 95, 85, 70,
    60, 55, 50, 55, 60, 50,
    30, 10, 0, 0, 0, 0,
  ],
  revenue: {
    weekdayMin: 350000, weekdayMax: 600000,
    weekendMin: 700000, weekendMax: 1100000,
    avgTicketMin: 5500, avgTicketMax: 11000,
  },
  staff: [
    { name: 'Walt P.', role: 'Head Professional' },
    { name: 'Dana R.', role: 'Pro Shop Lead' },
    { name: 'Gus M.', role: 'Starter' },
    { name: 'Lena K.', role: 'Grille Lead' },
    { name: 'Ray T.', role: 'Marshal' },
    { name: 'Sofia B.', role: 'Grille Cook' },
  ],
  products: [
    // Index 1 is the line the demo's shrink anomaly names, so it must be a
    // PHYSICAL product — counted stock cannot come up short on a green fee.
    { name: '18 Holes', sku: 'GRN-18', price: 6500, category: 'green fees', popularity: 0.95 },
    { name: 'Dozen Balls', sku: 'PRO-BAL', price: 3400, category: 'pro shop', popularity: 0.65 },
    { name: 'Twilight Rate', sku: 'GRN-TWI', price: 4200, category: 'green fees', popularity: 0.60 },
    { name: 'Cart Rental', sku: 'CRT-001', price: 2200, category: 'rentals', popularity: 0.90 },
    { name: 'Range Bucket', sku: 'RNG-001', price: 1200, category: 'rentals', popularity: 0.75 },
    { name: 'Club Rental Set', sku: 'CLB-001', price: 4500, category: 'rentals', popularity: 0.20 },
    { name: '9 Holes', sku: 'GRN-09', price: 3800, category: 'green fees', popularity: 0.70 },
    { name: 'Golf Glove', sku: 'PRO-GLV', price: 2400, category: 'pro shop', popularity: 0.55 },
    { name: 'Logo Polo', sku: 'PRO-POL', price: 5800, category: 'pro shop', popularity: 0.35 },
    { name: 'Logo Windbreaker', sku: 'PRO-WND', price: 8900, category: 'pro shop', popularity: 0.10 },
    { name: 'Turn Dog & Chips', sku: 'GRL-DOG', price: 950, category: 'grille', popularity: 0.85 },
    { name: 'Clubhouse Burger', sku: 'GRL-BRG', price: 1600, category: 'grille', popularity: 0.70 },
    { name: 'Domestic Beer', sku: 'GRL-BER', price: 650, category: 'grille', popularity: 0.80 },
    { name: 'Iced Tea', sku: 'GRL-TEA', price: 400, category: 'grille', popularity: 0.60 },
  ],
}

const PROFILES: Record<BusinessType, BusinessProfile> = {
  coffee_shop: COFFEE_SHOP,
  restaurant: RESTAURANT,
  fast_food: FAST_FOOD,
  auto_shop: AUTO_SHOP,
  smoke_shop: SMOKE_SHOP,
  peptide_shop: PEPTIDE_SHOP,
  barbershop: BARBERSHOP,
  nails: NAIL_STUDIO,
  medspa: MED_SPA,
  detailing: DETAILING,
  mobile_detailing: MOBILE_DETAILING,
  pizzeria: PIZZERIA,
  golf_course: GOLF_COURSE,
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
