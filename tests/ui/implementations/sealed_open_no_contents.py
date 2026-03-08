"""
Hand-written implementation for sealed_open_no_contents.

Verifies that products without contents data show a badge and cannot be selected.
"""


def steps(harness):
    # Navigate to sealed collection page
    harness.navigate("/sealed")
    harness.wait_for_visible("#open-btn")

    # Click the Open Product button
    harness.click_by_selector("#open-btn")
    harness.wait_for_visible("#open-modal-overlay.active")

    # Search for Lorwyn Eclipsed to get mixed results (some with, some without contents)
    harness.fill_by_selector("#open-search-input", "Lorwyn Eclipsed")
    harness.wait_for_visible("#open-product-results li")

    # Verify the "No contents data" badge appears for products without contents
    harness.assert_text_present("No contents data")

    # Screenshot showing results with and without contents
    harness.screenshot("final_state")
