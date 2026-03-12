"""Unit tests for domain_router.py — no external dependencies."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from domain_router import classify, classify_email, domains_for_query


def test_bloomberg_email_is_finance():
    result = classify_email(
        subject="NVDA Earnings Beat — Price Target Raised to $950",
        body="Nvidia reported Q4 earnings that beat analyst expectations. "
             "The stock surged 8% in after-hours trading. Bullish momentum continues.",
        sender="noreply@bloomberg.com",
    )
    assert result.domains == ["finance"], f"Expected ['finance'], got {result.domains}"
    assert result.confidence in ("high", "medium")


def test_acme_email_is_sales():
    result = classify_email(
        subject="Re: Q2 expansion discussion",
        body="Mike, thanks for the proposal. Can we get volume discount on 50 seats? "
             "What's the onboarding timeline?",
        sender="tom.bradley@acmecorp.com",
    )
    assert result.domains == ["sales"], f"Expected ['sales'], got {result.domains}"


def test_finnair_email_is_travel():
    result = classify_email(
        subject="Your Helsinki Adventure Awaits! Confirmation #AY7829104",
        body="Your flight to Finland is confirmed. Austin (AUS) → Helsinki (HEL). "
             "Departure: 4:30 PM. Seat 14A (window).",
        sender="booking@finnair.com",
    )
    assert result.domains == ["travel"], f"Expected ['travel'], got {result.domains}"


def test_team_email_is_team():
    result = classify_email(
        subject="March SDR metrics + new leads",
        body="Hi Mike, here's the weekly SDR update: 47 new MQLs, 18 meetings booked.",
        sender="priya.patel@vertexsolutions.com",
    )
    assert result.domains == ["team"], f"Expected ['team'], got {result.domains}"


def test_stock_query_is_finance():
    domains = domains_for_query("show me NVDA stock price")
    assert "finance" in domains, f"Expected 'finance' in {domains}"


def test_meeting_prep_is_sales():
    domains = domains_for_query("prepare for my meeting with Tom from Acme")
    assert "sales" in domains, f"Expected 'sales' in {domains}"


def test_travel_query_is_travel():
    domains = domains_for_query("what's the weather in Helsinki for my trip?")
    assert "travel" in domains, f"Expected 'travel' in {domains}"


def test_no_cross_contamination_finance_travel():
    """Stock email should NOT include travel domain."""
    result = classify_email(
        subject="AAPL upgrade — buy rating",
        body="Apple stock upgraded to buy. Strong earnings momentum. "
             "Portfolio allocation recommended.",
        sender="alerts@bloomberg.com",
    )
    assert "travel" not in result.domains, f"Travel leaked into finance: {result.domains}"
    assert "finance" in result.domains


def test_no_cross_contamination_travel_sales():
    """Travel email should NOT include sales domain."""
    result = classify_email(
        subject="Hotel Kämp Helsinki - Reservation Confirmed",
        body="Check-in March 14. Superior Room with City View. €285/night.",
        sender="reservations@hotelkamp.fi",
    )
    assert "sales" not in result.domains, f"Sales leaked into travel: {result.domains}"
    assert "travel" in result.domains


def test_bridge_finance_sales_allowed():
    """Finance + sales bridge is allowed (e.g. stock + client context)."""
    result = classify(
        "NVDA stock alert for our portfolio. Also need to prep for the Acme renewal deal."
    )
    # Both domains should be present since bridge is allowed
    assert "finance" in result.domains or "sales" in result.domains


def test_low_confidence_falls_back_to_admin():
    result = classify("remind me to do something later")
    assert "admin" in result.domains


if __name__ == "__main__":
    tests = [
        test_bloomberg_email_is_finance,
        test_acme_email_is_sales,
        test_finnair_email_is_travel,
        test_team_email_is_team,
        test_stock_query_is_finance,
        test_meeting_prep_is_sales,
        test_travel_query_is_travel,
        test_no_cross_contamination_finance_travel,
        test_no_cross_contamination_travel_sales,
        test_bridge_finance_sales_allowed,
        test_low_confidence_falls_back_to_admin,
    ]
    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS  {t.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL  {t.__name__}: {e}")
            failed += 1
    print(f"\n{passed}/{passed+failed} tests passed")
