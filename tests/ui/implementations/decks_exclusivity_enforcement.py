"""
Generated from intent: decks_exclusivity_enforcement
Generated at: 2026-02-28T23:12:39Z
System version: d11cf4c
Intent hash: 1dffed1b7dde5ebe
"""


def steps(harness):
    harness.click_by_text("Collection
Browse your card collection with search, filters, and prices")
    harness.fill_by_placeholder("Search cards...", "Scrawling Crawler")
    harness.click_by_selector("#main > table > tbody > tr:nth-of-type(2) > td:nth-of-type(3)")
    harness.click_by_selector("#main > table > tbody > tr:nth-of-type(2) > td:nth-of-type(3) > div")
    harness.click_by_selector("#main > table > tbody > tr:nth-of-type(1) > td:nth-of-type(1)")
    harness.select_by_label("Move to Binder ▾
Foil Collection
Test Binder
Trade Binder", "Trade Binder")
    harness.screenshot("final_state")
