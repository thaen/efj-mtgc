"""
Generated from intent: decks_manage_from_card_modal
Generated at: 2026-02-28T23:15:44Z
System version: d11cf4c
Intent hash: a7f7be630917ae17
"""


def steps(harness):
    harness.click_by_text("Collection
Browse your card collection with search, filters, and prices")
    harness.click_by_selector("#main > table > tbody > tr:nth-of-type(1) > td:nth-of-type(3)")
    harness.click_by_selector("#main > table > tbody > tr > td:nth-of-type(3) > div")
    harness.click_by_selector("#main > table > tbody > tr > td:nth-of-type(3)")
    harness.click_by_selector("#main > table > tbody > tr > td:nth-of-type(1)")
    harness.scroll("down")
    harness.scroll("down")
    harness.click_by_text("0001")
    harness.click_by_text("2")
    harness.navigate("/collection")
    harness.click_by_selector("#main > table > tbody > tr:nth-of-type(1) > td:nth-of-type(1)")
    harness.scroll("down")
    harness.click_by_text("Creature — Human Survivor")
    harness.click_by_selector("#main > table > tbody > tr:nth-of-type(20) > td:nth-of-type(3)")
    harness.click_by_selector("#main > table > tbody > tr:nth-of-type(1) > td:nth-of-type(1)")
    harness.select_by_label("Add to Deck ▾
Bolt Tribal
Test Deck", "Bolt Tribal")
    harness.screenshot("final_state")
