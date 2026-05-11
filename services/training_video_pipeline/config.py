"""
Training video pipeline configuration.
All 38 lessons across 9 modules with target durations.
"""

TRAINING_CURRICULUM = {
    "module_1": {
        "name": "New Rep Onboarding",
        "lessons": [
            {"id": "1.1", "title": "Welcome to Meridian Sales", "duration_target": 180},
            {"id": "1.2", "title": "Understanding the Product", "duration_target": 240},
            {"id": "1.3", "title": "Pricing & Plans Overview", "duration_target": 180},
            {"id": "1.4", "title": "Setting Up Your Pipeline", "duration_target": 180},
            {"id": "1.5", "title": "First Week Checklist", "duration_target": 180},
        ],
    },
    "module_2": {
        "name": "Perfecting Your Pitch",
        "lessons": [
            {"id": "2.1", "title": "The 60-Second Elevator Pitch", "duration_target": 180},
            {"id": "2.2", "title": "Pain Points by Vertical", "duration_target": 240},
            {"id": "2.3", "title": "Handling Price Objections", "duration_target": 240},
            {"id": "2.4", "title": "Competitive Positioning", "duration_target": 180},
        ],
    },
    "module_3": {
        "name": "Running a Great Demo",
        "lessons": [
            {"id": "3.1", "title": "Demo Environment Setup", "duration_target": 150},
            {"id": "3.2", "title": "The Discovery Call Framework", "duration_target": 180},
            {"id": "3.3", "title": "Feature Walkthrough Script", "duration_target": 300},
            {"id": "3.4", "title": "Closing After the Demo", "duration_target": 180},
        ],
    },
    "module_4": {
        "name": "Selling by Vertical",
        "lessons": [
            {"id": "4.1", "title": "Restaurants & Cafes", "duration_target": 240},
            {"id": "4.2", "title": "Smoke Shops & Vape", "duration_target": 180},
            {"id": "4.3", "title": "Salons & Spas", "duration_target": 180},
            {"id": "4.4", "title": "Retail & Boutiques", "duration_target": 180},
            {"id": "4.5", "title": "Food Trucks & QSR", "duration_target": 180},
        ],
    },
    "module_5": {
        "name": "Advanced Closing Techniques",
        "lessons": [
            {"id": "5.1", "title": "Creating Urgency Without Pressure", "duration_target": 180},
            {"id": "5.2", "title": "Multi-Location Upsell", "duration_target": 180},
            {"id": "5.3", "title": "Referral Programs", "duration_target": 180},
            {"id": "5.4", "title": "Commission Optimization", "duration_target": 180},
        ],
    },
    "module_6": {
        "name": "Compliance & Ethics",
        "lessons": [
            {"id": "6.1", "title": "Sales Ethics Policy", "duration_target": 180},
            {"id": "6.2", "title": "Data Privacy & Security", "duration_target": 180},
            {"id": "6.3", "title": "Accurate Representations", "duration_target": 150},
        ],
    },
    "module_7": {
        "name": "Camera Intelligence Setup",
        "lessons": [
            {"id": "7.1", "title": "What is Camera Intelligence?", "duration_target": 180},
            {"id": "7.2", "title": "Hardware Requirements & Placement", "duration_target": 240},
            {"id": "7.3", "title": "PIPEDA Compliance & Privacy Signage", "duration_target": 180},
            {"id": "7.4", "title": "Configuring Zones & Alerts", "duration_target": 180},
            {"id": "7.5", "title": "Selling the ROI to Prospects", "duration_target": 180},
        ],
    },
    "module_8": {
        "name": "Quick Tips",
        "lessons": [
            {"id": "8.1", "title": "Pricing in CAD — Handling Currency Questions", "duration_target": 120},
            {"id": "8.2", "title": "Canadian Payment Processing Landscape", "duration_target": 150},
            {"id": "8.3", "title": "Provincial Tax Differences (GST/HST/PST)", "duration_target": 120},
            {"id": "8.4", "title": "Seasonal Sales Patterns in Canada", "duration_target": 120},
        ],
    },
    "module_9": {
        "name": "POS Connection Guides",
        "lessons": [
            {"id": "9.1", "title": "Moneris Integration Walkthrough", "duration_target": 180},
            {"id": "9.2", "title": "Square Canada Setup", "duration_target": 180},
            {"id": "9.3", "title": "Clover Canada Configuration", "duration_target": 180},
            {"id": "9.4", "title": "Troubleshooting POS Connections", "duration_target": 240},
        ],
    },
}


def get_all_lessons():
    """Yield (lesson_dict, module_name) for every lesson."""
    for module_data in TRAINING_CURRICULUM.values():
        for lesson in module_data["lessons"]:
            yield lesson, module_data["name"]


def get_module_lessons(module_number: int):
    """Yield lessons for a specific module number."""
    key = f"module_{module_number}"
    if key not in TRAINING_CURRICULUM:
        return
    module_data = TRAINING_CURRICULUM[key]
    for lesson in module_data["lessons"]:
        yield lesson, module_data["name"]


def get_lesson(lesson_id: str):
    """Find a single lesson by ID (e.g. '3.2')."""
    for module_data in TRAINING_CURRICULUM.values():
        for lesson in module_data["lessons"]:
            if lesson["id"] == lesson_id:
                return lesson, module_data["name"]
    return None, None
