"""
Generated from intent: decks_delete_keeps_cards
Generated at: 2026-02-28T23:12:04Z
System version: d11cf4c
Intent hash: cf69fead570dff57
"""


def steps(harness):
    harness.click_by_text("Decks
Organize cards into decks with zones and metadata")
    harness.click_by_text("Eldrazi Ramp
commander
Big mana Eldrazi
6 cards")
    harness.click_by_text("Delete Deck")
    harness.navigate("/collection")
    harness.fill_by_placeholder("Search cards...", "Disruptor Flute")
    harness.screenshot("final_state")
