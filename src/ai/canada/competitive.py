"""
Canadian Competitive Landscape Data — Major chains by vertical and province.

Sources:
  - Financial Post Top 100 Restaurants 2024
  - Restaurants Canada (CRFA) Foodservice Facts 2024
  - Restaurant Brands International 2024 10-K (Tim Hortons)
  - Recipe Unlimited Corp 2024 Annual Report
  - Loblaw Companies 2024 Annual Report
  - Empire Company (Sobeys) 2024 Annual Report
"""

COMPETITIVE_LANDSCAPE: dict[str, dict[str, list[dict]]] = {
    "coffee_shop": {
        "national": [
            {"name": "Tim Hortons", "locations": 4_000, "avg_ticket_cents": 520,
             "market_share_pct": 52.0, "source": "Restaurant Brands Intl 2024 10-K"},
            {"name": "Starbucks", "locations": 1_900, "avg_ticket_cents": 680,
             "market_share_pct": 22.0, "source": "Starbucks Intl filings 2024"},
            {"name": "McDonald's McCafe", "locations": 1_450, "avg_ticket_cents": 450,
             "market_share_pct": 10.0, "source": "McDonald's Corp 2024 10-K"},
            {"name": "Second Cup", "locations": 200, "avg_ticket_cents": 620,
             "market_share_pct": 2.5, "source": "Aegis Brands filings"},
        ],
        "ON": [{"name": "Balzac's", "locations": 15, "notes": "Toronto premium"}],
        "BC": [
            {"name": "Blenz Coffee", "locations": 50, "notes": "Vancouver/BC chain"},
            {"name": "JJ Bean", "locations": 25, "notes": "Vancouver specialty"},
        ],
        "QC": [{"name": "Van Houtte", "locations": 45, "notes": "Quebec heritage brand"}],
    },
    "restaurant": {
        "national": [
            {"name": "Boston Pizza", "locations": 370, "avg_ticket_cents": 2600,
             "source": "Boston Pizza Intl 2024"},
            {"name": "Keg Steakhouse", "locations": 106, "avg_ticket_cents": 5500,
             "source": "Keg Restaurants Ltd"},
            {"name": "Earls", "locations": 70, "avg_ticket_cents": 3800,
             "source": "Earls Restaurant Group"},
            {"name": "Moxies", "locations": 60, "avg_ticket_cents": 3500,
             "source": "Northland Properties"},
            {"name": "Swiss Chalet", "locations": 180, "avg_ticket_cents": 2200,
             "source": "Recipe Unlimited Corp 2024"},
        ],
    },
    "quick_service": {
        "national": [
            {"name": "Tim Hortons", "locations": 4_000, "avg_ticket_cents": 750,
             "source": "Restaurant Brands Intl 2024 10-K"},
            {"name": "A&W Canada", "locations": 1_000, "avg_ticket_cents": 1100,
             "source": "A&W Revenue Royalties 2024"},
            {"name": "Harvey's", "locations": 260, "avg_ticket_cents": 1000,
             "source": "Recipe Unlimited Corp 2024"},
            {"name": "Mary Brown's", "locations": 230, "avg_ticket_cents": 1200,
             "source": "Mary Brown's Chicken & Taters"},
        ],
    },
    "bar": {
        "national": [
            {"name": "Shark Club", "locations": 8, "notes": "Sports bar chain"},
            {"name": "The Keg (bar service)", "locations": 106,
             "notes": "Significant bar revenue alongside dining"},
        ],
    },
    "grocery": {
        "national": [
            {"name": "Loblaw/No Frills", "locations": 2_400,
             "source": "Loblaw Companies 2024 AR"},
            {"name": "Sobeys/FreshCo", "locations": 1_500,
             "source": "Empire Company 2024 AR"},
            {"name": "Metro", "locations": 950, "source": "Metro Inc 2024 AR"},
        ],
        "AB": [{"name": "Co-op", "locations": 200, "notes": "Federated Co-op strong in AB/SK"}],
    },
}
