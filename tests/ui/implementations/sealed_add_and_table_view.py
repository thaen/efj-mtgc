"""
Generated from intent: sealed_add_and_table_view
Generated at: 2026-02-28T23:25:42Z
System version: d11cf4c
Intent hash: edcdbc6766c8aa31
"""


def steps(harness):
    harness.click_by_text("Sealed Collection
Track sealed product inventory — boxes, bundles, and decks")
    harness.click_by_text("+ Add")
    harness.fill_by_placeholder("Search sealed products by name...", "Lorwyn Eclipsed")
    harness.click_by_selector("#product-results > li")
    harness.click_by_text("Add to Collection")
    harness.screenshot("final_state")
