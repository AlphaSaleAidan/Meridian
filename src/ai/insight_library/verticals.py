"""
Vertical taxonomy for the insight library.

Each vertical carries specialization attributes so an archetype instantiated for
it produces genuinely different reasoning (different staff role, sale unit, KPIs,
channels, and structural flags) — NOT a label swap. Structural flags gate which
archetypes even apply (e.g. no-show insights only fire for appointment-based
verticals), which is what keeps the generated catalog distinct rather than
variable-only.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Vertical:
    key: str
    name: str
    family: str
    staff_role: str          # the front-line worker noun
    sale_unit: str           # what one sale is called
    core_kpis: tuple[str, ...]   # vertical-specific KPIs (drive specialized archetypes)
    channels: tuple[str, ...]    # walk_in / phone / online / booking / drive_thru / delivery
    flags: frozenset[str] = field(default_factory=frozenset)
    # flags vocabulary: appointment_based, perishable, inventory_heavy, tipped,
    #   high_ticket, repeat_purchase, seasonal, regulated, table_service,
    #   membership, walk_in_heavy, delivery_capable


# Structural flags let one archetype apply to a precise subset of verticals.
F = frozenset

VERTICALS: tuple[Vertical, ...] = (
    # ── Food service ──
    Vertical("cafe", "Café / Coffee Shop", "food_service", "barista", "drink",
             ("avg_ticket", "morning_rush_share", "attach_rate"), ("walk_in", "phone", "online"),
             F({"perishable", "tipped", "repeat_purchase", "walk_in_heavy"})),
    Vertical("qsr", "Quick-Service Restaurant", "food_service", "line cook", "order",
             ("drive_thru_time", "throughput_per_hour", "combo_attach"), ("walk_in", "drive_thru", "delivery", "phone"),
             F({"perishable", "delivery_capable", "walk_in_heavy"})),
    Vertical("full_restaurant", "Full-Service Restaurant", "food_service", "server", "cover",
             ("table_turns", "avg_check", "labor_pct"), ("walk_in", "phone", "booking", "delivery"),
             F({"perishable", "tipped", "table_service", "delivery_capable"})),
    Vertical("bar", "Bar / Pub", "food_service", "bartender", "round",
             ("pour_cost", "covers_per_seat", "late_night_share"), ("walk_in", "phone"),
             F({"perishable", "tipped", "regulated", "table_service"})),
    Vertical("food_truck", "Food Truck", "food_service", "cook", "order",
             ("location_revenue", "prep_to_sale", "queue_length"), ("walk_in",),
             F({"perishable", "seasonal", "walk_in_heavy"})),
    Vertical("bakery", "Bakery", "food_service", "baker", "item",
             ("waste_pct", "morning_sellthrough", "preorder_share"), ("walk_in", "phone", "online"),
             F({"perishable", "repeat_purchase", "walk_in_heavy"})),
    Vertical("ghost_kitchen", "Ghost / Delivery Kitchen", "food_service", "cook", "order",
             ("delivery_pct", "platform_fee_share", "prep_time"), ("delivery", "online", "phone"),
             F({"perishable", "delivery_capable"})),
    # ── Personal care & wellness (appointment-led) ──
    Vertical("salon", "Hair Salon", "personal_care", "stylist", "appointment",
             ("rebook_rate", "chair_utilization", "retail_attach"), ("booking", "walk_in", "phone"),
             F({"appointment_based", "repeat_purchase", "tipped", "inventory_heavy"})),
    Vertical("barbershop", "Barbershop", "personal_care", "barber", "cut",
             ("walk_in_wait", "repeat_visit_days", "chair_utilization"), ("walk_in", "booking"),
             F({"appointment_based", "walk_in_heavy", "tipped", "repeat_purchase"})),
    Vertical("nail_salon", "Nail Salon", "personal_care", "technician", "service",
             ("rebook_rate", "service_mix", "addon_attach"), ("booking", "walk_in"),
             F({"appointment_based", "tipped", "inventory_heavy"})),
    Vertical("spa", "Day Spa", "personal_care", "therapist", "treatment",
             ("room_utilization", "package_share", "rebook_rate"), ("booking", "phone"),
             F({"appointment_based", "membership", "high_ticket"})),
    Vertical("med_spa", "Med Spa", "health_wellness", "provider", "treatment",
             ("consult_conversion", "package_share", "rebook_rate"), ("booking", "phone"),
             F({"appointment_based", "high_ticket", "regulated", "membership"})),
    Vertical("tattoo", "Tattoo Studio", "personal_care", "artist", "session",
             ("deposit_capture", "artist_booking_lead", "touch_up_rate"), ("booking", "walk_in"),
             F({"appointment_based", "high_ticket"})),
    # ── Health ──
    Vertical("dental", "Dental Practice", "health_wellness", "hygienist", "appointment",
             ("recall_rate", "chair_utilization", "treatment_acceptance"), ("booking", "phone"),
             F({"appointment_based", "regulated", "membership", "high_ticket"})),
    Vertical("chiro", "Chiropractic Clinic", "health_wellness", "practitioner", "visit",
             ("plan_adherence", "rebook_rate", "no_show_rate"), ("booking", "phone"),
             F({"appointment_based", "membership", "regulated"})),
    Vertical("physio", "Physiotherapy Clinic", "health_wellness", "therapist", "session",
             ("plan_completion", "rebook_rate", "referral_share"), ("booking", "phone"),
             F({"appointment_based", "regulated"})),
    Vertical("optometry", "Optometry", "health_wellness", "optometrist", "exam",
             ("frame_attach", "recall_rate", "exam_to_sale"), ("booking", "walk_in"),
             F({"appointment_based", "inventory_heavy", "high_ticket", "regulated"})),
    Vertical("vet", "Veterinary Clinic", "health_wellness", "vet tech", "visit",
             ("recall_rate", "plan_uptake", "no_show_rate"), ("booking", "phone"),
             F({"appointment_based", "regulated", "membership"})),
    # ── Fitness ──
    Vertical("gym", "Gym / Fitness Club", "fitness", "trainer", "membership",
             ("churn_rate", "class_fill", "freeze_rate"), ("membership", "booking", "walk_in"),
             F({"membership", "appointment_based"})),
    Vertical("yoga_studio", "Yoga / Pilates Studio", "fitness", "instructor", "class",
             ("class_fill", "pass_burn_rate", "rebook_rate"), ("booking", "membership"),
             F({"membership", "appointment_based"})),
    Vertical("crossfit", "CrossFit / Boutique Fitness", "fitness", "coach", "class",
             ("class_fill", "churn_rate", "ramp_conversion"), ("membership", "booking"),
             F({"membership", "appointment_based"})),
    # ── Retail ──
    Vertical("boutique", "Apparel Boutique", "retail", "associate", "transaction",
             ("units_per_txn", "fitting_room_conv", "markdown_pct"), ("walk_in", "online"),
             F({"inventory_heavy", "seasonal", "repeat_purchase"})),
    Vertical("convenience", "Convenience Store", "retail", "cashier", "basket",
             ("basket_size", "shrinkage_pct", "peak_share"), ("walk_in",),
             F({"inventory_heavy", "perishable", "walk_in_heavy"})),
    Vertical("grocery", "Grocery / Market", "retail", "clerk", "basket",
             ("basket_size", "perishable_waste", "loyalty_share"), ("walk_in", "delivery", "online"),
             F({"inventory_heavy", "perishable", "delivery_capable", "repeat_purchase"})),
    Vertical("liquor", "Liquor Store", "retail", "clerk", "transaction",
             ("basket_size", "premium_mix", "weekend_share"), ("walk_in", "delivery"),
             F({"inventory_heavy", "regulated", "repeat_purchase"})),
    Vertical("dispensary", "Cannabis Dispensary", "retail", "budtender", "transaction",
             ("basket_size", "category_mix", "loyalty_share"), ("walk_in", "online", "delivery"),
             F({"inventory_heavy", "regulated", "repeat_purchase", "perishable"})),
    Vertical("smoke_shop", "Smoke / Vape Shop", "retail", "clerk", "transaction",
             ("basket_size", "category_mix", "repeat_visit_days"), ("walk_in",),
             F({"inventory_heavy", "regulated", "repeat_purchase"})),
    Vertical("florist", "Florist", "retail", "designer", "order",
             ("preorder_share", "waste_pct", "occasion_mix"), ("walk_in", "phone", "online", "delivery"),
             F({"inventory_heavy", "perishable", "seasonal", "delivery_capable"})),
    Vertical("jewelry", "Jewelry Store", "retail", "consultant", "sale",
             ("close_rate", "avg_sale", "repair_attach"), ("walk_in", "booking"),
             F({"inventory_heavy", "high_ticket"})),
    Vertical("bookstore", "Bookstore / Gifts", "retail", "associate", "basket",
             ("basket_size", "event_lift", "online_share"), ("walk_in", "online"),
             F({"inventory_heavy", "seasonal"})),
    Vertical("pet_store", "Pet Store", "retail", "associate", "basket",
             ("subscription_share", "basket_size", "service_attach"), ("walk_in", "online", "delivery"),
             F({"inventory_heavy", "repeat_purchase", "membership"})),
    # ── Automotive & trades (job/bay based) ──
    Vertical("auto_repair", "Auto Repair Shop", "automotive", "technician", "repair order",
             ("bay_utilization", "approved_estimate_rate", "comeback_rate"), ("booking", "phone", "walk_in"),
             F({"appointment_based", "high_ticket", "inventory_heavy"})),
    Vertical("oil_change", "Quick Lube", "automotive", "technician", "service",
             ("cars_per_bay_hour", "upsell_attach", "wait_time"), ("walk_in",),
             F({"walk_in_heavy", "inventory_heavy"})),
    Vertical("car_wash", "Car Wash / Detail", "automotive", "attendant", "wash",
             ("membership_share", "throughput_per_hour", "weather_sensitivity"), ("walk_in", "membership"),
             F({"membership", "seasonal", "walk_in_heavy"})),
    Vertical("tire_shop", "Tire & Wheel Shop", "automotive", "technician", "job",
             ("seasonal_swing", "attach_alignment", "bay_utilization"), ("booking", "walk_in", "phone"),
             F({"seasonal", "inventory_heavy", "high_ticket"})),
    # ── Home & professional services (dispatch/job based) ──
    Vertical("hvac", "HVAC Services", "home_services", "technician", "job",
             ("first_visit_close", "membership_share", "seasonal_swing"), ("phone", "booking"),
             F({"appointment_based", "high_ticket", "seasonal", "membership"})),
    Vertical("plumbing", "Plumbing Services", "home_services", "plumber", "job",
             ("emergency_share", "first_visit_close", "callback_rate"), ("phone", "booking"),
             F({"appointment_based", "high_ticket"})),
    Vertical("cleaning", "Cleaning Service", "home_services", "cleaner", "job",
             ("recurring_share", "route_density", "churn_rate"), ("phone", "booking", "online"),
             F({"appointment_based", "membership", "repeat_purchase"})),
    Vertical("landscaping", "Landscaping / Lawn", "home_services", "crew lead", "job",
             ("recurring_share", "seasonal_swing", "route_density"), ("phone", "booking"),
             F({"appointment_based", "seasonal", "membership"})),
    # ── Hospitality / leisure ──
    Vertical("hotel_fb", "Hotel F&B / Boutique Stay", "hospitality", "attendant", "cover",
             ("occupancy_link", "rev_par", "package_share"), ("booking", "walk_in", "phone"),
             F({"perishable", "seasonal", "table_service"})),
    Vertical("event_venue", "Event Venue", "hospitality", "coordinator", "booking",
             ("booking_lead", "deposit_capture", "addon_attach"), ("phone", "booking"),
             F({"appointment_based", "high_ticket", "seasonal"})),
    Vertical("entertainment", "Entertainment / Arcade", "hospitality", "attendant", "ticket",
             ("party_share", "peak_share", "concession_attach"), ("walk_in", "booking", "online"),
             F({"seasonal", "walk_in_heavy"})),
)

VERTICALS_BY_KEY = {v.key: v for v in VERTICALS}
VERTICAL_FAMILIES = sorted({v.family for v in VERTICALS})


def verticals_with_flags(*required: str) -> list[Vertical]:
    """Verticals carrying ALL given structural flags — used by archetypes to
    target only the verticals where their reasoning genuinely applies."""
    req = set(required)
    return [v for v in VERTICALS if req.issubset(v.flags)]


def verticals_in_families(*families: str) -> list[Vertical]:
    fam = set(families)
    return [v for v in VERTICALS if v.family in fam]
