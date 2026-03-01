"""
Generated from intent: collection_orders_view
Generated at: 2026-02-28T23:09:44Z
System version: d11cf4c
Intent hash: 65c35143dd4a82f3
"""


def steps(harness):
    harness.click_by_text("Collection
Browse your card collection with search, filters, and prices")
    harness.click_by_text("View Ordered")
    harness.screenshot("final_state")
