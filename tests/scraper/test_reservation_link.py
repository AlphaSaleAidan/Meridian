"""Reservation-link extraction — the phone agent hands callers to the
restaurant's EXISTING rez system, so the scraper must find that link."""
import importlib.util
from pathlib import Path

_p = Path(__file__).resolve().parents[2] / "src" / "services" / "website_scraper.py"
_spec = importlib.util.spec_from_file_location("website_scraper_mod", _p)
ws = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ws)  # module-level code has no package-relative imports


def test_known_platform_absolute_url():
    html = '<nav><a href="https://www.opentable.com/r/tonys-pizza-toronto">Reservations</a></nav>'
    assert ws.extract_reservation_link(html) == {
        "url": "https://www.opentable.com/r/tonys-pizza-toronto", "platform": "opentable"}


def test_platform_beats_generic_anchor():
    html = ('<a href="/book-now">Book Now</a>'
            '<a href="https://resy.com/cities/tor/tonys">Reserve on Resy</a>')
    assert ws.extract_reservation_link(html, "https://tonys.ca")["platform"] == "resy"


def test_generic_book_a_table_resolved_against_base():
    html = '<a class="btn" href="/reservations"><span>Book a Table</span></a>'
    res = ws.extract_reservation_link(html, "https://tonys.ca/home")
    assert res == {"url": "https://tonys.ca/reservations", "platform": "website"}


def test_ignores_tel_mailto_and_plain_links():
    html = ('<a href="tel:+15551234567">Call to reserve</a>'
            '<a href="mailto:hi@x.com">Email</a><a href="/menu">Menu</a>')
    assert ws.extract_reservation_link(html, "https://x.com") == {}


def test_canadian_platform_libro():
    html = '<a href="https://widget.libroreserve.com/rest/XYZ">R&eacute;server</a>'
    assert ws.extract_reservation_link(html)["platform"] == "libro"
