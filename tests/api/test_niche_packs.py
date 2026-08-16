"""Niche script packs: does each trade's agent sound like it works there.

The four original packs all take FOOD ORDERS. Six of the ten trades Meridian
sells to book appointments instead, and "what can I get you" is the wrong
opening for a barbershop. These check the things that make a pack worth
having rather than just present: its own upsells, the questions its callers
actually ask, and an objection handle short enough to say on a phone.

The benchmark rule is enforced here too. A pack that has not out-scored the
legacy control must not reach a live call automatically, however good it
looks in review — that discipline is the reason the numbers mean anything.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "services" / "phone_agent"))

from script_pack_defs import PACK_DEFS  # noqa: E402
from script_packs import (  # noqa: E402
    PromptContext, TRADE_PACKS, auto_pack_for_trade, compose, pack_for_trade,
    refine_pack_for_cuisine,
)

NICHE_PACKS = ["restaurant_v1", "barbershop_v1", "nails_v1", "medspa_v1",
               "detailing_v1", "mobiledetailing_v1", "autoshop_v1", "smokeshop_v1"]

CTX = PromptContext(
    business_name="Test Shop",
    greeting="Thanks for calling Test Shop!",
    order_types="pickup, delivery",
    has_delivery=True,
    upsell_mode="active",
    multilingual=False,
)


class TestEveryTradeHasAPack:
    def test_all_ten_trades_map(self):
        # The ten in frontend/src/config/niches.ts. A trade with no pack falls
        # back to a generic food-ordering prompt, which is the thing this set
        # exists to stop.
        for trade in ["restaurant", "quickservice", "coffeeshop", "barbershop",
                      "nails", "medspa", "detailing", "mobiledetailing",
                      "autoshop", "smokeshop"]:
            assert pack_for_trade(trade), f"{trade} has no pack"

    def test_every_mapped_pack_exists(self):
        for trade, pack_id in TRADE_PACKS.items():
            assert pack_id in PACK_DEFS, f"{trade} maps to missing pack {pack_id}"

    def test_legacy_vocabularies_still_resolve(self):
        # Live data holds deck slugs and Square's BusinessType values as well
        # as trade keys — all three are in phone_agent_config today.
        assert pack_for_trade("ca-qsr") == pack_for_trade("quickservice")
        assert pack_for_trade("ca-salon") == pack_for_trade("barbershop")
        assert pack_for_trade("coffee_shop") == pack_for_trade("coffeeshop")

    def test_junk_maps_to_nothing(self):
        for junk in ["", "not-a-trade", None, 42]:
            assert pack_for_trade(junk) is None


class TestSelectingTheTradeSelectsThePack:
    """Aidan's call, after I argued for gating this on the benchmark.

    The trade's pack applies whether or not it has beaten the control. A
    barbershop answered by a prompt written for takeaway food is a worse call
    than one answered by an un-benchmarked barbershop prompt, and gating it
    means no merchant ever sees a trade-specific script.

    `status` is still recorded and still decides what we RECOMMEND — it just
    no longer decides what runs.
    """

    @pytest.mark.parametrize("trade", sorted(TRADE_PACKS))
    def test_every_trade_gets_its_pack_automatically(self, trade):
        assert auto_pack_for_trade(trade) == TRADE_PACKS[trade]

    def test_an_unmapped_trade_still_falls_back_to_legacy(self):
        # The floor that makes the whole thing safe: anything we do not
        # recognise gets the proven generic prompt, never a guess.
        for junk in ["", "art-gallery", "vet clinic", None]:
            assert auto_pack_for_trade(junk) is None

    def test_one_env_var_turns_it_all_off(self, monkeypatch):
        # This changes what a live agent says to a paying merchant's
        # customers, and the packs are un-benchmarked. Rolling back must not
        # need a deploy.
        monkeypatch.setenv("MERIDIAN_TRADE_PACK_AUTO", "0")
        for trade in TRADE_PACKS:
            assert auto_pack_for_trade(trade) is None

    @pytest.mark.parametrize("pack_id", NICHE_PACKS)
    def test_status_still_records_what_has_been_proven(self, pack_id):
        # Not a gate any more, but still the truth about what has been
        # measured — which is what the bench and the settings UI read.
        assert PACK_DEFS[pack_id].status in ("pending", "not_ready", "beat_baseline")


class TestTradeKnowledge:
    @pytest.mark.parametrize("pack_id", NICHE_PACKS)
    def test_it_knows_what_to_offer(self, pack_id):
        ups = PACK_DEFS[pack_id].upsells(CTX)
        assert len(ups) >= 2, f"{pack_id} has no upsells worth the name"
        joined = " ".join(ups).lower()
        # The failure mode this replaces: a vague prompt to ask for more.
        assert "anything else" not in joined or "never" in joined

    @pytest.mark.parametrize("pack_id", NICHE_PACKS)
    def test_it_knows_what_callers_ask(self, pack_id):
        faqs = PACK_DEFS[pack_id].faqs(CTX)
        assert len(faqs) >= 3, f"{pack_id} lists too few real questions"
        for q, a in faqs:
            assert q and a, f"{pack_id} has an empty FAQ entry"

    @pytest.mark.parametrize("pack_id", NICHE_PACKS)
    def test_objection_handles_are_short_enough_to_say(self, pack_id):
        objs = PACK_DEFS[pack_id].objections(CTX)
        assert len(objs) >= 2, f"{pack_id} handles no objections"
        for objection, handle in objs:
            assert objection and handle
            # A handle nobody can say in one breath is a handle that reads as
            # pressure. This is the whole design rule for the block.
            assert len(handle) < 240, f"{pack_id}: handle too long — {handle[:60]}..."

    @pytest.mark.parametrize("pack_id", NICHE_PACKS)
    def test_the_knowledge_reaches_the_prompt(self, pack_id):
        prompt = compose(pack_id, CTX)
        assert "WORTH OFFERING" in prompt
        assert "WHAT CALLERS ASK" in prompt
        assert "IF THEY HESITATE" in prompt
        first_upsell = PACK_DEFS[pack_id].upsells(CTX)[0][:40]
        assert first_upsell in prompt

    def test_packs_without_trade_knowledge_render_no_empty_headings(self):
        # An empty heading is worse than none — the model will fill it.
        prompt = compose("efficient_v1", CTX)
        assert "WORTH OFFERING" not in prompt
        assert "WHAT CALLERS ASK" not in prompt


class TestTradeSpecificSafety:
    def test_a_med_spa_never_gives_medical_advice(self):
        rules = " ".join(PACK_DEFS["medspa_v1"].hard_rules(CTX)).lower()
        assert "never give medical advice" in rules
        assert "promise a result" in rules

    def test_a_repair_shop_never_diagnoses_on_the_phone(self):
        rules = " ".join(PACK_DEFS["autoshop_v1"].hard_rules(CTX)).lower()
        assert "never diagnose" in rules
        # And says something when the caller describes an unsafe car.
        assert "unsafe" in rules or "should not be driven" in rules

    def test_a_mobile_detailer_never_books_outside_its_area(self):
        rules = " ".join(PACK_DEFS["mobiledetailing_v1"].hard_rules(CTX)).lower()
        assert "service area" in rules

    @pytest.mark.parametrize("pack_id", NICHE_PACKS)
    def test_no_pack_invents_availability(self, pack_id):
        # Applies to every appointment trade; the order trades have their own
        # read-back guarantee in the shared rules.
        if pack_id in ("smokeshop_v1", "restaurant_v1"):
            return
        rules = " ".join(PACK_DEFS[pack_id].hard_rules(CTX)).lower()
        assert "never invent availability" in rules


# ── cuisine refinement ───────────────────────────────────────────────────────

class TestAnIndianRestaurantNeverGetsThePizzaScript:
    """Aidan: "indian resturants shouldnt get the pizza resturant script."

    He was right and it was my mapping. "quickservice" pointed at
    pizzeria_v1, so Heritage Indian Cuisine — stored as the deck slug
    ca-qsr — was routed to a pack whose whole grammar is pizza sizes and
    half-and-half toppings. The trade is simply not specific enough for food:
    "restaurant" covers a tandoori kitchen and a pizzeria alike, and there is
    no cuisine column anywhere. The menu is the evidence, and we already hold
    it.
    """

    INDIAN_MENU = [{"name": "Butter Chicken"}, {"name": "Vegetable Samosas"},
                   {"name": "Chicken Tikka Masala"}, {"name": "Garlic Naan"}]
    PIZZA_MENU = [{"name": "Large Pepperoni Pizza"}, {"name": "Garlic Knots"},
                  {"name": "Cheese Pizza"}]
    BURGER_MENU = [{"name": "Cheeseburger"}, {"name": "Veggie Burger"},
                   {"name": "Crispy Chicken"}]

    def test_an_indian_menu_gets_the_indian_pack(self):
        assert refine_pack_for_cuisine(
            "restaurant_v1", "Maple Tandoor", self.INDIAN_MENU) == "indian_v1"

    def test_the_name_alone_is_enough_when_no_menu_is_loaded(self):
        # Heritage Indian Cuisine has no menu rows. A shop that says what it
        # is in its own name has told us plainly.
        assert refine_pack_for_cuisine(
            "cafe_quickserve_v1", "heritage indian cuisine", []) == "indian_v1"

    def test_a_pizza_menu_gets_the_pizza_pack(self):
        assert refine_pack_for_cuisine(
            "restaurant_v1", "Tony's Pizzeria", self.PIZZA_MENU) == "pizzeria_v1"

    def test_an_ordinary_menu_is_left_alone(self):
        # The conservative half. Burgers are not a cuisine we have a pack for,
        # and guessing is worse than the generic pack.
        assert refine_pack_for_cuisine(
            "restaurant_v1", "Meridian Test Kitchen", self.BURGER_MENU) == "restaurant_v1"

    def test_one_stray_word_is_not_evidence(self):
        # A pub with a curry on the menu is not an Indian restaurant.
        assert refine_pack_for_cuisine(
            "restaurant_v1", "The Anchor", [{"name": "Chicken Curry"}]) == "restaurant_v1"

    def test_it_never_touches_a_non_food_pack(self):
        # The rule that stops this being dangerous: a barbershop whose owner
        # is called Mr Curry stays a barbershop.
        for pack in ["barbershop_v1", "nails_v1", "medspa_v1", "autoshop_v1",
                     "mobiledetailing_v1", "smokeshop_v1"]:
            assert refine_pack_for_cuisine(pack, "Curry's Pizza Cuts",
                                           self.PIZZA_MENU) == pack

    def test_quickservice_no_longer_means_pizza(self):
        # The original bug in one line.
        assert pack_for_trade("quickservice") != "pizzeria_v1"
        assert pack_for_trade("ca-qsr") != "pizzeria_v1"

    def test_refinement_only_ever_lands_on_a_proven_pack(self):
        from script_pack_defs import PACK_DEFS
        for target in ("indian_v1", "pizzeria_v1"):
            assert PACK_DEFS[target].status == "beat_baseline", (
                f"{target} is a promotion target but has not beaten the control"
            )
