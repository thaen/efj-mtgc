"""
Generated from intent: sealed_multi_order_aggregation
Generated at: 2026-02-28T23:27:35Z
System version: d11cf4c
Intent hash: 5412d14278f7036d
"""


def steps(harness):
    harness.click_by_text("Sealed Collection
Track sealed product inventory — boxes, bundles, and decks")
    harness.click_by_text("+ Add")
    harness.fill_by_placeholder("Search sealed products by name...", "Murders at Karlov Manor")
    harness.scroll("down")
    harness.click_by_selector("Search sealed products by name...")
    harness.fill_by_placeholder("Search sealed products by name...", "Karlov")
    harness.fill_by_placeholder("Search sealed products by name...", "Bloomburrow Booster Box")
    harness.click_by_selector("#product-results > li")
    harness.fill_by_selector("#add-qty", "2")
    harness.fill_by_placeholder("Total purchase price", "90")
    harness.click_by_text("Add to Collection")
    harness.click_by_text("+ Add")
    harness.fill_by_placeholder("Search sealed products by name...", "Bloomburrow Booster Box")
    harness.click_by_selector("#product-results > li")
    harness.fill_by_selector("#add-qty", "3")
    harness.fill_by_placeholder("Total purchase price", "75")
    harness.click_by_text("Add to Collection")
    harness.click_by_text("6		Bloomburrow	Booster Box	$75.00")
    harness.screenshot("final_state")
