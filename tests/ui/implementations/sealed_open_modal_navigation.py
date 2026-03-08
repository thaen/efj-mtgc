"""
Hand-written implementation for sealed_open_modal_navigation.

Tests the modal search, preview, back navigation, and close interactions.
"""


def steps(harness):
    # Navigate to sealed collection page
    harness.navigate("/sealed")
    harness.wait_for_visible("#open-btn")

    # Open the modal
    harness.click_by_selector("#open-btn")
    harness.wait_for_visible("#open-modal-overlay.active")

    # Verify initial modal state
    harness.assert_text_present("Open Sealed Product")
    harness.assert_visible("#open-search-input")

    # Search for a product
    harness.fill_by_selector("#open-search-input", "Foundations Starter")
    harness.wait_for_visible("#open-product-results li")

    # Select a product to go to preview
    harness.click_by_text("Foundations Starter Collection")
    harness.wait_for_text("cards to add")

    # Verify preview state: title changed, search input hidden
    harness.assert_text_present("Open: Foundations Starter Collection")

    # Screenshot the preview step
    harness.screenshot("preview_step")

    # Click Back to return to search
    harness.click_by_selector("#open-back-btn")

    # Verify we're back to search: title reset, search input visible
    harness.wait_for_visible("#open-search-input")
    harness.assert_text_present("Open Sealed Product")

    # Close the modal
    harness.click_by_selector("#open-close")
    harness.wait_for_hidden("#open-modal-overlay.active")

    # Final state: modal is closed, sealed page visible
    harness.screenshot("final_state")
