"""
Generated from intent: edit_order_add_card
Generated at: 2026-02-28T23:16:27Z
System version: d11cf4c
Intent hash: 1f9befa8403f0015
"""


def steps(harness):
    harness.click_by_text("Collection
Browse your card collection with search, filters, and prices")
    harness.click_by_text("View Ordered")
    harness.click_by_selector("#view-orders-btn")
    harness.click_by_text("Edit")
    harness.click_by_text("+ Add Card")
    harness.fill_by_placeholder("Search for a card...", "Lightning Bolt")
    harness.fill_by_placeholder("Search for a card...", "Acrobatic")
    harness.click_by_text("Acrobatic Cheerleader
DSK #1")
    harness.screenshot("final_state")
