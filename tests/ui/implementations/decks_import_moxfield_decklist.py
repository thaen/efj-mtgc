"""
Generated from intent: decks_import_moxfield_decklist
Generated at: 2026-02-28T23:13:23Z
System version: d11cf4c
Intent hash: c14affab9a474ef1
"""


def steps(harness):
    harness.navigate("/csv-import")
    harness.navigate("/import")
    harness.navigate("/")
    harness.scroll("down")
    harness.click_by_text("Ingestor (CSV Import)
Import cards from Moxfield, Archidekt, or Deckbox CSV expo")
    harness.fill_by_placeholder("Paste CSV here (e.g. Moxfield deck export)...", "1 Scrawling Crawler (FDN) 132")
    harness.select_by_label("Auto-detect
Deck List (text)
Moxfield (CSV)
Archidekt (CSV)
Deckbox (CSV)", "Deck List (text)")
    harness.click_by_text("Parse & Resolve")
    harness.click_by_text("Add to Collection")
    harness.screenshot("final_state")
