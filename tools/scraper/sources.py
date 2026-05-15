"""
Meridian Knowledge Sources Registry — 120+ sources for swarm training.

Categories:
  - Consulting & Strategy (Big 4, top firms)
  - Finance & Accounting (CFO knowledge, accounting standards)
  - Restaurant & Food Service (ops, food cost, labor)
  - Retail & Commerce (inventory, pricing, merchandising)
  - Small Business & Entrepreneurship (startup wisdom, scaling)
  - Analytics & Data Science (BI, forecasting, ML)
  - POS & Payments (Square, Toast, Clover, Shopify)
  - Economics & Markets (macro trends, market intelligence)
  - Leadership & Management (top business authors)
  - Book Summaries & Expert Knowledge (top financial minds)
  - Industry Research & Reports
  - Marketing & Growth
"""

SOURCES = {
    # ═══════════════════════════════════════════════════════════
    # CONSULTING & STRATEGY
    # ═══════════════════════════════════════════════════════════
    "mckinsey": {
        "name": "McKinsey & Company",
        "base_url": "https://www.mckinsey.com",
        "start_paths": [
            "/industries/retail/our-insights",
            "/industries/consumer-packaged-goods/our-insights",
            "/capabilities/operations/our-insights",
            "/capabilities/growth-marketing-and-sales/our-insights",
            "/capabilities/strategy-and-corporate-finance/our-insights",
        ],
        "topics": ["retail", "restaurant", "supply-chain", "operations", "strategy", "finance"],
    },
    "bcg": {
        "name": "Boston Consulting Group",
        "base_url": "https://www.bcg.com",
        "start_paths": [
            "/publications/collections/retail-industry-insights",
            "/publications/collections/consumer-products-insights",
            "/publications/collections/pricing-revenue-management",
        ],
        "topics": ["strategy", "retail", "pricing", "consumer", "operations"],
    },
    "bain": {
        "name": "Bain & Company",
        "base_url": "https://www.bain.com",
        "start_paths": [
            "/insights/topics/retail",
            "/insights/topics/customer-experience",
            "/insights/topics/digital-transformation-innovation",
        ],
        "topics": ["retail", "customer-experience", "strategy", "growth"],
    },
    "deloitte": {
        "name": "Deloitte Insights",
        "base_url": "https://www2.deloitte.com",
        "start_paths": [
            "/us/en/insights/industry/retail-distribution.html",
            "/us/en/insights/industry/restaurant-and-food-service.html",
            "/us/en/insights/topics/analytics.html",
            "/us/en/insights/economy/financial-advisory.html",
        ],
        "topics": ["retail", "restaurant", "food-service", "analytics", "finance"],
    },
    "pwc": {
        "name": "PwC Strategy",
        "base_url": "https://www.pwc.com",
        "start_paths": [
            "/us/en/industries/consumer-markets.html",
            "/us/en/services/consulting/business-transformation.html",
        ],
        "topics": ["retail", "consumer", "transformation", "strategy"],
    },
    "ey": {
        "name": "EY Insights",
        "base_url": "https://www.ey.com",
        "start_paths": [
            "/en_us/insights/consumer-products-retail",
            "/en_us/insights/strategy-transactions",
        ],
        "topics": ["retail", "consumer", "strategy", "transactions"],
    },
    "kpmg": {
        "name": "KPMG Insights",
        "base_url": "https://kpmg.com",
        "start_paths": [
            "/xx/en/industries/consumer-and-retail.html",
            "/xx/en/insights.html",
        ],
        "topics": ["retail", "consumer", "audit", "strategy"],
    },

    # ═══════════════════════════════════════════════════════════
    # ACADEMIA & BUSINESS SCHOOLS
    # ═══════════════════════════════════════════════════════════
    "hbr": {
        "name": "Harvard Business Review",
        "base_url": "https://hbr.org",
        "start_paths": [
            "/topic/subject/operations-and-supply-chain-management",
            "/topic/subject/customer-experience",
            "/topic/subject/analytics-and-data-science",
            "/topic/subject/finance-and-investing",
            "/topic/subject/accounting",
            "/topic/subject/entrepreneurship",
            "/topic/subject/pricing-strategy",
        ],
        "topics": ["analytics", "management", "finance", "accounting", "pricing", "entrepreneurship"],
    },
    "mit_sloan": {
        "name": "MIT Sloan Management Review",
        "base_url": "https://sloanreview.mit.edu",
        "start_paths": [
            "/tag/analytics/",
            "/tag/digital-transformation/",
            "/tag/operations/",
            "/tag/strategy/",
            "/tag/leadership/",
        ],
        "topics": ["analytics", "digital-transformation", "operations", "ai", "strategy"],
    },
    "wharton": {
        "name": "Wharton Knowledge",
        "base_url": "https://knowledge.wharton.upenn.edu",
        "start_paths": [
            "/topic/finance/",
            "/topic/marketing/",
            "/topic/management/",
            "/topic/entrepreneurship/",
        ],
        "topics": ["finance", "marketing", "management", "entrepreneurship"],
    },
    "stanford_gsb": {
        "name": "Stanford GSB Insights",
        "base_url": "https://www.gsb.stanford.edu",
        "start_paths": [
            "/insights/topics/finance",
            "/insights/topics/entrepreneurship",
            "/insights/topics/operations-information-technology",
        ],
        "topics": ["finance", "entrepreneurship", "operations", "technology"],
    },
    "kellogg_insight": {
        "name": "Kellogg Insight",
        "base_url": "https://insight.kellogg.northwestern.edu",
        "start_paths": [
            "/finance-accounting",
            "/marketing",
            "/strategy",
            "/operations",
        ],
        "topics": ["finance", "accounting", "marketing", "strategy", "operations"],
    },
    "columbia_ideas": {
        "name": "Columbia Business School Ideas",
        "base_url": "https://www8.gsb.columbia.edu",
        "start_paths": [
            "/articles/topics/finance",
            "/articles/topics/management",
        ],
        "topics": ["finance", "management", "economics"],
    },

    # ═══════════════════════════════════════════════════════════
    # FINANCE & ACCOUNTING
    # ═══════════════════════════════════════════════════════════
    "investopedia": {
        "name": "Investopedia",
        "base_url": "https://www.investopedia.com",
        "start_paths": [
            "/small-business-4427754",
            "/financial-analysis-4427788",
            "/terms/c/cashflow.asp",
            "/terms/b/burnrate.asp",
            "/terms/g/grossmargin.asp",
            "/terms/n/net-profit-margin.asp",
            "/terms/e/ebitda.asp",
            "/terms/w/workingcapital.asp",
            "/terms/r/returnoninvestment.asp",
            "/terms/b/breakeven-analysis.asp",
        ],
        "topics": ["finance", "small-business", "cash-flow", "margins", "accounting"],
    },
    "cfo_magazine": {
        "name": "CFO Magazine",
        "base_url": "https://www.cfo.com",
        "start_paths": [
            "/accounting-tax/",
            "/finance/",
            "/risk-compliance/",
            "/strategy/",
        ],
        "topics": ["cfo", "finance", "accounting", "tax", "risk", "strategy"],
    },
    "accounting_today": {
        "name": "Accounting Today",
        "base_url": "https://www.accountingtoday.com",
        "start_paths": [
            "/news/",
            "/opinion/",
        ],
        "topics": ["accounting", "tax", "audit", "finance", "compliance"],
    },
    "journal_accountancy": {
        "name": "Journal of Accountancy",
        "base_url": "https://www.journalofaccountancy.com",
        "start_paths": [
            "/issues/",
            "/news/",
        ],
        "topics": ["accounting", "cpa", "audit", "tax", "standards"],
    },
    "nerdwallet_biz": {
        "name": "NerdWallet Business",
        "base_url": "https://www.nerdwallet.com",
        "start_paths": [
            "/article/small-business/",
            "/article/finance/",
        ],
        "topics": ["small-business", "finance", "lending", "cash-flow"],
    },
    "bench_accounting": {
        "name": "Bench Accounting Blog",
        "base_url": "https://bench.co",
        "start_paths": [
            "/blog/",
            "/blog/bookkeeping/",
            "/blog/tax-tips/",
        ],
        "topics": ["accounting", "bookkeeping", "tax", "small-business", "cash-flow"],
    },
    "quickbooks_blog": {
        "name": "QuickBooks Resource Center",
        "base_url": "https://quickbooks.intuit.com",
        "start_paths": [
            "/r/cash-flow",
            "/r/bookkeeping",
            "/r/growing-a-business",
            "/r/payments",
        ],
        "topics": ["accounting", "cash-flow", "bookkeeping", "payments", "small-business"],
    },
    "xero_blog": {
        "name": "Xero Blog",
        "base_url": "https://www.xero.com",
        "start_paths": [
            "/us/resources/small-business-guides/",
            "/blog/",
        ],
        "topics": ["accounting", "small-business", "cash-flow", "invoicing"],
    },
    "freshbooks_blog": {
        "name": "FreshBooks Blog",
        "base_url": "https://www.freshbooks.com",
        "start_paths": [
            "/blog/",
            "/hub/accounting/",
            "/hub/invoicing/",
        ],
        "topics": ["invoicing", "accounting", "freelance", "small-business"],
    },

    # ═══════════════════════════════════════════════════════════
    # RESTAURANT & FOOD SERVICE
    # ═══════════════════════════════════════════════════════════
    "nra_restaurant": {
        "name": "National Restaurant Association",
        "base_url": "https://restaurant.org",
        "start_paths": [
            "/research-and-media/research",
            "/education-and-resources/running-a-restaurant",
            "/education-and-resources/workforce",
        ],
        "topics": ["restaurant", "food-service", "labor", "food-cost", "operations"],
    },
    "toast_blog": {
        "name": "Toast Restaurant Blog",
        "base_url": "https://pos.toasttab.com",
        "start_paths": [
            "/blog/restaurant-management",
            "/blog/restaurant-finance",
            "/blog/restaurant-operations",
            "/blog/restaurant-marketing",
            "/blog/restaurant-technology",
        ],
        "topics": ["restaurant", "pos", "operations", "finance", "food-cost", "marketing"],
    },
    "restaurant_dive": {
        "name": "Restaurant Dive",
        "base_url": "https://www.restaurantdive.com",
        "start_paths": [
            "/topic/operations/",
            "/topic/finance/",
            "/topic/technology/",
            "/topic/marketing/",
        ],
        "topics": ["restaurant", "operations", "finance", "technology", "trends"],
    },
    "fsr_magazine": {
        "name": "FSR Magazine",
        "base_url": "https://www.fsrmagazine.com",
        "start_paths": [
            "/finance/",
            "/operations/",
            "/workforce/",
        ],
        "topics": ["restaurant", "full-service", "finance", "operations", "labor"],
    },
    "qsr_magazine": {
        "name": "QSR Magazine",
        "base_url": "https://www.qsrmagazine.com",
        "start_paths": [
            "/finance/",
            "/operations/",
            "/growth/",
            "/technology/",
        ],
        "topics": ["restaurant", "quick-service", "finance", "operations", "growth"],
    },
    "nations_restaurant": {
        "name": "Nation's Restaurant News",
        "base_url": "https://www.nrn.com",
        "start_paths": [
            "/operations/",
            "/finance/",
            "/technology/",
        ],
        "topics": ["restaurant", "operations", "finance", "technology", "trends"],
    },
    "modern_restaurant": {
        "name": "Modern Restaurant Management",
        "base_url": "https://modernrestaurantmanagement.com",
        "start_paths": [
            "/category/operations/",
            "/category/finance/",
            "/category/technology/",
        ],
        "topics": ["restaurant", "management", "operations", "technology"],
    },
    "restaurant_engine": {
        "name": "Restaurant Engine",
        "base_url": "https://restaurantengine.com",
        "start_paths": [
            "/blog/",
        ],
        "topics": ["restaurant", "marketing", "operations", "finance"],
    },
    "foodservice_director": {
        "name": "FoodService Director",
        "base_url": "https://www.foodservicedirector.com",
        "start_paths": [
            "/operations/",
            "/menu-development/",
        ],
        "topics": ["food-service", "operations", "menu", "food-cost"],
    },
    "the_restaurant_expert": {
        "name": "The Restaurant Expert",
        "base_url": "https://www.therestaurantexpert.com",
        "start_paths": [
            "/restaurant-systems/",
            "/restaurant-coaching/",
        ],
        "topics": ["restaurant", "coaching", "systems", "finance", "operations"],
    },

    # ═══════════════════════════════════════════════════════════
    # RETAIL & COMMERCE
    # ═══════════════════════════════════════════════════════════
    "lightspeed_blog": {
        "name": "Lightspeed Blog",
        "base_url": "https://www.lightspeedhq.com",
        "start_paths": [
            "/blog/category/restaurant-management",
            "/blog/category/retail-management",
            "/blog/category/ecommerce",
        ],
        "topics": ["retail", "restaurant", "pos", "inventory", "analytics", "ecommerce"],
    },
    "retail_dive": {
        "name": "Retail Dive",
        "base_url": "https://www.retaildive.com",
        "start_paths": [
            "/topic/store-operations/",
            "/topic/marketing/",
            "/topic/technology/",
            "/topic/supply-chain/",
        ],
        "topics": ["retail", "operations", "marketing", "technology", "supply-chain"],
    },
    "nrf": {
        "name": "National Retail Federation",
        "base_url": "https://nrf.com",
        "start_paths": [
            "/blog/",
            "/research/",
        ],
        "topics": ["retail", "industry", "trends", "technology", "workforce"],
    },
    "shopify_blog": {
        "name": "Shopify Blog",
        "base_url": "https://www.shopify.com",
        "start_paths": [
            "/blog/topics/guides",
            "/blog/topics/ecommerce",
            "/blog/topics/retail",
            "/blog/topics/sell-online",
        ],
        "topics": ["retail", "ecommerce", "marketing", "inventory", "pos"],
    },
    "vend_blog": {
        "name": "Vend (Lightspeed Retail)",
        "base_url": "https://www.vendhq.com",
        "start_paths": [
            "/blog/",
        ],
        "topics": ["retail", "pos", "inventory", "customer-experience"],
    },
    "retail_minded": {
        "name": "Retail Minded",
        "base_url": "https://retailminded.com",
        "start_paths": [
            "/category/retail-tips/",
        ],
        "topics": ["retail", "small-business", "merchandising", "operations"],
    },
    "retail_touch_points": {
        "name": "Retail TouchPoints",
        "base_url": "https://www.retailtouchpoints.com",
        "start_paths": [
            "/topics/store-operations/",
            "/topics/customer-experience/",
            "/topics/payment-security/",
        ],
        "topics": ["retail", "operations", "customer-experience", "payments"],
    },
    "progressive_grocer": {
        "name": "Progressive Grocer",
        "base_url": "https://progressivegrocer.com",
        "start_paths": [
            "/operations/",
            "/technology/",
        ],
        "topics": ["grocery", "retail", "operations", "technology", "food"],
    },

    # ═══════════════════════════════════════════════════════════
    # SMALL BUSINESS & ENTREPRENEURSHIP
    # ═══════════════════════════════════════════════════════════
    "score_org": {
        "name": "SCORE Small Business",
        "base_url": "https://www.score.org",
        "start_paths": [
            "/resource-library/topics/financial-management",
            "/resource-library/topics/marketing-and-sales",
            "/resource-library/topics/managing-a-business",
            "/resource-library/topics/starting-a-business",
        ],
        "topics": ["small-business", "finance", "marketing", "growth", "cash-flow", "startup"],
    },
    "sba_gov": {
        "name": "SBA.gov",
        "base_url": "https://www.sba.gov",
        "start_paths": [
            "/business-guide/manage-your-business/",
            "/business-guide/grow-your-business/",
            "/business-guide/plan-your-business/",
            "/funding-programs/",
        ],
        "topics": ["small-business", "government", "funding", "management", "growth"],
    },
    "entrepreneur": {
        "name": "Entrepreneur",
        "base_url": "https://www.entrepreneur.com",
        "start_paths": [
            "/growing-a-business",
            "/finance",
            "/leadership",
            "/starting-a-business",
        ],
        "topics": ["entrepreneurship", "finance", "leadership", "growth", "startup"],
    },
    "inc_magazine": {
        "name": "Inc. Magazine",
        "base_url": "https://www.inc.com",
        "start_paths": [
            "/money",
            "/strategy",
            "/grow",
            "/lead",
        ],
        "topics": ["entrepreneurship", "finance", "strategy", "growth", "leadership"],
    },
    "forbes_small_biz": {
        "name": "Forbes Small Business",
        "base_url": "https://www.forbes.com",
        "start_paths": [
            "/small-business/",
            "/leadership/",
            "/money/",
        ],
        "topics": ["small-business", "leadership", "finance", "entrepreneurship"],
    },
    "fast_company": {
        "name": "Fast Company",
        "base_url": "https://www.fastcompany.com",
        "start_paths": [
            "/work-life/",
            "/technology/",
        ],
        "topics": ["innovation", "technology", "management", "leadership"],
    },
    "startup_nation": {
        "name": "StartupNation",
        "base_url": "https://startupnation.com",
        "start_paths": [
            "/grow-your-business/",
            "/start-your-business/",
        ],
        "topics": ["startup", "small-business", "growth", "finance"],
    },
    "bplans": {
        "name": "Bplans",
        "base_url": "https://www.bplans.com",
        "start_paths": [
            "/business-planning/",
            "/starting-a-business/",
            "/business-funding/",
        ],
        "topics": ["business-planning", "startup", "funding", "small-business"],
    },
    "fundera": {
        "name": "Fundera by NerdWallet",
        "base_url": "https://www.fundera.com",
        "start_paths": [
            "/blog/",
        ],
        "topics": ["small-business", "lending", "finance", "cash-flow"],
    },

    # ═══════════════════════════════════════════════════════════
    # ANALYTICS & DATA SCIENCE
    # ═══════════════════════════════════════════════════════════
    "a16z": {
        "name": "Andreessen Horowitz",
        "base_url": "https://a16z.com",
        "start_paths": [
            "/content-type/article/",
        ],
        "topics": ["fintech", "marketplace", "saas", "ai", "growth"],
    },
    "towards_data_science": {
        "name": "Towards Data Science",
        "base_url": "https://towardsdatascience.com",
        "start_paths": [
            "/tagged/business-analytics",
            "/tagged/forecasting",
            "/tagged/time-series",
            "/tagged/retail-analytics",
        ],
        "topics": ["analytics", "data-science", "forecasting", "time-series", "ml"],
    },
    "analytics_vidhya": {
        "name": "Analytics Vidhya",
        "base_url": "https://www.analyticsvidhya.com",
        "start_paths": [
            "/blog/category/business-analytics/",
            "/blog/category/data-science/",
        ],
        "topics": ["analytics", "data-science", "business-analytics", "ml"],
    },
    "kdnuggets": {
        "name": "KDnuggets",
        "base_url": "https://www.kdnuggets.com",
        "start_paths": [
            "/tag/business-analytics",
            "/tag/forecasting",
            "/tag/retail",
        ],
        "topics": ["analytics", "data-science", "forecasting", "retail", "ml"],
    },
    "data_science_central": {
        "name": "Data Science Central",
        "base_url": "https://www.datasciencecentral.com",
        "start_paths": [
            "/profiles/blogs/list",
        ],
        "topics": ["data-science", "analytics", "ml", "ai", "forecasting"],
    },
    "mode_analytics": {
        "name": "Mode Analytics Blog",
        "base_url": "https://mode.com",
        "start_paths": [
            "/blog/",
        ],
        "topics": ["analytics", "sql", "data-science", "business-intelligence"],
    },

    # ═══════════════════════════════════════════════════════════
    # POS & PAYMENTS
    # ═══════════════════════════════════════════════════════════
    "square_blog": {
        "name": "Square Blog",
        "base_url": "https://squareup.com",
        "start_paths": [
            "/us/en/townsquare/",
            "/us/en/townsquare/growing-your-business",
            "/us/en/townsquare/managing-your-finances",
        ],
        "topics": ["pos", "payments", "small-business", "finance", "growth"],
    },
    "clover_blog": {
        "name": "Clover Blog",
        "base_url": "https://blog.clover.com",
        "start_paths": [
            "/",
        ],
        "topics": ["pos", "payments", "restaurant", "retail", "operations"],
    },
    "stripe_guides": {
        "name": "Stripe Guides",
        "base_url": "https://stripe.com",
        "start_paths": [
            "/guides",
            "/resources",
        ],
        "topics": ["payments", "fintech", "saas", "revenue", "billing"],
    },
    "adyen_insights": {
        "name": "Adyen Insights",
        "base_url": "https://www.adyen.com",
        "start_paths": [
            "/knowledge-hub/",
        ],
        "topics": ["payments", "retail", "omnichannel", "fintech"],
    },
    "revel_blog": {
        "name": "Revel Systems Blog",
        "base_url": "https://revelsystems.com",
        "start_paths": [
            "/blog/",
        ],
        "topics": ["pos", "restaurant", "retail", "operations", "technology"],
    },
    "touchbistro_blog": {
        "name": "TouchBistro Blog",
        "base_url": "https://www.touchbistro.com",
        "start_paths": [
            "/blog/",
        ],
        "topics": ["pos", "restaurant", "operations", "marketing", "finance"],
    },
    "olo_blog": {
        "name": "Olo Blog",
        "base_url": "https://www.olo.com",
        "start_paths": [
            "/blog/",
        ],
        "topics": ["restaurant", "digital-ordering", "operations", "technology"],
    },

    # ═══════════════════════════════════════════════════════════
    # ECONOMICS & MARKETS
    # ═══════════════════════════════════════════════════════════
    "fed_reserve": {
        "name": "Federal Reserve Economic Data Blog",
        "base_url": "https://fredblog.stlouisfed.org",
        "start_paths": [
            "/",
        ],
        "topics": ["economics", "macro", "inflation", "employment", "gdp"],
    },
    "economist": {
        "name": "The Economist (Free)",
        "base_url": "https://www.economist.com",
        "start_paths": [
            "/finance-and-economics",
            "/business",
        ],
        "topics": ["economics", "finance", "business", "global-markets"],
    },
    "brookings": {
        "name": "Brookings Institution",
        "base_url": "https://www.brookings.edu",
        "start_paths": [
            "/topic/us-economy/",
            "/topic/business/",
            "/topic/workforce/",
        ],
        "topics": ["economics", "policy", "workforce", "business"],
    },
    "world_bank": {
        "name": "World Bank Blogs",
        "base_url": "https://blogs.worldbank.org",
        "start_paths": [
            "/developmenttalk",
            "/psd",
        ],
        "topics": ["economics", "development", "markets", "finance"],
    },
    "imf_blog": {
        "name": "IMF Blog",
        "base_url": "https://www.imf.org",
        "start_paths": [
            "/en/Blogs",
        ],
        "topics": ["economics", "macro", "global-finance", "policy"],
    },
    "nber_digest": {
        "name": "NBER Digest",
        "base_url": "https://www.nber.org",
        "start_paths": [
            "/digest/",
        ],
        "topics": ["economics", "research", "labor", "finance", "policy"],
    },

    # ═══════════════════════════════════════════════════════════
    # LEADERSHIP & MANAGEMENT (TOP BUSINESS AUTHORS)
    # ═══════════════════════════════════════════════════════════
    "simon_sinek": {
        "name": "Simon Sinek Blog",
        "base_url": "https://simonsinek.com",
        "start_paths": [
            "/stories/",
        ],
        "topics": ["leadership", "management", "culture", "purpose"],
    },
    "seth_godin": {
        "name": "Seth Godin Blog",
        "base_url": "https://seths.blog",
        "start_paths": [
            "/",
        ],
        "topics": ["marketing", "leadership", "entrepreneurship", "strategy"],
    },
    "james_clear": {
        "name": "James Clear (Atomic Habits)",
        "base_url": "https://jamesclear.com",
        "start_paths": [
            "/articles/",
            "/best-articles/",
        ],
        "topics": ["habits", "productivity", "leadership", "self-improvement"],
    },
    "adam_grant": {
        "name": "Adam Grant Articles",
        "base_url": "https://adamgrant.net",
        "start_paths": [
            "/articles/",
        ],
        "topics": ["management", "leadership", "organizational-psychology"],
    },
    "gary_vee": {
        "name": "GaryVee Blog",
        "base_url": "https://www.garyvaynerchuk.com",
        "start_paths": [
            "/blog/",
        ],
        "topics": ["entrepreneurship", "marketing", "growth", "social-media"],
    },
    "naval_blog": {
        "name": "Naval Ravikant (Almanack)",
        "base_url": "https://nav.al",
        "start_paths": [
            "/",
        ],
        "topics": ["wealth", "entrepreneurship", "investing", "philosophy"],
    },
    "tim_ferriss": {
        "name": "Tim Ferriss Blog",
        "base_url": "https://tim.blog",
        "start_paths": [
            "/",
        ],
        "topics": ["productivity", "entrepreneurship", "investing", "optimization"],
    },
    "first_round": {
        "name": "First Round Review",
        "base_url": "https://review.firstround.com",
        "start_paths": [
            "/",
        ],
        "topics": ["startup", "management", "leadership", "growth", "hiring"],
    },

    # ═══════════════════════════════════════════════════════════
    # BOOK SUMMARIES & EXPERT KNOWLEDGE
    # (Public summaries, reviews, and author content)
    # ═══════════════════════════════════════════════════════════
    "fourminutebooks": {
        "name": "Four Minute Books",
        "base_url": "https://fourminutebooks.com",
        "start_paths": [
            "/book-summaries/",
        ],
        "topics": ["book-summaries", "business", "finance", "self-improvement", "leadership"],
    },
    "readingraphics": {
        "name": "Readingraphics Book Summaries",
        "base_url": "https://readingraphics.com",
        "start_paths": [
            "/book-summary/",
        ],
        "topics": ["book-summaries", "business", "strategy", "management"],
    },
    "getstoryshots": {
        "name": "StoryShots Book Summaries",
        "base_url": "https://www.getstoryshots.com",
        "start_paths": [
            "/books/",
        ],
        "topics": ["book-summaries", "business", "finance", "self-help"],
    },
    "sam_thomas_davies": {
        "name": "Sam Thomas Davies Summaries",
        "base_url": "https://www.samuelthomasdavies.com",
        "start_paths": [
            "/book-summaries/",
        ],
        "topics": ["book-summaries", "business", "productivity", "finance"],
    },

    # ═══════════════════════════════════════════════════════════
    # INVESTING & FINANCIAL EXPERTS
    # ═══════════════════════════════════════════════════════════
    "motley_fool": {
        "name": "Motley Fool",
        "base_url": "https://www.fool.com",
        "start_paths": [
            "/investing/",
            "/retirement/",
            "/personal-finance/",
        ],
        "topics": ["investing", "finance", "retirement", "personal-finance"],
    },
    "morningstar": {
        "name": "Morningstar",
        "base_url": "https://www.morningstar.com",
        "start_paths": [
            "/articles/",
        ],
        "topics": ["investing", "funds", "finance", "markets", "analysis"],
    },
    "seeking_alpha": {
        "name": "Seeking Alpha",
        "base_url": "https://seekingalpha.com",
        "start_paths": [
            "/market-outlook/",
            "/stock-ideas/",
        ],
        "topics": ["investing", "stocks", "analysis", "markets", "valuation"],
    },
    "investor_gov": {
        "name": "Investor.gov",
        "base_url": "https://www.investor.gov",
        "start_paths": [
            "/introduction-investing/",
            "/financial-tools-calculators/",
        ],
        "topics": ["investing", "finance", "education", "regulation"],
    },
    "buffett_berkshire": {
        "name": "Berkshire Hathaway Letters",
        "base_url": "https://www.berkshirehathaway.com",
        "start_paths": [
            "/letters/letters.html",
        ],
        "topics": ["investing", "value-investing", "buffett", "business-analysis"],
    },
    "bridgewater": {
        "name": "Bridgewater (Ray Dalio)",
        "base_url": "https://www.bridgewater.com",
        "start_paths": [
            "/research-and-insights/",
        ],
        "topics": ["investing", "macro", "economics", "principles", "risk"],
    },
    "oaktree_memos": {
        "name": "Oaktree Capital (Howard Marks)",
        "base_url": "https://www.oaktreecapital.com",
        "start_paths": [
            "/insights/memos/",
        ],
        "topics": ["investing", "risk", "value-investing", "markets", "cycles"],
    },

    # ═══════════════════════════════════════════════════════════
    # INDUSTRY RESEARCH & REPORTS
    # ═══════════════════════════════════════════════════════════
    "ibisworld": {
        "name": "IBISWorld Industry Insights",
        "base_url": "https://www.ibisworld.com",
        "start_paths": [
            "/industry-insider/",
        ],
        "topics": ["industry-research", "market-analysis", "trends"],
    },
    "statista": {
        "name": "Statista",
        "base_url": "https://www.statista.com",
        "start_paths": [
            "/topics/",
        ],
        "topics": ["statistics", "market-data", "industry-research", "trends"],
    },
    "technomic": {
        "name": "Technomic (Food Industry)",
        "base_url": "https://www.technomic.com",
        "start_paths": [
            "/newsroom/",
        ],
        "topics": ["food-service", "restaurant", "industry-research", "trends"],
    },
    "npd_group": {
        "name": "Circana (NPD Group)",
        "base_url": "https://www.circana.com",
        "start_paths": [
            "/intelligence/press-releases/",
        ],
        "topics": ["consumer", "retail", "food-service", "industry-research"],
    },
    "gartner": {
        "name": "Gartner Research",
        "base_url": "https://www.gartner.com",
        "start_paths": [
            "/en/insights",
        ],
        "topics": ["technology", "analytics", "strategy", "industry-research"],
    },
    "forrester": {
        "name": "Forrester Research",
        "base_url": "https://www.forrester.com",
        "start_paths": [
            "/blogs/",
        ],
        "topics": ["technology", "customer-experience", "analytics", "retail"],
    },
    "cb_insights": {
        "name": "CB Insights",
        "base_url": "https://www.cbinsights.com",
        "start_paths": [
            "/research/",
        ],
        "topics": ["fintech", "retail-tech", "trends", "startup", "venture"],
    },

    # ═══════════════════════════════════════════════════════════
    # MARKETING & GROWTH
    # ═══════════════════════════════════════════════════════════
    "hubspot_blog": {
        "name": "HubSpot Blog",
        "base_url": "https://blog.hubspot.com",
        "start_paths": [
            "/marketing/",
            "/sales/",
            "/service/",
        ],
        "topics": ["marketing", "sales", "crm", "growth", "customer-service"],
    },
    "neil_patel": {
        "name": "Neil Patel Blog",
        "base_url": "https://neilpatel.com",
        "start_paths": [
            "/blog/",
        ],
        "topics": ["marketing", "seo", "growth", "digital-marketing"],
    },
    "copyblogger": {
        "name": "Copyblogger",
        "base_url": "https://copyblogger.com",
        "start_paths": [
            "/blog/",
        ],
        "topics": ["content-marketing", "copywriting", "marketing", "strategy"],
    },
    "growthhackers": {
        "name": "GrowthHackers",
        "base_url": "https://growthhackers.com",
        "start_paths": [
            "/articles/",
        ],
        "topics": ["growth", "marketing", "product", "analytics", "conversion"],
    },
    "buffer_blog": {
        "name": "Buffer Blog",
        "base_url": "https://buffer.com",
        "start_paths": [
            "/resources/",
        ],
        "topics": ["social-media", "marketing", "small-business", "growth"],
    },

    # ═══════════════════════════════════════════════════════════
    # LABOR & WORKFORCE
    # ═══════════════════════════════════════════════════════════
    "bls_gov": {
        "name": "Bureau of Labor Statistics",
        "base_url": "https://www.bls.gov",
        "start_paths": [
            "/news.release/",
            "/opub/mlr/",
        ],
        "topics": ["labor", "wages", "employment", "economics", "statistics"],
    },
    "shrm": {
        "name": "SHRM (HR)",
        "base_url": "https://www.shrm.org",
        "start_paths": [
            "/topics-tools/",
            "/resourcesandtools/",
        ],
        "topics": ["hr", "labor", "compensation", "workforce", "management"],
    },
    "7shifts_blog": {
        "name": "7shifts Blog (Restaurant Labor)",
        "base_url": "https://www.7shifts.com",
        "start_paths": [
            "/blog/",
        ],
        "topics": ["restaurant", "labor", "scheduling", "workforce", "operations"],
    },
    "homebase_blog": {
        "name": "Homebase Blog",
        "base_url": "https://joinhomebase.com",
        "start_paths": [
            "/blog/",
        ],
        "topics": ["small-business", "labor", "scheduling", "hr", "operations"],
    },

    # ═══════════════════════════════════════════════════════════
    # SUPPLY CHAIN & OPERATIONS
    # ═══════════════════════════════════════════════════════════
    "supply_chain_dive": {
        "name": "Supply Chain Dive",
        "base_url": "https://www.supplychaindive.com",
        "start_paths": [
            "/topic/logistics/",
            "/topic/procurement/",
            "/topic/technology/",
        ],
        "topics": ["supply-chain", "logistics", "procurement", "operations"],
    },
    "scm_world": {
        "name": "Gartner Supply Chain",
        "base_url": "https://www.gartner.com",
        "start_paths": [
            "/en/supply-chain/insights",
        ],
        "topics": ["supply-chain", "operations", "logistics", "planning"],
    },

    # ═══════════════════════════════════════════════════════════
    # CANADA-SPECIFIC
    # ═══════════════════════════════════════════════════════════
    "bdc_canada": {
        "name": "BDC (Business Dev Bank of Canada)",
        "base_url": "https://www.bdc.ca",
        "start_paths": [
            "/en/articles-tools/",
            "/en/articles-tools/money/",
        ],
        "topics": ["canada", "small-business", "finance", "growth", "lending"],
    },
    "restaurants_canada": {
        "name": "Restaurants Canada",
        "base_url": "https://www.restaurantscanada.org",
        "start_paths": [
            "/resources/",
        ],
        "topics": ["canada", "restaurant", "food-service", "labor", "operations"],
    },
    "retail_council_canada": {
        "name": "Retail Council of Canada",
        "base_url": "https://www.retailcouncil.org",
        "start_paths": [
            "/resources/",
        ],
        "topics": ["canada", "retail", "operations", "policy", "trends"],
    },
    "cfib": {
        "name": "Canadian Federation of Independent Business",
        "base_url": "https://www.cfib-fcei.ca",
        "start_paths": [
            "/en/research/",
            "/en/tools-resources/",
        ],
        "topics": ["canada", "small-business", "policy", "tax", "operations"],
    },
    "statscan_daily": {
        "name": "Statistics Canada Daily",
        "base_url": "https://www150.statcan.gc.ca",
        "start_paths": [
            "/n1/en/type/analysis",
        ],
        "topics": ["canada", "statistics", "economics", "labor", "business"],
    },

    # ═══════════════════════════════════════════════════════════
    # CANADA — FINANCIAL & INDUSTRY (EXPANDED)
    # ═══════════════════════════════════════════════════════════
    "bank_of_canada": {
        "name": "Bank of Canada",
        "base_url": "https://www.bankofcanada.ca",
        "start_paths": [
            "/publications/",
            "/rates/",
            "/2025/",
        ],
        "topics": ["canada", "economics", "interest-rates", "inflation", "monetary-policy"],
    },
    "conference_board_canada": {
        "name": "Conference Board of Canada",
        "base_url": "https://www.conferenceboard.ca",
        "start_paths": [
            "/topics/",
            "/research/",
        ],
        "topics": ["canada", "economics", "business", "forecast", "policy"],
    },
    "statscan_food_services": {
        "name": "Statistics Canada — Food Services",
        "base_url": "https://www150.statcan.gc.ca",
        "start_paths": [
            "/t1/tbl1/en/tv.action?pid=2110001901",
            "/t1/tbl1/en/tv.action?pid=2010000801",
            "/n1/pub/11-627-m/index-eng.htm",
        ],
        "topics": ["canada", "food-service", "retail", "statistics", "restaurant"],
    },
    "canada_revenue_agency": {
        "name": "CRA Small Business Resources",
        "base_url": "https://www.canada.ca",
        "start_paths": [
            "/en/revenue-agency/services/tax/businesses/small-businesses-self-employed-income.html",
            "/en/services/business/research.html",
        ],
        "topics": ["canada", "tax", "small-business", "compliance", "gst-hst"],
    },
    "canadian_brewers": {
        "name": "Beer Canada",
        "base_url": "https://www.beercanada.com",
        "start_paths": [
            "/resources/",
            "/policy/",
        ],
        "topics": ["canada", "brewery", "craft-beer", "industry", "regulation"],
    },
    "cannabis_council_canada": {
        "name": "Cannabis Council of Canada",
        "base_url": "https://www.cannabis-council.ca",
        "start_paths": [
            "/resources/",
            "/policy/",
        ],
        "topics": ["canada", "cannabis", "regulation", "policy", "retail"],
    },
    "ocs_cannabis": {
        "name": "Ontario Cannabis Store (Market Data)",
        "base_url": "https://ocs.ca",
        "start_paths": [
            "/pages/cannabis-market-data",
        ],
        "topics": ["canada", "cannabis", "ontario", "market-data", "retail"],
    },
    "canadian_franchise_assoc": {
        "name": "Canadian Franchise Association",
        "base_url": "https://www.cfa.ca",
        "start_paths": [
            "/resources/",
        ],
        "topics": ["canada", "franchise", "restaurant", "retail", "operations"],
    },
    "financial_post": {
        "name": "Financial Post (Postmedia)",
        "base_url": "https://financialpost.com",
        "start_paths": [
            "/category/fp-finance/",
            "/category/news/economy/",
            "/category/entrepreneur/",
        ],
        "topics": ["canada", "finance", "economy", "business", "entrepreneurship"],
    },
    "globe_business": {
        "name": "Globe and Mail Business",
        "base_url": "https://www.theglobeandmail.com",
        "start_paths": [
            "/business/small-business/",
            "/business/industry-news/",
        ],
        "topics": ["canada", "business", "small-business", "economy", "finance"],
    },
    "moneysense_ca": {
        "name": "MoneySense Canada",
        "base_url": "https://www.moneysense.ca",
        "start_paths": [
            "/save/",
            "/spend/",
            "/invest/",
        ],
        "topics": ["canada", "personal-finance", "investing", "tax", "money"],
    },
    "futurpreneur": {
        "name": "Futurpreneur Canada",
        "base_url": "https://www.futurpreneur.ca",
        "start_paths": [
            "/resources/",
            "/blog/",
        ],
        "topics": ["canada", "entrepreneurship", "startup", "youth", "finance"],
    },

    # ═══════════════════════════════════════════════════════════
    # FINANCIAL BOOKS & DEEP KNOWLEDGE
    # (Public summaries, author blogs, key excerpts — NOT pirated books)
    # ═══════════════════════════════════════════════════════════
    "blinkist_free": {
        "name": "Blinkist Magazine",
        "base_url": "https://www.blinkist.com",
        "start_paths": [
            "/magazine/",
        ],
        "topics": ["book-summaries", "finance", "business", "leadership"],
    },
    "investopedia": {
        "name": "Investopedia",
        "base_url": "https://www.investopedia.com",
        "start_paths": [
            "/terms/",
            "/articles/investing/",
            "/articles/personal-finance/",
            "/financial-ratios-4689817",
        ],
        "topics": ["finance", "investing", "ratios", "accounting", "education"],
    },
    "accounting_tools": {
        "name": "AccountingTools",
        "base_url": "https://www.accountingtools.com",
        "start_paths": [
            "/articles/",
        ],
        "topics": ["accounting", "finance", "ratios", "bookkeeping", "standards"],
    },
    "corporate_finance_inst": {
        "name": "CFI (Corporate Finance Institute)",
        "base_url": "https://corporatefinanceinstitute.com",
        "start_paths": [
            "/resources/knowledge/finance/",
            "/resources/knowledge/accounting/",
            "/resources/knowledge/valuation/",
        ],
        "topics": ["finance", "valuation", "accounting", "ratios", "modeling"],
    },
    "wallstreetprep": {
        "name": "Wall Street Prep Blog",
        "base_url": "https://www.wallstreetprep.com",
        "start_paths": [
            "/knowledge/",
        ],
        "topics": ["finance", "valuation", "accounting", "modeling", "investing"],
    },
    "score_org": {
        "name": "SCORE Small Business Resources",
        "base_url": "https://www.score.org",
        "start_paths": [
            "/resource-library/",
            "/blog/",
        ],
        "topics": ["small-business", "finance", "operations", "marketing", "startup"],
    },
    "sba_gov": {
        "name": "US Small Business Administration",
        "base_url": "https://www.sba.gov",
        "start_paths": [
            "/business-guide/",
            "/funding-programs/",
        ],
        "topics": ["small-business", "finance", "lending", "policy", "startup"],
    },
    "nra_research": {
        "name": "National Restaurant Association Research",
        "base_url": "https://restaurant.org",
        "start_paths": [
            "/research-and-media/research/",
            "/education-and-resources/",
        ],
        "topics": ["restaurant", "food-service", "benchmarks", "labor", "trends"],
    },
    "nrf_research": {
        "name": "National Retail Federation Research",
        "base_url": "https://nrf.com",
        "start_paths": [
            "/research/",
            "/blog/",
        ],
        "topics": ["retail", "e-commerce", "benchmarks", "inventory", "trends"],
    },
    "franchise_times": {
        "name": "Franchise Times",
        "base_url": "https://www.franchisetimes.com",
        "start_paths": [
            "/",
        ],
        "topics": ["franchise", "restaurant", "retail", "finance", "growth"],
    },

    # ═══════════════════════════════════════════════════════════
    # AI & TECHNOLOGY
    # ═══════════════════════════════════════════════════════════
    "openai_blog": {
        "name": "OpenAI Blog",
        "base_url": "https://openai.com",
        "start_paths": [
            "/blog/",
        ],
        "topics": ["ai", "ml", "technology", "research"],
    },
    "anthropic_blog": {
        "name": "Anthropic Blog",
        "base_url": "https://www.anthropic.com",
        "start_paths": [
            "/news/",
            "/research/",
        ],
        "topics": ["ai", "safety", "research", "ml"],
    },
    "google_ai_blog": {
        "name": "Google AI Blog",
        "base_url": "https://blog.google",
        "start_paths": [
            "/technology/ai/",
        ],
        "topics": ["ai", "ml", "technology", "research"],
    },
    "mit_tech_review": {
        "name": "MIT Technology Review",
        "base_url": "https://www.technologyreview.com",
        "start_paths": [
            "/topic/artificial-intelligence/",
            "/topic/business/",
        ],
        "topics": ["ai", "technology", "business", "innovation"],
    },

    # ═══════════════════════════════════════════════════════════
    # ADDITIONAL FINANCIAL EXPERTS & THOUGHT LEADERS
    # ═══════════════════════════════════════════════════════════
    "damodaran": {
        "name": "Aswath Damodaran (NYU Stern)",
        "base_url": "https://aswathdamodaran.blogspot.com",
        "start_paths": [
            "/",
        ],
        "topics": ["valuation", "corporate-finance", "investing", "risk"],
    },
    "ycharts_blog": {
        "name": "YCharts Blog",
        "base_url": "https://ycharts.com",
        "start_paths": [
            "/resources/blog/",
        ],
        "topics": ["finance", "investing", "data", "analysis"],
    },
    "visible_alpha": {
        "name": "Visible Alpha Blog",
        "base_url": "https://visiblealpha.com",
        "start_paths": [
            "/blog/",
        ],
        "topics": ["finance", "analysis", "forecasting", "earnings"],
    },
    "pragcap": {
        "name": "Pragmatic Capitalism (Cullen Roche)",
        "base_url": "https://www.pragcap.com",
        "start_paths": [
            "/",
        ],
        "topics": ["macro", "investing", "finance", "economics"],
    },
    "abnormal_returns": {
        "name": "Abnormal Returns",
        "base_url": "https://abnormalreturns.com",
        "start_paths": [
            "/",
        ],
        "topics": ["investing", "finance", "markets", "economics"],
    },
    "collaborative_fund": {
        "name": "Collaborative Fund Blog (Morgan Housel)",
        "base_url": "https://collabfund.com",
        "start_paths": [
            "/blog/",
        ],
        "topics": ["investing", "psychology", "finance", "business"],
    },
    "stratechery": {
        "name": "Stratechery (Ben Thompson)",
        "base_url": "https://stratechery.com",
        "start_paths": [
            "/",
        ],
        "topics": ["strategy", "technology", "business-models", "platforms"],
    },

    # ═══════════════════════════════════════════════════════════
    # OPERATIONS & PRODUCTIVITY
    # ═══════════════════════════════════════════════════════════
    "process_street": {
        "name": "Process Street",
        "base_url": "https://www.process.st",
        "start_paths": [
            "/blog/",
        ],
        "topics": ["operations", "processes", "automation", "productivity"],
    },
    "lean_enterprise": {
        "name": "Lean Enterprise Institute",
        "base_url": "https://www.lean.org",
        "start_paths": [
            "/the-lean-post/",
        ],
        "topics": ["lean", "operations", "manufacturing", "efficiency"],
    },
    "asq_quality": {
        "name": "ASQ Quality Resources",
        "base_url": "https://asq.org",
        "start_paths": [
            "/quality-resources/",
        ],
        "topics": ["quality", "operations", "six-sigma", "continuous-improvement"],
    },
}
