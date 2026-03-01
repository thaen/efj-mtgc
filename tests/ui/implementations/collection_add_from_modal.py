"""
Generated from intent: collection_add_from_modal
Generated at: 2026-02-28T23:06:47Z
System version: d11cf4c
Intent hash: 55f1249f8ce63c70
"""


def steps(harness):
    harness.click_by_text("Collection
Browse your card collection with search, filters, and prices")
    harness.click_by_selector("#main > table > tbody > tr:nth-of-type(1) > td:nth-of-type(3)")
    harness.click_by_selector("#main > table > tbody > tr > td:nth-of-type(1)")
    harness.click_by_text("Add")
    harness.fill_by_placeholder("Price", "1.50")
    harness.fill_by_placeholder("Source", "TCGPlayer")
    harness.click_by_text("Confirm")
    harness.screenshot("final_state")
