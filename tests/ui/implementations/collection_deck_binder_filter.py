"""
Generated from intent: collection_deck_binder_filter
Generated at: 2026-02-28T23:45:55Z
System version: d11cf4c
Intent hash: 2da833333a5e6ef5
"""


def steps(harness):
    harness.click_by_text("Filters")
    harness.scroll("down")
    harness.scroll("down")
    harness.scroll("down")
    harness.scroll("down")
    harness.navigate("/collection")
    harness.click_by_text("Filters")
    harness.navigate("/collection?container=unassigned")
    harness.click_by_text("Filters")
    harness.click_by_selector("Max")
    harness.scroll("down")
    harness.select_by_label("All Cards", "Unassigned Only")
    harness.select_by_label("All Cards", "All Cards")
    harness.screenshot("final_state")
