"""
Hand-written implementation for deck_detail_rich_card_table.

Navigates to a deck detail page and verifies the card table renders
rich content: thumbnails, set icons, mana symbols, and proper columns.
"""


def steps(harness):
    # Navigate to deck detail page
    harness.navigate("/decks/1")

    # Wait for card table to load
    harness.wait_for_text("Beast-Kin Ranger")

    # Verify table header columns
    harness.assert_text_present("Name")
    harness.assert_text_present("Type")
    harness.assert_text_present("Mana")
    harness.assert_text_present("Set")
    harness.assert_text_present("Condition")
    harness.assert_text_present("Price")

    # Verify thumbnails render (card-thumb img inside the table body)
    harness.assert_visible("#card-tbody .card-thumb")

    # Verify set icons render (keyrune ss icon)
    harness.assert_visible("#card-tbody .set-cell .ss")

    # Verify mana symbols render (mana-font ms icon)
    harness.assert_visible("#card-tbody .mana-cost .ms")

    # Verify card-cell structure (name cell with thumbnail + name)
    harness.assert_visible("#card-tbody .card-cell")

    harness.screenshot("final_state")
