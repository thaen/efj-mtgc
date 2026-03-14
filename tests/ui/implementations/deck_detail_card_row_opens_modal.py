"""
Hand-written implementation for deck_detail_card_row_opens_modal.

Clicks a card row in the deck detail table to open the card modal,
verifies modal content, then closes it.
"""


def steps(harness):
    # Navigate to deck detail page
    harness.navigate("/decks/1")

    # Wait for card table to load
    harness.wait_for_text("Beast-Kin Ranger")

    # Click on the card row (click the card name text)
    harness.click_by_text("Beast-Kin Ranger")

    # Wait for the card modal to appear
    harness.wait_for_visible(".card-modal-overlay.active")

    # Verify modal shows the card name
    harness.assert_visible(".card-modal-details h2")

    # Verify modal has the full page link
    harness.assert_text_present("Full page")

    # Verify modal shows type info
    harness.assert_text_present("Creature")

    # Verify modal has price links section
    harness.assert_visible(".modal-links")

    # Screenshot the open modal
    harness.screenshot("modal_open")

    # Close the modal via the X button
    harness.click_by_selector(".card-modal-close")

    # Verify the modal is hidden
    harness.wait_for_hidden(".card-modal-overlay.active")

    harness.screenshot("final_state")
