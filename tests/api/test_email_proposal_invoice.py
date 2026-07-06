"""proposal_sent + invoice_sent — templates the rep portal has posted since
launch but which never existed server-side (every send 400'd "Unknown template").

Covers: template rendering (setup fee / due today / CTA link presence) and
fn_map wiring in the /api/email/send route.
"""
import pytest

from src.email.templates import proposal_sent, invoice_sent


class TestProposalSentTemplate:
    def test_renders_all_fee_rows(self):
        html = proposal_sent.render(
            business_name="Maple & Main Cafe",
            first_name="Aidan",
            rep_name="Rep One",
            rep_email="rep@meridian.tips",
            plan_name="Standard",
            monthly_price="CA$500",
            setup_fee="CA$500",
            due_today="CA$1,000",
            proposal_url="https://meridian-decks.vercel.app/cafe/?setup=500",
        )
        assert "Maple &amp; Main Cafe" in html or "Maple & Main Cafe" in html
        assert "Hi Aidan," in html
        assert "CA$500" in html
        assert "Setup Fee (one-time)" in html
        assert "Due today" in html
        assert "CA$1,000" in html
        assert "https://meridian-decks.vercel.app/cafe/?setup=500" in html
        assert "View Your Proposal" in html

    def test_omits_empty_rows_and_cta(self):
        html = proposal_sent.render(business_name="Biz")
        assert "Setup Fee" not in html
        assert "Due today" not in html
        assert "View Your Proposal" not in html
        assert "Hello," in html

    def test_rep_contact_line(self):
        html = proposal_sent.render(
            business_name="Biz", rep_name="Rep One", rep_email="rep@meridian.tips",
        )
        assert "Rep One (rep@meridian.tips)" in html


class TestInvoiceSentTemplate:
    def test_renders_invoice_details(self):
        html = invoice_sent.render(
            business_name="Maple & Main Cafe",
            first_name="Aidan",
            invoice_number="INV-2026-001",
            amount="CA$500",
            invoice_url="https://meridian.tips/invoice/INV-2026-001",
            recurring=True,
        )
        assert "INV-2026-001" in html
        assert "CA$500 / month" in html
        assert "Recurring monthly" in html
        assert "https://meridian.tips/invoice/INV-2026-001" in html
        assert "Pay Invoice" in html

    def test_one_time_invoice_has_no_recurring_copy(self):
        html = invoice_sent.render(
            business_name="Biz", invoice_number="INV-1", amount="CA$500",
        )
        assert "/ month" not in html
        assert "Recurring" not in html


class TestFnMapWiring:
    """Both templates must be reachable through POST /api/email/send."""

    def test_send_functions_exist(self):
        from src.email import send as email_send
        assert callable(email_send.send_proposal_sent)
        assert callable(email_send.send_invoice_sent)

    @pytest.mark.asyncio
    async def test_route_dispatches_proposal_sent(self, monkeypatch):
        from src.api.routes import email as email_route

        calls = {}

        async def fake_proposal(**kw):
            calls.update(kw)
            return {"ok": True}

        from src.email import send as email_send
        monkeypatch.setattr(email_send, "send_proposal_sent", fake_proposal)

        req = email_route.SendEmailRequest(
            template="proposal_sent",
            to="owner@example.com",
            first_name="Aidan",
            portal="canada",
            extra={
                "business_name": "Maple & Main Cafe",
                "setup_fee": "CA$500",
                "due_today": "CA$1,000",
                "proposal_url": "https://meridian-decks.vercel.app/cafe/",
            },
        )
        result = await email_route.send_email(req, principal={"role": "service"})
        assert result == {"ok": True}
        assert calls["setup_fee"] == "CA$500"
        assert calls["due_today"] == "CA$1,000"
        assert calls["proposal_url"] == "https://meridian-decks.vercel.app/cafe/"

    @pytest.mark.asyncio
    async def test_route_dispatches_invoice_sent(self, monkeypatch):
        from src.api.routes import email as email_route

        calls = {}

        async def fake_invoice(**kw):
            calls.update(kw)
            return {"ok": True}

        from src.email import send as email_send
        monkeypatch.setattr(email_send, "send_invoice_sent", fake_invoice)

        req = email_route.SendEmailRequest(
            template="invoice_sent",
            to="owner@example.com",
            portal="canada",
            extra={
                "business_name": "Maple & Main Cafe",
                "invoice_number": "INV-1",
                "amount": "CA$500",
                "recurring": True,
            },
        )
        result = await email_route.send_email(req, principal={"role": "service"})
        assert result == {"ok": True}
        assert calls["invoice_number"] == "INV-1"
        assert calls["recurring"] is True
