"""
Generated from intent: binders_manage_from_card_modal
Generated at: 2026-02-28T23:05:59Z
System version: d11cf4c
Intent hash: ea0f6433f372b24d
"""


def steps(harness):
    harness.click_by_text("Collection
Browse your card collection with search, filters, and prices")
    harness.navigate("/binders")
    harness.navigate("/collection")
    harness.click_by_selector("#main > table > tbody > tr:nth-of-type(1) > td:nth-of-type(3)")
    harness.click_by_selector("#main > table > tbody > tr > td:nth-of-type(1)")
    harness.click_by_text("×")
    harness.fill_by_placeholder("Search cards...", "")
    harness.click_by_selector("#main > table > tbody > tr:nth-of-type(2) > td:nth-of-type(1)")
    harness.click_by_text("×")
    harness.click_by_selector("#main > table > tbody > tr:nth-of-type(3) > td:nth-of-type(2)")
    harness.click_by_text("×")
    harness.click_by_selector("#main > table > tbody > tr:nth-of-type(5) > td:nth-of-type(1)")
    harness.click_by_text("×")
    harness.click_by_selector("#main > table > tbody > tr:nth-of-type(6) > td:nth-of-type(1)")
    harness.select_by_label("Add to Binder ▾
Foil Collection
Test Binder
Trade Binder", "Trade Binder")
    harness.screenshot("final_state")
