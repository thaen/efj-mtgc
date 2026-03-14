"""
Hand-written implementation for collection_table_renders_after_shared_extraction.

Verifies the collection table view still renders rich card cells correctly
after CSS/JS extraction into shared modules.
"""


def steps(harness):
    # Navigate to collection page
    harness.navigate("/collection")

    # Wait for cards to load
    harness.wait_for_text("Beast-Kin Ranger")

    # Ensure we're in table view (click the table view button)
    harness.click_by_selector("#view-table-btn")

    # Wait for table to render
    harness.wait_for_visible(".collection-table")

    # Verify thumbnails render (card-thumb img inside the table)
    harness.assert_visible(".collection-table .card-thumb")

    # Verify set icons render (keyrune ss icon)
    harness.assert_visible(".collection-table .set-cell .ss")

    # Verify mana symbols render (mana-font ms icon, not raw text)
    harness.assert_visible(".collection-table .mana-cost .ms")

    # Verify card-cell structure exists
    harness.assert_visible(".collection-table .card-cell")

    harness.screenshot("final_state")
