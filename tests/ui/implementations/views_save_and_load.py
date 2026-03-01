"""
Generated from intent: views_save_and_load
Generated at: 2026-02-28T23:27:55Z
System version: d11cf4c
Intent hash: ceeb0652c3375a4a
"""


def steps(harness):
    harness.click_by_text("Collection
Browse your card collection with search, filters, and prices")
    harness.click_by_text("Filters")
    harness.select_by_label("-- None --
Modern Staples
Test View
Unassigned Cards", "Modern Staples")
    harness.screenshot("final_state")
